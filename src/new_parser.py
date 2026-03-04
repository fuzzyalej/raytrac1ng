"""
Adapter: parses a .pow file using lang_parser and builds a Scene.
"""
from pathlib import Path

from lang_parser import (
    parse_source,
    SceneCamera, SceneLight,
    SceneSphere, ScenePlane, SceneBox,
    SceneCylinder, SceneCone, SceneTorus,
)
from scene import Scene, Camera, Light
from shapes import Sphere, Plane, Box, Cylinder, Cone, Torus
from vector import Vec3
from color import Color


def _v(t) -> Vec3:
    return Vec3(t[0], t[1], t[2])


def _c(t) -> Color:
    return Color(t[0], t[1], t[2])


def parse_scene(path: str) -> Scene:
    src = open(path).read()
    base_path = str(Path(path).parent)
    items = parse_source(src, base_path=base_path)

    scene = Scene()

    for item in items:
        if isinstance(item, SceneCamera):
            scene.camera = Camera(
                location=_v(item.location),
                look_at=_v(item.look_at),
                fov=item.fov,
            )

        elif isinstance(item, SceneLight):
            scene.lights.append(Light(
                position=_v(item.position),
                radius=item.radius,
                samples=item.samples,
            ))

        elif isinstance(item, SceneSphere):
            scene.objects.append(Sphere(
                center=_v(item.center),
                radius=item.radius,
                color=_c(item.color),
                opacity=item.opacity,
                reflect=item.reflect,
                ior=item.ior,
            ))

        elif isinstance(item, ScenePlane):
            scene.objects.append(Plane(
                normal=_v(item.normal),
                offset=item.offset,
                color=_c(item.color),
                opacity=item.opacity,
                reflect=item.reflect,
                ior=item.ior,
            ))

        elif isinstance(item, SceneBox):
            scene.objects.append(Box(
                min_pt=_v(item.min),
                max_pt=_v(item.max),
                color=_c(item.color),
                opacity=item.opacity,
                reflect=item.reflect,
                ior=item.ior,
            ))

        elif isinstance(item, SceneCylinder):
            scene.objects.append(Cylinder(
                bottom=_v(item.bottom),
                top=_v(item.top),
                radius=item.radius,
                color=_c(item.color),
                opacity=item.opacity,
                reflect=item.reflect,
                ior=item.ior,
            ))

        elif isinstance(item, SceneCone):
            scene.objects.append(Cone(
                bottom=_v(item.bottom),
                top=_v(item.top),
                bottom_radius=item.bottom_radius,
                top_radius=item.top_radius,
                color=_c(item.color),
                opacity=item.opacity,
                reflect=item.reflect,
                ior=item.ior,
            ))

        elif isinstance(item, SceneTorus):
            scene.objects.append(Torus(
                center=_v(item.center),
                axis=_v(item.axis),
                major_radius=item.major_radius,
                minor_radius=item.minor_radius,
                color=_c(item.color),
                opacity=item.opacity,
                reflect=item.reflect,
                ior=item.ior,
            ))

    return scene
