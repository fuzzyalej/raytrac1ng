# Mini Raytracer — Documentation

**Version:** v1.2
**Last updated:** 2026-03-05

---

## Changelog

### v1.2 — 2026-03-05
- SAH BVH spatial acceleration; automatic for all scenes — no scene changes needed
- All bounded shapes (`Sphere`, `Box`, `Cylinder`, `Cone`, `Torus`) participate in the BVH
- `Plane` (infinite/unbounded) is always tested linearly outside the BVH

### v1.1 — 2026-03-04
- POW language: functions (`fn`), conditionals (`if`/`else if`/`else`)

### v1.0 — 2026-03-03
- POW scene language with variables, loops, materials, imports

---

## Overview

A pure-Python raytracer that reads a custom `.pov` scene description file and outputs an RGB PNG image. No external raytracing libraries are used — all intersection math and shading is implemented from scratch. The only external dependency is **Pillow** for image output.

It supports Lambertian diffuse shading with soft shadows from sphere area lights, per-object opacity with alpha blending, mirror reflections via the `reflect` field, physically-based refractions (Snell's law + Fresnel) via the `ior` field, and a custom `.pov` scene format.

---

## How It Works

### Rendering Pipeline

```
.pow file → lang_parser → Scene (camera, lights, objects)
.pov file → parser      ↗
                          ↓
                      Renderer
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
| **ShadowRay** | Hit point → light, determines if in shadow | Implemented |
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
- The result is clamped to [0, 1] and multiplied by the object's color to produce an RGB Color.

### Shadow Model

Shadow computation varies by light type:

- **Point light** (`radius 0`, the default): A single shadow ray is fired to `light.position`. The result is binary — fully lit or fully shadowed (hard shadows).
- **Area light** (`radius > 0`): `samples` shadow rays are fired to uniformly random points within a sphere of the given radius centred on `light.position`. The shadow factor is the average across all samples. This produces a **soft penumbra** — surfaces near the shadow edge receive partial light.

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
│   ├── vector.py       Vec3 — 3D math
│   ├── color.py        Color — RGB arithmetic + named palette
│   ├── ray.py          Ray types (VisionRay, ReflectionRay, RefractionRay)
│   ├── shapes.py       HitRecord + all primitives (Sphere, Plane, Box, Cylinder, Cone, Torus)
│   ├── scene.py        Camera, Light, Scene container
│   ├── bvh.py          SAH BVH spatial acceleration (AABB, BVHNode, BVH)
│   ├── renderer.py     Core render loop and shading
│   ├── parser.py       .pov scene file parser (legacy)
│   ├── lexer.py        POW language lexer
│   ├── lang_parser.py  POW recursive-descent parser + evaluator
│   └── new_parser.py   POW→Scene adapter
├── tests/
│   ├── conftest.py   Adds src/ to sys.path for pytest
│   └── test_*.py
├── examples/
│   ├── 01-basic.pov / .png
│   ├── 02-colors.pov / .png
│   ├── 03-transparency.pov / .png
│   ├── 04-shadows.pov / .png
│   ├── 05-two-lights.pov / .png
│   ├── 06-reflections.pov / .png
│   ├── 07-refractions.pov / .png
│   ├── 08-shapes.pov / .png
│   ├── 09-mecha.pov / .png
│   ├── 10-pow-loops.pow / .png   (POW: variables + for loops)
│   ├── 11-pow-materials.pow / .png (POW: materials + all shapes)
│   └── materials/
│       └── standard.pow          Shared material library
├── docs/
│   ├── pow-reference.md  POW language reference manual
│   └── plans/            Implementation plans
├── main.py           CLI entry point
└── README.md
```

### Module Details

#### `vector.py` — Vec3

The foundation of all math in the raytracer. A 3D vector class with:

- Arithmetic operators: `+`, `-`, `*` (scalar), `/` (scalar), unary `-`
- Vector operations: `dot()`, `cross()`, `normalize()`, `length()`, `length_squared()`
- Uses `__slots__` for memory efficiency
- No external dependencies (no numpy)

#### `color.py` — Color

- **`Color`**: Dataclass with `r`, `g`, `b` float components in [0.0, 1.0]. Supports `+`, `*` (scalar), `clamp()`, and `to_bytes()` → `(R, G, B)` int tuple.
- **`NAMED_COLORS`**: Dictionary of 15 preset named colors for use in `.pov` files.

#### `ray.py` — Ray Types

- **`Ray`**: Base class with `origin` (Vec3), `direction` (Vec3, auto-normalized), and `point_at(t)`.
- **`VisionRay`**: Camera-to-pixel rays.
- **`ReflectionRay`**: Mirror reflection rays (direction: `D − 2(D·N)N`).
- **`RefractionRay`**: Snell's-law refraction rays (direction computed by `_refract()` in `renderer.py`).

#### `shapes.py` — Geometric Primitives

- **`HitRecord`**: Dataclass holding intersection info — `t` (distance), `point` (world-space position), `normal` (surface normal at hit).
- **`Sphere`**: Defined by `center` and `radius`. Implements `hit(ray)` using the quadratic formula.
- **`Plane`**: Defined by `normal` and `offset`. Implements `hit(ray)` using ray-plane intersection.
- **`Box`**: Axis-aligned bounding box defined by `min` and `max` corners. Uses the slab intersection method; normals are derived from which slab face was hit.
- **`Cylinder`**: Capped cylinder defined by `bottom`, `top`, and `radius`. Decomposes the ray into axial and perpendicular components for intersection; closed disk caps are tested separately.
- **`Cone`**: Generalised frustum defined by `bottom`, `top`, `bottom_radius`, and `top_radius`. Setting `top_radius 0.0` gives a true cone apex.
- **`Torus`**: Ring defined by `center`, `axis`, `major_radius`, and `minor_radius`. Solved analytically via Ferrari's quartic method.
- All shape classes support optional `color`, `opacity`, `reflect`, and `ior` material fields.

#### `scene.py` — Scene Graph

- **`Camera`**: Builds a coordinate frame from `location`/`look_at`/`fov`. Provides `get_vision_ray(px, py, width, height)` to generate a VisionRay for any pixel.
- **`Light`**: Holds a `position` (Vec3), `radius` (float, default 0.0 = point light), and `samples` (int, default 16). Used for diffuse shading and shadow computation.
- **`Scene`**: Container dataclass holding a camera, a list of lights, and a list of objects.

#### `parser.py` — Scene File Parser

Reads the custom `.pov` format (see Scene File Format below). Uses regex to extract blocks (`camera { ... }`, `sphere { ... }`, etc.) and parse their key-value contents. Supports `//` single-line comments.

#### `renderer.py` — Render Loop

Uses a recursive `_trace()` helper (max depth: 8). For each hit it:
1. Computes diffuse shading via `_shade()` (skipped for `ior > 1.0` objects).
2. Applies mirror reflection (`obj.reflect`, only for `ior == 1.0` objects).
3. Handles transparency/refraction: if `ior == 1.0`, naive alpha blend; if `ior > 1.0`, physical Snell's law + TIR + Schlick Fresnel via `_refract()` and `_schlick()`.

Shadow computation via `_shadow_factor()` fires one shadow ray per point light or `light.samples` rays per area light. Transparent objects attenuate by `(1 - opacity)`. Returns a `list[Color]`. Prints progress every 50 rows.

#### `main.py` — Entry Point

Parses CLI arguments, calls the parser and renderer, and saves the result as a PNG via Pillow. Invoked via `python3 main.py`.

---

## POW Scene Language

`.pow` is the new scene language — a proper scripting language with variables, expressions, loops, imports, and reusable materials. See **[docs/pow-reference.md](docs/pow-reference.md)** for the full reference.

Quick example:

```
import "materials/standard.pow"

let count = 5
camera { location (0, 3, -9)  look_at (0, 1, 0)  fov 55 }
light  { position (4, 8, -4)  radius 1.5  samples 24 }
plane  { normal (0,1,0)  offset 0  material matte_gray }

for i in range(count) {
  sphere {
    center (i * 2.0, 1.0, 0)
    radius 0.8
    material glass
  }
}
```

```bash
python3 main.py examples/10-pow-loops.pow -W 800 -H 600 -o render.png
```

---

## Legacy Scene File Format (.pov)

The `.pov` format uses a block-based syntax with C-style braces. Vectors use angle-bracket notation `<x, y, z>`. Single-line comments with `//` are supported.

### Supported Blocks

#### camera (required, exactly one)

```
camera {
  location <x, y, z>    // Camera position in world space
  look_at  <x, y, z>    // Point the camera is aimed at
  fov      60           // Vertical field of view in degrees
}
```

#### light (one or more recommended)

```
light {
  position <x, y, z>    // Light position in world space
  radius   1.5          // Optional: sphere radius for area light (default: 0 = point light)
  samples  32           // Optional: shadow rays per area light sample (default: 16)
}
```

`radius 0` (default) produces hard shadows from a point light using a single shadow ray.
`radius > 0` produces soft penumbra shadows using `samples` rays fired to random points on the light sphere.

#### sphere

```
sphere {
  center <x, y, z>      // Center of the sphere
  radius 1.0            // Radius
  color <r, g, b>       // Optional RGB color, floats in [0.0, 1.0] (default: white)
  color name            // OR: a named color (see Named Colors)
  opacity 0.5           // Optional opacity in [0.0, 1.0] (default: 1.0 = fully opaque)
  reflect 0.5           // Optional reflectivity in [0.0, 1.0] (default: 0.0); ignored if ior > 1.0
  ior 1.5               // Optional index of refraction >= 1.0 (default: 1.0 = air, no refraction)
                        //   Common values: 1.33 (water), 1.5 (glass), 2.4 (diamond)
                        //   Set opacity 0.0 for clear glass
}
```

#### plane

```
plane {
  normal <x, y, z>      // Surface normal (will be normalized)
  offset 0              // Distance from origin along the normal
  color <r, g, b>       // Optional RGB color, floats in [0.0, 1.0] (default: white)
  color name            // OR: a named color (see Named Colors)
  opacity 0.5           // Optional opacity in [0.0, 1.0] (default: 1.0 = fully opaque)
  reflect 0.5           // Optional reflectivity in [0.0, 1.0] (default: 0.0); ignored if ior > 1.0
  ior 1.5               // Optional index of refraction >= 1.0 (default: 1.0 = air, no refraction)
}
```

#### box

```
box {
  min <x, y, z>            // Minimum corner of the axis-aligned bounding box
  max <x, y, z>            // Maximum corner of the axis-aligned bounding box
  color <r, g, b>          // Optional RGB color (default: white)
  color name               // OR: a named color (see Named Colors)
  opacity 0.5              // Optional opacity in [0.0, 1.0] (default: 1.0)
  reflect 0.5              // Optional reflectivity in [0.0, 1.0] (default: 0.0)
  ior 1.5                  // Optional index of refraction >= 1.0 (default: 1.0)
}
```

#### cylinder

```
cylinder {
  bottom <x, y, z>         // Centre of the bottom cap
  top    <x, y, z>         // Centre of the top cap (axis direction = top − bottom)
  radius 1.0               // Radius of the cylinder
  color <r, g, b>          // Optional RGB color (default: white)
  color name               // OR: a named color (see Named Colors)
  opacity 0.5              // Optional opacity in [0.0, 1.0] (default: 1.0)
  reflect 0.5              // Optional reflectivity in [0.0, 1.0] (default: 0.0)
  ior 1.5                  // Optional index of refraction >= 1.0 (default: 1.0)
}
```

#### cone

```
cone {
  bottom        <x, y, z>  // Centre of the bottom cap
  top           <x, y, z>  // Centre of the top cap
  bottom_radius 1.0        // Radius at the bottom cap
  top_radius    0.0        // Radius at the top cap (0.0 = true cone apex)
  color <r, g, b>          // Optional RGB color (default: white)
  color name               // OR: a named color (see Named Colors)
  opacity 0.5              // Optional opacity in [0.0, 1.0] (default: 1.0)
  reflect 0.5              // Optional reflectivity in [0.0, 1.0] (default: 0.0)
  ior 1.5                  // Optional index of refraction >= 1.0 (default: 1.0)
}
```

#### torus

```
torus {
  center       <x, y, z>   // Centre of the torus
  axis         <x, y, z>   // Symmetry axis (will be normalized)
  major_radius 1.5         // Distance from the torus centre to the tube centre
  minor_radius 0.4         // Radius of the tube
  color <r, g, b>          // Optional RGB color (default: white)
  color name               // OR: a named color (see Named Colors)
  opacity 0.5              // Optional opacity in [0.0, 1.0] (default: 1.0)
  reflect 0.5              // Optional reflectivity in [0.0, 1.0] (default: 0.0)
  ior 1.5                  // Optional index of refraction >= 1.0 (default: 1.0)
}
```

### Example

```
// A sphere floating above a ground plane
camera {
  location <0, 2, -5>
  look_at <0, 0.5, 0>
  fov 60
}

light {
  position <5, 10, -3>
}

plane {
  normal <0, 1, 0>
  offset 0
}

sphere {
  center <0, 1, 0>
  radius 1.0
}
```

### Named Colors

The following color names can be used directly in `sphere` and `plane` blocks:

| Name      | RGB (float)        |
|-----------|--------------------|
| `red`     | (1.0, 0.0, 0.0)   |
| `green`   | (0.0, 0.8, 0.0)   |
| `blue`    | (0.0, 0.0, 1.0)   |
| `yellow`  | (1.0, 1.0, 0.0)   |
| `cyan`    | (0.0, 1.0, 1.0)   |
| `magenta` | (1.0, 0.0, 1.0)   |
| `orange`  | (1.0, 0.5, 0.0)   |
| `purple`  | (0.5, 0.0, 0.5)   |
| `pink`    | (1.0, 0.4, 0.7)   |
| `indigo`  | (0.29, 0.0, 0.51) |
| `violet`  | (0.56, 0.0, 1.0)  |
| `white`   | (1.0, 1.0, 1.0)   |
| `black`   | (0.0, 0.0, 0.0)   |
| `gray`    | (0.5, 0.5, 0.5)   |
| `brown`   | (0.6, 0.3, 0.1)   |

---

## Usage

### Requirements

- Python 3.10+
- Pillow (`pip install Pillow`)

### Running

```bash
python3 main.py <scene.pov> [-W WIDTH] [-H HEIGHT] [-o OUTPUT]
```

**Arguments:**

| Flag | Default | Description |
|------|---------|-------------|
| `scene` | (required) | Path to the `.pov` scene file |
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
- Only sphere area lights — no disk or rectangular lights

---

## Possible Next Steps

- **Disk and rectangular area lights** — more physically accurate than sphere area lights for studio-style lighting setups (e.g., `disk { position ... normal ... radius ... }`)
- **Mesh file loading (OBJ/PLY)** for complex geometry
- **GIF animations** - capacity of animating objects through space and output a gif/video

---

## Changelog

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
