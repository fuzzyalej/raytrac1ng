"""Renderer — casts VisionRays through each pixel and computes RGB shading."""

import math
import random
from concurrent.futures import ProcessPoolExecutor
from color import Color
from ray import Ray, ReflectionRay, RefractionRay
from scene import Scene
from shapes import HitRecord
from vector import Vec3
from bvh import BVH
from shapes import Plane

MAX_DEPTH = 8  # maximum transparency recursion depth
BG_COLOR = Color(0.05, 0.05, 0.08)  # very dark blue-gray background


def _refract(direction: Vec3, normal: Vec3, n1: float, n2: float):
    """Compute refracted direction using Snell's law.

    direction and normal must be normalized. normal must point into the same
    hemisphere as the incoming ray (i.e. dot(direction, normal) < 0, so that
    cos_i = -dot(direction, normal) > 0). The caller is responsible for flipping
    the normal when the ray is exiting a medium.
    Returns the refracted direction Vec3, or None if total internal reflection occurs.
    The returned direction is unit-length when inputs are unit-length.
    """
    cos_i = -direction.dot(normal)
    eta = n1 / n2
    sin2_t = eta * eta * (1.0 - cos_i * cos_i)
    if sin2_t > 1.0:
        return None  # Total internal reflection
    cos_t = math.sqrt(1.0 - sin2_t)
    return direction * eta + normal * (eta * cos_i - cos_t)


def _schlick(cos_theta: float, n1: float, n2: float) -> float:
    """Schlick approximation for Fresnel reflectance at a dielectric interface.

    cos_theta is the cosine of the angle of incidence (clamped to [0, 1]).
    """
    cos_theta = max(0.0, min(1.0, cos_theta))
    r0 = ((n1 - n2) / (n1 + n2)) ** 2
    return r0 + (1.0 - r0) * (1.0 - cos_theta) ** 5


def _shadow_factor(hit_point: Vec3, light, scene: Scene) -> float:
    """Return the fraction of light reaching hit_point from light (0.0=fully shadowed, 1.0=fully lit).

    For a point light (light.radius == 0), fires one shadow ray to light.position.
    For an area light (light.radius > 0), fires light.samples rays to random points
    on the light sphere using rejection sampling, then averages the results.

    Transparent blockers attenuate the factor by (1 - opacity) instead of fully
    blocking the ray. Multiple transparent blockers multiply their attenuation.
    """
    n = light.samples if light.radius > 0.0 else 1
    total = 0.0

    for _ in range(n):
        # Pick a point on the light sphere (or the center for point lights)
        if light.radius > 0.0:
            # Rejection sampling: pick random point inside unit sphere, scale by radius
            while True:
                dx = random.uniform(-1, 1)
                dy = random.uniform(-1, 1)
                dz = random.uniform(-1, 1)
                if dx*dx + dy*dy + dz*dz <= 1.0:
                    break
            sample = Vec3(
                light.position.x + dx * light.radius,
                light.position.y + dy * light.radius,
                light.position.z + dz * light.radius,
            )
        else:
            sample = light.position

        to_light = sample - hit_point
        dist_to_light = to_light.length()
        if dist_to_light < 1e-6:
            continue
        bias = 0.001
        light_dir = to_light / dist_to_light
        shadow_ray = Ray(hit_point + light_dir * bias, light_dir)

        # NOTE: shadow rays use a linear scan rather than the BVH.
        # For most scenes (point lights, moderate object counts) this is fast enough.
        # Area lights with thousands of objects would benefit from BVH shadow traversal.
        # Walk all objects along the shadow ray up to the light
        light_factor = 1.0
        for obj in scene.objects:
            hit = obj.hit(shadow_ray, t_min=0.0, t_max=dist_to_light - bias)
            if hit:
                light_factor *= (1.0 - obj.opacity)
                if light_factor < 1e-4:
                    break  # fully shadowed — no need to continue

        total += light_factor

    return total / n


def _shade(hit: HitRecord, obj_color: Color, scene: Scene) -> Color:
    """Compute shaded surface color at a hit point (Lambertian + soft shadows)."""
    ambient = 0.15
    total = ambient

    for light in scene.lights:
        light_dir = (light.position - hit.point).normalize()
        diffuse = max(0.0, hit.normal.dot(light_dir))
        if diffuse > 0.0:
            shadow = _shadow_factor(hit.point, light, scene)
            total += diffuse * shadow

    total = min(total, 1.0)
    return (obj_color * total).clamp()


def _find_hit(ray, scene: Scene):
    """Return (closest_hit, closest_obj) or (None, None) if no intersection.

    Uses the BVH (stored in scene._bvh) for bounded shapes, and tests
    infinite shapes (Planes) linearly. Falls back to a linear scan if the BVH
    has not been set up (e.g. in unit tests that call _trace directly).

    _bvh and _unbounded are always set and cleared together by render(); they
    are treated atomically — if _bvh is absent then _unbounded is also absent,
    so the fallback linear scan covers all objects.
    """
    bvh = getattr(scene, '_bvh', None)
    if bvh is None:
        # Fallback: linear scan (used when render() has not been called,
        # e.g. in unit tests that drive _trace directly).
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

    # BVH path: _bvh and _unbounded are always set together by render()
    unbounded = scene._unbounded
    hit, obj = bvh.hit(ray, 0.001, float('inf'))
    t_max = hit.t if hit else float('inf')
    for plane in unbounded:
        plane_hit = plane.hit(ray, t_max=t_max)
        if plane_hit:
            hit, obj, t_max = plane_hit, plane, plane_hit.t
    return hit, obj


def _trace(ray, scene: Scene, depth: int) -> Color:
    """Trace a ray into the scene and return the resulting Color.

    Handles reflections and transparency; depth counts down from MAX_DEPTH.
    At depth 0 both reflection and transparency recursion are skipped.
    """
    hit, obj = _find_hit(ray, scene)

    if hit is None:
        return BG_COLOR

    surface_color = _shade(hit, obj.color, scene) if obj.ior == 1.0 else Color(0.0, 0.0, 0.0)

    # Reflection — applied before opacity blend (ior > 1.0 objects use Fresnel instead)
    if obj.reflect > 0.0 and obj.ior == 1.0 and depth > 0:
        D = ray.direction
        N = hit.normal
        reflect_dir = D - N * (2.0 * D.dot(N))
        reflect_origin = hit.point + N * 0.001
        reflect_ray = ReflectionRay(reflect_origin, reflect_dir)
        reflected_color = _trace(reflect_ray, scene, depth - 1)
        surface_color = (surface_color * (1.0 - obj.reflect)
                         + reflected_color * obj.reflect).clamp()

    # Opacity / Refraction
    if obj.opacity >= 1.0 or depth <= 0:
        return surface_color

    if obj.ior == 1.0:
        # Naive straight-through: backward-compatible for existing scenes
        continuation = Ray(hit.point + ray.direction * 0.002, ray.direction)
        behind_color = _trace(continuation, scene, depth - 1)
        blended = surface_color * obj.opacity + behind_color * (1.0 - obj.opacity)
        return blended.clamp()

    # Physical refraction path (Snell's law + TIR + Schlick Fresnel)
    D = ray.direction
    N = hit.normal

    # Determine direction: entering (D·N < 0) or exiting (D·N > 0)
    if D.dot(N) < 0.0:
        n1, n2 = 1.0, obj.ior
        outward_N = N
    else:
        n1, n2 = obj.ior, 1.0
        outward_N = N * -1.0

    cos_i = -D.dot(outward_N)
    refract_dir = _refract(D, outward_N, n1, n2)

    if refract_dir is None:
        # Total internal reflection — pure mirror bounce
        tir_dir = D - outward_N * (2.0 * D.dot(outward_N))
        tir_ray = ReflectionRay(hit.point + outward_N * 0.001, tir_dir)
        return _trace(tir_ray, scene, depth - 1)

    fresnel = _schlick(cos_i, n1, n2)

    # Reflection component (Fresnel-weighted)
    refl_dir = D - outward_N * (2.0 * D.dot(outward_N))
    refl_ray = ReflectionRay(hit.point + outward_N * 0.001, refl_dir)
    refl_color = _trace(refl_ray, scene, depth - 1)

    # Refraction component (bias origin INTO the medium)
    refr_ray = RefractionRay(hit.point - outward_N * 0.001, refract_dir)
    refr_color = _trace(refr_ray, scene, depth - 1)

    return (refl_color * fresnel + refr_color * (1.0 - fresnel)).clamp()


def _render_row_chunk(args: tuple) -> list[Color]:
    """Render a contiguous band of rows; called in worker processes.

    args: (scene, width, height, y_start, y_end, aa_samples)
    Returns a flat list of Color values in row-major order.
    """
    scene, width, height, y_start, y_end, aa_samples = args
    pixels = []
    for y in range(y_start, y_end):
        for x in range(width):
            if aa_samples <= 1:
                vision_ray = scene.camera.get_vision_ray(x, y, width, height)
                pixels.append(_trace(vision_ray, scene, MAX_DEPTH))
            else:
                r_acc = g_acc = b_acc = 0.0
                for _ in range(aa_samples):
                    dx = random.random()
                    dy = random.random()
                    vision_ray = scene.camera.get_vision_ray(
                        x + dx - 0.5, y + dy - 0.5, width, height
                    )
                    c = _trace(vision_ray, scene, MAX_DEPTH)
                    r_acc += c.r
                    g_acc += c.g
                    b_acc += c.b
                pixels.append(
                    Color(r_acc / aa_samples, g_acc / aa_samples, b_acc / aa_samples).clamp()
                )
    return pixels


def render(scene: Scene, width: int, height: int,
           aa_samples: int = 0, workers: int = 1) -> list[Color]:
    """Render the scene and return a flat list of Color pixels.

    Pixel order is row-major: [row0_col0, row0_col1, ..., rowN_colM].
    aa_samples: 0 or 1 = single centred ray (no AA); N >= 2 = N jittered rays averaged.
    workers: 1 = single-threaded (default); N > 1 = N parallel worker processes.
    """
    if workers < 0:
        raise ValueError(f"workers must be >= 0, got {workers}")

    # Build BVH once; attach to scene so both single- and multi-process paths
    # can access it via _find_hit. Cleaned up in the finally block below.
    _bounded   = [o for o in scene.objects if not isinstance(o, Plane)]
    _unbounded = [o for o in scene.objects if     isinstance(o, Plane)]
    scene._bvh       = BVH.build(_bounded)
    scene._unbounded = _unbounded
    print(f"  BVH: {len(_bounded)} bounded + {len(_unbounded)} unbounded object(s)")
    try:
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
        all_pixels: list[Color] = []

        print(f"  Rendering… 0.0% (using {workers} workers)", flush=True)
        with ProcessPoolExecutor(max_workers=workers) as executor:
            for done, chunk_pixels in enumerate(executor.map(_render_row_chunk, chunks), 1):
                all_pixels.extend(chunk_pixels)
                print(f"  Rendering… {done / total * 100:5.1f}%", flush=True)

        return all_pixels
    finally:
        # Always clean up so stale BVH is not left on the scene object
        del scene._bvh
        del scene._unbounded
