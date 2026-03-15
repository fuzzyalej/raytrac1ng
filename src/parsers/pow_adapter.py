"""
Adapter: parses a .pow file using lang_parser and builds a Scene.
"""
import os
from pathlib import Path

from .pow_parser import (
    parse_source,
    SceneCamera, SceneLight, SceneDiskLight, SceneRectLight,
    SceneSphere, ScenePlane, SceneBox,
    SceneCylinder, SceneCone, SceneTorus,
    SceneCSGUnion, SceneCSGIntersection, SceneCSGDifference,
    SceneMesh,
    SceneTransform,          # NEW
)
from scene import Scene, Camera, Light, PointLight, SphereLight, DiskLight, RectLight
from shapes import Sphere, Plane, Box, Cylinder, Cone, Torus
from shapes import CSGUnion, CSGIntersection, CSGDifference
from shapes import Transform, TransformedShape  # NEW
from obj_loader import load_obj
from vector import Vec3
from color import Color
from material import Material


def _v(t) -> Vec3:
    return Vec3(t[0], t[1], t[2])


def _c(t) -> Color:
    return Color(t[0], t[1], t[2])


def _make_transform(st: SceneTransform) -> Transform:
    """Convert a SceneTransform dataclass to an engine Transform."""
    return Transform(scale=st.scale, rotate=st.rotate, translate=st.translate)


def _light_kwargs(item) -> dict:
    """Extract shared LightBase kwargs from a scene light dataclass."""
    return dict(
        color=_c(item.color),
        intensity=item.intensity,
        color_temperature=item.color_temperature,
        visible=item.visible,
        samples=item.samples,
    )


def _maybe_wrap(shape, item):
    """Wrap shape in TransformedShape if the scene item carries a transform."""
    tf = getattr(item, 'transform', None)
    if tf is not None:
        return TransformedShape(shape, _make_transform(tf))
    return shape


def _build_shape(item, base_path: str = "."):
    """Recursively convert a scene item dataclass to a shape object."""
    if isinstance(item, SceneSphere):
        mat = Material(color=_c(item.color), opacity=item.opacity,
                       reflect=item.reflect, ior=item.ior)
        shape = Sphere(center=_v(item.center), radius=item.radius, material=mat)
        return _maybe_wrap(shape, item)
    if isinstance(item, SceneBox):
        mat = Material(color=_c(item.color), opacity=item.opacity,
                       reflect=item.reflect, ior=item.ior)
        shape = Box(min_pt=_v(item.min), max_pt=_v(item.max), material=mat)
        return _maybe_wrap(shape, item)
    if isinstance(item, SceneCylinder):
        mat = Material(color=_c(item.color), opacity=item.opacity,
                       reflect=item.reflect, ior=item.ior)
        shape = Cylinder(bottom=_v(item.bottom), top=_v(item.top),
                         radius=item.radius, material=mat)
        return _maybe_wrap(shape, item)
    if isinstance(item, SceneCone):
        mat = Material(color=_c(item.color), opacity=item.opacity,
                       reflect=item.reflect, ior=item.ior)
        shape = Cone(bottom=_v(item.bottom), top=_v(item.top),
                     bottom_radius=item.bottom_radius, top_radius=item.top_radius,
                     material=mat)
        return _maybe_wrap(shape, item)
    if isinstance(item, SceneTorus):
        mat = Material(color=_c(item.color), opacity=item.opacity,
                       reflect=item.reflect, ior=item.ior)
        shape = Torus(center=_v(item.center), axis=_v(item.axis),
                      major_radius=item.major_radius, minor_radius=item.minor_radius,
                      material=mat)
        return _maybe_wrap(shape, item)
    if isinstance(item, SceneCSGUnion):
        children = [_build_shape(c, base_path) for c in item.children]
        # Each child may already be a TransformedShape (child-level transform);
        # the union's own transform (if any) wraps the entire node on top.
        # This hierarchical composition is intentional — transforms apply independently.
        shape = CSGUnion(children, fuse=item.fuse,
                         color=_c(item.color) if item.color else None,
                         opacity=item.opacity, reflect=item.reflect, ior=item.ior)
        return _maybe_wrap(shape, item)
    if isinstance(item, SceneCSGIntersection):
        children = [_build_shape(c, base_path) for c in item.children]
        # Each child may already be a TransformedShape (child-level transform);
        # the union's own transform (if any) wraps the entire node on top.
        # This hierarchical composition is intentional — transforms apply independently.
        shape = CSGIntersection(children,
                                color=_c(item.color) if item.color else None,
                                opacity=item.opacity, reflect=item.reflect, ior=item.ior)
        return _maybe_wrap(shape, item)
    if isinstance(item, SceneCSGDifference):
        # Each child may already be a TransformedShape (child-level transform);
        # the union's own transform (if any) wraps the entire node on top.
        # This hierarchical composition is intentional — transforms apply independently.
        shape = CSGDifference(_build_shape(item.left, base_path), _build_shape(item.right, base_path),
                              color=_c(item.color) if item.color else None,
                              opacity=item.opacity, reflect=item.reflect, ior=item.ior)
        return _maybe_wrap(shape, item)
    if isinstance(item, SceneMesh):
        resolved = os.path.join(base_path, item.file)
        mesh = load_obj(
            resolved,
            color=_c(item.color) if item.color is not None else None,
            opacity=item.opacity,
            reflect=item.reflect,
            ior=item.ior,
        )
        return _maybe_wrap(mesh, item)
    raise ValueError(f"unknown scene item type: {type(item)}")


def _build_from_items(items, base_path: str = ".") -> Scene:
    """Iterate parsed scene items and populate a Scene object."""
    scene = Scene()

    for item in items:
        if isinstance(item, SceneCamera):
            scene.camera = Camera(
                location=_v(item.location),
                look_at=_v(item.look_at),
                fov=item.fov,
            )

        elif isinstance(item, SceneLight):
            kwargs = _light_kwargs(item)
            if item.radius > 0.0:
                scene.lights.append(SphereLight(
                    position=_v(item.position),
                    radius=item.radius,
                    **kwargs,
                ))
            else:
                scene.lights.append(PointLight(
                    position=_v(item.position),
                    **kwargs,
                ))

        elif isinstance(item, SceneDiskLight):
            scene.lights.append(DiskLight(
                position=_v(item.position),
                normal=_v(item.normal),
                radius=item.radius,
                two_sided=item.two_sided,
                **_light_kwargs(item),
            ))

        elif isinstance(item, SceneRectLight):
            scene.lights.append(RectLight(
                corner=_v(item.corner),
                edge1=_v(item.edge1),
                edge2=_v(item.edge2),
                two_sided=item.two_sided,
                **_light_kwargs(item),
            ))

        elif isinstance(item, ScenePlane):
            mat = Material(color=_c(item.color), opacity=item.opacity,
                           reflect=item.reflect, ior=item.ior)
            shape = Plane(
                normal=_v(item.normal),
                offset=item.offset,
                material=mat,
            )
            scene.objects.append(_maybe_wrap(shape, item))

        else:
            # All other types (Sphere, Box, Cylinder, CSG, Mesh, etc.)
            # are shapes and should be built via _build_shape.
            scene.objects.append(_build_shape(item, base_path))

    return scene


def parse_scene(path: str) -> Scene:
    with open(path) as fh:
        src = fh.read()
    base_path = str(Path(path).parent)
    items = parse_source(src, base_path=base_path)
    return _build_from_items(items, base_path)


def build_scene(source: str, base_path: str = ".") -> Scene:
    """Parse POW source text and return a Scene."""
    items = parse_source(source, base_path=base_path)
    return _build_from_items(items, base_path)
