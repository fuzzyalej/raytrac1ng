"""Renderer — casts VisionRays through each pixel and computes RGB shading."""

import math
import random
import concurrent.futures
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

from color import Color
from ray import Ray, ReflectionRay, RefractionRay
from scene import Scene
from shapes import HitRecord, Plane
from vector import Vec3
from bvh import BVH
from .shading import shade, shadow_factor
from .physics import refract, schlick

MAX_DEPTH = 8  # maximum transparency recursion depth
BG_COLOR = Color(0.05, 0.05, 0.08)  # very dark blue-gray background


@dataclass
class RenderContext:
    scene:     Scene
    bvh:       object  # BVH | None
    unbounded: list    # Plane instances


def _find_hit(ray, ctx):
    """Return (closest_hit, closest_obj) or (None, None) if no intersection.

    Uses the BVH (stored in ctx.bvh) for bounded shapes, and tests
    infinite shapes (Planes) linearly. Falls back to a linear scan if the BVH
    has not been set up (e.g. in unit tests that call _trace directly).

    bvh and unbounded are always set and cleared together by render(); they
    are treated atomically — if bvh is None then unbounded is also absent,
    so the fallback linear scan covers all objects.
    """
    bvh = ctx.bvh if ctx is not None else None
    if bvh is None:
        # Fallback: linear scan (used when render() has not been called,
        # e.g. in unit tests that drive _trace directly).
        scene = ctx.scene if ctx is not None else None
        if scene is None:
            return None, None
        closest_hit = None
        closest_obj = None
        closest_t   = float('inf')
        for obj in scene.objects:
            hit = obj.hit(ray, t_max=closest_t)
            if hit and hit.t < closest_t:
                closest_t   = hit.t
                closest_hit = hit
                closest_obj = obj
        return closest_hit, closest_obj

    # BVH path: bvh and unbounded are always set together by render()
    unbounded = ctx.unbounded
    hit, obj = bvh.hit(ray, 0.001, float('inf'))
    t_max = hit.t if hit else float('inf')
    for plane in unbounded:
        plane_hit = plane.hit(ray, t_max=t_max)
        if plane_hit:
            hit, obj, t_max = plane_hit, plane, plane_hit.t
    return hit, obj


def _trace(ray, ctx, depth: int) -> Color:
    """Trace a ray into the scene and return the resulting Color.

    Handles reflections and transparency; depth counts down from MAX_DEPTH.
    At depth 0 both reflection and transparency recursion are skipped.
    """
    hit, obj = _find_hit(ray, ctx)

    if hit is None:
        return BG_COLOR

    mat_obj = hit.mat_obj if hit.mat_obj is not None else obj  # CSG material routing
    mat = mat_obj.material  # Material dataclass

    surface_color = shade(hit, mat.color, ctx) if mat.ior == 1.0 else Color(0.0, 0.0, 0.0)

    # Reflection — applied before opacity blend (ior > 1.0 objects use Fresnel instead)
    if mat.reflect > 0.0 and mat.ior == 1.0 and depth > 0:
        D = ray.direction
        N = hit.normal
        reflect_dir = D - N * (2.0 * D.dot(N))
        reflect_origin = hit.point + N * 0.001
        reflect_ray = ReflectionRay(reflect_origin, reflect_dir)
        reflected_color = _trace(reflect_ray, ctx, depth - 1)
        surface_color = (surface_color * (1.0 - mat.reflect)
                         + reflected_color * mat.reflect).clamp()

    # Opacity / Refraction
    if mat.opacity >= 1.0 or depth <= 0:
        return surface_color

    if mat.ior == 1.0:
        # Naive straight-through: backward-compatible for existing scenes
        continuation = Ray(hit.point + ray.direction * 0.002, ray.direction)
        behind_color = _trace(continuation, ctx, depth - 1)
        blended = surface_color * mat.opacity + behind_color * (1.0 - mat.opacity)
        return blended.clamp()

    # Physical refraction path (Snell's law + TIR + Schlick Fresnel)
    D = ray.direction
    N = hit.normal

    # Determine direction: entering (D·N < 0) or exiting (D·N > 0)
    if D.dot(N) < 0.0:
        n1, n2 = 1.0, mat.ior
        outward_N = N
    else:
        n1, n2 = mat.ior, 1.0
        outward_N = N * -1.0

    cos_i = -D.dot(outward_N)
    refract_dir = refract(D, outward_N, n1, n2)

    if refract_dir is None:
        # Total internal reflection — pure mirror bounce
        tir_dir = D - outward_N * (2.0 * D.dot(outward_N))
        tir_ray = ReflectionRay(hit.point + outward_N * 0.001, tir_dir)
        return _trace(tir_ray, ctx, depth - 1)

    fresnel = schlick(cos_i, n1, n2)

    # Reflection component (Fresnel-weighted)
    refl_dir = D - outward_N * (2.0 * D.dot(outward_N))
    refl_ray = ReflectionRay(hit.point + outward_N * 0.001, refl_dir)
    refl_color = _trace(refl_ray, ctx, depth - 1)

    # Refraction component (bias origin INTO the medium)
    refr_ray = RefractionRay(hit.point - outward_N * 0.001, refract_dir)
    refr_color = _trace(refr_ray, ctx, depth - 1)

    return (refl_color * fresnel + refr_color * (1.0 - fresnel)).clamp()


def _render_row_chunk(args: tuple) -> list:
    """Render a contiguous band of rows; called in worker processes.

    args: (scene, width, height, y_start, y_end, aa_samples)
    Returns a flat list of Color values in row-major order.
    """
    scene, width, height, y_start, y_end, aa_samples = args
    # Reconstruct ctx locally (since scene._bvh / scene._unbounded are not pickled)
    _bounded   = [o for o in scene.objects if not isinstance(o, Plane)]
    _unbounded = [o for o in scene.objects if     isinstance(o, Plane)]
    bvh = BVH.build(_bounded)
    ctx = RenderContext(scene=scene, bvh=bvh, unbounded=_unbounded)

    pixels = []
    for y in range(y_start, y_end):
        for x in range(width):
            if aa_samples <= 1:
                vision_ray = scene.camera.get_vision_ray(x, y, width, height)
                pixels.append(_trace(vision_ray, ctx, MAX_DEPTH))
            else:
                r_acc = g_acc = b_acc = 0.0
                for _ in range(aa_samples):
                    dx = random.random()
                    dy = random.random()
                    vision_ray = scene.camera.get_vision_ray(
                        x + dx - 0.5, y + dy - 0.5, width, height
                    )
                    c = _trace(vision_ray, ctx, MAX_DEPTH)
                    r_acc += c.r
                    g_acc += c.g
                    b_acc += c.b
                pixels.append(
                    Color(r_acc / aa_samples, g_acc / aa_samples, b_acc / aa_samples).clamp()
                )
    return pixels


def render(scene: Scene, width: int, height: int,
           aa_samples: int = 0, workers: int = 1) -> list:
    """Render the scene and return a flat list of Color pixels.

    Pixel order is row-major: [row0_col0, row0_col1, ..., rowN_colM].
    aa_samples: 0 or 1 = single centred ray (no AA); N >= 2 = N jittered rays averaged.
    workers: 1 = single-threaded (default); N > 1 = N parallel worker processes.
    """
    if workers < 0:
        raise ValueError(f"workers must be >= 0, got {workers}")

    # Build BVH once; create a RenderContext to pass around.
    # No scene mutation — ctx is a local dataclass.
    _bounded   = [o for o in scene.objects if not isinstance(o, Plane)]
    _unbounded = [o for o in scene.objects if     isinstance(o, Plane)]
    bvh = BVH.build(_bounded)
    ctx = RenderContext(scene=scene, bvh=bvh, unbounded=_unbounded)
    print(f"  BVH: {len(_bounded)} bounded + {len(_unbounded)} unbounded object(s)")

    if workers <= 1:
        # ---- Single-process path (unchanged behaviour) ------------------
        pixels = []
        total_pixels = width * height
        for y in range(height):
            if y % 50 == 0:
                pct = (y * width) / total_pixels * 100
                print(f"  Rendering… {pct:5.1f}%", flush=True)
            pixels.extend(_render_row_chunk((scene, width, height, y, y + 1, aa_samples)))
        print("  Rendering… 100.0%")
        return pixels

    # ---- Multi-process path ---------------------------------------------
    chunk_rows = max(1, math.ceil(height / (workers * 4)))  # ~4 chunks per worker
    chunks = [
        (scene, width, height, y, min(y + chunk_rows, height), aa_samples)
        for y in range(0, height, chunk_rows)
    ]
    total = len(chunks)
    all_pixels = []

    print(f"  Rendering… 0.0% (using {workers} workers)", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for done, chunk_pixels in enumerate(executor.map(_render_row_chunk, chunks), 1):
            all_pixels.extend(chunk_pixels)
            print(f"  Rendering… {done / total * 100:5.1f}%", flush=True)

    return all_pixels
