# tests/test_color.py
import pytest
import math
from color import Color, NAMED_COLORS, color_from_kelvin

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

def test_color_mul_color():
    a = Color(0.5, 0.4, 0.2)
    b = Color(1.0, 0.5, 0.0)
    result = a * b
    assert result.r == pytest.approx(0.5)
    assert result.g == pytest.approx(0.2)
    assert result.b == pytest.approx(0.0)

def test_color_from_kelvin_warm():
    # ~2700K should be warm: red channel highest, blue channel lowest
    c = color_from_kelvin(2700)
    assert c.r > c.b
    assert c.r > c.g

def test_color_from_kelvin_cool():
    # ~10000K should be cool: blue channel highest
    c = color_from_kelvin(10000)
    assert c.b > c.r

def test_color_from_kelvin_daylight():
    # ~5500K should be close to neutral white
    c = color_from_kelvin(5500)
    assert c.r == pytest.approx(1.0)  # red is 1.0 for t <= 66

def test_color_from_kelvin_clamps():
    # Out-of-range inputs should not raise
    c_low  = color_from_kelvin(100)
    c_high = color_from_kelvin(99999)
    for ch in (c_low.r, c_low.g, c_low.b, c_high.r, c_high.g, c_high.b):
        assert 0.0 <= ch <= 1.0
