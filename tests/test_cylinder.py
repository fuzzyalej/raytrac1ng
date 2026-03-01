"""Tests for the Cylinder primitive (capped, arbitrary axis)."""
import pytest
from shapes import Cylinder
from vector import Vec3
from ray import VisionRay
from color import Color


def make_ray(ox, oy, oz, dx, dy, dz):
    return VisionRay(Vec3(ox, oy, oz), Vec3(dx, dy, dz))


def test_cylinder_hit_curved_surface():
    """Horizontal ray hits the curved side of an upright cylinder."""
    cyl = Cylinder(Vec3(0, 0, 0), Vec3(0, 2, 0), radius=1.0)
    ray = make_ray(3, 1, 0, -1, 0, 0)
    hit = cyl.hit(ray)
    assert hit is not None
    assert abs(hit.t - 2.0) < 1e-6      # hits at x=1
    assert abs(hit.normal.x - 1.0) < 1e-6
    assert abs(hit.normal.y) < 1e-6


def test_cylinder_miss_above_top():
    """Ray at height above the top cap misses."""
    cyl = Cylinder(Vec3(0, 0, 0), Vec3(0, 2, 0), radius=1.0)
    ray = make_ray(3, 5, 0, -1, 0, 0)   # y=5 > height=2
    assert cyl.hit(ray) is None


def test_cylinder_hit_bottom_cap():
    """Ray from below hits the bottom cap; outward normal points down."""
    cyl = Cylinder(Vec3(0, 0, 0), Vec3(0, 2, 0), radius=1.0)
    ray = make_ray(0, -5, 0, 0, 1, 0)
    hit = cyl.hit(ray)
    assert hit is not None
    assert abs(hit.t - 5.0) < 1e-6
    assert abs(hit.normal.y - (-1.0)) < 1e-6


def test_cylinder_hit_top_cap():
    """Ray from above hits the top cap; outward normal points up."""
    cyl = Cylinder(Vec3(0, 0, 0), Vec3(0, 2, 0), radius=1.0)
    ray = make_ray(0, 5, 0, 0, -1, 0)
    hit = cyl.hit(ray)
    assert hit is not None
    assert abs(hit.t - 3.0) < 1e-6
    assert abs(hit.normal.y - 1.0) < 1e-6


def test_cylinder_miss_cap_outside_radius():
    """Ray aimed at cap plane but outside the disk radius misses."""
    cyl = Cylinder(Vec3(0, 0, 0), Vec3(0, 2, 0), radius=1.0)
    ray = make_ray(2, 5, 0, 0, -1, 0)   # x=2 > radius=1
    assert cyl.hit(ray) is None


def test_cylinder_tilted_axis():
    """Cylinder with a horizontal (X) axis can be hit from above."""
    # Cylinder along X axis from (-2,0,0) to (2,0,0), radius 1
    cyl = Cylinder(Vec3(-2, 0, 0), Vec3(2, 0, 0), radius=1.0)
    ray = make_ray(0, 3, 0, 0, -1, 0)
    hit = cyl.hit(ray)
    assert hit is not None
    # Normal at top of curved surface points +y
    assert abs(hit.normal.y - 1.0) < 1e-6


def test_cylinder_default_material():
    cyl = Cylinder(Vec3(0, 0, 0), Vec3(0, 1, 0), radius=1.0)
    assert cyl.color == Color(1.0, 1.0, 1.0)
    assert cyl.opacity == 1.0
    assert cyl.reflect == 0.0
    assert cyl.ior == 1.0
