"""Tests for the light class hierarchy."""
import math
import pytest
from color import Color
from scene import LightBase, Light, PointLight, SphereLight, DiskLight, RectLight
from vector import Vec3


# ---- LightBase / shared params ----

def test_light_effective_color_defaults():
    light = PointLight(position=Vec3(0, 10, 0))
    c = light.effective_color()
    assert c.r == pytest.approx(1.0)
    assert c.g == pytest.approx(1.0)
    assert c.b == pytest.approx(1.0)

def test_light_effective_color_tinted():
    light = PointLight(position=Vec3(0, 10, 0), color=Color(1.0, 0.0, 0.0))
    c = light.effective_color()
    assert c.r == pytest.approx(1.0)
    assert c.g == pytest.approx(0.0)
    assert c.b == pytest.approx(0.0)

def test_light_effective_color_intensity():
    light = PointLight(position=Vec3(0, 10, 0), intensity=0.5)
    c = light.effective_color()
    assert c.r == pytest.approx(0.5)

def test_light_effective_color_temperature_warm():
    light = PointLight(position=Vec3(0, 10, 0), color_temperature=2700)
    c = light.effective_color()
    assert c.r > c.b

def test_light_effective_color_temperature_cool():
    light = PointLight(position=Vec3(0, 10, 0), color_temperature=10000)
    c = light.effective_color()
    assert c.b > c.r


# ---- PointLight ----

def test_point_light_sample_returns_position():
    pos = Vec3(1, 2, 3)
    light = PointLight(position=pos)
    for _ in range(10):
        assert light.sample_point() == pos

def test_point_light_samples_always_1():
    light = PointLight(position=Vec3(0, 0, 0), samples=64)
    assert light.samples == 1


# ---- SphereLight ----

def test_sphere_light_sample_within_sphere():
    import random; random.seed(0)
    light = SphereLight(position=Vec3(0, 0, 0), radius=2.0)
    for _ in range(50):
        p = light.sample_point()
        d = math.sqrt(p.x**2 + p.y**2 + p.z**2)
        assert d <= 2.0 + 1e-9


# ---- Backwards compat: old Light still works ----

def test_old_light_point_sample():
    light = Light(position=Vec3(0, 10, 0))
    assert light.sample_point() == Vec3(0, 10, 0)

def test_old_light_area_sample_within_sphere():
    import random; random.seed(0)
    light = Light(position=Vec3(0, 10, 0), radius=2.0)
    for _ in range(20):
        p = light.sample_point()
        dx = p.x - 0
        dy = p.y - 10
        dz = p.z - 0
        assert dx*dx + dy*dy + dz*dz <= 4.0 + 1e-9


# ---- DiskLight ----

def test_disk_light_sample_on_disk():
    import random; random.seed(42)
    light = DiskLight(
        position=Vec3(0, 5, 0),
        normal=Vec3(0, -1, 0),
        radius=1.0,
    )
    for _ in range(50):
        p = light.sample_point()
        assert p.y == pytest.approx(5.0, abs=1e-9)
        r = math.sqrt(p.x**2 + p.z**2)
        assert r <= 1.0 + 1e-9

def test_disk_light_default_not_visible():
    light = DiskLight(position=Vec3(0,5,0), normal=Vec3(0,-1,0), radius=1.0)
    assert light.visible is False

def test_disk_light_defaults_one_sided():
    light = DiskLight(position=Vec3(0,5,0), normal=Vec3(0,-1,0), radius=1.0)
    assert light.two_sided is False


# ---- RectLight ----

def test_rect_light_sample_on_parallelogram():
    import random; random.seed(7)
    corner = Vec3(0, 5, 0)
    edge1  = Vec3(2, 0, 0)
    edge2  = Vec3(0, 0, 2)
    light  = RectLight(corner=corner, edge1=edge1, edge2=edge2)
    for _ in range(50):
        p = light.sample_point()
        assert p.y == pytest.approx(5.0, abs=1e-9)
        assert 0.0 - 1e-9 <= p.x <= 2.0 + 1e-9
        assert 0.0 - 1e-9 <= p.z <= 2.0 + 1e-9

def test_rect_light_position_is_center():
    corner = Vec3(0, 5, 0)
    edge1  = Vec3(2, 0, 0)
    edge2  = Vec3(0, 0, 2)
    light  = RectLight(corner=corner, edge1=edge1, edge2=edge2)
    assert light.position == Vec3(1, 5, 1)
