"""Lambertian shading and shadow computation."""
import random
from color import Color
from ray import Ray
from shapes import HitRecord


def _light_facing(light, hit_point) -> bool:
    """Return True if hit_point is on the emitting side of a directional light.

    DiskLight and RectLight with two_sided=False only illuminate points on
    their front face (same side as the light normal). All other light types
    (PointLight, SphereLight, Light) are omnidirectional — always return True.
    """
    if getattr(light, 'two_sided', True):
        return True
    normal = getattr(light, 'normal', None)
    if normal is None:
        return True
    # Front face: hit_point is on the same side as the light's outward normal
    return (hit_point - light.position).dot(normal) > 0.0


def shadow_factor(hit_point, light, ctx) -> float:
    """Return the fraction of light reaching hit_point (0.0=shadowed, 1.0=lit).

    Fires light.samples shadow rays, each to a point returned by
    light.sample_point(). One-sided DiskLight/RectLight: hit points behind
    the emitting face always receive 0. Transparent blockers attenuate by
    (1 - opacity).
    """
    if not _light_facing(light, hit_point):
        return 0.0

    n = light.samples
    total = 0.0

    for _ in range(n):
        sample = light.sample_point()

        to_light = sample - hit_point
        dist_to_light = to_light.length()
        if dist_to_light < 1e-6:
            continue

        bias = 0.001
        light_dir = to_light / dist_to_light
        shadow_ray = Ray(hit_point + light_dir * bias, light_dir)

        light_factor = 1.0
        for obj in ctx.scene.objects:
            hit = obj.hit(shadow_ray, t_min=0.0, t_max=dist_to_light - bias)
            if hit:
                mat_obj = hit.mat_obj if hit.mat_obj is not None else obj
                light_factor *= (1.0 - mat_obj.material.opacity)
                if light_factor < 1e-4:
                    break

        total += light_factor

    return total / n


def shade(hit: HitRecord, obj_color: Color, ctx) -> Color:
    """Compute shaded surface color (Lambertian + colored lights + soft shadows)."""
    ambient = 0.15
    result = obj_color * ambient

    for light in ctx.scene.lights:
        light_dir = (light.position - hit.point).normalize()
        diffuse = max(0.0, hit.normal.dot(light_dir))
        if diffuse > 0.0:
            shadow = shadow_factor(hit.point, light, ctx)
            if shadow > 0.0:
                contribution = light.effective_color() * (diffuse * shadow)
                result = result + obj_color * contribution

    return result.clamp()
