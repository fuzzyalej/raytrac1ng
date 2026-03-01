"""Tests for anti-aliasing in renderer.render()."""

from color import Color
from scene import Scene, Camera, Light
from shapes import Sphere
from vector import Vec3
from renderer import render


def _simple_scene():
    cam = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    light = Light(Vec3(5, 5, -5))
    sphere = Sphere(Vec3(0, 0, 0), 1.0, Color(1, 0, 0))
    return Scene(camera=cam, lights=[light], objects=[sphere])


def test_render_no_aa_pixel_count():
    pixels = render(_simple_scene(), 8, 6, aa_samples=0)
    assert len(pixels) == 8 * 6


def test_render_aa_samples_1_pixel_count():
    # aa_samples=1 uses the fast path (same as 0)
    pixels = render(_simple_scene(), 8, 6, aa_samples=1)
    assert len(pixels) == 8 * 6


def test_render_aa_pixel_count():
    pixels = render(_simple_scene(), 8, 6, aa_samples=4)
    assert len(pixels) == 8 * 6


def test_render_aa_colors_in_range():
    pixels = render(_simple_scene(), 8, 6, aa_samples=3)
    for p in pixels:
        assert 0.0 <= p.r <= 1.0
        assert 0.0 <= p.g <= 1.0
        assert 0.0 <= p.b <= 1.0
