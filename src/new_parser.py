"""
Adapter: parses a .pow file using lang_parser and builds a Scene.
"""
from pathlib import Path

from lang_parser import (
    parse_source,
    SceneCamera, SceneLight,
    SceneSphere, ScenePlane, SceneBox,
    SceneCylinder, SceneCone, SceneTorus,
    SceneCSGUnion, SceneCSGIntersection, SceneCSGDifference,
)
from scene import Scene, Camera, Light
from shapes import Sphere, Plane, Box, Cylinder, Cone, Torus
from shapes import CSGUnion, CSGIntersection, CSGDifference
from vector import Vec3
from color import Color


def _v(t) -> Vec3:
    return Vec3(t[0], t[1], t[2])


def _c(t) -> Color:
    return Color(t[0], t[1], t[2])


def _build_shape(item):
    """Recursively convert a scene item dataclass to a shape object."""
    if isinstance(item, SceneSphere):
        return Sphere(center=_v(item.center), radius=item.radius,
                      color=_c(item.color), opacity=item.opacity,
                      reflect=item.reflect, ior=item.ior)
    if isinstance(item, SceneBox):
        return Box(min_pt=_v(item.min), max_pt=_v(item.max),
                   color=_c(item.color), opacity=item.opacity,
                   reflect=item.reflect, ior=item.ior)
    if isinstance(item, SceneCylinder):
        return Cylinder(bottom=_v(item.bottom), top=_v(item.top),
                        radius=item.radius, color=_c(item.color),
                        opacity=item.opacity, reflect=item.reflect, ior=item.ior)
    if isinstance(item, SceneCone):
        return Cone(bottom=_v(item.bottom), top=_v(item.top),
                    bottom_radius=item.bottom_radius, top_radius=item.top_radius,
                    color=_c(item.color), opacity=item.opacity,
                    reflect=item.reflect, ior=item.ior)
    if isinstance(item, SceneTorus):
        return Torus(center=_v(item.center), axis=_v(item.axis),
                     major_radius=item.major_radius, minor_radius=item.minor_radius,
                     color=_c(item.color), opacity=item.opacity,
                     reflect=item.reflect, ior=item.ior)
    if isinstance(item, SceneCSGUnion):
        children = [_build_shape(c) for c in item.children]
        return CSGUnion(children, fuse=item.fuse,
                        color=_c(item.color) if item.color else None,
                        opacity=item.opacity, reflect=item.reflect, ior=item.ior)
    if isinstance(item, SceneCSGIntersection):
        children = [_build_shape(c) for c in item.children]
        return CSGIntersection(children,
                               color=_c(item.color) if item.color else None,
                               opacity=item.opacity, reflect=item.reflect, ior=item.ior)
    if isinstance(item, SceneCSGDifference):
        return CSGDifference(_build_shape(item.left), _build_shape(item.right),
                             color=_c(item.color) if item.color else None,
                             opacity=item.opacity, reflect=item.reflect, ior=item.ior)
    raise ValueError(f"unknown scene item type: {type(item)}")


def parse_scene(path: str) -> Scene:
    with open(path) as fh:
        src = fh.read()
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

        elif isinstance(item, ScenePlane):
            scene.objects.append(Plane(
                normal=_v(item.normal),
                offset=item.offset,
                color=_c(item.color),
                opacity=item.opacity,
                reflect=item.reflect,
                ior=item.ior,
            ))

        else:
            # All bounded shapes (primitives and CSG) go through _build_shape
            try:
                scene.objects.append(_build_shape(item))
            except ValueError as exc:
                raise RuntimeError(f"unrecognised scene item: {type(item)}") from exc

    return scene
