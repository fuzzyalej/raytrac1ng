"""Parser tests for Box, Cylinder, Cone, and Torus blocks."""
import textwrap, tempfile, os

from parsers.pov import parse_scene
from shapes import Box, Cylinder, Cone, Torus
from vector import Vec3


def _write(content: str) -> str:
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.pov', delete=False)
    f.write(textwrap.dedent(content))
    f.close()
    return f.name


CAM = "camera { location <0,5,-15> look_at <0,0,0> fov 45 }\n"
LIGHT = "light { position <10,20,-10> }\n"


def test_parse_box():
    path = _write(CAM + LIGHT + """
        box { min <-1,-1,-1> max <1,1,1> color red }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    assert len(scene.objects) == 1
    obj = scene.objects[0]
    assert isinstance(obj, Box)
    assert abs(obj.min_pt.x - (-1.0)) < 1e-6
    assert abs(obj.max_pt.y - 1.0) < 1e-6


def test_parse_box_defaults():
    path = _write(CAM + LIGHT + """
        box { min <0,0,0> max <1,1,1> }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    obj = scene.objects[0]
    assert obj.material.opacity == 1.0
    assert obj.material.reflect == 0.0
    assert obj.material.ior == 1.0


def test_parse_cylinder():
    path = _write(CAM + LIGHT + """
        cylinder { bottom <0,0,0> top <0,3,0> radius 1.5 color blue }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    assert len(scene.objects) == 1
    obj = scene.objects[0]
    assert isinstance(obj, Cylinder)
    assert abs(obj.radius - 1.5) < 1e-6
    assert abs(obj.top.y - 3.0) < 1e-6


def test_parse_cone():
    path = _write(CAM + LIGHT + """
        cone { bottom <0,0,0> top <0,4,0> bottom_radius 2.0 top_radius 0.0 }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    assert len(scene.objects) == 1
    obj = scene.objects[0]
    assert isinstance(obj, Cone)
    assert abs(obj.bottom_radius - 2.0) < 1e-6
    assert abs(obj.top_radius - 0.0) < 1e-6


def test_parse_torus():
    path = _write(CAM + LIGHT + """
        torus { center <0,1,0> axis <0,1,0> major_radius 2.0 minor_radius 0.5 color yellow }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    assert len(scene.objects) == 1
    obj = scene.objects[0]
    assert isinstance(obj, Torus)
    assert abs(obj.major_radius - 2.0) < 1e-6
    assert abs(obj.minor_radius - 0.5) < 1e-6
    assert abs(obj.center.y - 1.0) < 1e-6


def test_parse_multiple_shapes():
    path = _write(CAM + LIGHT + """
        box      { min <-3,0,-1> max <-1,2,1> }
        cylinder { bottom <0,0,0> top <0,2,0> radius 0.5 }
        cone     { bottom <2,0,0> top <2,3,0> bottom_radius 1.0 top_radius 0.0 }
        torus    { center <5,1,0> axis <0,1,0> major_radius 1.0 minor_radius 0.3 }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    assert len(scene.objects) == 4
    assert isinstance(scene.objects[0], Box)
    assert isinstance(scene.objects[1], Cylinder)
    assert isinstance(scene.objects[2], Cone)
    assert isinstance(scene.objects[3], Torus)


# ---- New POV light type tests ----
import pytest
import tempfile, os


def _write_pov(content: str) -> str:
    """Write POV content to a temp file and return the path."""
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.pov', delete=False)
    f.write(content)
    f.close()
    return f.name


def test_pov_light_new_params():
    path = _write_pov("""
camera { location <0,0,-5>  look_at <0,0,0>  fov 60 }
light {
  position <0, 10, 0>
  color <1.0, 0.5, 0.0>
  intensity 1.5
  color_temperature 2700
  visible false
  samples 32
}
""")
    try:
        from parsers.pov import parse_scene
        scene = parse_scene(path)
    finally:
        os.unlink(path)
    assert len(scene.lights) == 1
    light = scene.lights[0]
    assert light.color_temperature == pytest.approx(2700)
    assert light.intensity == pytest.approx(1.5)
    assert light.visible is False


def test_pov_disk_light_parsed():
    path = _write_pov("""
camera { location <0,0,-5>  look_at <0,0,0>  fov 60 }
disk_light {
  position <0, 5, 0>
  normal <0, -1, 0>
  radius 1.5
  two_sided false
  color <1.0, 0.8, 0.0>
  intensity 2.0
  visible true
  samples 16
}
""")
    try:
        from parsers.pov import parse_scene
        from scene import DiskLight
        scene = parse_scene(path)
    finally:
        os.unlink(path)
    assert len(scene.lights) == 1
    light = scene.lights[0]
    assert isinstance(light, DiskLight)
    assert light.radius == pytest.approx(1.5)
    assert light.visible is True
    assert light.intensity == pytest.approx(2.0)


def test_pov_rect_light_parsed():
    path = _write_pov("""
camera { location <0,0,-5>  look_at <0,0,0>  fov 60 }
rect_light {
  corner <0, 5, 0>
  edge1  <2, 0, 0>
  edge2  <0, 0, 2>
  two_sided true
  samples 32
}
""")
    try:
        from parsers.pov import parse_scene
        from scene import RectLight
        scene = parse_scene(path)
    finally:
        os.unlink(path)
    assert len(scene.lights) == 1
    light = scene.lights[0]
    assert isinstance(light, RectLight)
    assert light.two_sided is True
    assert light.samples == 32


def test_pov_legacy_light_still_works():
    path = _write_pov("""
camera { location <0,0,-5>  look_at <0,0,0>  fov 60 }
light { position <0, 10, 0> }
""")
    try:
        from parsers.pov import parse_scene
        scene = parse_scene(path)
    finally:
        os.unlink(path)
    assert len(scene.lights) == 1
    assert scene.lights[0].visible is False
