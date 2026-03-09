# tests/test_obj_loader.py
import os
import textwrap
import tempfile

from obj_loader import load_obj
from shapes import TriangleMesh, Triangle
from color import Color
from vector import Vec3


def _write_file(content: str, suffix: str) -> str:
    f = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
    f.write(textwrap.dedent(content))
    f.close()
    return f.name


# ---- minimal OBJ with one triangle ----

OBJ_ONE_TRI = """\
v 0 0 0
v 1 0 0
v 0 1 0
f 1 2 3
"""

def test_load_single_triangle():
    path = _write_file(OBJ_ONE_TRI, '.obj')
    mesh = load_obj(path)
    os.unlink(path)
    assert isinstance(mesh, TriangleMesh)


def test_triangle_vertices():
    path = _write_file(OBJ_ONE_TRI, '.obj')
    mesh = load_obj(path)
    os.unlink(path)
    tris = mesh._triangles
    assert len(tris) == 1
    assert abs(tris[0].v0.x) < 1e-9
    assert abs(tris[0].v1.x - 1.0) < 1e-9


# ---- quad triangulation ----

OBJ_QUAD = """\
v 0 0 0
v 1 0 0
v 1 1 0
v 0 1 0
f 1 2 3 4
"""

def test_quad_produces_two_triangles():
    path = _write_file(OBJ_QUAD, '.obj')
    mesh = load_obj(path)
    os.unlink(path)
    assert len(mesh._triangles) == 2


# ---- vertex normals ----

OBJ_WITH_NORMALS = """\
v 0 0 0
v 1 0 0
v 0 1 0
vn 0 0 -1
vn 0 0 -1
vn 0 0 -1
f 1//1 2//2 3//3
"""

def test_vertex_normals_loaded():
    path = _write_file(OBJ_WITH_NORMALS, '.obj')
    mesh = load_obj(path)
    os.unlink(path)
    tri = mesh._triangles[0]
    assert tri.n0 is not None
    assert abs(tri.n0.z + 1.0) < 1e-6


# ---- texture coords parsed but ignored ----

OBJ_WITH_UV = """\
v 0 0 0
v 1 0 0
v 0 1 0
vt 0.0 0.0
vt 1.0 0.0
vt 0.0 1.0
f 1/1 2/2 3/3
"""

def test_uv_coords_dont_break_loading():
    path = _write_file(OBJ_WITH_UV, '.obj')
    mesh = load_obj(path)
    os.unlink(path)
    assert len(mesh._triangles) == 1


# ---- negative indices ----

OBJ_NEG_INDICES = """\
v 0 0 0
v 1 0 0
v 0 1 0
f -3 -2 -1
"""

def test_negative_face_indices():
    path = _write_file(OBJ_NEG_INDICES, '.obj')
    mesh = load_obj(path)
    os.unlink(path)
    assert len(mesh._triangles) == 1


# ---- MTL material loading ----

MTL_CONTENT = """\
newmtl red_mat
Kd 1.0 0.0 0.0
d 0.5
"""

OBJ_WITH_MTL_TEMPLATE = """\
mtllib {mtl_filename}
v 0 0 0
v 1 0 0
v 0 1 0
usemtl red_mat
f 1 2 3
"""

def test_mtl_color_applied():
    mtl = _write_file(MTL_CONTENT, '.mtl')
    mtl_name = os.path.basename(mtl)
    mtl_dir = os.path.dirname(mtl)
    obj_content = OBJ_WITH_MTL_TEMPLATE.format(mtl_filename=mtl_name)
    obj_path = os.path.join(mtl_dir, 'test_mesh.obj')
    with open(obj_path, 'w') as f:
        f.write(obj_content)
    try:
        mesh = load_obj(obj_path)
        tri = mesh._triangles[0]
        assert abs(tri.color.r - 1.0) < 1e-6
        assert abs(tri.color.g) < 1e-6
        assert abs(tri.opacity - 0.5) < 1e-6
    finally:
        os.unlink(mtl)
        os.unlink(obj_path)


def test_missing_mtl_uses_defaults():
    obj = _write_file("v 0 0 0\nv 1 0 0\nv 0 1 0\nmtllib nonexistent.mtl\nf 1 2 3\n", '.obj')
    mesh = load_obj(obj)
    os.unlink(obj)
    tri = mesh._triangles[0]
    assert tri.color == Color(1.0, 1.0, 1.0)


# ---- material override from load_obj args ----

def test_color_override():
    path = _write_file(OBJ_ONE_TRI, '.obj')
    mesh = load_obj(path, color=Color(0.5, 0.5, 0.5))
    os.unlink(path)
    assert abs(mesh._triangles[0].color.r - 0.5) < 1e-6


def test_reflect_ior_always_applied():
    path = _write_file(OBJ_ONE_TRI, '.obj')
    mesh = load_obj(path, reflect=0.3, ior=1.5)
    os.unlink(path)
    assert abs(mesh._triangles[0].reflect - 0.3) < 1e-6
    assert abs(mesh._triangles[0].ior - 1.5) < 1e-6


def test_opacity_override_without_color():
    path = _write_file(OBJ_ONE_TRI, '.obj')
    mesh = load_obj(path, opacity=0.5)
    os.unlink(path)
    assert abs(mesh._triangles[0].opacity - 0.5) < 1e-6
    # Color should remain unchanged (white)
    assert mesh._triangles[0].color == Color(1.0, 1.0, 1.0)
