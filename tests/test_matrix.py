# tests/test_matrix.py
import sys, os, math, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from vector import Vec3, Matrix4x4

def test_identity_transform_point():
    m = Matrix4x4()
    assert m.transform_point(Vec3(1, 2, 3)) == pytest.approx((1, 2, 3), abs=1e-6)

def test_identity_transform_direction():
    m = Matrix4x4()
    v = m.transform_direction(Vec3(0, 1, 0))
    assert (v.x, v.y, v.z) == pytest.approx((0, 1, 0), abs=1e-6)

def test_scale_matrix():
    m = Matrix4x4.from_trs(scale=(2, 3, 4), rotate=(0,0,0), translate=(0,0,0))
    p = m.transform_point(Vec3(1, 1, 1))
    assert (p.x, p.y, p.z) == pytest.approx((2, 3, 4), abs=1e-6)

def test_translate_matrix():
    m = Matrix4x4.from_trs(scale=(1,1,1), rotate=(0,0,0), translate=(5, 0, -3))
    p = m.transform_point(Vec3(0, 0, 0))
    assert (p.x, p.y, p.z) == pytest.approx((5, 0, -3), abs=1e-6)

def test_rotate_y_90():
    m = Matrix4x4.from_trs(scale=(1,1,1), rotate=(0, 90, 0), translate=(0,0,0))
    p = m.transform_point(Vec3(1, 0, 0))
    # Standard Ry(90°): x'=cos(90)*x + sin(90)*z = 0, z'=-sin(90)*x + cos(90)*z = -1
    # So (1,0,0) -> (0,0,-1)
    assert (p.x, p.y, p.z) == pytest.approx((0, 0, -1), abs=1e-6)

def test_inverse_round_trip():
    m = Matrix4x4.from_trs(scale=(2,1,3), rotate=(30, 45, 0), translate=(1,2,3))
    inv = m.inverse()
    combined = m @ inv
    identity = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]
    for i, (a, b) in enumerate(zip(combined.m, identity)):
        assert a == pytest.approx(b, abs=1e-6), f"m[{i}] = {a}, expected {b}"

def test_transpose():
    m = Matrix4x4([1,2,3,4, 5,6,7,8, 9,10,11,12, 13,14,15,16])
    t = m.transpose()
    assert t.m == pytest.approx(
        [1,5,9,13, 2,6,10,14, 3,7,11,15, 4,8,12,16], abs=1e-9
    )


def test_init_wrong_length_raises():
    with pytest.raises(ValueError, match="16 values"):
        Matrix4x4([1, 2, 3])

def test_direction_ignores_translation():
    m = Matrix4x4.from_trs(scale=(1,1,1), rotate=(0,0,0), translate=(99, 99, 99))
    d = m.transform_direction(Vec3(0, 1, 0))
    assert (d.x, d.y, d.z) == pytest.approx((0, 1, 0), abs=1e-6)
