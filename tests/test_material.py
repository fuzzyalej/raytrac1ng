from material import Material
from color import Color


def test_material_defaults():
    m = Material()
    assert m.color == Color(1, 1, 1)
    assert m.opacity == 1.0
    assert m.reflect == 0.0
    assert m.ior == 1.0


def test_material_explicit():
    m = Material(color=Color(1, 0, 0), opacity=0.5, reflect=0.8, ior=1.5)
    assert m.color == Color(1, 0, 0)
    assert m.opacity == 0.5
    assert m.reflect == 0.8
    assert m.ior == 1.5


def test_material_clamps_opacity():
    m = Material(opacity=2.0)
    assert m.opacity == 1.0
    m2 = Material(opacity=-0.5)
    assert m2.opacity == 0.0


def test_material_clamps_reflect():
    m = Material(reflect=1.5)
    assert m.reflect == 1.0
    m2 = Material(reflect=-0.1)
    assert m2.reflect == 0.0


def test_material_clamps_ior():
    m = Material(ior=0.5)
    assert m.ior == 1.0
    m2 = Material(ior=1.5)
    assert m2.ior == 1.5
