"""Ray types for the raytracer.

VisionRay — cast from the camera through each pixel to determine what is visible.
ReflectionRay — mirror reflection ray.
RefractionRay — Snell's law refraction ray through a dielectric.
"""

from vector import Vec3


class Ray:
    """Base ray: an origin and a direction."""

    __slots__ = ('origin', 'direction')

    def __init__(self, origin: Vec3, direction: Vec3):
        self.origin = origin
        self.direction = direction.normalize()

    def point_at(self, t: float) -> Vec3:
        """Return the point along the ray at parameter t."""
        return self.origin + self.direction * t


class VisionRay(Ray):
    """A ray cast from the camera through a pixel to see the scene.

    Distinct from future shadow rays, reflection rays, etc.
    """
    pass


class ReflectionRay(Ray):
    """A ray cast from a hit point in the mirror-reflected direction.

    Direction: D - 2 * dot(D, N) * N  where D is the incoming direction, N is the surface normal.
    The reflected direction is computed in the renderer before constructing this ray.
    """
    pass


class RefractionRay(Ray):
    """A ray cast from a hit point in the Snell's-law refracted direction.

    Direction computed by _refract() in renderer.py using Snell's law.
    The origin is biased slightly into the refracting medium to avoid self-intersection.
    """
    pass
