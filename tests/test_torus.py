"""Tests for the Torus primitive."""
import pytest, math
from shapes import Torus
from vector import Vec3
from ray import VisionRay
from color import Color


def make_ray(ox, oy, oz, dx, dy, dz):
    return VisionRay(Vec3(ox, oy, oz), Vec3(dx, dy, dz))


def test_torus_hit_equatorial_ray():
    """Ray through the torus plane hits the outer wall."""
    # Torus: center=(0,0,0), axis=Y, R=2, r=0.5
    # Ray from x=4, pointing -x. Outer surface at x=2.5 → t=1.5
    torus = Torus(Vec3(0, 0, 0), Vec3(0, 1, 0),
                  major_radius=2.0, minor_radius=0.5)
    ray   = make_ray(4, 0, 0, -1, 0, 0)
    hit   = torus.hit(ray)
    assert hit is not None
    assert abs(hit.t - 1.5) < 1e-4


def test_torus_miss():
    """Ray clearly above the torus misses."""
    torus = Torus(Vec3(0, 0, 0), Vec3(0, 1, 0),
                  major_radius=2.0, minor_radius=0.5)
    ray   = make_ray(0, 5, 0, 0, 1, 0)   # going up from above
    assert torus.hit(ray) is None


def test_torus_outward_normal():
    """Normal at the outer equatorial hit points away from the tube centre."""
    torus = Torus(Vec3(0, 0, 0), Vec3(0, 1, 0),
                  major_radius=2.0, minor_radius=0.5)
    ray   = make_ray(4, 0, 0, -1, 0, 0)
    hit   = torus.hit(ray)
    assert hit is not None
    # Normal should point in +x direction (outward from tube at x=2.5)
    assert hit.normal.x > 0.9


def test_torus_offset_center():
    """Torus not at the origin can still be hit."""
    torus = Torus(Vec3(5, 3, 0), Vec3(0, 1, 0),
                  major_radius=2.0, minor_radius=0.5)
    ray   = make_ray(9, 3, 0, -1, 0, 0)   # same geometry, shifted +5 in x
    hit   = torus.hit(ray)
    assert hit is not None
    assert abs(hit.t - 1.5) < 1e-4


def test_torus_default_material():
    torus = Torus(Vec3(0, 0, 0), Vec3(0, 1, 0), 2.0, 0.5)
    assert torus.material.color == Color(1.0, 1.0, 1.0)
    assert torus.material.opacity == 1.0
    assert torus.material.reflect == 0.0
    assert torus.material.ior == 1.0
