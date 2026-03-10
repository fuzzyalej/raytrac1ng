# tests/test_new_parser_transform.py
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from new_parser import parse_scene
from shapes import TransformedShape, Sphere, Transform
import tempfile

def _parse(src: str):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pow', delete=False) as f:
        f.write(src)
        path = f.name
    try:
        scene = parse_scene(path)
    finally:
        os.unlink(path)
    return scene

def test_sphere_with_translate_gives_transformed_shape():
    src = """
    camera { location (0,0,-10)  look_at (0,0,0)  fov 60 }
    let t = transform { translate (5, 0, 0) }
    sphere { center (0,0,0)  radius 1  color (1,0,0)  transform t }
    """
    scene = _parse(src)
    assert len(scene.objects) == 1
    obj = scene.objects[0]
    assert isinstance(obj, TransformedShape)
    assert isinstance(obj.shape, Sphere)
    assert obj.transform.translate == pytest.approx((5.0, 0.0, 0.0), abs=1e-9)

def test_shape_without_transform_is_not_wrapped():
    src = """
    camera { location (0,0,-10)  look_at (0,0,0)  fov 60 }
    sphere { center (0,0,0)  radius 1 }
    """
    scene = _parse(src)
    obj = scene.objects[0]
    assert isinstance(obj, Sphere)
    assert not isinstance(obj, TransformedShape)

def test_union_with_transform_gives_transformed_shape():
    from shapes import CSGUnion
    src = """
    camera { location (0,0,-10)  look_at (0,0,0)  fov 60 }
    let t = transform { scale (2, 1, 1) }
    union {
      transform t
      sphere { center (0,0,0)  radius 1 }
      box    { min (-2,-1,-1)  max (2,1,1) }
    }
    """
    scene = _parse(src)
    obj = scene.objects[0]
    assert isinstance(obj, TransformedShape)
    assert isinstance(obj.shape, CSGUnion)

def test_plane_with_transform_gives_transformed_shape():
    from shapes import Plane
    src = """
    camera { location (0,0,-10)  look_at (0,0,0)  fov 60 }
    let t = transform { rotate (0, 45, 0) }
    plane { normal (0,1,0)  offset 0  transform t }
    """
    scene = _parse(src)
    obj = scene.objects[0]
    assert isinstance(obj, TransformedShape)
    assert isinstance(obj.shape, Plane)

def test_csg_child_with_transform_wraps_child_not_parent():
    """Child transform wraps only the child; parent CSG is not wrapped."""
    from shapes import CSGUnion, TransformedShape, Sphere
    src = """
    camera { location (0,0,-10)  look_at (0,0,0)  fov 60 }
    let t = transform { translate (3, 0, 0) }
    union {
      sphere { center (0,0,0)  radius 1  transform t }
      sphere { center (2,0,0)  radius 1 }
    }
    """
    scene = _parse(src)
    obj = scene.objects[0]
    assert isinstance(obj, CSGUnion), "parent union should NOT be wrapped"
    assert isinstance(obj.children[0], TransformedShape), "first child should be wrapped"
    assert isinstance(obj.children[0].shape, Sphere)
    assert isinstance(obj.children[1], Sphere), "second child should not be wrapped"

def test_mesh_with_transform_gives_transformed_shape():
    """Mesh loaded with a transform must be wrapped in TransformedShape."""
    import os
    mesh_dir = os.path.join(os.path.dirname(__file__), "..", "examples", "models")
    # Use the boot.obj that already exists in the project
    src = f"""
    camera {{ location (0,0,-10)  look_at (0,0,0)  fov 60 }}
    let t = transform {{ scale 0.5 }}
    mesh {{ file "models/boot.obj"  transform t }}
    """
    # Write the file next to the examples dir so relative path resolves
    examples_dir = os.path.join(os.path.dirname(__file__), "..", "examples")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pow',
                                     dir=examples_dir, delete=False) as f:
        f.write(src)
        path = f.name
    try:
        scene = parse_scene(path)
    finally:
        os.unlink(path)
    assert len(scene.objects) == 1
    assert isinstance(scene.objects[0], TransformedShape)
