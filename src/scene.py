"""Scene graph: Camera, light hierarchy, and Scene container."""

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from color import Color, color_from_kelvin
from vector import Vec3
from ray import VisionRay


# ---------------------------------------------------------------------------
# Camera
# ---------------------------------------------------------------------------

class Camera:
    """Pinhole camera that generates VisionRays for each pixel."""

    def __init__(self, location: Vec3, look_at: Vec3, fov: float = 60.0):
        self.location = location
        self.look_at = look_at
        self.fov = fov

        self.forward = (look_at - location).normalize()
        world_up = Vec3(0, 1, 0)
        if abs(self.forward.dot(world_up)) > 0.999:
            world_up = Vec3(0, 0, 1)
        self.right = self.forward.cross(world_up).normalize()
        self.up = self.right.cross(self.forward).normalize()

    def get_vision_ray(self, px: float, py: float,
                       img_width: int, img_height: int) -> VisionRay:
        aspect = img_width / img_height
        half_height = math.tan(math.radians(self.fov / 2))
        half_width = aspect * half_height
        u = (2 * (px + 0.5) / img_width - 1) * half_width
        v = (1 - 2 * (py + 0.5) / img_height) * half_height
        direction = self.forward + self.right * u + self.up * v
        return VisionRay(self.location, direction)


# ---------------------------------------------------------------------------
# Light base class
# ---------------------------------------------------------------------------

class LightBase(ABC):
    """Abstract base for all light types.

    Shared parameters: color, intensity, color_temperature, visible, samples.
    """

    def __init__(self, color=None, intensity=1.0, color_temperature=None,
                 visible=False, samples=16):
        self.color = color if color is not None else Color(1.0, 1.0, 1.0)
        self.intensity = float(intensity)
        self.color_temperature = color_temperature  # float (Kelvin) or None
        self.visible = bool(visible)
        self.samples = max(1, int(samples))

    def effective_color(self) -> Color:
        """Return the light's emission color: kelvin_color * color * intensity."""
        base = (color_from_kelvin(self.color_temperature)
                if self.color_temperature is not None
                else Color(1.0, 1.0, 1.0))
        return (base * self.color * self.intensity).clamp()

    @abstractmethod
    def sample_point(self) -> Vec3:
        """Return a random point on (or inside) the light surface."""
        ...

    @property
    @abstractmethod
    def position(self) -> Vec3:
        """Center/position used for diffuse direction calculation."""
        ...


# ---------------------------------------------------------------------------
# Concrete light types
# ---------------------------------------------------------------------------

class PointLight(LightBase):
    """Infinitesimal point light. Always fires exactly one shadow ray."""

    def __init__(self, position: Vec3, **kwargs):
        super().__init__(**kwargs)
        self._position = position
        self.samples = 1  # point lights never need multiple samples

    @property
    def position(self) -> Vec3:
        return self._position

    def sample_point(self) -> Vec3:
        return self._position


class SphereLight(LightBase):
    """Spherical area light (uniform sampling inside the sphere)."""

    def __init__(self, position: Vec3, radius: float, **kwargs):
        super().__init__(**kwargs)
        self._position = position
        self.radius = float(radius)

    @property
    def position(self) -> Vec3:
        return self._position

    def sample_point(self) -> Vec3:
        while True:
            dx = random.uniform(-1, 1)
            dy = random.uniform(-1, 1)
            dz = random.uniform(-1, 1)
            if dx * dx + dy * dy + dz * dz <= 1.0:
                break
        return Vec3(
            self._position.x + dx * self.radius,
            self._position.y + dy * self.radius,
            self._position.z + dz * self.radius,
        )


class DiskLight(LightBase):
    """Flat circular area light.

    Emits from the side facing `normal` (or both sides if two_sided=True).
    """

    def __init__(self, position: Vec3, normal: Vec3, radius: float,
                 two_sided: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._position = position
        self.normal = normal.normalize()
        self.radius = float(radius)
        self.two_sided = bool(two_sided)

        # Build orthonormal frame in the disk plane for uniform sampling
        arb = (Vec3(0, 0, 1)
               if abs(self.normal.dot(Vec3(0, 1, 0))) > 0.999
               else Vec3(0, 1, 0))
        self._u = self.normal.cross(arb).normalize()
        self._v = self.normal.cross(self._u).normalize()

    @property
    def position(self) -> Vec3:
        return self._position

    def sample_point(self) -> Vec3:
        while True:
            u = random.uniform(-1, 1)
            v = random.uniform(-1, 1)
            if u * u + v * v <= 1.0:
                break
        return (self._position
                + self._u * (u * self.radius)
                + self._v * (v * self.radius))

    def hit(self, ray, t_min: float = 0.001, t_max: float = float('inf')):
        """Return a HitRecord if ray hits the disk face (respects two_sided)."""
        # Deferred import to avoid circular dependency with shapes
        from shapes.primitives import HitRecord
        denom = ray.direction.dot(self.normal)
        if abs(denom) < 1e-8:          # parallel ray — no intersection
            return None
        if not self.two_sided and denom >= 0:   # back face, one-sided
            return None
        t = (self._position - ray.origin).dot(self.normal) / denom
        if t < t_min or t > t_max:
            return None
        point = ray.point_at(t)
        if (point - self._position).length() > self.radius:
            return None
        n = self.normal if denom < 0 else self.normal * -1.0
        return HitRecord(t=t, point=point, normal=n)


class RectLight(LightBase):
    """Parallelogram area light defined by a corner and two edge vectors.

    Normal = cross(edge1, edge2).normalize().
    Emits from the normal side only unless two_sided=True.
    """

    def __init__(self, corner: Vec3, edge1: Vec3, edge2: Vec3,
                 two_sided: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.corner = corner
        self.edge1 = edge1
        self.edge2 = edge2
        self.two_sided = bool(two_sided)
        self._normal = edge1.cross(edge2).normalize()
        # Precompute for hit() bounds check
        self._e1_dot = edge1.dot(edge1)
        self._e2_dot = edge2.dot(edge2)

    @property
    def normal(self) -> Vec3:
        return self._normal

    @property
    def position(self) -> Vec3:
        """Center of the rectangle."""
        return self.corner + self.edge1 * 0.5 + self.edge2 * 0.5

    def sample_point(self) -> Vec3:
        u = random.random()
        v = random.random()
        return self.corner + self.edge1 * u + self.edge2 * v

    def hit(self, ray, t_min: float = 0.001, t_max: float = float('inf')):
        """Return a HitRecord if ray hits the parallelogram (respects two_sided)."""
        # Deferred import to avoid circular dependency with shapes
        from shapes.primitives import HitRecord
        denom = ray.direction.dot(self._normal)
        if abs(denom) < 1e-8:          # parallel ray — no intersection
            return None
        if not self.two_sided and denom >= 0:   # back face, one-sided
            return None
        t = (self.corner - ray.origin).dot(self._normal) / denom
        if t < t_min or t > t_max:
            return None
        point = ray.point_at(t)
        d = point - self.corner
        u = d.dot(self.edge1) / self._e1_dot
        v = d.dot(self.edge2) / self._e2_dot
        if not (0.0 <= u <= 1.0 and 0.0 <= v <= 1.0):
            return None
        n = self._normal if denom < 0 else self._normal * -1.0
        return HitRecord(t=t, point=point, normal=n)


# ---------------------------------------------------------------------------
# Backwards-compatible Light class
# ---------------------------------------------------------------------------

class Light(LightBase):
    """Legacy light: radius=0 -> point light; radius>0 -> sphere area light.

    Kept for full backwards compatibility. New code should use
    PointLight or SphereLight directly.
    """

    def __init__(self, position: Vec3, radius: float = 0.0,
                 samples: int = 16, **kwargs):
        super().__init__(samples=samples, **kwargs)
        self._position = position
        self.radius = float(radius)

    @property
    def position(self) -> Vec3:
        return self._position

    def sample_point(self) -> Vec3:
        if self.radius == 0.0:
            return self._position
        while True:
            dx = random.uniform(-1, 1)
            dy = random.uniform(-1, 1)
            dz = random.uniform(-1, 1)
            if dx * dx + dy * dy + dz * dz <= 1.0:
                break
        return Vec3(
            self._position.x + dx * self.radius,
            self._position.y + dy * self.radius,
            self._position.z + dz * self.radius,
        )


# ---------------------------------------------------------------------------
# Scene container
# ---------------------------------------------------------------------------

@dataclass
class Scene:
    camera: Camera = None
    lights: list = field(default_factory=list)
    objects: list = field(default_factory=list)

    @property
    def visible_lights(self) -> list:
        """Lights with visible=True -- tested by primary rays."""
        return [l for l in self.lights if l.visible]
