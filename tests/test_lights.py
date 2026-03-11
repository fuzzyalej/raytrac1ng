"""Tests for the light class hierarchy."""
import math
import pytest
from color import Color
from ray import Ray
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


# ---- LightBase is abstract ----

def test_lightbase_cannot_be_instantiated():
    """LightBase is abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        LightBase()


# ---- DiskLight.hit() ----

def test_disk_light_hit_front_face():
    """Ray from below hitting the front face of a downward-facing disk."""
    light = DiskLight(position=Vec3(0, 5, 0), normal=Vec3(0, -1, 0), radius=1.0)
    # Ray from below pointing up
    ray = Ray(Vec3(0, 0, 0), Vec3(0, 1, 0))
    hit = light.hit(ray)
    assert hit is not None
    assert hit.t == pytest.approx(5.0, abs=1e-6)


def test_disk_light_hit_back_face_one_sided_returns_none():
    """One-sided disk: ray hitting the back face returns None."""
    light = DiskLight(position=Vec3(0, 5, 0), normal=Vec3(0, -1, 0),
                      radius=1.0, two_sided=False)
    # Ray from above hitting the back side of the downward-facing disk
    ray = Ray(Vec3(0, 10, 0), Vec3(0, -1, 0))
    hit = light.hit(ray)
    assert hit is None


def test_disk_light_hit_back_face_two_sided_returns_hit():
    """Two-sided disk: ray hitting the back face returns a HitRecord."""
    light = DiskLight(position=Vec3(0, 5, 0), normal=Vec3(0, -1, 0),
                      radius=1.0, two_sided=True)
    ray = Ray(Vec3(0, 10, 0), Vec3(0, -1, 0))
    hit = light.hit(ray)
    assert hit is not None


def test_disk_light_hit_miss_outside_radius():
    """Ray that hits the disk plane but outside the radius returns None."""
    light = DiskLight(position=Vec3(0, 5, 0), normal=Vec3(0, -1, 0), radius=1.0)
    ray = Ray(Vec3(5, 0, 0), Vec3(0, 1, 0))  # offset far to the side
    hit = light.hit(ray)
    assert hit is None


# ---- RectLight.hit() ----

def test_rect_light_hit_front_face():
    """Ray hitting the front face of a rect light."""
    corner = Vec3(-1, 5, -1)
    edge1  = Vec3(2, 0, 0)
    edge2  = Vec3(0, 0, 2)
    light  = RectLight(corner=corner, edge1=edge1, edge2=edge2)
    # Normal is cross(edge1, edge2) = cross((2,0,0),(0,0,2)) = (0,-4,0) -> norm (0,-1,0)
    # So the rect faces downward. Ray from below going up hits front face.
    ray = Ray(Vec3(0, 0, 0), Vec3(0, 1, 0))
    hit = light.hit(ray)
    assert hit is not None
    assert hit.t == pytest.approx(5.0, abs=1e-6)


def test_rect_light_hit_back_face_one_sided_returns_none():
    """One-sided rect: ray from the back returns None."""
    corner = Vec3(-1, 5, -1)
    edge1  = Vec3(2, 0, 0)
    edge2  = Vec3(0, 0, 2)
    light  = RectLight(corner=corner, edge1=edge1, edge2=edge2, two_sided=False)
    ray = Ray(Vec3(0, 10, 0), Vec3(0, -1, 0))
    # Normal is (0,-1,0); denom = (0,-1,0)·(0,-1,0) = 1 > 0 → back face
    hit = light.hit(ray)
    assert hit is None


def test_rect_light_hit_back_face_two_sided_returns_hit():
    """Two-sided rect: ray from the back returns a HitRecord."""
    corner = Vec3(-1, 5, -1)
    edge1  = Vec3(2, 0, 0)
    edge2  = Vec3(0, 0, 2)
    light  = RectLight(corner=corner, edge1=edge1, edge2=edge2, two_sided=True)
    ray = Ray(Vec3(0, 10, 0), Vec3(0, -1, 0))
    hit = light.hit(ray)
    assert hit is not None


def test_rect_light_hit_miss_outside_bounds():
    """Ray that hits the plane but outside the rectangle returns None."""
    corner = Vec3(-1, 5, -1)
    edge1  = Vec3(2, 0, 0)
    edge2  = Vec3(0, 0, 2)
    light  = RectLight(corner=corner, edge1=edge1, edge2=edge2)
    ray = Ray(Vec3(10, 0, 0), Vec3(0, 1, 0))  # far to the side
    hit = light.hit(ray)
    assert hit is None


# ---- Scene.visible_lights ----

def test_scene_visible_lights_filters_correctly():
    """Scene.visible_lights returns only lights with visible=True."""
    from scene import Scene
    scene = Scene()
    visible  = DiskLight(position=Vec3(0,5,0), normal=Vec3(0,-1,0),
                         radius=1.0, visible=True)
    invisible = PointLight(position=Vec3(0,10,0), visible=False)
    scene.lights = [visible, invisible]
    assert scene.visible_lights == [visible]


def test_scene_visible_lights_empty_when_none_visible():
    from scene import Scene
    scene = Scene()
    scene.lights = [PointLight(position=Vec3(0,10,0))]
    assert scene.visible_lights == []
