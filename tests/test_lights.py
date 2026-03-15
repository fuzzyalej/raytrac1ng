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


# ---- Shading tests ----

import pytest as _pytest

def _make_ctx_from_scene(scene):
    """Build a RenderContext from a scene for unit testing."""
    from shapes import Plane as _Plane
    from bvh import BVH
    from rendering.renderer import RenderContext
    bounded   = [o for o in scene.objects if not isinstance(o, _Plane)]
    unbounded = [o for o in scene.objects if     isinstance(o, _Plane)]
    bvh = BVH.build(bounded)
    return RenderContext(scene=scene, bvh=bvh, unbounded=unbounded)


def test_disk_light_one_sided_behind_gets_zero_shadow():
    """Hit point behind a one-sided disk light gets zero shadow contribution."""
    import random as _random
    _random.seed(0)
    from scene import Scene, Camera, DiskLight
    from rendering.shading import shadow_factor
    scene = Scene()
    scene.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0))
    # Disk faces DOWN (-Y normal). A point ABOVE the disk (y=6) is behind the emitting face.
    light = DiskLight(
        position=Vec3(0, 5, 0),
        normal=Vec3(0, -1, 0),
        radius=2.0,
        two_sided=False,
        samples=8,
    )
    scene.lights = [light]
    scene.objects = []
    ctx = _make_ctx_from_scene(scene)
    factor = shadow_factor(Vec3(0, 6, 0), light, ctx)
    assert factor == _pytest.approx(0.0)


def test_disk_light_two_sided_behind_gets_contribution():
    """Hit point behind a two_sided disk still receives light."""
    import random as _random
    _random.seed(0)
    from scene import Scene, Camera, DiskLight
    from rendering.shading import shadow_factor
    scene = Scene()
    scene.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0))
    light = DiskLight(
        position=Vec3(0, 5, 0),
        normal=Vec3(0, -1, 0),
        radius=2.0,
        two_sided=True,
        samples=8,
    )
    scene.lights = [light]
    scene.objects = []
    ctx = _make_ctx_from_scene(scene)
    factor = shadow_factor(Vec3(0, 6, 0), light, ctx)
    assert factor > 0.0


def test_shade_colored_light_tints_surface():
    """A red PointLight on a white surface produces a reddish result."""
    import random as _random
    _random.seed(0)
    from scene import Scene, Camera, PointLight
    from shapes.primitives import HitRecord
    from rendering.shading import shade
    scene = Scene()
    scene.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0))
    scene.lights = [PointLight(position=Vec3(0, 10, 0), color=Color(1.0, 0.0, 0.0))]
    scene.objects = []
    ctx = _make_ctx_from_scene(scene)
    hit = HitRecord(t=1.0, point=Vec3(0, 0, 0), normal=Vec3(0, 1, 0))
    result = shade(hit, Color(1.0, 1.0, 1.0), ctx)
    assert result.r > result.g
    assert result.r > result.b


def test_shade_warm_light_tints_surface():
    """A 2700K light on a white surface produces a warmer (r > b) result."""
    import random as _random
    _random.seed(0)
    from scene import Scene, Camera, PointLight
    from shapes.primitives import HitRecord
    from rendering.shading import shade
    scene = Scene()
    scene.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0))
    scene.lights = [PointLight(position=Vec3(0, 10, 0), color_temperature=2700)]
    scene.objects = []
    ctx = _make_ctx_from_scene(scene)
    hit = HitRecord(t=1.0, point=Vec3(0, 0, 0), normal=Vec3(0, 1, 0))
    result = shade(hit, Color(1.0, 1.0, 1.0), ctx)
    # Warm light: result should have r > b
    assert result.r > result.b


# ---- Renderer visible light tests ----

def test_visible_disk_light_appears_in_render():
    """A visible DiskLight facing the camera produces a bright colored pixel at center."""
    from scene import Scene, Camera, DiskLight
    from rendering import render
    scene = Scene()
    scene.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    scene.lights = [
        DiskLight(
            position=Vec3(0, 0, 2),
            normal=Vec3(0, 0, -1),   # facing the camera
            radius=0.5,
            visible=True,
            color=Color(1.0, 1.0, 0.0),  # yellow
            intensity=1.0,
        )
    ]
    scene.objects = []
    pixels = render(scene, 20, 20)
    center = pixels[10 * 20 + 10]
    # Should be close to yellow (r≈1, g≈1, b≈0)
    assert center.r > 0.8
    assert center.g > 0.8
    assert center.b < 0.2


def test_invisible_disk_light_does_not_appear_in_render():
    """A DiskLight with visible=False should not produce visible geometry."""
    from scene import Scene, Camera, DiskLight
    from rendering import render
    from rendering.renderer import BG_COLOR
    scene = Scene()
    scene.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    scene.lights = [
        DiskLight(
            position=Vec3(0, 0, 2),
            normal=Vec3(0, 0, -1),
            radius=0.5,
            visible=False,
            color=Color(1.0, 1.0, 0.0),
        )
    ]
    scene.objects = []
    pixels = render(scene, 20, 20)
    center = pixels[10 * 20 + 10]
    assert center.r == pytest.approx(BG_COLOR.r, abs=0.05)
    assert center.g == pytest.approx(BG_COLOR.g, abs=0.05)
    assert center.b == pytest.approx(BG_COLOR.b, abs=0.05)


def test_visible_rect_light_appears_in_render():
    """A visible RectLight facing the camera produces a bright pixel."""
    from scene import Scene, Camera, RectLight
    from rendering import render
    scene = Scene()
    scene.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    # Rect in the XY plane at z=2, facing camera (-Z normal)
    # normal = cross(edge1, edge2) = cross((1,0,0),(0,1,0)) = (0,0,1) — faces away from camera
    # So use edge1=(1,0,0), edge2=(0,-1,0) to get normal=(0,0,-1) facing camera
    scene.lights = [
        RectLight(
            corner=Vec3(-0.5, 0.5, 2),
            edge1=Vec3(1, 0, 0),
            edge2=Vec3(0, -1, 0),
            visible=True,
            color=Color(0.0, 1.0, 1.0),  # cyan
        )
    ]
    scene.objects = []
    pixels = render(scene, 20, 20)
    center = pixels[10 * 20 + 10]
    # Should be close to cyan (r≈0, g≈1, b≈1)
    assert center.r < 0.2
    assert center.g > 0.8
    assert center.b > 0.8


def test_visible_light_does_not_block_shadows():
    """A visible light should not cast shadows on other objects."""
    from scene import Scene, Camera, DiskLight, PointLight
    from shapes import Sphere, Plane
    from material import Material
    from rendering import render
    # Point light above, visible disk in front of a sphere — disk should not shadow the sphere
    scene = Scene()
    scene.camera = Camera(Vec3(0, 2, -5), Vec3(0, 0, 0), fov=60)
    scene.lights = [
        PointLight(position=Vec3(0, 10, 0)),
        DiskLight(
            position=Vec3(0, 1, 0), normal=Vec3(0, -1, 0),
            radius=0.3, visible=True,
        ),
    ]
    scene.objects = [
        Plane(Vec3(0, 1, 0), -1.0, material=Material()),
    ]
    # If disk doesn't block shadows, the plane under it should still be lit
    pixels = render(scene, 30, 30)
    # Center-bottom pixel should not be fully dark
    bottom = pixels[25 * 30 + 15]
    total = bottom.r + bottom.g + bottom.b
    assert total > 0.1
