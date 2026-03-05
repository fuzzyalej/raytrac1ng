# POW Scene Language Reference

**Version:** 1.0
**File extension:** `.pow`

---

## Overview

POW is the scene description language for the Mini Raytracer. It replaces the old `.pov` format with a proper scripting language that supports variables, expressions, loops, imports, and reusable materials. The old `.pov` format continues to work — the renderer auto-detects the file extension.

**Key improvements over `.pov`:**
- Variables (`let`) so you don't repeat magic numbers
- Arithmetic expressions on numbers and vectors
- `for` loops to generate repeated geometry
- `import` to share material libraries across scenes
- Reusable `material` blocks with all four material fields
- Vec3 uses `(x, y, z)` instead of `<x, y, z>`

---

## Comments

```
// This is a single-line comment — everything after // is ignored
```

---

## Variables

```
let name = <expr>
```

`let` binds a value to a name in the current scope. Variables can hold numbers, vec3s, strings, lists, or materials.

```
let radius   = 1.5
let center   = (0, 1, 0)
let color    = (1.0, 0.2, 0.2)
let positions = [(0,0,0), (1,0,0), (2,0,0)]
```

Variables are lexically scoped. Variables defined inside a `for` block are not visible outside it. Variables from `import`ed files are merged into the current scope.

---

## Types

| Type     | Example                  | Notes                          |
|----------|--------------------------|--------------------------------|
| Number   | `3.14`, `-1`, `0`        | All numbers are floats         |
| Vec3     | `(1.0, 2.0, 3.0)`        | Three comma-separated numbers  |
| String   | `"materials/lib.pow"`    | Used only in `import`          |
| List     | `[(1,0,0), (0,1,0)]`     | For loop iteration             |
| Material | `material { ... }`       | Assigned via `let`             |

---

## Expressions

Expressions support the standard arithmetic operators with conventional precedence:

```
+   -   *   /
```

Parentheses override precedence: `(2 + 3) * 4`.

**Number arithmetic:**
```
let x = 2 + 3 * 4       // 14
let y = (2 + 3) * 4     // 20
```

**Vec3 arithmetic:**
```
let a = (1,0,0) + (0,1,0)    // (1,1,0)
let b = (1,2,3) * 2          // (2,4,6)
let c = 2 * (1,2,3)          // (2,4,6)
let d = (4,6,8) / 2          // (2,3,4)
```

**Built-in functions and constants:**

| Name      | Description                     |
|-----------|---------------------------------|
| `pi`      | 3.14159…                        |
| `sin(x)`  | Sine of x (radians)             |
| `cos(x)`  | Cosine of x (radians)           |
| `abs(x)`  | Absolute value of x             |

```
let angle = pi / 4
let x = cos(angle)
let y = sin(angle)
```

---

## Material Blocks

Materials bundle the four material properties into a reusable object:

```
let name = material {
  color   (r, g, b)   // RGB in [0.0, 1.0] — default (1.0, 1.0, 1.0)
  opacity N           // [0.0, 1.0] — default 1.0 (fully opaque)
  reflect N           // [0.0, 1.0] — default 0.0 (matte)
  ior     N           // >= 1.0     — default 1.0 (air, no refraction)
}
```

All four fields are optional. Unspecified fields take their defaults. Reference a material by name inside any shape block using the `material` keyword:

```
let glass = material { color (0.8, 0.9, 1.0)  opacity 0.0  ior 1.5 }

sphere { center (0,1,0)  radius 1.0  material glass }
```

Inline material fields (`color`, `opacity`, `reflect`, `ior`) written directly in a shape block take precedence over a referenced material:

```
sphere { center (0,1,0)  radius 1.0  material glass  opacity 0.5 }
// opacity is 0.5, other fields come from glass
```

---

## Object Blocks

All object blocks share the same structure: a keyword, braces, and key-value properties. Properties can be expressions.

### camera (required, exactly one)

```
camera {
  location (x, y, z)    // camera position in world space
  look_at  (x, y, z)    // point the camera aims at
  fov      N            // vertical field of view in degrees
}
```

### light

```
light {
  position (x, y, z)    // light position in world space
  radius   N            // sphere radius for area light (default: 0 = point light)
  samples  N            // shadow rays per area light sample (default: 16)
}
```

`radius 0` gives hard shadows (point light). `radius > 0` gives soft penumbra shadows.

### sphere

```
sphere {
  center (x, y, z)
  radius N
  // material fields (choose one approach):
  material <name>                          // reference a material variable
  color (r,g,b)  opacity N  reflect N  ior N  // or inline
}
```

### plane

```
plane {
  normal (x, y, z)    // surface normal (will be normalized)
  offset N            // distance from origin along the normal
  material <name>     // or inline color/opacity/reflect/ior
}
```

### box

Axis-aligned bounding box.

```
box {
  min (x, y, z)    // minimum corner
  max (x, y, z)    // maximum corner
  material <name>  // or inline fields
}
```

### cylinder

Capped cylinder with arbitrary axis.

```
cylinder {
  bottom (x, y, z)    // center of bottom cap
  top    (x, y, z)    // center of top cap (axis = top − bottom)
  radius N
  material <name>     // or inline fields
}
```

### cone

Generalised frustum — set `top_radius 0.0` for a true cone apex.

```
cone {
  bottom        (x, y, z)
  top           (x, y, z)
  bottom_radius N
  top_radius    N         // 0.0 = true cone apex
  material <name>         // or inline fields
}
```

### torus

```
torus {
  center       (x, y, z)    // center of the torus ring
  axis         (x, y, z)    // symmetry axis (will be normalized)
  major_radius N            // distance from center to tube center
  minor_radius N            // radius of the tube
  material <name>           // or inline fields
}
```

### Material field reference (all shapes)

| Field     | Type   | Range      | Default          | Description                            |
|-----------|--------|------------|------------------|----------------------------------------|
| `color`   | vec3   | [0.0, 1.0] | (1.0, 1.0, 1.0)  | RGB surface color                      |
| `opacity` | number | [0.0, 1.0] | 1.0              | 0 = fully transparent, 1 = fully opaque|
| `reflect` | number | [0.0, 1.0] | 0.0              | 0 = matte, 1 = perfect mirror          |
| `ior`     | number | >= 1.0     | 1.0              | Index of refraction (1.5 = glass)      |

Common `ior` values: `1.33` (water), `1.5` (glass), `2.4` (diamond). Setting `ior > 1.0` enables physical Snell's law refraction (Fresnel); `reflect` is then ignored on that object.

---

## Loops

### range loop

```
for i in range(n) {
  // i goes 0, 1, ..., n-1
}

for i in range(start, stop) {
  // i goes start, start+1, ..., stop-1
}
```

### list loop

```
let colors = [(1,0,0), (0,1,0), (0,0,1)]
for c in colors {
  sphere { center (0,1,0)  radius 0.5  color c }
}
```

The loop variable is available as an expression inside the body:

```
let spacing = 2.5
for i in range(5) {
  sphere {
    center (i * spacing, 1.0, 0)
    radius 0.8
    color  (1, 0, 0)
  }
}
```

Loops can be nested. Each iteration runs in a child scope — assignments inside the loop body do not affect the outer scope.

---

## Imports

```
import "relative/path/to/file.pow"
```

The path is resolved relative to the importing file. After the import, all variables defined in the imported file are available in the current scope.

```
import "materials/standard.pow"

sphere { center (0,1,0)  radius 1.0  material glass }  // glass defined in standard.pow
```

Circular imports are detected and raise an error. Import does not re-export scene objects — only variable bindings are merged.

---

## Complete Example

```
// Import shared materials
import "materials/standard.pow"

// Local materials
let red_glass = material {
  color   (1.0, 0.2, 0.2)
  opacity 0.0
  ior     1.5
}

// Scene setup
camera { location (0, 3, -9)  look_at (0, 1, 0)  fov 55 }
light  { position (4, 8, -4)  radius 1.5  samples 24 }

// Ground
plane { normal (0,1,0)  offset 0  material matte_gray }

// A row of glass spheres using a loop
let count   = 7
let spacing = 2.0
for i in range(count) {
  sphere {
    center ((i - count / 2) * spacing, 1.0, 0)
    radius 0.8
    material glass
  }
}

// One distinctive sphere using a local material
sphere { center (0, 1, -2)  radius 1.2  material red_glass }

// Other shapes
box      { min (-0.5, 0, 2)  max (0.5, 2, 3)  material mirror }
cylinder { bottom (3,0,0)  top (3,2,0)  radius 0.4  material glass }
cone     { bottom (5,0,0)  top (5,2,0)  bottom_radius 0.6  top_radius 0.0  material matte_white }
torus    { center (-3,0.5,2)  axis (0,1,0)  major_radius 1.0  minor_radius 0.3  material glass }
```

---

## Migrating from `.pov`

| Old `.pov`                  | New `.pow`                       |
|-----------------------------|----------------------------------|
| `<x, y, z>`                 | `(x, y, z)`                      |
| `color name` (e.g. `red`)   | `let red = material { color (1,0,0) }` then `material red` |
| Repeated magic numbers      | `let spacing = 2.5` then use `spacing` |
| Copy-pasted sphere blocks   | `for i in range(n) { sphere { ... } }` |
| No material sharing         | `import "materials/standard.pow"` |

---

## Running

```bash
python3 main.py examples/10-pow-loops.pow -W 800 -H 600 -o render.png
python3 main.py examples/10-pow-loops.pow -W 800 -H 600 -o render.png --aa 4 --jobs 0
```

`.pov` files continue to work unchanged:
```bash
python3 main.py examples/01-basic.pov -W 800 -H 600 -o render.png
```

---

## Functions

```
let name = fn(param1, param2, ...) {
  // body: let bindings, loops, if/else, scene blocks, other fn calls
  // last expression = return value (or None if body ends with a scene block)
}
```

### Value-returning function

```
let circle_pos = fn(i, count, r) {
  let angle = i * 2 * pi / count
  (cos(angle) * r, 0, sin(angle) * r)
}
sphere { center circle_pos(3, 8, 2.0)  radius 0.5  color (1,1,1) }
```

### Scene-emitting function

```
let ring = fn(i, count, radius) {
  let angle = i * 2 * pi / count
  let pos   = (cos(angle) * radius, 0, sin(angle) * radius)
  sphere { center pos  radius 0.3  color (1, 0.3, 0.3) }
}
for i in range(8) { ring(i, 8, 3.0) }
```

Functions can emit any scene objects (sphere, box, cylinder, etc.) and can call other previously-defined functions. Recursion is not supported.

### Calling

- **As a statement** (to emit scene objects): `name(arg1, arg2)`
- **As an expression** (to use return value): `sphere { radius name(x)  ... }`

### Scope

Functions capture the environment at definition time. Variables defined after the function definition are not visible inside the function body. Parameters shadow outer variables of the same name.

---

## Conditionals

```
if <condition> {
  // body
} else if <condition> {
  // body
} else {
  // body
}
```

Conditions use comparison operators: `==`, `!=`, `<`, `>`, `<=`, `>=`. Only number comparisons are supported — comparing vec3 values raises an error. No `and`/`or` operators; nest `if` statements instead.

### As a statement

```
let x = 2.0
if x > 5 {
  sphere { center (0,1,0)  radius 3.0  color (1,0,0) }
} else if x > 1 {
  sphere { center (0,1,0)  radius 2.0  color (0,1,0) }
} else {
  sphere { center (0,1,0)  radius 1.0  color (0,0,1) }
}
```

### As a return expression in a function

```
let bigger = fn(a, b) {
  if a > b { a } else { b }
}
sphere { center (0,1,0)  radius bigger(1.5, 0.8)  color (1,1,1) }
```
