"""Integration test: .pow file with mesh block → Scene with TriangleMesh."""
import os
import tempfile
import pytest

from new_parser import parse_scene
from shapes import TriangleMesh


# Minimal OBJ written alongside the .pow file so relative paths work
OBJ_CONTENT = """\
v 0 0 0
v 1 0 0
v 0 1 0
f 1 2 3
"""

POW_TEMPLATE = """\
camera {{ location (0,0,-5)  look_at (0,0,0)  fov 60 }}
light  {{ position (5,10,-5) }}
mesh   {{ file "{obj_name}" }}
"""

POW_WITH_COLOR_TEMPLATE = """\
camera {{ location (0,0,-5)  look_at (0,0,0)  fov 60 }}
light  {{ position (5,10,-5) }}
mesh   {{ file "{obj_name}"  color (0.8, 0.3, 0.1) }}
"""


def _make_scene(pow_template):
    d = tempfile.mkdtemp()
    obj_path = os.path.join(d, 'test.obj')
    with open(obj_path, 'w') as f:
        f.write(OBJ_CONTENT)
    pow_path = os.path.join(d, 'test.pow')
    with open(pow_path, 'w') as f:
        f.write(pow_template.format(obj_name='test.obj'))
    return parse_scene(pow_path), d


def test_mesh_in_scene_objects():
    scene, _ = _make_scene(POW_TEMPLATE)
    meshes = [o for o in scene.objects if isinstance(o, TriangleMesh)]
    assert len(meshes) == 1


def test_mesh_has_triangles():
    scene, _ = _make_scene(POW_TEMPLATE)
    mesh = scene.objects[0]
    assert len(mesh._triangles) == 1


def test_mesh_color_override():
    scene, _ = _make_scene(POW_WITH_COLOR_TEMPLATE)
    mesh = scene.objects[0]
    tri = mesh._triangles[0]
    assert abs(tri.color.r - 0.8) < 1e-6


def test_missing_obj_raises():
    d = tempfile.mkdtemp()
    pow_path = os.path.join(d, 'test.pow')
    with open(pow_path, 'w') as f:
        f.write(
            'camera { location (0,0,-5) look_at (0,0,0) fov 60 }\n'
            'light { position (5,10,-5) }\n'
            'mesh { file "nonexistent.obj" }\n'
        )
    with pytest.raises(OSError):
        parse_scene(pow_path)
