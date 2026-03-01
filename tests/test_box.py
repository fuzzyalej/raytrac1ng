"""Tests for the Box (AABB) primitive."""
import pytest
from shapes import Box, HitRecord
from vector import Vec3
from ray import VisionRay
from color import Color


def make_ray(ox, oy, oz, dx, dy, dz):
    return VisionRay(Vec3(ox, oy, oz), Vec3(dx, dy, dz))


def test_box_hit_plus_x_face():
    """Ray from +x hits the max-x face; normal should be +x."""
    box = Box(Vec3(0, 0, 0), Vec3(1, 1, 1))
    ray = make_ray(5, 0.5, 0.5, -1, 0, 0)
    hit = box.hit(ray)
    assert hit is not None
    assert abs(hit.t - 4.0) < 1e-6
    assert abs(hit.normal.x - 1.0) < 1e-6
    assert abs(hit.normal.y) < 1e-6
    assert abs(hit.normal.z) < 1e-6


def test_box_hit_minus_x_face():
    """Ray from -x hits the min-x face; normal should be -x."""
    box = Box(Vec3(0, 0, 0), Vec3(1, 1, 1))
    ray = make_ray(-5, 0.5, 0.5, 1, 0, 0)
    hit = box.hit(ray)
    assert hit is not None
    assert abs(hit.t - 5.0) < 1e-6
    assert abs(hit.normal.x - (-1.0)) < 1e-6


def test_box_miss():
    """Ray aimed off to the side misses."""
    box = Box(Vec3(0, 0, 0), Vec3(1, 1, 1))
    ray = make_ray(5, 2.0, 0.5, -1, 0, 0)   # y=2 > max.y=1
    assert box.hit(ray) is None


def test_box_hit_top_face():
    """Ray from above hits the +y face."""
    box = Box(Vec3(0, 0, 0), Vec3(1, 1, 1))
    ray = make_ray(0.5, 5, 0.5, 0, -1, 0)
    hit = box.hit(ray)
    assert hit is not None
    assert abs(hit.t - 4.0) < 1e-6
    assert abs(hit.normal.y - 1.0) < 1e-6


def test_box_ray_from_inside_exits_correct_face():
    """Ray starting inside the box returns the exit face normal."""
    box = Box(Vec3(0, 0, 0), Vec3(1, 1, 1))
    ray = make_ray(0.5, 0.5, 0.5, -1, 0, 0)   # exits through x=0 face
    hit = box.hit(ray)
    assert hit is not None
    assert hit.t > 0
    assert abs(hit.normal.x - (-1.0)) < 1e-6   # outward normal of min-x face


def test_box_default_material():
    """Default material: white, fully opaque, no reflection."""
    box = Box(Vec3(0, 0, 0), Vec3(1, 1, 1))
    assert box.color == Color(1.0, 1.0, 1.0)
    assert box.opacity == 1.0
    assert box.reflect == 0.0
    assert box.ior == 1.0


def test_box_custom_material():
    """Custom material values are stored correctly."""
    box = Box(Vec3(0, 0, 0), Vec3(1, 1, 1),
              color=Color(1, 0, 0), opacity=0.5, reflect=0.3, ior=1.5)
    assert box.color == Color(1, 0, 0)
    assert abs(box.opacity - 0.5) < 1e-6
    assert abs(box.reflect - 0.3) < 1e-6
    assert abs(box.ior - 1.5) < 1e-6
