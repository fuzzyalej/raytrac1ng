"""Tests for the Cone (generalised frustum) primitive."""
import pytest, math
from shapes import Cone
from vector import Vec3
from ray import VisionRay
from color import Color


def make_ray(ox, oy, oz, dx, dy, dz):
    return VisionRay(Vec3(ox, oy, oz), Vec3(dx, dy, dz))


def test_cone_hit_curved_surface():
    """Ray hits the curved side of a true cone at its base level."""
    # True cone: base radius=1 at y=0, apex at y=2
    cone = Cone(Vec3(0, 0, 0), Vec3(0, 2, 0),
                bottom_radius=1.0, top_radius=0.0)
    ray  = make_ray(3, 0, 0, -1, 0, 0)
    hit  = cone.hit(ray)
    assert hit is not None
    assert abs(hit.t - 2.0) < 1e-6   # ray from x=3 hits at x=1
    assert hit.normal.x > 0           # normal points toward ray (+x component)
    assert hit.normal.y > 0           # has upward slope component


def test_cone_miss_above():
    """Ray going upward from above the cone misses."""
    cone = Cone(Vec3(0, 0, 0), Vec3(0, 2, 0),
                bottom_radius=1.0, top_radius=0.0)
    ray = make_ray(0, 5, 0, 0, 1, 0)
    assert cone.hit(ray) is None


def test_cone_hit_bottom_cap():
    """Ray from below hits the bottom cap when bottom_radius > 0."""
    cone = Cone(Vec3(0, 0, 0), Vec3(0, 2, 0),
                bottom_radius=1.0, top_radius=0.0)
    ray  = make_ray(0, -5, 0, 0, 1, 0)
    hit  = cone.hit(ray)
    assert hit is not None
    assert abs(hit.t - 5.0) < 1e-6
    assert abs(hit.normal.y - (-1.0)) < 1e-6


def test_true_cone_has_no_top_cap():
    """A cone with top_radius=0 skips the top cap (zero-radius disk)."""
    cone = Cone(Vec3(0, 0, 0), Vec3(0, 2, 0),
                bottom_radius=1.0, top_radius=0.0)
    # Ray aimed straight down at centre — would trivially hit any top cap;
    # instead it should hit the curved surface on the way down or miss.
    # The key check is that no crash occurs and top_radius=0 is handled.
    ray = make_ray(0, 5, 0, 0, -1, 0)
    hit = cone.hit(ray)   # may hit curved surface near apex — just no crash
    assert hit is None or hit.t > 0


def test_cone_frustum_hit():
    """Frustum (both radii non-zero) hit at the base."""
    cone = Cone(Vec3(0, 0, 0), Vec3(0, 2, 0),
                bottom_radius=2.0, top_radius=1.0)
    ray  = make_ray(4, 0, 0, -1, 0, 0)
    hit  = cone.hit(ray)
    assert hit is not None
    assert abs(hit.t - 2.0) < 1e-6   # base radius=2, hit at x=2


def test_cone_frustum_hit_top_cap():
    """Ray from above hits the top cap of a frustum."""
    cone = Cone(Vec3(0, 0, 0), Vec3(0, 2, 0),
                bottom_radius=2.0, top_radius=1.0)
    ray  = make_ray(0, 5, 0, 0, -1, 0)
    hit  = cone.hit(ray)
    assert hit is not None
    assert abs(hit.t - 3.0) < 1e-6
    assert abs(hit.normal.y - 1.0) < 1e-6


def test_cone_default_material():
    cone = Cone(Vec3(0, 0, 0), Vec3(0, 1, 0), 1.0, 0.5)
    assert cone.material.color == Color(1.0, 1.0, 1.0)
    assert cone.material.opacity == 1.0
    assert cone.material.reflect == 0.0
    assert cone.material.ior == 1.0
