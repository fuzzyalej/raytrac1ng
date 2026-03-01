# tests/test_color.py
import pytest
from color import Color, NAMED_COLORS

def test_color_creation():
    c = Color(1.0, 0.5, 0.0)
    assert c.r == 1.0
    assert c.g == 0.5
    assert c.b == 0.0

def test_color_add():
    a = Color(0.2, 0.3, 0.4)
    b = Color(0.1, 0.1, 0.1)
    result = a + b
    assert abs(result.r - 0.3) < 1e-9
    assert abs(result.g - 0.4) < 1e-9
    assert abs(result.b - 0.5) < 1e-9

def test_color_mul_scalar():
    c = Color(1.0, 0.5, 0.25)
    result = c * 0.5
    assert abs(result.r - 0.5) < 1e-9
    assert abs(result.g - 0.25) < 1e-9
    assert abs(result.b - 0.125) < 1e-9

def test_color_rmul_scalar():
    c = Color(1.0, 0.5, 0.25)
    result = 0.5 * c
    assert abs(result.r - 0.5) < 1e-9

def test_color_clamp():
    c = Color(1.5, -0.1, 0.5)
    clamped = c.clamp()
    assert clamped.r == 1.0
    assert clamped.g == 0.0
    assert clamped.b == 0.5

def test_color_to_bytes():
    c = Color(1.0, 0.5, 0.0)
    assert c.to_bytes() == (255, 127, 0)

def test_named_colors_exist():
    for name in ['red', 'green', 'blue', 'white', 'black',
                 'yellow', 'cyan', 'magenta', 'orange',
                 'purple', 'pink', 'brown', 'gray']:
        assert name in NAMED_COLORS, f"Missing named color: {name}"
    assert isinstance(NAMED_COLORS['red'], Color)
