import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parsers.pow_parser import (parse_source, ParseError,
    SceneSphere, SceneCamera, SceneLight, ScenePlane,
    SceneBox, SceneCylinder, SceneCone, SceneTorus)
import pytest

def test_camera_block():
    src = """
    camera {
      location (0, 2, -5)
      look_at  (0, 0, 0)
      fov      60
    }
    """
    items = parse_source(src)
    cam = items[0]
    assert isinstance(cam, SceneCamera)
    assert cam.location == (0.0, 2.0, -5.0)
    assert cam.fov == 60.0

def test_light_block():
    src = """
    light { position (4, 8, -4)  radius 1.5  samples 24 }
    """
    items = parse_source(src)
    l = items[0]
    assert isinstance(l, SceneLight)
    assert l.position == (4.0, 8.0, -4.0)
    assert l.radius == pytest.approx(1.5)
    assert l.samples == 24

def test_sphere_block():
    src = """
    sphere {
      center (0, 1, 0)
      radius 1.0
      color  (1, 0, 0)
    }
    """
    items = parse_source(src)
    s = items[0]
    assert isinstance(s, SceneSphere)
    assert s.radius == 1.0
    assert s.color == (1.0, 0.0, 0.0)

def test_plane_block():
    src = """
    plane { normal (0,1,0)  offset 0  color (0.5, 0.5, 0.5) }
    """
    items = parse_source(src)
    p = items[0]
    assert isinstance(p, ScenePlane)
    assert p.normal == (0.0, 1.0, 0.0)

def test_box_block():
    src = """
    box { min (-1,-1,-1)  max (1,1,1)  color (1,0,0) }
    """
    items = parse_source(src)
    b = items[0]
    assert isinstance(b, SceneBox)
    assert b.min == (-1.0, -1.0, -1.0)
    assert b.max == (1.0, 1.0, 1.0)
    assert b.color == (1.0, 0.0, 0.0)

def test_cylinder_block():
    src = """
    cylinder { bottom (0,0,0)  top (0,2,0)  radius 0.5  color (0,1,0) }
    """
    items = parse_source(src)
    c = items[0]
    assert isinstance(c, SceneCylinder)
    assert c.bottom == (0.0, 0.0, 0.0)
    assert c.top == (0.0, 2.0, 0.0)
    assert c.radius == pytest.approx(0.5)

def test_cone_block():
    src = """
    cone { bottom (0,0,0)  top (0,2,0)  bottom_radius 1.0  top_radius 0.0 }
    """
    items = parse_source(src)
    c = items[0]
    assert isinstance(c, SceneCone)
    assert c.bottom_radius == pytest.approx(1.0)
    assert c.top_radius == pytest.approx(0.0)

def test_torus_block():
    src = """
    torus { center (0,0,0)  axis (0,1,0)  major_radius 1.5  minor_radius 0.4 }
    """
    items = parse_source(src)
    t = items[0]
    assert isinstance(t, SceneTorus)
    assert t.major_radius == pytest.approx(1.5)
    assert t.minor_radius == pytest.approx(0.4)

def test_let_and_use():
    src = """
    let r = 2.5
    sphere { center (0,0,0)  radius r  color (1,1,1) }
    """
    items = parse_source(src)
    assert items[0].radius == pytest.approx(2.5)

def test_for_range():
    src = """
    for i in range(3) {
      sphere { center (i, 0, 0)  radius 0.5  color (1,1,1) }
    }
    """
    items = parse_source(src)
    assert len(items) == 3
    centers = [s.center for s in items]
    assert centers == [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0)]

def test_for_range_two_args():
    src = """
    for i in range(2, 5) {
      sphere { center (i, 0, 0)  radius 0.5  color (1,1,1) }
    }
    """
    items = parse_source(src)
    assert len(items) == 3

def test_for_list():
    src = """
    let positions = [(0,0,0), (1,0,0), (2,0,0)]
    for p in positions {
      sphere { center p  radius 0.5  color (1,1,1) }
    }
    """
    items = parse_source(src)
    assert len(items) == 3
    assert items[1].center == (1.0, 0.0, 0.0)

def test_let_expression():
    src = """
    let spacing = 2.5
    sphere { center (spacing * 2, 0, 0)  radius 1.0  color (1,1,1) }
    """
    items = parse_source(src)
    assert items[0].center == (5.0, 0.0, 0.0)

def test_material_block():
    src = """
    let glass = material {
      color   (0.2, 0.8, 1.0)
      opacity 0.3
      reflect 0.1
      ior     1.5
    }
    sphere { center (0,1,0)  radius 1.0  material glass }
    """
    items = parse_source(src)
    s = items[0]
    assert s.color == (0.2, 0.8, 1.0)
    assert s.opacity == pytest.approx(0.3)
    assert s.reflect == pytest.approx(0.1)
    assert s.ior == pytest.approx(1.5)

def test_material_partial_fields():
    # material with only some fields — defaults apply for the rest
    src = """
    let m = material { color (1.0, 0.0, 0.0) }
    sphere { center (0,0,0)  radius 1.0  material m }
    """
    items = parse_source(src)
    s = items[0]
    assert s.color == (1.0, 0.0, 0.0)
    assert s.opacity == pytest.approx(1.0)   # default
    assert s.reflect == pytest.approx(0.0)   # default
    assert s.ior == pytest.approx(1.0)       # default

def test_inline_fields_override_material():
    src = """
    let m = material { color (1.0, 0.0, 0.0)  opacity 0.5 }
    sphere { center (0,0,0)  radius 1.0  material m  opacity 0.9 }
    """
    items = parse_source(src)
    assert items[0].opacity == pytest.approx(0.9)
    assert items[0].color == (1.0, 0.0, 0.0)

def test_comment_ignored():
    src = """
    // This is a comment
    sphere { center (0,0,0)  radius 1.0  color (1,1,1) }
    """
    items = parse_source(src)
    assert len(items) == 1

def test_sphere_material_fields():
    src = """
    sphere { center (0,1,0)  radius 1.0  color (1,1,1)  opacity 0.5  reflect 0.3  ior 1.33 }
    """
    items = parse_source(src)
    s = items[0]
    assert s.opacity == pytest.approx(0.5)
    assert s.reflect == pytest.approx(0.3)
    assert s.ior == pytest.approx(1.33)

def test_nested_for_expression():
    src = """
    let count = 3
    let spacing = 2.0
    for i in range(count) {
      sphere { center (i * spacing, 0, 0)  radius 0.5  color (1,1,1) }
    }
    """
    items = parse_source(src)
    assert len(items) == 3
    assert items[2].center == pytest.approx((4.0, 0.0, 0.0))
