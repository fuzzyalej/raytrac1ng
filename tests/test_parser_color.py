# tests/test_parser_color.py
import textwrap, tempfile, os
from parser import parse_scene
from color import Color

def _write_scene(content: str) -> str:
    f = tempfile.NamedTemporaryFile(mode='w', suffix='.pov', delete=False)
    f.write(textwrap.dedent(content))
    f.close()
    return f.name

def test_sphere_raw_color():
    path = _write_scene("""
        camera { location <0,2,-5> look_at <0,0,0> fov 60 }
        light { position <5,10,-3> }
        sphere { center <0,1,0> radius 1.0 color <1.0, 0.0, 0.0> }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    sphere = scene.objects[0]
    assert abs(sphere.color.r - 1.0) < 1e-6
    assert abs(sphere.color.g - 0.0) < 1e-6
    assert abs(sphere.color.b - 0.0) < 1e-6

def test_sphere_named_color():
    path = _write_scene("""
        camera { location <0,2,-5> look_at <0,0,0> fov 60 }
        light { position <5,10,-3> }
        sphere { center <0,1,0> radius 1.0 color blue }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    sphere = scene.objects[0]
    assert sphere.color == Color(0.0, 0.0, 1.0)

def test_plane_named_color():
    path = _write_scene("""
        camera { location <0,2,-5> look_at <0,0,0> fov 60 }
        light { position <5,10,-3> }
        plane { normal <0,1,0> offset 0 color gray }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    plane = scene.objects[0]
    assert plane.color == Color(0.5, 0.5, 0.5)

def test_sphere_no_color_defaults_to_white():
    path = _write_scene("""
        camera { location <0,2,-5> look_at <0,0,0> fov 60 }
        light { position <5,10,-3> }
        sphere { center <0,1,0> radius 1.0 }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    sphere = scene.objects[0]
    assert sphere.color == Color(1.0, 1.0, 1.0)

def test_sphere_opacity():
    path = _write_scene("""
        camera { location <0,2,-5> look_at <0,0,0> fov 60 }
        light { position <5,10,-3> }
        sphere { center <0,1,0> radius 1.0 color red opacity 0.5 }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    assert abs(scene.objects[0].opacity - 0.5) < 1e-6

def test_sphere_no_opacity_defaults_to_opaque():
    path = _write_scene("""
        camera { location <0,2,-5> look_at <0,0,0> fov 60 }
        light { position <5,10,-3> }
        sphere { center <0,1,0> radius 1.0 }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    assert scene.objects[0].opacity == 1.0

def test_plane_opacity():
    path = _write_scene("""
        camera { location <0,2,-5> look_at <0,0,0> fov 60 }
        light { position <5,10,-3> }
        plane { normal <0,1,0> offset 0 opacity 0.25 }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    assert abs(scene.objects[0].opacity - 0.25) < 1e-6

def test_light_default_radius_and_samples(tmp_path):
    pov = tmp_path / "s.pov"
    pov.write_text("""
camera { location <0,0,-5> look_at <0,0,0> fov 60 }
light { position <5,10,-3> }
""")
    scene = parse_scene(str(pov))
    light = scene.lights[0]
    assert light.radius == 0.0
    assert light.samples == 16

def test_light_custom_radius_and_samples(tmp_path):
    pov = tmp_path / "s.pov"
    pov.write_text("""
camera { location <0,0,-5> look_at <0,0,0> fov 60 }
light { position <5,10,-3> radius 1.5 samples 32 }
""")
    scene = parse_scene(str(pov))
    light = scene.lights[0]
    assert light.radius == 1.5
    assert light.samples == 32


def test_sphere_ior_parsed():
    path = _write_scene("""
        camera { location <0,2,-5> look_at <0,0,0> fov 60 }
        light { position <5,10,-3> }
        sphere { center <0,1,0> radius 1.0 color white opacity 0.0 ior 1.5 }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    assert abs(scene.objects[0].ior - 1.5) < 1e-6


def test_sphere_default_ior_when_absent():
    path = _write_scene("""
        camera { location <0,2,-5> look_at <0,0,0> fov 60 }
        light { position <5,10,-3> }
        sphere { center <0,1,0> radius 1.0 }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    assert scene.objects[0].ior == 1.0


def test_plane_ior_parsed():
    path = _write_scene("""
        camera { location <0,2,-5> look_at <0,0,0> fov 60 }
        light { position <5,10,-3> }
        plane { normal <0,1,0> offset 0 ior 1.33 }
    """)
    scene = parse_scene(path)
    os.unlink(path)
    assert abs(scene.objects[0].ior - 1.33) < 1e-6
