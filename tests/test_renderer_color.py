# tests/test_renderer_color.py
from color import Color
from scene import Scene, Camera, Light
from shapes import Sphere
from vector import Vec3
from renderer import render

def _make_scene(sphere_color: Color) -> Scene:
    scene = Scene()
    scene.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    scene.lights = [Light(position=Vec3(0, 10, -10))]
    scene.objects = [Sphere(Vec3(0, 0, 0), 1.0, color=sphere_color)]
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
    scene.objects = [Sphere(Vec3(0, 0, 0), 1.0, color=Color(1.0, 0.0, 0.0), opacity=0.0)]
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
        Sphere(Vec3(0, 0, 0), 0.4, color=Color(0.0, 0.0, 1.0), opacity=1.0),   # blue, behind
        Sphere(Vec3(0, 0, -1.5), 0.8, color=Color(1.0, 0.0, 0.0), opacity=0.5), # red, in front
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
    scene2.objects = [Sphere(Vec3(0, 0, 0), 1.0, color=Color(1.0, 0.0, 0.0), opacity=1.0)]
    pixels2 = render(scene2, 50, 50)

    c1 = pixels1[25 * 50 + 25]
    c2 = pixels2[25 * 50 + 25]
    assert abs(c1.r - c2.r) < 1e-6
    assert abs(c1.g - c2.g) < 1e-6
    assert abs(c1.b - c2.b) < 1e-6
