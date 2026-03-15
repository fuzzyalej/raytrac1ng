"""Parser for the custom .pov scene description format.

Supported blocks:
    camera    { location <x,y,z>  look_at <x,y,z>  fov N }
    light     { position <x,y,z> }
    sphere    { center <x,y,z>  radius N }
    plane     { normal <x,y,z>  offset N }
    box       { min <x,y,z>  max <x,y,z> }
    cylinder  { bottom <x,y,z>  top <x,y,z>  radius N }
    cone      { bottom <x,y,z>  top <x,y,z>  bottom_radius N  top_radius N }
    torus     { center <x,y,z>  axis <x,y,z>  major_radius N  minor_radius N }
"""

import re
from vector import Vec3
from scene import Camera, Light, PointLight, SphereLight, DiskLight, RectLight, Scene
from shapes import Sphere, Plane, Box, Cylinder, Cone, Torus
from color import Color, NAMED_COLORS
from material import Material


# ---------------------------------------------------------------------------
# Tokeniser helpers
# ---------------------------------------------------------------------------

_BLOCK_RE = re.compile(
    r'(\w+)\s*\{([^}]*)\}',
    re.DOTALL,
)

_VEC_RE = re.compile(
    r'<\s*([^,>]+)\s*,\s*([^,>]+)\s*,\s*([^,>]+)\s*>'
)


def _parse_vec3(text: str) -> Vec3:
    """Extract the first <x, y, z> from *text*."""
    m = _VEC_RE.search(text)
    if not m:
        raise ValueError(f"Expected <x, y, z> vector in: {text!r}")
    return Vec3(float(m.group(1)), float(m.group(2)), float(m.group(3)))


def _parse_float(text: str, key: str) -> float:
    """Extract a float value for *key* from *text* (e.g. 'radius 1.5')."""
    pattern = re.compile(rf'{key}\s+([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)')
    m = pattern.search(text)
    if not m:
        raise ValueError(f"Expected '{key} <number>' in: {text!r}")
    return float(m.group(1))


def _parse_vec3_for_key(text: str, key: str) -> Vec3:
    """Extract a Vec3 that follows *key* (e.g. 'center <1,2,3>')."""
    pattern = re.compile(
        rf'{key}\s+<\s*([^,>]+)\s*,\s*([^,>]+)\s*,\s*([^,>]+)\s*>'
    )
    m = pattern.search(text)
    if not m:
        raise ValueError(f"Expected '{key} <x,y,z>' in: {text!r}")
    return Vec3(float(m.group(1)), float(m.group(2)), float(m.group(3)))


_COLOR_VEC_RE = re.compile(
    r'\bcolor\s+<\s*([^,>]+)\s*,\s*([^,>]+)\s*,\s*([^,>]+)\s*>'
)
_COLOR_NAME_RE = re.compile(r'\bcolor\s+([a-zA-Z]\w*)\b')


def _parse_color(body: str) -> Color:
    """Parse 'color <r,g,b>' or 'color name' from a block body.

    Returns white if no color directive is found.
    """
    m = _COLOR_VEC_RE.search(body)
    if m:
        return Color(float(m.group(1)), float(m.group(2)), float(m.group(3)))
    m = _COLOR_NAME_RE.search(body)
    if m:
        name = m.group(1).lower()
        if name not in NAMED_COLORS:
            raise ValueError(f"Unknown color name: '{name}'. "
                             f"Valid names: {sorted(NAMED_COLORS)}")
        return NAMED_COLORS[name]
    return Color(1.0, 1.0, 1.0)  # default white


def _parse_light_common(body: str) -> dict:
    """Parse shared light params from a block body string."""
    color = _parse_color(body)
    try:
        intensity = _parse_float(body, 'intensity')
    except ValueError:
        intensity = 1.0
    try:
        color_temperature = _parse_float(body, 'color_temperature')
    except ValueError:
        color_temperature = None
    vis_match = re.search(r'\bvisible\s+(true|false)\b', body, re.IGNORECASE)
    visible = vis_match.group(1).lower() == 'true' if vis_match else False
    try:
        samples = int(_parse_float(body, 'samples'))
    except ValueError:
        samples = 16
    return dict(
        color=color,
        intensity=intensity,
        color_temperature=color_temperature,
        visible=visible,
        samples=samples,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_scene(filepath: str) -> Scene:
    """Read a .pov file and return a Scene."""
    with open(filepath, 'r') as f:
        text = f.read()

    # Strip comments (// to end-of-line)
    text = re.sub(r'//[^\n]*', '', text)

    scene = Scene()

    for match in _BLOCK_RE.finditer(text):
        block_type = match.group(1).lower()
        body = match.group(2)

        if block_type == 'camera':
            location = _parse_vec3_for_key(body, 'location')
            look_at = _parse_vec3_for_key(body, 'look_at')
            fov = _parse_float(body, 'fov')
            scene.camera = Camera(location, look_at, fov)

        elif block_type == 'light':
            position = _parse_vec3_for_key(body, 'position')
            try:
                radius = _parse_float(body, 'radius')
            except ValueError:
                radius = 0.0
            kwargs = _parse_light_common(body)
            if radius > 0.0:
                scene.lights.append(SphereLight(position=position, radius=radius, **kwargs))
            else:
                scene.lights.append(PointLight(position=position, **kwargs))

        elif block_type == 'disk_light':
            position = _parse_vec3_for_key(body, 'position')
            normal   = _parse_vec3_for_key(body, 'normal')
            radius   = _parse_float(body, 'radius')
            ts_match = re.search(r'\btwo_sided\s+(true|false)\b', body, re.IGNORECASE)
            two_sided = ts_match.group(1).lower() == 'true' if ts_match else False
            kwargs = _parse_light_common(body)
            scene.lights.append(DiskLight(
                position=position, normal=normal, radius=radius,
                two_sided=two_sided, **kwargs,
            ))

        elif block_type == 'rect_light':
            corner = _parse_vec3_for_key(body, 'corner')
            edge1  = _parse_vec3_for_key(body, 'edge1')
            edge2  = _parse_vec3_for_key(body, 'edge2')
            ts_match = re.search(r'\btwo_sided\s+(true|false)\b', body, re.IGNORECASE)
            two_sided = ts_match.group(1).lower() == 'true' if ts_match else False
            kwargs = _parse_light_common(body)
            scene.lights.append(RectLight(
                corner=corner, edge1=edge1, edge2=edge2,
                two_sided=two_sided, **kwargs,
            ))

        elif block_type == 'sphere':
            center = _parse_vec3_for_key(body, 'center')
            radius = _parse_float(body, 'radius')
            color = _parse_color(body)
            try:
                opacity = _parse_float(body, 'opacity')
            except ValueError:
                opacity = 1.0
            try:
                reflect = _parse_float(body, 'reflect')
            except ValueError:
                reflect = 0.0
            try:
                ior = _parse_float(body, 'ior')
            except ValueError:
                ior = 1.0
            mat = Material(color=color, opacity=opacity, reflect=reflect, ior=ior)
            scene.objects.append(Sphere(center, radius, material=mat))

        elif block_type == 'plane':
            normal = _parse_vec3_for_key(body, 'normal')
            offset = _parse_float(body, 'offset')
            color = _parse_color(body)
            try:
                opacity = _parse_float(body, 'opacity')
            except ValueError:
                opacity = 1.0
            try:
                reflect = _parse_float(body, 'reflect')
            except ValueError:
                reflect = 0.0
            try:
                ior = _parse_float(body, 'ior')
            except ValueError:
                ior = 1.0
            mat = Material(color=color, opacity=opacity, reflect=reflect, ior=ior)
            scene.objects.append(Plane(normal, offset, material=mat))

        elif block_type == 'box':
            min_pt = _parse_vec3_for_key(body, 'min')
            max_pt = _parse_vec3_for_key(body, 'max')
            color  = _parse_color(body)
            try:
                opacity = _parse_float(body, 'opacity')
            except ValueError:
                opacity = 1.0
            try:
                reflect = _parse_float(body, 'reflect')
            except ValueError:
                reflect = 0.0
            try:
                ior = _parse_float(body, 'ior')
            except ValueError:
                ior = 1.0
            mat = Material(color=color, opacity=opacity, reflect=reflect, ior=ior)
            scene.objects.append(Box(min_pt, max_pt, material=mat))

        elif block_type == 'cylinder':
            bottom = _parse_vec3_for_key(body, 'bottom')
            top    = _parse_vec3_for_key(body, 'top')
            radius = _parse_float(body, 'radius')
            color  = _parse_color(body)
            try:
                opacity = _parse_float(body, 'opacity')
            except ValueError:
                opacity = 1.0
            try:
                reflect = _parse_float(body, 'reflect')
            except ValueError:
                reflect = 0.0
            try:
                ior = _parse_float(body, 'ior')
            except ValueError:
                ior = 1.0
            mat = Material(color=color, opacity=opacity, reflect=reflect, ior=ior)
            scene.objects.append(Cylinder(bottom, top, radius, material=mat))

        elif block_type == 'cone':
            bottom        = _parse_vec3_for_key(body, 'bottom')
            top           = _parse_vec3_for_key(body, 'top')
            bottom_radius = _parse_float(body, 'bottom_radius')
            top_radius    = _parse_float(body, 'top_radius')
            color         = _parse_color(body)
            try:
                opacity = _parse_float(body, 'opacity')
            except ValueError:
                opacity = 1.0
            try:
                reflect = _parse_float(body, 'reflect')
            except ValueError:
                reflect = 0.0
            try:
                ior = _parse_float(body, 'ior')
            except ValueError:
                ior = 1.0
            mat = Material(color=color, opacity=opacity, reflect=reflect, ior=ior)
            scene.objects.append(Cone(bottom, top, bottom_radius, top_radius,
                                      material=mat))

        elif block_type == 'torus':
            center       = _parse_vec3_for_key(body, 'center')
            axis         = _parse_vec3_for_key(body, 'axis')
            major_radius = _parse_float(body, 'major_radius')
            minor_radius = _parse_float(body, 'minor_radius')
            color        = _parse_color(body)
            try:
                opacity = _parse_float(body, 'opacity')
            except ValueError:
                opacity = 1.0
            try:
                reflect = _parse_float(body, 'reflect')
            except ValueError:
                reflect = 0.0
            try:
                ior = _parse_float(body, 'ior')
            except ValueError:
                ior = 1.0
            mat = Material(color=color, opacity=opacity, reflect=reflect, ior=ior)
            scene.objects.append(Torus(center, axis, major_radius, minor_radius,
                                       material=mat))

        else:
            print(f"Warning: unknown block type '{block_type}', skipping.")

    if scene.camera is None:
        raise ValueError("Scene file must contain a 'camera' block.")

    return scene
