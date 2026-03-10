"""Tests for multiprocessing render path."""
import pytest
from scene import Scene, Camera, Light
from shapes import Sphere
from vector import Vec3
from color import Color
from material import Material
from rendering import render
from rendering.renderer import _render_row_chunk


def _simple_scene() -> Scene:
    """Deterministic scene: point light, opaque sphere, no AA — no random calls."""
    s = Scene()
    s.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    s.lights = [Light(position=Vec3(5, 10, -5))]  # point light (radius=0)
    s.objects = [Sphere(Vec3(0, 0, 0), 1.0, material=Material(color=Color(1, 0, 0)))]
    return s


def test_render_row_chunk_pixel_count():
    """_render_row_chunk returns exactly (y_end - y_start) * width Color objects."""
    scene = _simple_scene()
    width, height = 10, 8
    result = _render_row_chunk((scene, width, height, 2, 5, 0))
    assert len(result) == 3 * width  # rows 2,3,4


def test_render_row_chunk_returns_colors():
    """Every element returned is a Color."""
    scene = _simple_scene()
    result = _render_row_chunk((scene, 4, 4, 0, 4, 0))
    assert all(isinstance(p, Color) for p in result)


def test_multiprocess_matches_single_process():
    """render() with workers=2 returns identical pixels to workers=1 for a deterministic scene."""
    scene = _simple_scene()
    w, h = 20, 15
    single = render(scene, w, h, aa_samples=0, workers=1)
    multi  = render(scene, w, h, aa_samples=0, workers=2)
    assert len(single) == len(multi) == w * h
    for i, (a, b) in enumerate(zip(single, multi)):
        assert a.r == pytest.approx(b.r, abs=1e-9), f"pixel {i} red differs"
        assert a.g == pytest.approx(b.g, abs=1e-9), f"pixel {i} green differs"
        assert a.b == pytest.approx(b.b, abs=1e-9), f"pixel {i} blue differs"
