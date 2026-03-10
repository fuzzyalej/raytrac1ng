# tests/test_transform.py
import sys, os, math, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from shapes import Transform
from vector import Vec3

def test_default_transform_is_identity():
    t = Transform()
    m = t.matrix()
    p = m.transform_point(Vec3(3, 4, 5))
    assert (p.x, p.y, p.z) == pytest.approx((3, 4, 5), abs=1e-6)

def test_translate_stored_and_applied():
    t = Transform(translate=(1, 2, 3))
    p = t.matrix().transform_point(Vec3(0, 0, 0))
    assert (p.x, p.y, p.z) == pytest.approx((1, 2, 3), abs=1e-6)

def test_scale_stored_and_applied():
    t = Transform(scale=(2, 3, 4))
    p = t.matrix().transform_point(Vec3(1, 1, 1))
    assert (p.x, p.y, p.z) == pytest.approx((2, 3, 4), abs=1e-6)

def test_matrix_is_cached():
    t = Transform(scale=(2, 1, 1))
    m1 = t.matrix()
    m2 = t.matrix()
    assert m1 is m2  # same object — must be cached

def test_inverse_matrix_is_cached():
    t = Transform(translate=(5, 0, 0))
    i1 = t.inverse_matrix()
    i2 = t.inverse_matrix()
    assert i1 is i2

def test_inverse_round_trip():
    t = Transform(scale=(2, 1, 3), rotate=(0, 45, 0), translate=(1, 2, 3))
    p_orig = Vec3(4, 5, 6)
    p_world = t.matrix().transform_point(p_orig)
    p_back  = t.inverse_matrix().transform_point(p_world)
    assert (p_back.x, p_back.y, p_back.z) == pytest.approx((4, 5, 6), abs=1e-5)

def test_uniform_scale_shorthand():
    """scalar scale 2.0 should be interpreted as (2, 2, 2)"""
    t = Transform(scale=2.0)
    assert t.scale == (2.0, 2.0, 2.0)
    p = t.matrix().transform_point(Vec3(1, 1, 1))
    assert (p.x, p.y, p.z) == pytest.approx((2, 2, 2), abs=1e-6)

def test_repr_contains_components():
    t = Transform(scale=(1,2,3), rotate=(10,20,30), translate=(4,5,6))
    r = repr(t)
    assert "Transform" in r
    assert "(1.0, 2.0, 3.0)" in r   # scale
    assert "(10.0, 20.0, 30.0)" in r  # rotate
    assert "(4.0, 5.0, 6.0)" in r    # translate

def test_rotate_wrong_arity_raises():
    with pytest.raises(ValueError, match="rotate"):
        Transform(rotate=(1, 2))

def test_translate_wrong_arity_raises():
    with pytest.raises(ValueError, match="translate"):
        Transform(translate=(1,))

def test_scale_wrong_arity_raises():
    with pytest.raises(ValueError, match="scale"):
        Transform(scale=(1, 2))
