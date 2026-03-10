"""
Integration test: parse a minimal .pow scene, render a tiny image,
verify no exceptions and correct pixel dimensions.
"""
import sys, os, tempfile, textwrap
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

MINIMAL_SCENE = textwrap.dedent("""\
    camera {
      location (0, 2, -5)
      look_at  (0, 0, 0)
      fov      60
    }
    light { position (5, 10, -3) }
    plane { normal (0,1,0)  offset 0  color (0.5, 0.5, 0.5) }
    sphere { center (0, 1, 0)  radius 1.0  color (1, 0.3, 0.3) }
""")

ALL_SHAPES_SCENE = textwrap.dedent("""\
    camera { location (0, 4, -10)  look_at (0, 1, 0)  fov 55 }
    light  { position (5, 10, -3)  radius 1.0  samples 4 }
    plane  { normal (0,1,0)  offset 0  color (0.8, 0.8, 0.8) }
    sphere { center (-3, 1, 0)  radius 0.8  color (1, 0, 0) }
    box    { min (-0.5, 0, -0.5)  max (0.5, 1, 0.5)  color (0, 1, 0) }
    cylinder { bottom (2,0,0)  top (2,2,0)  radius 0.4  color (0, 0, 1) }
    cone { bottom (4,0,0)  top (4,2,0)  bottom_radius 0.6  top_radius 0.0  color (1,1,0) }
    torus { center (0,0,3)  axis (0,1,0)  major_radius 1.0  minor_radius 0.3  color (1,0,1) }
""")

LOOP_SCENE = textwrap.dedent("""\
    camera { location (0, 3, -9)  look_at (0, 1, 0)  fov 55 }
    light  { position (4, 8, -4) }
    plane  { normal (0,1,0)  offset 0  color (0.5, 0.5, 0.5) }
    let count = 3
    let spacing = 2.0
    for i in range(count) {
      sphere { center (i * spacing, 1.0, 0)  radius 0.5  color (1,1,1) }
    }
""")

MATERIAL_SCENE = textwrap.dedent("""\
    let glass = material { color (0.8, 0.9, 1.0)  opacity 0.0  ior 1.5 }
    camera { location (0, 2, -6)  look_at (0, 1, 0)  fov 60 }
    light  { position (3, 6, -3) }
    plane  { normal (0,1,0)  offset 0  color (0.5, 0.5, 0.5) }
    sphere { center (0, 1, 0)  radius 1.0  material glass }
""")


def _write_temp(content: str, suffix=".pow") -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return f.name


def _render(path: str, width=8, height=6):
    from parsers.pow_adapter import parse_scene
    from rendering import render
    scene = parse_scene(path)
    return render(scene, width, height)


def test_minimal_scene_renders():
    path = _write_temp(MINIMAL_SCENE)
    pixels = _render(path)
    assert len(pixels) == 6 * 8


def test_all_shapes_render():
    path = _write_temp(ALL_SHAPES_SCENE)
    pixels = _render(path)
    assert len(pixels) == 6 * 8


def test_loop_scene_renders():
    path = _write_temp(LOOP_SCENE)
    pixels = _render(path)
    assert len(pixels) == 6 * 8


def test_material_scene_renders():
    path = _write_temp(MATERIAL_SCENE)
    pixels = _render(path)
    assert len(pixels) == 6 * 8


def test_old_pov_still_works():
    """Regression: existing .pov files must still parse and render."""
    from parsers.pov import parse_scene
    from rendering import render
    pov_path = os.path.join(os.path.dirname(__file__), "..", "examples", "01-basic.pov")
    scene = parse_scene(pov_path)
    pixels = render(scene, 8, 6)
    assert len(pixels) == 6 * 8
