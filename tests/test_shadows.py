"""Tests for shadow ray computation.

Scene geometry used throughout:
  - Camera at z=-5 looking toward +Z origin
  - Light at <0, 10, 0>  (directly above origin)
  - Ground plane: normal <0,1,0>, offset -1  (y = -1)
  - Blocker sphere: center <0, 1, 0>, radius 0.5  (between light and ground)
"""
import random
import pytest
from color import Color
from material import Material
from scene import Scene, Camera, Light
from shapes import Sphere, Plane
from vector import Vec3
from rendering import render
from rendering.shading import shadow_factor
from rendering.renderer import RenderContext
from bvh import BVH
from shapes import Plane as _Plane


def _basic_scene(light_radius=0.0, light_samples=1):
    """One sphere above a ground plane, one light."""
    scene = Scene()
    scene.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    scene.lights = [Light(position=Vec3(0, 10, 0), radius=light_radius, samples=light_samples)]
    scene.objects = [
        Plane(Vec3(0, 1, 0), -1.0,
              material=Material(color=Color(0.8, 0.8, 0.8))),         # ground at y=-1
        Sphere(Vec3(0, 1, 0), 0.5,
               material=Material(color=Color(1.0, 0.0, 0.0))),        # red blocker
    ]
    return scene


def _make_ctx(scene):
    """Build a RenderContext from a scene (for unit-testing shadow_factor directly)."""
    bounded   = [o for o in scene.objects if not isinstance(o, _Plane)]
    unbounded = [o for o in scene.objects if     isinstance(o, _Plane)]
    bvh = BVH.build(bounded)
    return RenderContext(scene=scene, bvh=bvh, unbounded=unbounded)


def test_shadow_factor_unoccluded_is_one():
    """A point with clear line-of-sight to the light gets factor 1.0."""
    scene = _basic_scene()
    ctx = _make_ctx(scene)
    light = scene.lights[0]
    # Point far to the side of the blocker — nothing between it and the light
    hit_point = Vec3(5, 0, 0)
    factor = shadow_factor(hit_point, light, ctx)
    assert factor == pytest.approx(1.0)


def test_shadow_factor_opaque_blocker_is_zero():
    """A point directly behind an opaque sphere gets factor 0.0 (point light)."""
    scene = _basic_scene(light_radius=0.0, light_samples=1)
    ctx = _make_ctx(scene)
    light = scene.lights[0]
    # Point directly below the blocker sphere — fully in shadow
    hit_point = Vec3(0, -0.9, 0)
    factor = shadow_factor(hit_point, light, ctx)
    assert factor == pytest.approx(0.0, abs=0.01)


def test_shadow_factor_transparent_blocker_partial():
    """A 50%-transparent sphere lets through 50% of the light."""
    scene = Scene()
    scene.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    scene.lights = [Light(position=Vec3(0, 10, 0), radius=0.0, samples=1)]
    scene.objects = [
        Sphere(Vec3(0, 1, 0), 0.5,
               material=Material(color=Color(1.0, 0.0, 0.0), opacity=0.5)),
    ]
    ctx = _make_ctx(scene)
    hit_point = Vec3(0, -0.9, 0)
    factor = shadow_factor(hit_point, scene.lights[0], ctx)
    assert factor == pytest.approx(0.5, abs=0.01)


def test_shadow_factor_fully_transparent_blocker_is_one():
    """A fully transparent object (opacity=0) does not block light at all."""
    scene = Scene()
    scene.camera = Camera(Vec3(0, 0, -5), Vec3(0, 0, 0), fov=60)
    scene.lights = [Light(position=Vec3(0, 10, 0), radius=0.0, samples=1)]
    scene.objects = [
        Sphere(Vec3(0, 1, 0), 0.5,
               material=Material(color=Color(1.0, 0.0, 0.0), opacity=0.0)),
    ]
    ctx = _make_ctx(scene)
    hit_point = Vec3(0, -0.9, 0)
    factor = shadow_factor(hit_point, scene.lights[0], ctx)
    assert factor == pytest.approx(1.0, abs=0.01)


def test_soft_shadow_factor_is_between_zero_and_one():
    """Area light (radius>0) gives a partial factor for penumbra points."""
    random.seed(42)
    scene = _basic_scene(light_radius=3.0, light_samples=64)
    ctx = _make_ctx(scene)
    light = scene.lights[0]
    # Point at the edge of the shadow — some samples blocked, some not
    hit_point = Vec3(0.4, -0.9, 0)
    factor = shadow_factor(hit_point, light, ctx)
    assert 0.0 < factor < 1.0


def test_shadowed_sphere_is_darker_than_unshadowed():
    """Rendering with shadows: the ground under the sphere is darker than ground to the side."""
    random.seed(0)
    scene = _basic_scene(light_radius=0.0, light_samples=1)
    pixels = render(scene, 50, 50)
    # Center column, row 33 — directly under the blocker sphere (in shadow)
    shadow_pixel = pixels[33 * 50 + 25]
    # Far left side — not in shadow
    lit_pixel = pixels[33 * 50 + 2]
    # Shadow pixel should be darker (lower total brightness)
    shadow_brightness = shadow_pixel.r + shadow_pixel.g + shadow_pixel.b
    lit_brightness = lit_pixel.r + lit_pixel.g + lit_pixel.b
    assert shadow_brightness < lit_brightness
