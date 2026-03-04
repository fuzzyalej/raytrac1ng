import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lexer import tokenise
from lang_parser import Parser, ParseError
import pytest

def parse_expr(src, env=None):
    tokens = tokenise(src)
    p = Parser(tokens, env or {})
    return p.parse_expr()

def test_number():
    assert parse_expr("3.14") == pytest.approx(3.14)

def test_addition():
    assert parse_expr("1 + 2") == pytest.approx(3.0)

def test_subtraction():
    assert parse_expr("5 - 2") == pytest.approx(3.0)

def test_multiplication():
    assert parse_expr("3 * 4") == pytest.approx(12.0)

def test_division():
    assert parse_expr("10 / 4") == pytest.approx(2.5)

def test_precedence():
    assert parse_expr("2 + 3 * 4") == pytest.approx(14.0)

def test_parens():
    assert parse_expr("(2 + 3) * 4") == pytest.approx(20.0)

def test_variable():
    assert parse_expr("x", env={"x": 5.0}) == pytest.approx(5.0)

def test_vec3_literal():
    assert parse_expr("(1, 2, 3)") == (1.0, 2.0, 3.0)

def test_vec3_add():
    assert parse_expr("(1,0,0) + (0,1,0)") == (1.0, 1.0, 0.0)

def test_vec3_scale():
    assert parse_expr("(1, 2, 3) * 2") == (2.0, 4.0, 6.0)

def test_scalar_times_vec3():
    assert parse_expr("2 * (1, 2, 3)") == (2.0, 4.0, 6.0)

def test_sin():
    import math
    assert parse_expr("sin(0)") == pytest.approx(0.0)
    assert parse_expr("sin(pi)") == pytest.approx(0.0, abs=1e-9)

def test_cos():
    import math
    assert parse_expr("cos(0)") == pytest.approx(1.0)

def test_abs_builtin():
    assert parse_expr("abs(-3)") == pytest.approx(3.0)

def test_pi():
    import math
    assert parse_expr("pi") == pytest.approx(math.pi)

def test_list_literal():
    result = parse_expr("[(1,0,0), (0,1,0)]")
    assert result == [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]

def test_empty_list():
    result = parse_expr("[]")
    assert result == []

def test_undefined_variable_raises():
    with pytest.raises(ParseError):
        parse_expr("undefined_var")

def test_expr_with_loop_var():
    assert parse_expr("i * 2.5", env={"i": 3.0}) == pytest.approx(7.5)

def test_unary_minus():
    assert parse_expr("-3") == pytest.approx(-3.0)

def test_string_literal():
    result = parse_expr('"hello"')
    assert result == "hello"
