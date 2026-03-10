"""Lambertian shading and shadow computation."""
import math
import random
from color import Color
from vector import Vec3
from ray import Ray
from shapes import HitRecord


def shadow_factor(hit_point: Vec3, light, ctx) -> float:
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
        for obj in ctx.scene.objects:
            hit = obj.hit(shadow_ray, t_min=0.0, t_max=dist_to_light - bias)
            if hit:
                mat_obj = hit.mat_obj if hit.mat_obj is not None else obj  # CSG routing
                light_factor *= (1.0 - mat_obj.material.opacity)
                if light_factor < 1e-4:
                    break  # fully shadowed — no need to continue

        total += light_factor

    return total / n


def shade(hit: HitRecord, obj_color: Color, ctx) -> Color:
    """Compute shaded surface color at a hit point (Lambertian + soft shadows)."""
    ambient = 0.15
    total = ambient

    for light in ctx.scene.lights:
        light_dir = (light.position - hit.point).normalize()
        diffuse = max(0.0, hit.normal.dot(light_dir))
        if diffuse > 0.0:
            shadow = shadow_factor(hit.point, light, ctx)
            total += diffuse * shadow

    total = min(total, 1.0)
    return (obj_color * total).clamp()
