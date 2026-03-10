# tests/test_renderer_color.py
from color import Color
from material import Material
from scene import Scene, Camera, Light
from shapes import Sphere, Plane
from vector import Vec3
from rendering import render

def _make_scene(sphere_color: Color) -> Scene:
    scene = Scene()
    scene.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    scene.lights = [Light(position=Vec3(0, 10, -10))]
    scene.objects = [Sphere(Vec3(0, 0, 0), 1.0, material=Material(color=sphere_color))]
    return scene

def test_render_returns_color_objects():
    scene = _make_scene(Color(1.0, 0.0, 0.0))
    pixels = render(scene, 10, 10)
    assert len(pixels) == 100
    assert all(isinstance(p, Color) for p in pixels)

def test_red_sphere_has_red_pixels():
    scene = _make_scene(Color(1.0, 0.0, 0.0))
    pixels = render(scene, 50, 50)
    center_pixel = pixels[25 * 50 + 25]
    assert center_pixel.r > center_pixel.b
    assert center_pixel.r > center_pixel.g

def test_blue_sphere_has_blue_pixels():
    scene = _make_scene(Color(0.0, 0.0, 1.0))
    pixels = render(scene, 50, 50)
    center_pixel = pixels[25 * 50 + 25]
    assert center_pixel.b > center_pixel.r
    assert center_pixel.b > center_pixel.g

def test_background_is_dark():
    scene = _make_scene(Color(1.0, 0.0, 0.0))
    pixels = render(scene, 50, 50)
    corner = pixels[0]
    assert corner.r < 0.2
    assert corner.g < 0.2
    assert corner.b < 0.2

def test_fully_transparent_sphere_shows_background():
    """A sphere with opacity=0 is invisible — center pixel is the background color."""
    scene = _make_scene(Color(1.0, 0.0, 0.0))
    scene.objects = [Sphere(Vec3(0, 0, 0), 1.0,
                             material=Material(color=Color(1.0, 0.0, 0.0), opacity=0.0))]
    pixels = render(scene, 50, 50)
    center = pixels[25 * 50 + 25]
    # Background is Color(0.05, 0.05, 0.08) — should be very close to it
    assert center.r < 0.1
    assert center.g < 0.1
    assert center.b < 0.15

def test_semi_transparent_sphere_blends_colors():
    """A 50% transparent red sphere in front of a solid blue sphere blends both colors.

    Camera is at z=-5 looking toward +Z. Red sphere (opacity=0.5) is at z=-1.5
    (closer to camera), blue sphere is at z=0 (behind the red one).
    """
    scene = Scene()
    scene.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    scene.lights = [Light(position=Vec3(0, 10, -10))]
    scene.objects = [
        Sphere(Vec3(0, 0, 0), 0.4,
               material=Material(color=Color(0.0, 0.0, 1.0), opacity=1.0)),   # blue, behind
        Sphere(Vec3(0, 0, -1.5), 0.8,
               material=Material(color=Color(1.0, 0.0, 0.0), opacity=0.5)),   # red, in front
    ]
    pixels = render(scene, 50, 50)
    center = pixels[25 * 50 + 25]
    # Both red and blue should be clearly present in the blended result
    assert center.r > 0.1
    assert center.b > 0.1
    # Neither channel should dominate completely (sanity check)
    assert center.r < 0.95
    assert center.b < 0.95

def test_opaque_sphere_unchanged():
    """A sphere with opacity=1.0 (default) behaves exactly as before."""
    scene1 = _make_scene(Color(1.0, 0.0, 0.0))
    pixels1 = render(scene1, 50, 50)

    scene2 = _make_scene(Color(1.0, 0.0, 0.0))
    scene2.objects = [Sphere(Vec3(0, 0, 0), 1.0,
                              material=Material(color=Color(1.0, 0.0, 0.0), opacity=1.0))]
    pixels2 = render(scene2, 50, 50)

    c1 = pixels1[25 * 50 + 25]
    c2 = pixels2[25 * 50 + 25]
    assert abs(c1.r - c2.r) < 1e-6
    assert abs(c1.g - c2.g) < 1e-6
    assert abs(c1.b - c2.b) < 1e-6


def test_render_empty_scene():
    """A scene with no objects renders to background color."""
    from scene import Scene, Camera, Light
    from rendering import render
    from color import Color
    from vector import Vec3
    camera = Camera(location=Vec3(0, 0, -5), look_at=Vec3(0, 0, 0), fov=60)
    scene = Scene(camera=camera, lights=[], objects=[])
    pixels = render(scene, 10, 10)
    assert len(pixels) == 100
    # All pixels should be background color (no objects to hit)
    bg = Color(0.05, 0.05, 0.08)
    for p in pixels:
        assert abs(p.r - bg.r) < 1e-6 and abs(p.g - bg.g) < 1e-6 and abs(p.b - bg.b) < 1e-6


def test_render_all_planes_scene():
    """A scene with only Plane objects (no BVH-bounded objects) renders correctly."""
    from scene import Scene, Camera, Light
    from rendering import render
    from shapes import Plane
    from color import Color
    from material import Material
    from vector import Vec3
    camera = Camera(location=Vec3(0, 5, -10), look_at=Vec3(0, 0, 0), fov=60)
    light = Light(position=Vec3(5, 10, -5))
    plane = Plane(Vec3(0, 1, 0), 0,
                  material=Material(color=Color(0.8, 0.8, 0.8)))  # horizontal ground plane
    scene = Scene(camera=camera, lights=[light], objects=[plane])
    pixels = render(scene, 10, 10)
    assert len(pixels) == 100
    # At least some pixels should be the plane color (not background)
    bg = Color(0.05, 0.05, 0.08)
    non_bg = [p for p in pixels if abs(p.r - bg.r) > 0.01]
    assert len(non_bg) > 0, "Expected some pixels to hit the plane"
