"""Tests for ior field on Sphere and Plane."""
from material import Material
from shapes import Sphere, Plane
from vector import Vec3


def test_sphere_default_ior():
    s = Sphere(Vec3(0, 0, 0), 1.0)
    assert s.material.ior == 1.0


def test_sphere_custom_ior():
    s = Sphere(Vec3(0, 0, 0), 1.0, material=Material(ior=1.5))
    assert s.material.ior == 1.5


def test_sphere_ior_glass():
    s = Sphere(Vec3(0, 0, 0), 1.0, material=Material(ior=2.4))
    assert s.material.ior == 2.4


def test_plane_default_ior():
    p = Plane(Vec3(0, 1, 0), 0.0)
    assert p.material.ior == 1.0


def test_plane_custom_ior():
    p = Plane(Vec3(0, 1, 0), 0.0, material=Material(ior=1.33))
    assert abs(p.material.ior - 1.33) < 1e-9


def test_sphere_ior_clamped_below_one():
    s = Sphere(Vec3(0, 0, 0), 1.0, material=Material(ior=0.5))
    assert s.material.ior == 1.0


def test_plane_ior_clamped_below_one():
    p = Plane(Vec3(0, 1, 0), 0.0, material=Material(ior=0.0))
    assert p.material.ior == 1.0
