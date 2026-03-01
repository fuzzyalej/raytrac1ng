"""Scene graph: Camera, Light, and the Scene container."""

import math
from dataclasses import dataclass, field

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

        # Build an orthonormal basis (right, up, forward)
        self.forward = (look_at - location).normalize()
        world_up = Vec3(0, 1, 0)

        # Handle degenerate case where forward ≈ world_up
        if abs(self.forward.dot(world_up)) > 0.999:
            world_up = Vec3(0, 0, 1)

        self.right = self.forward.cross(world_up).normalize()
        self.up = self.right.cross(self.forward).normalize()

    def get_vision_ray(self, px: float, py: float,
                       img_width: int, img_height: int) -> VisionRay:
        """Return a VisionRay for pixel coordinates (px, py).

        px, py are in [0, width) and [0, height) respectively.
        """
        aspect = img_width / img_height
        half_height = math.tan(math.radians(self.fov / 2))
        half_width = aspect * half_height

        # Map pixel to normalized coordinates [-1, 1]
        u = (2 * (px + 0.5) / img_width - 1) * half_width
        v = (1 - 2 * (py + 0.5) / img_height) * half_height

        direction = self.forward + self.right * u + self.up * v
        return VisionRay(self.location, direction)


# ---------------------------------------------------------------------------
# Light
# ---------------------------------------------------------------------------

class Light:
    def __init__(self, position: Vec3, radius: float = 0.0, samples: int = 16):
        self.position = position
        self.radius = max(0.0, float(radius))
        self.samples = max(1, int(samples))


# ---------------------------------------------------------------------------
# Scene container
# ---------------------------------------------------------------------------

@dataclass
class Scene:
    camera: Camera = None
    lights: list = field(default_factory=list)
    objects: list = field(default_factory=list)
