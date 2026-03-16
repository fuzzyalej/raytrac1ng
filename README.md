# Raytrac1ng - A small AI experiment

**Version:** v1.4
**Last updated:** 2026-03-15

---

## Overview

A pure-Python raytracer that reads a scene description file and outputs an RGB PNG image. No external raytracing libraries are used — all intersection math and shading is implemented from scratch. The only external dependency is **Pillow** for image output.

Two scene formats are supported: the legacy `.pov` block format and the modern `.pow` scripting language (variables, loops, functions, materials, imports, CSG, transforms). Scenes are accelerated by a SAH-based BVH tree. Supported primitives: sphere, plane, box, cylinder, cone, torus, OBJ mesh, and CSG composites (union, intersection, difference). Rendering features include Lambertian diffuse shading, soft shadows from area lights (point, sphere, disk, rect), per-object opacity, mirror reflections, physically-based refractions (Snell's law + Fresnel), anti-aliasing, affine transforms (scale, rotate, translate) on any shape or CSG node, and color-temperature lighting (Kelvin-to-RGB, Tanner Helland approximation).

---

## Documentation

| Reference | Description |
|-----------|-------------|
| **[docs/pov-reference.md](docs/pov-reference.md)** | Legacy `.pov` format — block syntax, all six primitives, named colors, material fields |
| **[docs/pow-reference.md](docs/pow-reference.md)** | Modern `.pow` scripting language — variables, loops, functions, materials, imports, CSG, transforms |

---

## How It Works

### Rendering Pipeline

```
.pow file → parsers.parse() → Scene (camera, lights, objects)
.pov file → parsers.parse() ↗
                               ↓
                          rendering.render()
                               ↓
               For each pixel (x, y):
                1. Camera generates a VisionRay through the pixel
                2. VisionRay is tested against every object in the scene
                3. The closest intersection (smallest positive t) wins
                4. Shading is computed at the hit point (ambient + diffuse)
                5. Result is an RGB Color value
                          ↓
                    Pixel buffer → Pillow → PNG
```

### Ray Types

The raytracer uses typed rays to distinguish their purpose:

| Ray Type | Purpose | Status |
|----------|---------|--------|
| **VisionRay** | Camera → pixel, determines visibility | Implemented |
| **ShadowRay** | Hit point → light, determines if in shadow | Plain `Ray` base class (no subclass) |
| **ReflectionRay** | Hit point → reflected direction | Implemented |
| **RefractionRay** | Hit point → Snell's-law transmitted direction | Implemented |

All ray types inherit from a base `Ray` class (origin + direction).

### Shading Model

```
intensity = ambient + Σ max(0, dot(normal, light_direction)) × shadow_factor
```

- **Ambient:** 0.15 (hardcoded) — prevents surfaces facing away from the light from being completely black.
- **Diffuse:** Lambertian dot product between the surface normal and the direction toward each light. Only computed when the surface faces the light.
- **Shadow factor:** For each light, one or more shadow rays are fired from the hit point toward the light. Opaque objects block light completely; transparent objects attenuate by `(1 - opacity)`. Multiple transparent blockers multiply their attenuation. Result is in [0.0, 1.0].
- The result is clamped to [0, 1] and the light's `effective_color` (color × color_temperature × intensity) is multiplied with the object's color to produce an RGB Color.

### Shadow Model

Shadow computation varies by light type:

- **Point light** (`radius 0`, the default): A single shadow ray is fired to `light.position`. The result is binary — fully lit or fully shadowed (hard shadows).
- **Sphere area light** (`radius > 0`): `samples` shadow rays are fired to uniformly random points within a sphere of the given radius centred on `light.position`. The shadow factor is the average across all samples. This produces a **soft penumbra** — surfaces near the shadow edge receive partial light.
- **Disk area light**: `samples` shadow rays fire to random points on the disk face. One-sided by default (only illuminates surfaces facing the disk's normal side); `two_sided` enables both-sides emission.
- **Rect area light**: `samples` shadow rays fire to random points on the parallelogram surface. Same one-sided semantics as disk.

All flat lights (disk, rect) skip shadow samples that originate on the wrong side of the light, avoiding phantom illumination.

Transparent objects in the shadow path attenuate rather than block light: a 50%-opaque object passes 50% of the light through. Multiple transparent blockers multiply their attenuation factors. Fully opaque blockers cut the factor to zero (with early-exit optimisation).

Shadow rays are biased 0.001 units away from the hit surface to avoid self-intersection ("shadow acne").

### Anti-aliasing

When `--aa N` is passed (N >= 2), each pixel fires N VisionRays instead of one. Each ray is jittered by a random sub-pixel offset drawn uniformly from the pixel's footprint. The N resulting Colors are averaged component-wise. This is **uniform random supersampling** (SSAA):

- `--aa 0` or `--aa 1`: no AA (default) — one centred ray per pixel, fastest
- `--aa 2`–`--aa 3`: noticeably smoother edges, ~2–3× render time
- `--aa 4`: good quality for most scenes, ~4× render time
- `--aa 8`+: diminishing returns; use only for final renders

The implementation lives entirely in `renderer.py::render()`. The camera model already accepts fractional pixel coordinates, so no camera changes were needed.

### Parallelism

When `--jobs N` is passed (N >= 2), the image is divided into horizontal row-bands and rendered in parallel across `N` worker processes using `concurrent.futures.ProcessPoolExecutor`. Each band is an independent unit of work — pixels have no inter-pixel dependencies, so the result is identical to a single-threaded render.

The image height is divided into approximately `N × 4` bands (to give each core multiple chunks and balance the load if some bands take longer than others). Results are assembled in order before writing the PNG.

```bash
python3 main.py scene.pov --jobs 4      # use 4 cores
python3 main.py scene.pov --jobs 0      # use all available cores
```

Worker processes need to import modules from `src/`. Because macOS uses Python's "spawn" start method (each worker starts a fresh interpreter), `main.py` adds `src/` to the `PYTHONPATH` environment variable before spawning so workers can resolve their imports.

- `--jobs 1` or omitted: single-threaded (default)
- `--jobs 0`: auto-detect all CPU cores (`os.cpu_count()`)
- Expected speedup: roughly proportional to core count, minus small pickling overhead (~5–10% per render)

### Reflection

When an object has `reflect > 0.0` and `ior == 1.0`, a `ReflectionRay` is fired from the hit point in the mirror-reflected direction before the opacity blend:

```
reflect_dir = D - N × 2(D·N)
final_color = surface_color × (1 − reflect) + trace(reflect_ray) × reflect
```

- `reflect 0.0`: fully matte (default)
- `reflect 0.5`: 50% diffuse shading + 50% mirror reflection
- `reflect 1.0`: perfect mirror

The origin is biased 0.001 units along the surface normal to prevent self-intersection. Reflection and transparency are independent — `reflect 0.8` with `opacity 0.3` produces a semi-transparent mirror. Reflection depth is capped by `MAX_DEPTH = 8`. Note: `reflect` is ignored on objects with `ior > 1.0` — Fresnel handles reflection for glass (see Refraction below).

### Refraction

When an object has `ior > 1.0` and `opacity < 1.0`, the renderer uses physically-based refraction instead of naive transparency:

1. **Entering/exiting detection:** If `dot(D, N) < 0`, the ray is entering the medium (`n1=1.0 → n2=ior`); if `dot(D, N) > 0`, it is exiting (`n1=ior → n2=1.0`). The normal is flipped accordingly.
2. **Snell's law (vector form):** Computes the refracted direction. If the angle of incidence exceeds the critical angle, total internal reflection (TIR) occurs — the ray mirrors instead of transmitting.
3. **Schlick Fresnel:** The reflectance `R` is approximated as `R0 + (1 − R0)(1 − cosθ)⁵`, where `R0 = ((n1−n2)/(n1+n2))²`. At grazing angles `R → 1` (all reflection); at normal incidence `R = R0`.
4. **Final blend:** `trace(reflection_ray) × R + trace(refraction_ray) × (1 − R)`

Objects with `ior > 1.0` bypass diffuse shading — pure glass has no Lambertian response. `opacity` is not used in the physical path; set it to `0.0` for clear glass.

Common `ior` values: `1.33` (water), `1.5` (glass), `2.4` (diamond). Default is `1.0` (air, disables refraction). Recursion is capped by `MAX_DEPTH = 8`.

### Camera Model

The camera uses a standard **pinhole model**:

1. An orthonormal basis is built from `location` and `look_at` using cross products (forward, right, up vectors).
2. The `fov` (field of view, in degrees) determines the viewport height via `tan(fov/2)`. Viewport width is derived from the image aspect ratio.
3. For each pixel `(x, y)`, coordinates are mapped to the range [-1, 1] across the viewport, and a VisionRay is constructed from the camera location through that point on the viewport plane.

### Intersection Math

All primitives use a `t_min` (default 0.001) to avoid self-intersection artifacts.

**Sphere:** Substitutes the ray equation `P = O + tD` into the sphere equation `|P - C|² = r²`, producing a quadratic in `t`. The discriminant determines hit/miss, and the smallest positive root is returned.

**Plane:** Defined by a normal `N` and offset `d` (the plane equation is `dot(P, N) = d`). Intersection is `t = (d - dot(O, N)) / dot(D, N)`. Returns `None` if the ray is parallel (denominator ≈ 0) or the intersection is behind the ray.

**Box (AABB — slab method):** For each of the three axis-aligned slab pairs, computes the entry `t₀` and exit `t₁` values by dividing the slab boundaries minus the ray origin by the ray direction component. The ray hits the box when `max(t₀ₓ, t₀ᵧ, t₀_z) < min(t₁ₓ, t₁ᵧ, t₁_z)`. The outward normal points along whichever axis the ray entered last, with its sign matching the ray's approach direction. Rays parallel to a slab that originate outside that slab are immediately rejected.

**Cylinder (capped, arbitrary axis):** The cylinder axis `D̂ = (top − bottom) / height` is used to decompose the ray into axial and perpendicular components. A quadratic is solved in the perpendicular plane (`a·t² + b·t + c = 0`, where the coefficients involve only the perpendicular parts of the ray). Candidate hits are kept only if the axial coordinate `h = D̂ · (P − bottom)` falls in `[0, height]`; the curved-surface normal is the radial vector `(P − bottom − D̂·h) / radius`. Each flat cap is a disk: the ray-plane intersection is computed first, then the hit point must satisfy `|P − cap_center|² ≤ radius²`; the cap normal is ±D̂.

**Cone (generalised frustum):** The radius varies linearly along the axis: `R(h) = R₀ + slope·h`, where `slope = (R₁ − R₀) / height`. Substituting into the cone-surface equation yields a quadratic whose coefficients are slope-modified versions of the cylinder ones: `a = |d_perp|² − (slope·d_proj)²`, `b = 2(d_perp·oc_perp − (R₀ + slope·oc_proj)·slope·d_proj)`, `c = |oc_perp|² − (R₀ + slope·oc_proj)²`. Candidates are accepted when `h ∈ [0, height]`. The outward normal at a curved hit is `(radial_unit − D̂·slope).normalize()`, which tilts inward toward the apex for a narrowing cone. Cap testing follows the same disk method as the cylinder; the top cap is omitted when `top_radius = 0` (true cone apex).

**Torus (Ferrari quartic):** The ray is transformed into a local orthonormal frame where the symmetry axis aligns with the Y-axis. In this frame the torus equation is `(x² + y² + z² + R² − r²)² = 4R²(x² + z²)`. Substituting `P = O + tD` and expanding yields a degree-4 polynomial in `t` with coefficients `c₄ = |D|⁴`, `c₃ = 4|D|²(D·O_local)`, and two further terms involving `|O_local|²`, `R`, and `r`. The quartic is solved analytically: a depressed form `u⁴ + pu² + qu + r = 0` is obtained, a cubic resolvent is solved for one real root, and that root is used to factor the quartic into two quadratics, each solved with the standard formula. Only real, positive roots within `[t_min, t_max]` are kept. The surface normal at a hit point is the direction from the nearest point on the generating circle to the hit point, transformed back to world space.

---

## File Structure

```
raytrac1ng/
├── src/
│   ├── material.py         Shared Material dataclass (color, opacity, reflect, ior)
│   ├── color.py            Color RGB arithmetic + named palette
│   ├── ray.py              Ray types (VisionRay, ReflectionRay, RefractionRay)
│   ├── vector.py           Vec3 + Matrix4x4 (3D math)
│   ├── scene.py            Camera, Light, Scene container
│   ├── bvh.py              SAH BVH spatial acceleration
│   ├── obj_loader.py       OBJ/MTL file loader → TriangleMesh
│   ├── shapes/
│   │   ├── __init__.py     Re-exports all public names (backward compat)
│   │   ├── primitives.py   Sphere, Plane, Box, Cylinder, Cone, Torus, HitRecord, HitInterval
│   │   ├── csg.py          CSGUnion, CSGIntersection, CSGDifference
│   │   ├── mesh.py         Triangle, TriangleMesh
│   │   └── transform.py    Transform, TransformedShape
│   ├── rendering/
│   │   ├── __init__.py     Re-exports render()
│   │   ├── renderer.py     Orchestration: RenderContext, BVH build, worker dispatch
│   │   ├── shading.py      Lambertian shading, soft shadow computation
│   │   └── physics.py      Snell's law refraction, Schlick Fresnel
│   └── parsers/
│       ├── __init__.py     parse(path) → Scene (dispatches by extension)
│       ├── pov.py          Legacy .pov block-format parser
│       ├── pow_lexer.py    .pow language tokenizer
│       ├── pow_parser.py   .pow recursive-descent parser + evaluator
│       └── pow_adapter.py  POW→Scene adapter (dataclasses → engine objects)
├── tests/
│   ├── conftest.py         Adds src/ to sys.path for pytest
│   └── test_*.py
├── examples/
│   └── models/
│       └── boot.obj        Example mesh .OBJ file
│   └── materials/
│       └── standard.pow    Shared material library
├── docs/
│   ├── pov-reference.md    Legacy .pov format reference manual
│   ├── pow-reference.md    POW scripting language reference manual
│   └── plans/              Implementation and design plans
├── main.py                 CLI entry point
└── README.md               This file
```

### Module Details

#### `vector.py` — Vec3, Matrix4x4

The foundation of all math in the raytracer.

- **`Vec3`**: 3D vector with arithmetic operators (`+`, `-`, `*`, `/`, unary `-`), `dot()`, `cross()`, `normalize()`, `length()`, `length_squared()`. Uses `__slots__` for memory efficiency. No numpy.
- **`Matrix4x4`**: Row-major 4×4 matrix. `from_trs(scale, rotate_deg, translate)` builds a combined TRS matrix (Scale → Rotate XYZ → Translate). `transform_point()` applies the full transform (including translation); `transform_direction()` applies only the linear part. `inverse()` via Gauss-Jordan elimination with partial pivoting. `transpose()`. Used by `Transform` and `TransformedShape`.

#### `color.py` — Color

- **`Color`**: Dataclass with `r`, `g`, `b` float components in [0.0, 1.0]. Supports `+`, `*` (scalar or `Color`×`Color` component-wise), `clamp()`, and `to_bytes()` → `(R, G, B)` int tuple.
- **`color_from_kelvin(k)`**: Converts a color temperature in Kelvin (1000–40000) to a `Color` using Tanner Helland's piecewise approximation.
- **`NAMED_COLORS`**: Dictionary of 15 preset named colors for use in `.pov` files.

#### `ray.py` — Ray Types

- **`Ray`**: Base class with `origin` (Vec3), `direction` (Vec3, auto-normalized), and `point_at(t)`.
- **`VisionRay`**: Camera-to-pixel rays.
- **`ReflectionRay`**: Mirror reflection rays (direction: `D − 2(D·N)N`).
- **`RefractionRay`**: Snell's-law refraction rays (direction computed by `_refract()` in `renderer.py`).

#### `material.py` — Material

- **`Material`**: Dataclass with `color` (Color), `opacity` (float), `reflect` (float), `ior` (float). Validated in `__post_init__`: opacity and reflect clamped to [0, 1], ior clamped to minimum 1.0. All shapes store a single `Material` instance rather than four loose fields.

#### `shapes/primitives.py` — Primitives

- **`HitRecord`**: Holds intersection info — `t` (distance), `point` (world-space position), `normal` (surface normal), `mat_obj` (material source object).
- **`HitInterval`**: Holds an enter/exit interval for CSG operations — `t_enter`, `t_exit`, enter/exit normals, and the material source for each face. All bounded shapes implement `hit_intervals()` returning a list of `HitInterval`.
- **`Sphere`**: Quadratic intersection via `|P − C|² = r²`.
- **`Plane`**: Defined by `normal` and `offset`; `t = (offset − O·N) / D·N`.
- **`Box`**: AABB slab intersection; normal derived from the entry slab.
- **`Cylinder`**: Capped arbitrary-axis cylinder; quadratic on perpendicular ray component; disk caps.
- **`Cone`**: Generalised frustum (`bottom_radius`/`top_radius`); slope-modified quadratic; `top_radius 0.0` = true cone apex.
- **`Torus`**: Ring defined by `center`, `axis`, `major_radius`, `minor_radius`. Solved analytically via Ferrari's quartic.
- All primitive shape classes store a single `Material` instance for material properties.

#### `shapes/csg.py` — CSG

- **`CSGUnion`**: Boolean union of two or more shapes using `hit_intervals()`. Optional `fuse` mode blends materials at the boundary.
- **`CSGIntersection`**: Boolean intersection — keeps only the region inside all children.
- **`CSGDifference`**: Boolean difference — subtracts the right shape from the left.

#### `shapes/mesh.py` — Mesh

- **`Triangle`**: Single triangle defined by three vertices; Möller-Trumbore intersection; interpolated vertex normals when available.
- **`TriangleMesh`**: Collection of `Triangle` objects loaded from an OBJ file, accelerated internally by a BVH. Supports per-face and per-vertex normals.

#### `shapes/transform.py` — Transforms

- **`Transform`**: Stores `scale` (3-tuple), `rotate` (XYZ Euler degrees, 3-tuple), and `translate` (3-tuple). Lazily builds and caches the combined `Matrix4x4` and its inverse.
- **`TransformedShape`**: Wraps any shape (or CSG node) with a `Transform`. The ray is inverse-transformed into local space for intersection; the hit normal is corrected via the transposed inverse matrix (`inv.T`) to remain perpendicular under non-uniform scale.

#### `scene.py` — Scene Graph

- **`Camera`**: Builds a coordinate frame from `location`/`look_at`/`fov`. Provides `get_vision_ray(px, py, width, height)` to generate a VisionRay for any pixel.
- **`LightBase`** (ABC): Shared base with `color`, `intensity`, `color_temperature`, `visible`, `samples`. Provides `effective_color()` (Kelvin × color × intensity) and a default `hit()` returning `None`. Abstract `sample_point()` and `position` property.
- **`PointLight`**: Infinitesimal point source; always uses 1 shadow ray.
- **`SphereLight`**: Spherical area light; rejection-sampling inside the sphere.
- **`DiskLight`**: Flat circular area light with `normal`, `radius`, `two_sided`; implements `hit()` for visible geometry.
- **`RectLight`**: Parallelogram area light with `corner`, `edge1`, `edge2`, `two_sided`; implements `hit()` for visible geometry.
- **`Light`**: Backwards-compatible wrapper (`radius=0` → point, `radius>0` → sphere).
- **`Scene`**: Container dataclass holding a camera, a list of lights, and a list of objects. `.visible_lights` property returns lights with `visible=True`.

#### `obj_loader.py` — OBJ/MTL Mesh Loader

Parses Wavefront `.obj` and `.mtl` files and returns a `TriangleMesh`. Handles triangulated faces (`f v1 v2 v3`), per-vertex normals (`vn`), and multi-material meshes via `.mtl` `newmtl`/`Kd`/`d`/`Tr` directives. Per-face material overrides `color`/`opacity`. Accepts optional `color`, `opacity`, `reflect`, and `ior` overrides from the scene file.

#### `parsers/pow_adapter.py` — POW→Scene Adapter

Bridges `pow_parser` output (dataclasses) to the `Scene` object model. `parse_scene(path)` tokenises and parses the `.pow` source, then converts each `SceneXxx` dataclass into its corresponding `shapes`/`scene` object. Handles `_build_shape()` for all primitives and CSG nodes (recursively), mesh loading via `obj_loader`, and `_maybe_wrap()` to apply `TransformedShape` when a `SceneTransform` is present.

#### `parsers/pov.py` — Legacy .pov Parser

Reads the legacy `.pov` format (see Scene File Format below). Uses regex to extract blocks (`camera { ... }`, `sphere { ... }`, etc.) and parse their key-value contents. Supports `//` single-line comments.

#### `rendering/renderer.py` — Orchestration

Manages `RenderContext`, builds the BVH over the scene objects, and dispatches row-bands to worker processes. Uses a recursive `_trace()` helper (max depth: 8). For each hit it:
1. Computes diffuse shading via `_shade()` (skipped for `ior > 1.0` objects).
2. Applies mirror reflection (`obj.reflect`, only for `ior == 1.0` objects).
3. Handles transparency/refraction: if `ior == 1.0`, naive alpha blend; if `ior > 1.0`, physical Snell's law + TIR + Schlick Fresnel via `_refract()` and `_schlick()`.

Returns a `list[Color]`. Prints progress every 50 rows.

#### `rendering/shading.py` — Shading

Lambertian diffuse shading and soft shadow computation. Shadow computation via `_shadow_factor()` fires one shadow ray per point light or `light.samples` rays per area light. Transparent objects attenuate by `(1 - opacity)`.

#### `rendering/physics.py` — Physics

Snell's law refraction (`_refract()`) and Schlick Fresnel approximation (`_schlick()`). Handles entering/exiting detection, total internal reflection, and the final reflection/refraction blend.

#### `main.py` — Entry Point

Parses CLI arguments, calls the parser and renderer, and saves the result as a PNG via Pillow. Invoked via `python3 main.py`.

---

## Usage

### Requirements

- Python 3.10+
- Pillow (`pip install Pillow`)

### Running

```bash
python3 main.py <scene> [-W WIDTH] [-H HEIGHT] [-o OUTPUT]
```

**Arguments:**

| Flag | Default | Description |
|------|---------|-------------|
| `scene` | (required) | Path to a `.pov` (legacy) or `.pow` scene file |
| `-W`, `--width` | 800 | Image width in pixels |
| `-H`, `--height` | 600 | Image height in pixels |
| `-o`, `--output` | `output.png` | Output file path (PNG format) |
| `--aa` | 0 | Anti-aliasing samples per pixel (0 = off, 2–4 = good quality) |
| `-j`, `--jobs` | 1 | Worker processes: `1` = single-threaded (default); `0` = all CPU cores |

**Example:**

```bash
python3 main.py examples/01-basic.pov -W 1024 -H 768 -o render.png
```

---

## Limitations

- Pure Python (slow for large images / many shadow samples); parallel rendering via `--jobs N` mitigates this for CPU-bound scenes but incurs pickling overhead

---

## Possible Next Steps

- **GIF animations** — capacity of animating objects through space and output a gif/video
- **Textures**

---

## Changelog

### v1.4 — Area Lights & Color Temperature (2026-03-15)

- **Light class hierarchy**: `LightBase` ABC → `PointLight`, `SphereLight`, `DiskLight`, `RectLight`; backwards-compat `Light` wrapper unchanged
- **`DiskLight`**: flat circular area light with `normal`, `radius`, `two_sided`; one-sided by default; supports `visible` rendering
- **`RectLight`**: parallelogram area light with `corner + edge1 + edge2`; same one-sided / visible semantics
- **Color temperature** (`color_temperature` field in Kelvin): `color_from_kelvin()` in `color.py` converts any value 1000–40000K to an RGB tint (Tanner Helland approximation); `effective_color()` multiplies kelvin × tint × intensity
- **Visible lights**: lights with `visible true` appear as glowing geometry; primary rays return `effective_color` when they hit a visible light before any surface
- **Colored light shading**: diffuse contribution now uses `light.effective_color()` — white lights behave identically to before; colored or warm lights tint the scene
- **POW parser**: added `disk_light`, `rect_light` blocks; `true`/`false` boolean literals; `color`, `intensity`, `color_temperature`, `visible` on all light types
- **POV parser**: added `disk_light`, `rect_light` blocks; all new light fields supported
- Example scene: `examples/18-area-lights.pow`

### v1.3 — Transform System (2026-03-10)

- `transform { scale (sx,sy,sz) rotate (rx,ry,rz) translate (tx,ty,tz) }` block in `.pow` — wraps any shape or CSG node with a full 4×4 affine matrix
- **Non-uniform scaling**, arbitrary Euler-angle rotation, and translation in a single composable block
- Transform values are stored as a `TransformedShape` wrapper; the ray is inverse-transformed into local space for intersection; normals are corrected via the transposed inverse
- Reusable: `let t = transform { ... }` can be referenced by multiple shapes, or inlined per-shape
- Works with all primitives (sphere, box, cylinder, cone, torus, mesh) and all CSG nodes (union, intersection, difference)
- Foundation for future keyframe animation — each frame can update transform fields
- Example scene: `examples/16-transforms.pow`

### v1.2 — CSG & OBJ Mesh Loading (2026-03-10)

- **CSG** — `union`, `intersection`, `difference` nodes in `.pow`; backed by `hit_intervals()` on all bounded shapes; optional `fuse` mode on union blends materials at boundaries
- **`HitInterval`** dataclass and `mat_obj` field on `HitRecord` to support CSG material routing
- **OBJ mesh loading** — `mesh { file "..." }` block in `.pow`; `obj_loader.py` parses Wavefront OBJ/MTL including per-vertex normals and multi-material groups; `TriangleMesh` accelerated by an internal BVH
- **`Triangle`** primitive with Möller-Trumbore intersection and interpolated vertex normals
- Example scenes: `examples/13-csg.pow`, `examples/15-boot.pow`

### v1.1 — Functions & Conditionals (2026-03-04)

- User-defined functions: `let f = fn(a, b) { ... }` with block bodies
- Functions can return values (last expression) and/or emit scene objects
- Functions can call other previously-defined functions
- `if`/`else if`/`else` conditionals with comparison operators (`==`, `!=`, `<`, `>`, `<=`, `>=`)
- `if` usable as return expression inside function bodies
- Example scene: `examples/12-pow-functions.pow`

### v1.0 — POW Scene Language (2026-03-04)

- New `.pow` scene format — a proper scripting language replacing the regex-based `.pov` parser
- **Lexer** (`src/lexer.py`): tokenises `.pow` source into typed tokens
- **Recursive-descent parser** (`src/lang_parser.py`): full expression parser with operator precedence, vec3 arithmetic, built-in math functions (`sin`, `cos`, `abs`, `pi`)
- **Variables:** `let name = expr` — eliminates repeated magic numbers
- **Loops:** `for i in range(n)`, `for i in range(start, stop)`, `for x in [list]` — generates repeated geometry programmatically
- **Materials:** `let m = material { color (...) opacity N reflect N ior N }` — reusable material definitions referenced by name in shape blocks
- **Imports:** `import "path/to/file.pow"` — share material libraries across scenes; `examples/materials/standard.pow` provided
- **All 6 shapes** supported in `.pow`: sphere, plane, box, cylinder, cone, torus — same property names as `.pov`
- **Backwards compatible:** `.pov` files continue to work unchanged; format is selected by file extension
- **Reference manual:** `docs/pow-reference.md` — complete language reference with all blocks, expressions, and migration guide
- Example scenes: `examples/10-pow-loops.pow`, `examples/11-pow-materials.pow`

### v0.9 — Multiprocessing (2026-03-04)

- `--jobs N` / `-j N` flag: splits the image into row-bands and renders them in parallel using `N` worker processes
- `--jobs 0` auto-detects the number of CPU cores (`os.cpu_count()`)
- Single-threaded path unchanged; `--jobs 1` (default) behaves identically to before
- Speedup scales roughly linearly with core count for CPU-bound renders

### v0.8.1 — Source layout restructuring (2026-03-04)

- Moved all source modules into `src/` (flat layout; no packaging required)
- Split `scene.py` into `shapes.py` (all geometric primitives + HitRecord) and `scene.py` (Camera, Light, Scene)
- Added `tests/conftest.py` so pytest finds `src/` modules without manual `PYTHONPATH`

### v0.8 — New Primitives (2026-03-04)

- `Box` (AABB) primitive: `min`/`max` corners, slab intersection, supports all material fields
- `Cylinder` primitive: arbitrary-axis capped cylinder (`bottom`/`top`/`radius`), closed caps with disk intersection
- `Cone` (generalised frustum): `bottom_radius`/`top_radius` allow true cones and frustums, arbitrary axis
- `Torus` primitive: `center`/`axis`/`major_radius`/`minor_radius`, solved analytically via Ferrari quartic
- Example scene `examples/08-shapes.pov` showcasing all four new primitives
- All new primitives support `color`, `opacity`, `reflect`, and `ior` material fields
- Fully backward-compatible: existing `.pov` files render identically

### v0.7 — Refractions (2026-03-02)

- `ior` field on `sphere` and `plane` objects (default: 1.0 = air; e.g. 1.5 = glass, 2.4 = diamond)
- Physically-based refraction via Snell's law in vector form (`_refract()`)
- Total internal reflection (TIR) when angle exceeds critical angle — ray mirrors instead of transmitting
- Schlick Fresnel approximation (`_schlick()`) blends reflection and refraction by angle of incidence
- `RefractionRay` type in `ray.py` (marker subclass of `Ray`)
- Backward-compatible: `ior 1.0` (default) uses the existing naive transparency path; all existing `.pov` files render identically
- `reflect` and diffuse shading bypassed for `ior > 1.0` objects — Fresnel handles reflection

### v0.6 — Reflections (2026-03-02)

- `reflect` field on `sphere` and `plane` objects (0.0 = matte, 1.0 = perfect mirror)
- Mirror reflections computed via recursive `ReflectionRay` tracing
- Blending: `surface_color × (1 − reflect) + reflected_color × reflect`
- Works with transparency: a surface can be simultaneously reflective and transparent
- Origin biased 0.001 along surface normal to prevent self-intersection artifacts
- Governed by existing `MAX_DEPTH = 8` recursion limit
- Fully backward-compatible: existing `.pov` files default to `reflect 0.0`

### v0.5 — Anti-aliasing (2026-03-02)

- `--aa N` CLI flag: fires N jittered VisionRays per pixel and averages the results (supersampling SSAA)
- Default is 0 (off) — existing scenes render identically without the flag
- `--aa 1` also uses the fast single-ray path; use `--aa 2` or higher to activate AA
- Jitter is uniform random within each pixel's footprint, eliminating aliased staircase edges
- Recommended values: `--aa 2` (fast), `--aa 4` (good quality), `--aa 8` (high quality)
- No new dependencies; pure-Python implementation

### v0.4 — Soft Shadows (2026-03-01)

- Sphere area lights: `radius` and `samples` fields on the `light` block
- `_shadow_factor()` in `renderer.py` — fires shadow rays from hit points to the light
- Point lights (`radius 0`): one ray, hard shadows
- Area lights (`radius > 0`): `samples` rays via rejection sampling, averaged → soft penumbra
- Transparent objects in shadow paths attenuate light by `(1 - opacity)` rather than blocking fully
- `.pov` parser reads `radius` and `samples` from light blocks (defaults: 0.0 and 16)
- Fully backward-compatible: existing `.pov` files render identically

### v0.3 — Transparency (2026-03-01)

- Per-object `opacity` field on `Sphere` and `Plane` (default: 1.0 = fully opaque)
- Alpha blending: transparent objects blend surface color with the scene behind them
- Recursive `_trace()` renderer with configurable max depth (default: 8)
- `.pov` parser supports `opacity N` field in sphere/plane blocks
- Fully backward-compatible: existing `.pov` files render identically

### v0.2 — Color Support (2026-03-01)

- Added `Color` class (r, g, b floats, arithmetic, clamp, to_bytes)
- Named color palette: 15 preset colors (full rainbow + neutrals)
- Per-object `color` field on `Sphere` and `Plane` (default: white)
- `.pov` parser supports `color <r,g,b>` and `color name` syntax
- Output upgraded from grayscale PNG to RGB PNG

### v0.1 — MVP (2026-03-01)

- Initial implementation
- VisionRay camera model with configurable FOV
- Sphere and Plane primitives
- Lambertian diffuse + ambient shading (grayscale)
- Custom `.pov` parser with comment support
- PNG output via Pillow
- CLI with configurable resolution and output path
