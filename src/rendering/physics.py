"""Snell's law refraction and Schlick Fresnel approximation."""
import math
from vector import Vec3


def refract(direction: Vec3, normal: Vec3, n1: float, n2: float):
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


def schlick(cos_theta: float, n1: float, n2: float) -> float:
    """Schlick approximation for Fresnel reflectance at a dielectric interface.

    cos_theta is the cosine of the angle of incidence (clamped to [0, 1]).
    """
    cos_theta = max(0.0, min(1.0, cos_theta))
    r0 = ((n1 - n2) / (n1 + n2)) ** 2
    return r0 + (1.0 - r0) * (1.0 - cos_theta) ** 5
