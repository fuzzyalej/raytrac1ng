import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lang_parser import parse_source, ParseError, SceneSphere, ScenePlane, SceneBox
import pytest


# ── Value-returning functions ──────────────────────────────────────────────

def test_fn_returns_number():
    src = """
    let double = fn(x) { x * 2 }
    sphere { center (0,1,0)  radius double(1.5)  color (1,1,1) }
    """
    items = parse_source(src)
    assert items[0].radius == pytest.approx(3.0)

def test_fn_returns_vec3():
    src = """
    let above = fn(y) { (0, y, 0) }
    sphere { center above(2.5)  radius 1.0  color (1,1,1) }
    """
    items = parse_source(src)
    assert items[0].center == (0.0, 2.5, 0.0)

def test_fn_with_let_inside():
    src = """
    let circle_pos = fn(i, r) {
      let angle = i * 2
      (cos(angle), 0, sin(angle)) * r
    }
    sphere { center circle_pos(0, 3.0)  radius 0.5  color (1,1,1) }
    """
    items = parse_source(src)
    assert len(items) == 1
    assert items[0].radius == pytest.approx(0.5)

def test_fn_multi_param():
    src = """
    let add = fn(a, b) { a + b }
    sphere { center (0,1,0)  radius add(1.0, 0.5)  color (1,1,1) }
    """
    items = parse_source(src)
    assert items[0].radius == pytest.approx(1.5)

def test_fn_calls_another_fn():
    src = """
    let double = fn(x) { x * 2 }
    let quad   = fn(x) { double(double(x)) }
    sphere { center (0,1,0)  radius quad(0.5)  color (1,1,1) }
    """
    items = parse_source(src)
    assert items[0].radius == pytest.approx(2.0)


# ── Scene-emitting functions ───────────────────────────────────────────────

def test_fn_emits_sphere():
    src = """
    let place = fn(x) {
      sphere { center (x, 1, 0)  radius 0.5  color (1,0,0) }
    }
    place(2.0)
    """
    items = parse_source(src)
    assert len(items) == 1
    assert isinstance(items[0], SceneSphere)
    assert items[0].center == (2.0, 1.0, 0.0)

def test_fn_emits_multiple_shapes():
    src = """
    let pair = fn(x) {
      sphere { center (x, 0, 0)  radius 0.3  color (1,0,0) }
      sphere { center (x, 1, 0)  radius 0.3  color (0,0,1) }
    }
    pair(1.0)
    """
    items = parse_source(src)
    assert len(items) == 2
    assert items[0].center == (1.0, 0.0, 0.0)
    assert items[1].center == (1.0, 1.0, 0.0)

def test_fn_called_in_for_loop():
    src = """
    let place = fn(i) {
      sphere { center (i, 1, 0)  radius 0.5  color (1,1,1) }
    }
    for i in range(3) { place(i) }
    """
    items = parse_source(src)
    assert len(items) == 3
    assert items[0].center == (0.0, 1.0, 0.0)
    assert items[2].center == (2.0, 1.0, 0.0)

def test_fn_emit_preserves_order():
    src = """
    let place = fn(x, color) {
      sphere { center (x, 1, 0)  radius 0.5  color color }
    }
    place(0.0, (1,0,0))
    place(1.0, (0,1,0))
    place(2.0, (0,0,1))
    """
    items = parse_source(src)
    assert len(items) == 3
    assert items[0].color == (1.0, 0.0, 0.0)
    assert items[1].color == (0.0, 1.0, 0.0)
    assert items[2].color == (0.0, 0.0, 1.0)


# ── Conditionals ───────────────────────────────────────────────────────────

def test_if_true_branch():
    src = """
    let x = 5.0
    if x > 3 {
      sphere { center (0,1,0)  radius 1.0  color (1,0,0) }
    }
    """
    items = parse_source(src)
    assert len(items) == 1
    assert isinstance(items[0], SceneSphere)

def test_if_false_branch_skipped():
    src = """
    let x = 1.0
    if x > 3 {
      sphere { center (0,1,0)  radius 1.0  color (1,0,0) }
    }
    """
    items = parse_source(src)
    assert len(items) == 0

def test_if_else():
    src = """
    let x = 1.0
    if x > 3 {
      sphere { center (0,1,0)  radius 1.0  color (1,0,0) }
    } else {
      sphere { center (0,1,0)  radius 0.5  color (0,0,1) }
    }
    """
    items = parse_source(src)
    assert len(items) == 1
    assert items[0].radius == pytest.approx(0.5)
    assert items[0].color == (0.0, 0.0, 1.0)

def test_if_else_if_else():
    src = """
    let x = 2.0
    if x > 5 {
      sphere { center (0,1,0)  radius 3.0  color (1,0,0) }
    } else if x > 1 {
      sphere { center (0,1,0)  radius 2.0  color (0,1,0) }
    } else {
      sphere { center (0,1,0)  radius 1.0  color (0,0,1) }
    }
    """
    items = parse_source(src)
    assert len(items) == 1
    assert items[0].radius == pytest.approx(2.0)
    assert items[0].color == (0.0, 1.0, 0.0)

def test_all_comparison_ops():
    def _check(cond, expected_r):
        src = f"""
        if {cond} {{
          sphere {{ center (0,1,0)  radius 1.0  color (1,1,1) }}
        }} else {{
          sphere {{ center (0,1,0)  radius 2.0  color (1,1,1) }}
        }}
        """
        items = parse_source(src)
        assert items[0].radius == pytest.approx(expected_r)

    _check("1 == 1", 1.0)
    _check("1 == 2", 2.0)
    _check("1 != 2", 1.0)
    _check("1 != 1", 2.0)
    _check("2 > 1",  1.0)
    _check("1 > 2",  2.0)
    _check("1 < 2",  1.0)
    _check("2 < 1",  2.0)
    _check("1 <= 1", 1.0)
    _check("2 <= 1", 2.0)
    _check("1 >= 1", 1.0)
    _check("1 >= 2", 2.0)

def test_if_as_return_value():
    src = """
    let bigger = fn(a, b) {
      if a > b { a } else { b }
    }
    sphere { center (0,1,0)  radius bigger(1.5, 0.8)  color (1,1,1) }
    """
    items = parse_source(src)
    assert items[0].radius == pytest.approx(1.5)

def test_if_in_fn_emits_shapes():
    src = """
    let place = fn(i, mat) {
      if i == 0 {
        sphere { center (0,1,0)  radius 1.0  color (1,0,0) }
      } else if i < 4 {
        box { min (-0.5,0,-0.5)  max (0.5,1,0.5)  color (0,1,0) }
      } else {
        sphere { center (0,1,0)  radius 0.3  color (0,0,1) }
      }
    }
    place(0.0, (1,1,1))
    place(2.0, (1,1,1))
    place(5.0, (1,1,1))
    """
    items = parse_source(src)
    assert len(items) == 3
    assert isinstance(items[0], SceneSphere)
    assert isinstance(items[1], SceneBox)
    assert isinstance(items[2], SceneSphere)
    assert items[0].radius == pytest.approx(1.0)
    assert items[2].radius == pytest.approx(0.3)


# ── Error cases ────────────────────────────────────────────────────────────

def test_undefined_function_raises():
    with pytest.raises(ParseError):
        parse_source("sphere { center (0,1,0)  radius undefined_fn(1)  color (1,1,1) }")

def test_wrong_arg_count_raises():
    with pytest.raises(ParseError):
        parse_source("""
        let f = fn(a, b) { a + b }
        sphere { center (0,1,0)  radius f(1.0)  color (1,1,1) }
        """)

def test_vec3_comparison_raises():
    with pytest.raises(ParseError):
        parse_source("""
        if (1,0,0) == (1,0,0) {
          sphere { center (0,1,0)  radius 1.0  color (1,1,1) }
        }
        """)
