# tests/test_scene_color.py
from color import Color
from scene import Light
from shapes import Sphere, Plane
from vector import Vec3

def test_sphere_default_color():
    s = Sphere(Vec3(0, 0, 0), 1.0)
    assert s.color == Color(1.0, 1.0, 1.0)

def test_sphere_custom_color():
    s = Sphere(Vec3(0, 0, 0), 1.0, color=Color(1.0, 0.0, 0.0))
    assert s.color.r == 1.0
    assert s.color.g == 0.0

def test_plane_default_color():
    p = Plane(Vec3(0, 1, 0), 0.0)
    assert p.color == Color(1.0, 1.0, 1.0)

def test_plane_custom_color():
    p = Plane(Vec3(0, 1, 0), 0.0, color=Color(0.0, 0.5, 1.0))
    assert p.color.b == 1.0

def test_sphere_default_opacity():
    s = Sphere(Vec3(0, 0, 0), 1.0)
    assert s.opacity == 1.0

def test_sphere_custom_opacity():
    s = Sphere(Vec3(0, 0, 0), 1.0, opacity=0.5)
    assert s.opacity == 0.5

def test_plane_default_opacity():
    p = Plane(Vec3(0, 1, 0), 0.0)
    assert p.opacity == 1.0

def test_plane_custom_opacity():
    p = Plane(Vec3(0, 1, 0), 0.0, opacity=0.0)
    assert p.opacity == 0.0

def test_sphere_opacity_clamped():
    s = Sphere(Vec3(0, 0, 0), 1.0, opacity=1.5)
    assert s.opacity == 1.0
    s2 = Sphere(Vec3(0, 0, 0), 1.0, opacity=-0.5)
    assert s2.opacity == 0.0

def test_plane_opacity_clamped():
    p = Plane(Vec3(0, 1, 0), 0.0, opacity=1.5)
    assert p.opacity == 1.0
    p2 = Plane(Vec3(0, 1, 0), 0.0, opacity=-0.5)
    assert p2.opacity == 0.0

def test_light_defaults():
    light = Light(position=Vec3(0, 10, 0))
    assert light.radius == 0.0
    assert light.samples == 16

def test_light_custom_radius_and_samples():
    light = Light(position=Vec3(0, 10, 0), radius=2.0, samples=32)
    assert light.radius == 2.0
    assert light.samples == 32
