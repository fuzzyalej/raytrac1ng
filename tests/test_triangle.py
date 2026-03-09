# tests/test_triangle.py
import math
import pytest
from shapes import Triangle, HitRecord
from vector import Vec3
from color import Color
from bvh import AABB
from ray import VisionRay


def _ray(origin, direction):
    return VisionRay(Vec3(*origin), Vec3(*direction))


V0 = Vec3(0, 0, 0)
V1 = Vec3(1, 0, 0)
V2 = Vec3(0, 1, 0)


def test_hit_center():
    tri = Triangle(V0, V1, V2)
    ray = _ray((0.25, 0.25, -1), (0, 0, 1))
    h = tri.hit(ray)
    assert h is not None
    assert abs(h.t - 1.0) < 1e-6
    assert h.mat_obj is tri


def test_miss_outside():
    tri = Triangle(V0, V1, V2)
    ray = _ray((2.0, 0.0, -1), (0, 0, 1))
    assert tri.hit(ray) is None


def test_miss_parallel():
    tri = Triangle(V0, V1, V2)
    ray = _ray((0.25, 0.25, 0), (1, 0, 0))
    assert tri.hit(ray) is None


def test_flat_normal_faces_camera():
    tri = Triangle(V0, V1, V2)
    ray = _ray((0.25, 0.25, -1), (0, 0, 1))
    h = tri.hit(ray)
    # face normal is (0, 0, -1) (toward camera) or (0, 0, 1)
    assert abs(abs(h.normal.z) - 1.0) < 1e-6


def test_smooth_normals_interpolated():
    n0 = Vec3(0, 0, -1)
    n1 = Vec3(0, 0, -1)
    n2 = Vec3(0, 0, -1)
    tri = Triangle(V0, V1, V2, n0=n0, n1=n1, n2=n2)
    ray = _ray((0.25, 0.25, -1), (0, 0, 1))
    h = tri.hit(ray)
    assert abs(h.normal.z + 1.0) < 1e-6  # interpolated = (0, 0, -1)


def test_t_min_respected():
    tri = Triangle(V0, V1, V2)
    ray = _ray((0.25, 0.25, -1), (0, 0, 1))
    # t=1.0 but t_min=2.0 → miss
    assert tri.hit(ray, t_min=2.0) is None


def test_t_max_respected():
    tri = Triangle(V0, V1, V2)
    ray = _ray((0.25, 0.25, -1), (0, 0, 1))
    # t=1.0 but t_max=0.5 → miss
    assert tri.hit(ray, t_max=0.5) is None


def test_bounding_box_contains_vertices():
    tri = Triangle(Vec3(-1, 0, 0), Vec3(1, 0, 0), Vec3(0, 2, 0))
    bb = tri.bounding_box()
    assert isinstance(bb, AABB)
    assert bb.min_pt.x < -1.0
    assert bb.max_pt.x > 1.0
    assert bb.max_pt.y > 2.0
    # Non-degenerate even for flat triangle in XY plane
    assert bb.max_pt.z > bb.min_pt.z


def test_material_defaults():
    tri = Triangle(V0, V1, V2)
    assert tri.color == Color(1.0, 1.0, 1.0)
    assert tri.opacity == 1.0
    assert tri.reflect == 0.0
    assert tri.ior == 1.0


def test_material_custom():
    tri = Triangle(V0, V1, V2, color=Color(1, 0, 0), opacity=0.5, reflect=0.2, ior=1.5)
    assert tri.color == Color(1, 0, 0)
    assert tri.opacity == 0.5
    assert tri.reflect == 0.2
    assert tri.ior == 1.5
