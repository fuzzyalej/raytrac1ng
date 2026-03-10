# tests/test_parser_transform.py
import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from lang_parser import parse_source, ParseError, SceneTransform, SceneSphere
from lexer import tokenise
from lang_parser import _ProgramParser, BUILTINS

def _env(src):
    """Parse src and return the environment dict (to inspect stored variables)."""
    tokens = tokenise(src)
    env = dict(BUILTINS)
    p = _ProgramParser(tokens, env)
    p.parse_program()
    return env

def test_parse_full_transform():
    src = "let t = transform { scale (2,1,0.5)  rotate (0,45,0)  translate (3,0,0) }"
    env = _env(src)
    t = env['t']
    assert isinstance(t, SceneTransform)
    assert t.scale     == pytest.approx((2.0, 1.0, 0.5), abs=1e-9)
    assert t.rotate    == pytest.approx((0.0, 45.0, 0.0), abs=1e-9)
    assert t.translate == pytest.approx((3.0, 0.0, 0.0), abs=1e-9)

def test_parse_transform_defaults():
    """Omitting fields gives defaults."""
    env = _env("let t = transform { rotate (0, 90, 0) }")
    t = env['t']
    assert isinstance(t, SceneTransform)
    assert t.scale     == (1.0, 1.0, 1.0)
    assert t.translate == (0.0, 0.0, 0.0)
    assert t.rotate    == pytest.approx((0.0, 90.0, 0.0), abs=1e-9)

def test_parse_transform_uniform_scale():
    """Scalar scale shorthand: scale 2.0"""
    env = _env("let t = transform { scale 2.0 }")
    t = env['t']
    assert t.scale == pytest.approx((2.0, 2.0, 2.0), abs=1e-9)

def test_unknown_transform_field_raises():
    with pytest.raises(ParseError, match="unknown transform field"):
        parse_source("let t = transform { size 5 }")


def test_sphere_with_transform():
    src = """
    let t = transform { translate (5, 0, 0) }
    sphere { center (0,0,0)  radius 1  transform t }
    """
    items = parse_source(src)
    s = items[0]
    assert isinstance(s, SceneSphere)
    assert isinstance(s.transform, SceneTransform)
    assert s.transform.translate == pytest.approx((5.0, 0.0, 0.0), abs=1e-9)

def test_box_with_transform():
    from lang_parser import SceneBox
    src = """
    let t = transform { scale (2, 1, 1) }
    box { min (-1,-1,-1)  max (1,1,1)  transform t }
    """
    items = parse_source(src)
    b = items[0]
    assert isinstance(b, SceneBox)
    assert b.transform is not None

def test_shape_without_transform_has_none():
    from lang_parser import SceneSphere
    src = "sphere { center (0,0,0)  radius 1 }"
    items = parse_source(src)
    assert items[0].transform is None

def test_undefined_transform_raises():
    src = "sphere { center (0,0,0)  radius 1  transform no_such }"
    with pytest.raises(ParseError):
        parse_source(src)

def test_csg_child_with_transform():
    """A primitive inside a CSG block can have a transform."""
    from lang_parser import SceneCSGUnion, SceneSphere
    src = """
    let t = transform { translate (1, 0, 0) }
    union {
      sphere { center (0,0,0)  radius 1  transform t }
      sphere { center (0,0,0)  radius 2 }
    }
    """
    items = parse_source(src)
    u = items[0]
    assert isinstance(u, SceneCSGUnion)
    assert isinstance(u.children[0].transform, SceneTransform)
    assert u.children[1].transform is None


def test_union_with_transform():
    from lang_parser import SceneCSGUnion
    src = """
    let t = transform { rotate (0, 45, 0) }
    union {
      transform t
      sphere { center (0,0,0)  radius 1 }
      box    { min (-1,-1,-1)  max (1,1,1) }
    }
    """
    items = parse_source(src)
    u = items[0]
    assert isinstance(u, SceneCSGUnion)
    assert isinstance(u.transform, SceneTransform)
    assert u.transform.rotate == pytest.approx((0.0, 45.0, 0.0), abs=1e-9)

def test_difference_with_transform():
    from lang_parser import SceneCSGDifference
    src = """
    let t = transform { scale (2, 1, 1) }
    difference {
      transform t
      sphere { center (0,0,0)  radius 2 }
      sphere { center (0,0,0)  radius 1 }
    }
    """
    items = parse_source(src)
    d = items[0]
    assert isinstance(d, SceneCSGDifference)
    assert d.transform is not None

def test_csg_without_transform_has_none():
    from lang_parser import SceneCSGUnion
    src = """
    union {
      sphere { center (0,0,0)  radius 1 }
      sphere { center (0,0,0)  radius 2 }
    }
    """
    items = parse_source(src)
    assert items[0].transform is None
