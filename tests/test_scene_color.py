# tests/test_scene_color.py
from color import Color
from material import Material
from scene import Light
from shapes import Sphere, Plane
from vector import Vec3

def test_sphere_default_color():
    s = Sphere(Vec3(0, 0, 0), 1.0)
    assert s.material.color == Color(1.0, 1.0, 1.0)

def test_sphere_custom_color():
    s = Sphere(Vec3(0, 0, 0), 1.0, material=Material(color=Color(1.0, 0.0, 0.0)))
    assert s.material.color.r == 1.0
    assert s.material.color.g == 0.0

def test_plane_default_color():
    p = Plane(Vec3(0, 1, 0), 0.0)
    assert p.material.color == Color(1.0, 1.0, 1.0)

def test_plane_custom_color():
    p = Plane(Vec3(0, 1, 0), 0.0, material=Material(color=Color(0.0, 0.5, 1.0)))
    assert p.material.color.b == 1.0

def test_sphere_default_opacity():
    s = Sphere(Vec3(0, 0, 0), 1.0)
    assert s.material.opacity == 1.0

def test_sphere_custom_opacity():
    s = Sphere(Vec3(0, 0, 0), 1.0, material=Material(opacity=0.5))
    assert s.material.opacity == 0.5

def test_plane_default_opacity():
    p = Plane(Vec3(0, 1, 0), 0.0)
    assert p.material.opacity == 1.0

def test_plane_custom_opacity():
    p = Plane(Vec3(0, 1, 0), 0.0, material=Material(opacity=0.0))
    assert p.material.opacity == 0.0

def test_sphere_opacity_clamped():
    s = Sphere(Vec3(0, 0, 0), 1.0, material=Material(opacity=1.5))
    assert s.material.opacity == 1.0
    s2 = Sphere(Vec3(0, 0, 0), 1.0, material=Material(opacity=-0.5))
    assert s2.material.opacity == 0.0

def test_plane_opacity_clamped():
    p = Plane(Vec3(0, 1, 0), 0.0, material=Material(opacity=1.5))
    assert p.material.opacity == 1.0
    p2 = Plane(Vec3(0, 1, 0), 0.0, material=Material(opacity=-0.5))
    assert p2.material.opacity == 0.0

def test_light_defaults():
    light = Light(position=Vec3(0, 10, 0))
    assert light.radius == 0.0
    assert light.samples == 16

def test_light_custom_radius_and_samples():
    light = Light(position=Vec3(0, 10, 0), radius=2.0, samples=32)
    assert light.radius == 2.0
    assert light.samples == 32
