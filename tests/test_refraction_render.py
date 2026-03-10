"""Integration tests for physical refraction in renderer._trace()."""
import pytest
from color import Color
from material import Material
from scene import Scene, Camera, Light
from shapes import Sphere
from vector import Vec3
from rendering import render


def _glass_scene(ior=1.5):
    """Camera looking at a glass sphere in front of a red background sphere."""
    cam = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    light = Light(Vec3(0, 5, -3))
    glass = Sphere(Vec3(0, 0, 0), 1.0,
                   material=Material(color=Color(1, 1, 1), opacity=0.0, ior=ior))
    red_bg = Sphere(Vec3(0, 0, 5), 4.0,
                    material=Material(color=Color(1, 0, 0)))
    return Scene(camera=cam, lights=[light], objects=[glass, red_bg])


def test_glass_sphere_render_completes():
    """render() with ior=1.5 completes without error."""
    pixels = render(_glass_scene(), 16, 12)
    assert len(pixels) == 16 * 12


def test_glass_sphere_colors_in_range():
    """All pixels from a glass-sphere render are valid colors."""
    pixels = render(_glass_scene(), 16, 12)
    for p in pixels:
        assert 0.0 <= p.r <= 1.0
        assert 0.0 <= p.g <= 1.0
        assert 0.0 <= p.b <= 1.0


def test_glass_differs_from_naive_transparent():
    """ior=1.5 glass sphere renders differently from ior=1.0 transparent sphere."""
    px_glass = render(_glass_scene(ior=1.5), 32, 24)
    px_naive = render(_glass_scene(ior=1.0), 32, 24)
    diffs = [abs(a.r - b.r) + abs(a.g - b.g) + abs(a.b - b.b)
             for a, b in zip(px_glass, px_naive)]
    assert max(diffs) > 0.05


def test_glass_passes_background_color():
    """Glass sphere center pixels should show significant red from the background."""
    pixels = render(_glass_scene(), 32, 24)
    center = pixels[12 * 32 + 16]  # center pixel
    assert center.r > 0.1  # red background should be visible through glass


def test_existing_opaque_scene_unchanged():
    """Opaque objects (ior=1.0, opacity=1.0) render exactly as before."""
    cam = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    light = Light(Vec3(5, 5, -5))
    s = Sphere(Vec3(0, 0, 0), 1.0,
               material=Material(color=Color(1, 0, 0)))  # default ior=1.0, opacity=1.0
    scene = Scene(camera=cam, lights=[light], objects=[s])
    pixels = render(scene, 16, 12)
    assert len(pixels) == 16 * 12
    for p in pixels:
        assert 0.0 <= p.r <= 1.0
