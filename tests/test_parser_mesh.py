# tests/test_parser_mesh.py
"""Tests for parsing mesh {} blocks in the POW language."""
import pytest
from lang_parser import parse_source, SceneMesh


CAM   = "camera { location (0,0,-5)  look_at (0,0,0)  fov 60 }\n"
LIGHT = "light  { position (5,10,-5) }\n"


def test_parse_mesh_basic():
    src = CAM + LIGHT + 'mesh { file "models/boot.obj" }\n'
    items = parse_source(src)
    meshes = [i for i in items if isinstance(i, SceneMesh)]
    assert len(meshes) == 1
    assert meshes[0].file == "models/boot.obj"


def test_parse_mesh_with_color():
    src = CAM + LIGHT + 'mesh { file "a.obj"  color (0.8, 0.2, 0.1) }\n'
    items = parse_source(src)
    m = [i for i in items if isinstance(i, SceneMesh)][0]
    assert abs(m.color[0] - 0.8) < 1e-6
    assert m.color is not None


def test_parse_mesh_no_color_gives_none():
    src = CAM + LIGHT + 'mesh { file "a.obj" }\n'
    items = parse_source(src)
    m = [i for i in items if isinstance(i, SceneMesh)][0]
    assert m.color is None


def test_parse_mesh_with_reflect_ior():
    src = CAM + LIGHT + 'mesh { file "a.obj"  reflect 0.3  ior 1.5 }\n'
    items = parse_source(src)
    m = [i for i in items if isinstance(i, SceneMesh)][0]
    assert abs(m.reflect - 0.3) < 1e-6
    assert abs(m.ior - 1.5) < 1e-6
    assert m.color is None
    assert m.opacity is None


def test_parse_mesh_defaults():
    src = CAM + LIGHT + 'mesh { file "a.obj" }\n'
    items = parse_source(src)
    m = [i for i in items if isinstance(i, SceneMesh)][0]
    assert m.reflect == 0.0
    assert m.ior == 1.0


def test_parse_mesh_missing_file_raises():
    from lang_parser import ParseError
    src = CAM + LIGHT + 'mesh { color (1,0,0) }\n'
    with pytest.raises(ParseError):
        parse_source(src)


def test_parse_mesh_with_material_ref():
    src = (CAM + LIGHT +
           'let shiny = material { color (0.5, 0.5, 0.8)  reflect 0.4 }\n'
           'mesh { file "a.obj"  material shiny }\n')
    items = parse_source(src)
    m = [i for i in items if isinstance(i, SceneMesh)][0]
    assert m.color is not None
    assert abs(m.color[2] - 0.8) < 1e-6
    assert abs(m.reflect - 0.4) < 1e-6
