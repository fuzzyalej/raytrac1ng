# tests/test_transformed_shape.py
import sys, os, math, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from shapes import Sphere, Box, Transform, TransformedShape, HitRecord
from vector import Vec3
from color import Color
from ray import VisionRay
from bvh import AABB

def _sphere():
    return Sphere(center=Vec3(0,0,0), radius=1.0, color=Color(1,1,1))

def _ray(ox, oy, oz, dx, dy, dz):
    return VisionRay(Vec3(ox, oy, oz), Vec3(dx, dy, dz))

# --- Translation ---

def test_translated_sphere_hit():
    """Sphere translated to (5,0,0): ray from (5,0,-5) along +Z should hit."""
    t = Transform(translate=(5, 0, 0))
    ts = TransformedShape(_sphere(), t)
    ray = _ray(5, 0, -5,  0, 0, 1)
    rec = ts.hit(ray, 0.001, 1e9)
    assert rec is not None

def test_translated_sphere_miss():
    """Sphere translated to (5,0,0): ray along origin +Z should miss."""
    t = Transform(translate=(5, 0, 0))
    ts = TransformedShape(_sphere(), t)
    ray = _ray(0, 0, -5,  0, 0, 1)
    rec = ts.hit(ray, 0.001, 1e9)
    assert rec is None

def test_translated_hit_point_in_world_space():
    """Hit point must be in world space, not object space."""
    t = Transform(translate=(5, 0, 0))
    ts = TransformedShape(_sphere(), t)
    ray = _ray(5, 0, -5,  0, 0, 1)
    rec = ts.hit(ray, 0.001, 1e9)
    assert rec is not None
    # Front of translated sphere is at z = -1 world
    assert rec.point.z == pytest.approx(-1.0, abs=1e-4)
    assert rec.point.x == pytest.approx(5.0,  abs=1e-4)

# --- Scale ---

def test_scale_stretch_hit():
    """Unit sphere scaled x2 on X: ray aimed at x=1.5 should hit (would miss unit sphere)."""
    t = Transform(scale=(2, 1, 1))
    ts = TransformedShape(_sphere(), t)
    ray = _ray(1.5, 0, -5,  0, 0, 1)
    rec = ts.hit(ray, 0.001, 1e9)
    assert rec is not None

def test_scale_stretch_miss():
    """Unit sphere scaled x2 on X but NOT Y: ray at y=1.5 should miss."""
    t = Transform(scale=(2, 1, 1))
    ts = TransformedShape(_sphere(), t)
    ray = _ray(0, 1.5, -5,  0, 0, 1)
    rec = ts.hit(ray, 0.001, 1e9)
    assert rec is None

# --- Bounding box ---

def test_bounding_box_translated():
    t = Transform(translate=(5, 0, 0))
    ts = TransformedShape(_sphere(), t)
    bbox = ts.bounding_box()
    assert bbox is not None
    assert bbox.min_pt.x == pytest.approx(4.0, abs=1e-4)
    assert bbox.max_pt.x == pytest.approx(6.0, abs=1e-4)

def test_bounding_box_scaled():
    t = Transform(scale=(3, 1, 1))
    ts = TransformedShape(_sphere(), t)
    bbox = ts.bounding_box()
    assert bbox.max_pt.x == pytest.approx(3.0, abs=1e-4)
    assert bbox.max_pt.y == pytest.approx(1.0, abs=1e-4)

# --- Normal is in world space ---

def test_normal_world_space_translated():
    t = Transform(translate=(5, 0, 0))
    ts = TransformedShape(_sphere(), t)
    ray = _ray(5, 0, -5,  0, 0, 1)
    rec = ts.hit(ray, 0.001, 1e9)
    # Front face normal points towards camera → z ≈ -1
    assert rec.normal.z == pytest.approx(-1.0, abs=1e-4)

def test_normal_non_uniform_scale():
    """Normal must be transformed by inv.T (not forward matrix) under non-uniform scale."""
    # Sphere scaled 3x on X only. Hit from above straight down.
    # The top of the ellipsoid is at y=1 world-space.
    # The normal at the top must still point up (+Y), not be skewed by X scale.
    t = Transform(scale=(3, 1, 1))
    ts = TransformedShape(_sphere(), t)
    ray = _ray(0, 5, 0,  0, -1, 0)
    rec = ts.hit(ray, 0.001, 1e9)
    assert rec is not None
    assert rec.normal.y == pytest.approx(1.0, abs=1e-4)
    assert abs(rec.normal.x) < 1e-4
