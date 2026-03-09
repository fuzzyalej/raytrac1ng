"""OBJ/MTL file loader — returns a TriangleMesh."""
from __future__ import annotations
import os
from color import Color
from vector import Vec3
from shapes import Triangle, TriangleMesh


def _parse_mtl(path: str) -> dict[str, dict]:
    """Parse a .mtl file. Returns {material_name: {color, opacity}}."""
    materials: dict[str, dict] = {}
    current: dict | None = None
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if parts[0] == 'newmtl':
                    current = {'color': Color(1, 1, 1), 'opacity': 1.0}
                    materials[parts[1]] = current
                elif parts[0] == 'Kd' and current is not None:
                    current['color'] = Color(float(parts[1]),
                                             float(parts[2]),
                                             float(parts[3]))
                elif parts[0] == 'd' and current is not None:
                    current['opacity'] = float(parts[1])
                elif parts[0] == 'Tr' and current is not None:
                    current['opacity'] = 1.0 - float(parts[1])
    except FileNotFoundError:
        pass  # Missing MTL is fine — triangles keep default material
    return materials


def _parse_face_vertex(token: str) -> tuple[int, int | None, int | None]:
    """Parse a face token 'v', 'v/vt', 'v//vn', or 'v/vt/vn'.
    Returns (v_idx, vt_idx_or_None, vn_idx_or_None) as raw integers
    (1-based, negative OK — caller resolves to 0-based).
    """
    parts = token.split('/')
    vi  = int(parts[0])
    vti = int(parts[1]) if len(parts) > 1 and parts[1] else None
    vni = int(parts[2]) if len(parts) > 2 and parts[2] else None
    return vi, vti, vni


def load_obj(path: str,
             color:   Color | None = None,
             opacity: float | None = None,
             reflect: float        = 0.0,
             ior:     float        = 1.0) -> TriangleMesh:
    """Parse an OBJ file and return a TriangleMesh.

    color / opacity: if provided, override all triangle materials.
    reflect / ior:   always applied to every triangle.
    """
    obj_dir = os.path.dirname(os.path.abspath(path))

    vertices: list[Vec3] = []
    normals:  list[Vec3] = []

    materials: dict[str, dict] = {}
    current_mat: str = '__default__'
    materials[current_mat] = {'color': Color(1, 1, 1), 'opacity': 1.0}

    triangles: list[Triangle] = []

    try:
        with open(path) as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # Skip smooth-shading groups (we use vn data directly)
                if line == 's' or line.startswith('s ') or line.startswith('s\t'):
                    continue
                parts = line.split()
                directive = parts[0]

                if directive == 'v':
                    if len(parts) < 4:
                        raise ValueError(f"{path}:{lineno}: 'v' needs 3 components, got {len(parts)-1}")
                    vertices.append(Vec3(float(parts[1]), float(parts[2]), float(parts[3])))

                elif directive == 'vn':
                    if len(parts) < 4:
                        raise ValueError(f"{path}:{lineno}: 'vn' needs 3 components, got {len(parts)-1}")
                    normals.append(Vec3(float(parts[1]), float(parts[2]), float(parts[3])))

                elif directive == 'vt':
                    pass  # tex-coords parsed to handle f v/vt/vn syntax, not stored

                elif directive == 'mtllib':
                    filename = line[len('mtllib'):].strip()
                    mtl_path = os.path.join(obj_dir, filename)
                    materials.update(_parse_mtl(mtl_path))

                elif directive == 'usemtl':
                    current_mat = line[len('usemtl'):].strip()
                    if current_mat not in materials:
                        materials[current_mat] = {'color': Color(1, 1, 1), 'opacity': 1.0}

                elif directive == 'f':
                    face_tokens = parts[1:]
                    if len(face_tokens) < 3:
                        continue  # skip degenerate edge or point faces
                    n_v  = len(vertices)
                    n_vn = len(normals)
                    parsed = []
                    for tok in face_tokens:
                        vi, vti, vni = _parse_face_vertex(tok)
                        vi  = vi  + n_v  if vi  < 0 else vi  - 1
                        vni = (vni + n_vn if vni < 0 else vni - 1) if vni is not None else None
                        parsed.append((vi, vni))

                    # Fan triangulation: (0,1,2), (0,2,3), (0,3,4), ...
                    mat_props = materials.get(current_mat, materials['__default__'])
                    tri_color   = mat_props['color']
                    tri_opacity = mat_props['opacity']

                    for i in range(1, len(parsed) - 1):
                        ai, ani = parsed[0]
                        bi, bni = parsed[i]
                        ci, cni = parsed[i + 1]

                        n0 = normals[ani] if ani is not None else None
                        n1 = normals[bni] if bni is not None else None
                        n2 = normals[cni] if cni is not None else None

                        try:
                            triangles.append(Triangle(
                                vertices[ai], vertices[bi], vertices[ci],
                                n0=n0, n1=n1, n2=n2,
                                color=tri_color, opacity=tri_opacity,
                                reflect=reflect, ior=ior,
                            ))
                        except ValueError:
                            # Mixed normal specification — fall back to flat shading for this face
                            triangles.append(Triangle(
                                vertices[ai], vertices[bi], vertices[ci],
                                color=tri_color, opacity=tri_opacity,
                                reflect=reflect, ior=ior,
                            ))
    except OSError as exc:
        raise OSError(f"load_obj: cannot open '{os.path.abspath(path)}'") from exc

    # Apply color/opacity override (reflect/ior already baked per-triangle above)
    if color is not None:
        for tri in triangles:
            tri.color = color
    if opacity is not None:
        for tri in triangles:
            tri.opacity = opacity

    return TriangleMesh(triangles)
