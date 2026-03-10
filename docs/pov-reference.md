# POV Scene Language Reference

**Version:** legacy
**File extension:** `.pov`

---

## Overview

POV is the legacy scene description format for the Mini Raytracer. It uses a simple block-based syntax with C-style braces and angle-bracket vectors. No variables, loops, or scripting — every value is written inline.

The renderer auto-detects the file extension: `.pov` files use this parser, `.pow` files use the modern scripting language.

**When to use `.pov`:**
- Quick one-off scenes where scripting overhead isn't worth it
- Reference for how `.pov` files work before migrating to `.pow`
- Compatibility with existing scene files

**Limitations compared to `.pow`:**
- No variables — magic numbers must be repeated everywhere
- No loops — repeated geometry requires copy-pasting blocks
- No material sharing — each shape carries its own inline material fields
- No imports — no way to share definitions across files
- No CSG — union, intersection, difference not supported
- No transforms — scale, rotate, translate not available
- Vectors use `<x, y, z>` instead of `(x, y, z)`

---

## Comments

```
// This is a single-line comment — everything after // is ignored
```

---

## Vectors

Vectors use angle-bracket notation with comma-separated components:

```
<x, y, z>
```

```
<0, 1, 0>
<1.5, -0.3, 2.7>
<0.8, 0.2, 0.0>    // used for color RGB
```

---

## Object Blocks

All blocks share the same structure: a keyword, braces, and key-value properties on separate lines (or inline — whitespace is flexible).

### camera (required, exactly one)

```
camera {
  location <x, y, z>    // camera position in world space
  look_at  <x, y, z>    // point the camera aims at
  fov      N            // vertical field of view in degrees
}
```

**Example:**

```
camera {
  location <0, 2, -5>
  look_at  <0, 0.5, 0>
  fov 60
}
```

---

### light

```
light {
  position <x, y, z>    // light position in world space
  radius   N            // sphere radius for area light (default: 0 = point light)
  samples  N            // shadow rays per area light sample (default: 16)
}
```

`radius 0` (default) produces hard shadows from a point light using a single shadow ray.
`radius > 0` produces soft penumbra shadows using `samples` rays fired to random points on the light sphere.

**Examples:**

```
// Point light — hard shadows
light {
  position <5, 10, -3>
}

// Area light — soft shadows
light {
  position <4, 8, -4>
  radius   1.5
  samples  32
}
```

---

### sphere

```
sphere {
  center <x, y, z>      // center of the sphere
  radius N              // radius
  color <r, g, b>       // optional RGB in [0.0, 1.0] (default: white)
  color name            // OR a named color (see Named Colors)
  opacity N             // [0.0, 1.0] — default 1.0 (fully opaque)
  reflect N             // [0.0, 1.0] — default 0.0 (matte); ignored if ior > 1.0
  ior     N             // >= 1.0 — default 1.0 (air, no refraction)
}
```

---

### plane

An infinite flat surface.

```
plane {
  normal <x, y, z>      // surface normal (will be normalized)
  offset N              // distance from origin along the normal
  color <r, g, b>       // optional RGB (default: white)
  color name            // OR a named color
  opacity N             // [0.0, 1.0] — default 1.0
  reflect N             // [0.0, 1.0] — default 0.0; ignored if ior > 1.0
  ior     N             // >= 1.0 — default 1.0
}
```

**Plane equation:** `dot(point, normal) = offset`. For a horizontal ground plane at y=0: `normal <0, 1, 0>  offset 0`.

---

### box

Axis-aligned bounding box (AABB).

```
box {
  min <x, y, z>         // minimum corner
  max <x, y, z>         // maximum corner
  color <r, g, b>       // optional RGB (default: white)
  color name            // OR a named color
  opacity N             // [0.0, 1.0] — default 1.0
  reflect N             // [0.0, 1.0] — default 0.0
  ior     N             // >= 1.0 — default 1.0
}
```

---

### cylinder

Capped cylinder with arbitrary axis.

```
cylinder {
  bottom <x, y, z>      // center of the bottom cap
  top    <x, y, z>      // center of the top cap (axis = top − bottom)
  radius N              // radius of the cylinder
  color <r, g, b>       // optional RGB (default: white)
  color name            // OR a named color
  opacity N             // [0.0, 1.0] — default 1.0
  reflect N             // [0.0, 1.0] — default 0.0
  ior     N             // >= 1.0 — default 1.0
}
```

---

### cone

Generalised frustum. Set `top_radius 0.0` for a true cone apex.

```
cone {
  bottom        <x, y, z>   // center of the bottom cap
  top           <x, y, z>   // center of the top cap
  bottom_radius N           // radius at the bottom cap
  top_radius    N           // radius at the top cap (0.0 = true cone apex)
  color <r, g, b>           // optional RGB (default: white)
  color name                // OR a named color
  opacity N                 // [0.0, 1.0] — default 1.0
  reflect N                 // [0.0, 1.0] — default 0.0
  ior     N                 // >= 1.0 — default 1.0
}
```

---

### torus

```
torus {
  center       <x, y, z>    // center of the torus ring
  axis         <x, y, z>    // symmetry axis (will be normalized)
  major_radius N            // distance from center to tube center
  minor_radius N            // radius of the tube
  color <r, g, b>           // optional RGB (default: white)
  color name                // OR a named color
  opacity N                 // [0.0, 1.0] — default 1.0
  reflect N                 // [0.0, 1.0] — default 0.0
  ior     N                 // >= 1.0 — default 1.0
}
```

---

## Material Field Reference

All shapes share the same four optional material fields:

| Field     | Type   | Range      | Default          | Description                            |
|-----------|--------|------------|------------------|----------------------------------------|
| `color`   | vec3   | [0.0, 1.0] | (1.0, 1.0, 1.0)  | RGB surface color                      |
| `opacity` | number | [0.0, 1.0] | 1.0              | 0 = fully transparent, 1 = fully opaque|
| `reflect` | number | [0.0, 1.0] | 0.0              | 0 = matte, 1 = perfect mirror          |
| `ior`     | number | >= 1.0     | 1.0              | Index of refraction (1.5 = glass)      |

Common `ior` values: `1.33` (water), `1.5` (glass), `2.4` (diamond). Setting `ior > 1.0` enables physical Snell's law refraction (Fresnel); `reflect` is then ignored on that object. Set `opacity 0.0` for clear glass.

---

## Named Colors

The following color names can be used instead of `<r, g, b>` vectors:

| Name      | RGB (float)         |
|-----------|---------------------|
| `red`     | (1.0, 0.0, 0.0)    |
| `green`   | (0.0, 0.8, 0.0)    |
| `blue`    | (0.0, 0.0, 1.0)    |
| `yellow`  | (1.0, 1.0, 0.0)    |
| `cyan`    | (0.0, 1.0, 1.0)    |
| `magenta` | (1.0, 0.0, 1.0)    |
| `orange`  | (1.0, 0.5, 0.0)    |
| `purple`  | (0.5, 0.0, 0.5)    |
| `pink`    | (1.0, 0.4, 0.7)    |
| `indigo`  | (0.29, 0.0, 0.51)  |
| `violet`  | (0.56, 0.0, 1.0)   |
| `white`   | (1.0, 1.0, 1.0)    |
| `black`   | (0.0, 0.0, 0.0)    |
| `gray`    | (0.5, 0.5, 0.5)    |
| `brown`   | (0.6, 0.3, 0.1)    |

---

## Complete Example

```
// 08-shapes.pov — Showcase of all six primitives

camera { location <0, 6, -18>  look_at <0, 1, 0>  fov 45 }
light  { position <10, 20, -5> }

// Ground plane
plane { normal <0, 1, 0>  offset -0.1  color gray }

// Box (AABB)
box {
  min <-6, 0, -2>  max <-3.5, 2.5, 1>
  color red
  reflect 0.1
}

// Cylinder
cylinder {
  bottom <-1.5, 0, -1>  top <-1.5, 3, -1>  radius 0.8
  color blue
}

// Cone (true apex)
cone {
  bottom <1.5, 0, -1>  top <1.5, 3, -1>
  bottom_radius 1.0  top_radius 0.0
  color green
}

// Torus
torus {
  center <5, 1.5, 0>  axis <0, 1, 0>
  major_radius 1.3  minor_radius 0.45
  color yellow
  reflect 0.2
}

// Glass sphere (Snell's law + Fresnel)
sphere {
  center <0, 1, 0>
  radius 1.2
  color white
  opacity 0.0
  ior 1.5
}

// Mirror sphere
sphere {
  center <-3, 1, 0>
  radius 1.0
  color <0.9, 0.9, 0.9>
  reflect 0.9
}
```

---

## Running

```bash
python3 main.py examples/01-basic.pov -W 800 -H 600 -o render.png
python3 main.py examples/08-shapes.pov -W 800 -H 600 -o render.png --aa 4 --jobs 0
```

---

## Migrating to `.pow`

The `.pov` format is fully supported but has no scripting features. Consider migrating to `.pow` when:

- You need to place multiple copies of the same shape
- You want to reuse material definitions
- You want named variables instead of magic numbers

| Old `.pov`                        | New `.pow`                              |
|-----------------------------------|-----------------------------------------|
| `<x, y, z>`                       | `(x, y, z)`                             |
| `color red`                       | `let red = material { color (1,0,0) }`  |
| Repeated inline material fields   | `let m = material { ... }`              |
| Copy-pasted shape blocks          | `for i in range(n) { sphere { ... } }`  |
| No sharing across files           | `import "materials/standard.pow"`       |

See **[pow-reference.md](pow-reference.md)** for the full POW language reference.
