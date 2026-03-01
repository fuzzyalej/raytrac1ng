"""Tests for mirror reflections in renderer._trace()."""

import pytest
from color import Color
from scene import Scene, Camera, Light
from shapes import Sphere, Plane
from vector import Vec3
from renderer import render


def _scene_with_mirror_sphere():
    """A red sphere reflected in a mirror sphere."""
    cam = Camera(Vec3(0, 1, -5), Vec3(0, 1, 0), fov=60)
    light = Light(Vec3(5, 5, -5))
    mirror = Sphere(Vec3(-1.5, 1, 0), 1.0, Color(1, 1, 1), opacity=1.0, reflect=1.0)
    red    = Sphere(Vec3(1.5, 1, 0),  1.0, Color(1, 0, 0), opacity=1.0, reflect=0.0)
    ground = Plane(Vec3(0, 1, 0), 0.0, Color(0.8, 0.8, 0.8), opacity=1.0, reflect=0.3)
    return Scene(camera=cam, lights=[light], objects=[mirror, red, ground])


def test_reflect_zero_colors_in_range():
    """reflect=0 must produce valid colors."""
    cam = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    light = Light(Vec3(5, 5, -5))
    s = Sphere(Vec3(0, 0, 0), 1.0, Color(1, 0, 0), reflect=0.0)
    scene = Scene(camera=cam, lights=[light], objects=[s])
    pixels = render(scene, 8, 6)
    for p in pixels:
        assert 0.0 <= p.r <= 1.0
        assert 0.0 <= p.g <= 1.0
        assert 0.0 <= p.b <= 1.0


def test_render_with_reflection_completes():
    """render() with reflect > 0 must complete without error."""
    scene = _scene_with_mirror_sphere()
    pixels = render(scene, 16, 12)
    assert len(pixels) == 16 * 12


def test_render_reflection_colors_in_range():
    """All pixel colors must be valid after reflection."""
    scene = _scene_with_mirror_sphere()
    pixels = render(scene, 16, 12)
    for p in pixels:
        assert 0.0 <= p.r <= 1.0
        assert 0.0 <= p.g <= 1.0
        assert 0.0 <= p.b <= 1.0


def test_mirror_sphere_reflects_red():
    """A perfect mirror sphere facing a red sphere should have some red pixels."""
    scene = _scene_with_mirror_sphere()
    pixels = render(scene, 32, 24)
    max_red = max(p.r for p in pixels)
    assert max_red > 0.3


def test_reflect_clamped_at_construction():
    """reflect is clamped to [0, 1] at object construction time."""
    s = Sphere(Vec3(0, 0, 0), 1.0, reflect=2.0)
    assert s.reflect == 1.0
    s2 = Sphere(Vec3(0, 0, 0), 1.0, reflect=-0.5)
    assert s2.reflect == 0.0


def test_partial_reflection_differs_from_matte():
    """A mirror sphere must render differently from a matte sphere of the same color."""
    cam = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    light = Light(Vec3(5, 5, -5))

    matte  = Sphere(Vec3(0, 0, 0), 1.0, Color(0, 0, 1), reflect=0.0)
    mirror = Sphere(Vec3(0, 0, 0), 1.0, Color(0, 0, 1), reflect=1.0)

    px_matte  = render(Scene(camera=cam, lights=[light], objects=[matte]),  8, 6)
    px_mirror = render(Scene(camera=cam, lights=[light], objects=[mirror]), 8, 6)

    diffs = [abs(a.r - b.r) + abs(a.g - b.g) + abs(a.b - b.b)
             for a, b in zip(px_matte, px_mirror)]
    assert max(diffs) > 0.01
