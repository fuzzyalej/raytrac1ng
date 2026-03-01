"""Parser tests for Box, Cylinder, Cone, and Torus blocks."""
import textwrap, tempfile, os

from parser import parse_scene
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
    assert obj.opacity == 1.0
    assert obj.reflect == 0.0
    assert obj.ior == 1.0


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
