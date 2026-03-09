# tests/test_triangle_mesh.py
from shapes import Triangle, TriangleMesh, HitRecord
from vector import Vec3
from color import Color
from ray import VisionRay


def _ray(ox, oy, oz, dx, dy, dz):
    return VisionRay(Vec3(ox, oy, oz), Vec3(dx, dy, dz))


def _tri(v0, v1, v2, **kw):
    return Triangle(Vec3(*v0), Vec3(*v1), Vec3(*v2), **kw)


def test_hit_single_triangle():
    mesh = TriangleMesh([_tri((0,0,0), (1,0,0), (0,1,0))])
    ray = _ray(0.25, 0.25, -1, 0, 0, 1)
    h = mesh.hit(ray)
    assert h is not None
    assert abs(h.t - 1.0) < 1e-6


def test_miss_no_triangles():
    mesh = TriangleMesh([])
    ray = _ray(0, 0, -1, 0, 0, 1)
    assert mesh.hit(ray) is None


def test_miss_wrong_direction():
    mesh = TriangleMesh([_tri((0,0,0), (1,0,0), (0,1,0))])
    ray = _ray(5, 5, -1, 0, 0, 1)
    assert mesh.hit(ray) is None


def test_bounding_box_covers_all_triangles():
    mesh = TriangleMesh([
        _tri((0,0,0), (1,0,0), (0,1,0)),
        _tri((3,3,3), (4,3,3), (3,4,3)),
    ])
    bb = mesh.bounding_box()
    assert bb.min_pt.x < 0.1
    assert bb.max_pt.x > 3.9
    assert bb.max_pt.y > 3.9


def test_hit_returns_triangle_as_mat_obj():
    tri = _tri((0,0,0), (1,0,0), (0,1,0))
    mesh = TriangleMesh([tri])
    ray = _ray(0.25, 0.25, -1, 0, 0, 1)
    h = mesh.hit(ray)
    assert isinstance(h.mat_obj, Triangle)


def test_closer_triangle_wins():
    mesh = TriangleMesh([
        _tri((0,0,2), (1,0,2), (0,1,2)),   # farther
        _tri((0,0,0), (1,0,0), (0,1,0)),   # closer
    ])
    ray = _ray(0.25, 0.25, -1, 0, 0, 1)
    h = mesh.hit(ray)
    assert abs(h.t - 1.0) < 1e-6  # hit the closer one at z=0
