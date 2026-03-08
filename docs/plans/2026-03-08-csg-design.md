# CSG — Constructive Solid Geometry Design

**Date:** 2026-03-08
**Status:** Approved

---

## Overview

Add Constructive Solid Geometry (CSG) operations to the raytracer and POW language.
CSG lets users combine primitive shapes with boolean set operations to create complex solids.

### Operations

| Keyword | Arity | Description |
|---------|-------|-------------|
| `union` | n-ary | All regions covered by any child. Optional `fuse yes` suppresses internal seams. |
| `intersection` | n-ary | Only regions covered by all children simultaneously. |
| `difference` | binary | First child minus second child (A − B). |

`merge` is **not** a separate keyword — it is `union { fuse yes  ... }`.

---

## Constraints & Decisions

- **Bounded children only** — `Plane` is not allowed as a CSG child (it has no bounding box). Future extension possible.
- **CSG as statements** — CSG blocks are scene-emitting statements, like `sphere`. They work inside `for` loops, `if`/`else`, and function bodies. They cannot be returned as values or assigned to variables.
- **Material override** — CSG node may optionally specify material fields (`color`, `opacity`, `reflect`, `ior`, `material <name>`). If provided, overrides child materials. If not, the specific child shape that was hit donates its material. Mirrors existing inline-override behaviour.

---

## Architecture

### Core challenge

The current `hit()` method returns only the **first** (closest) intersection. CSG requires all ray–solid overlap intervals `[t_enter, t_exit]` to perform boolean set operations. A new `hit_intervals()` protocol is added alongside `hit()`.

### New: `HitInterval` dataclass (`shapes.py`)

```python
@dataclass
class HitInterval:
    t_enter:      float
    t_exit:       float
    enter_normal: Vec3    # outward normal at entry face
    exit_normal:  Vec3    # outward normal at exit face
    enter_obj:    object  # source shape for material at entry
    exit_obj:     object  # source shape for material at exit
```

### Extended: `HitRecord` (`shapes.py`)

```python
@dataclass
class HitRecord:
    t:       float
    point:   Vec3
    normal:  Vec3
    mat_obj: object = None  # if set, renderer uses this for material
```

`mat_obj = None` for all existing primitives — renderer falls back to `obj` as today. CSG nodes set `mat_obj` to either themselves (material override present) or the specific child that was intersected.

### New protocol: `hit_intervals()`

Every bounded shape gains:

```python
def hit_intervals(self, ray, t_min=0.001, t_max=float('inf')) -> list[HitInterval]
```

| Shape | Max intervals | Notes |
|-------|-------------|-------|
| Sphere | 1 | both roots of quadratic |
| Box | 1 | slab method already tracks t_enter/t_exit |
| Cylinder | 1 | curved surface + both caps |
| Cone | 1 | curved surface + both caps |
| Torus | 2 | quartic gives up to 4 roots → 2 intervals |

CSG nodes implement the same protocol, so nesting is free.

---

## Interval Operations

### `union` (n-ary)

Collect all intervals from all children, sort by `t_enter`, merge overlapping:
- Entry normal/obj from the first-entering child.
- Exit normal/obj from the last-exiting child.

```
A: [──────]        [────]
B:     [──────]
→  [──────────]    [────]
```

### `union` with `fuse yes`

Same merge geometry, but internal boundaries between overlapping children are **suppressed**. A ray travelling from outside → into A → into B continues seamlessly without seeing the A–B internal surface. Critical for transparent/glass unions (no seam rendered at the overlap).

### `intersection` (n-ary)

Keep only regions where **all** children contain the ray simultaneously:
- `t_enter` = max of all children's entry t's → normal from the **last-entering** child.
- `t_exit`  = min of all children's exit t's  → normal from the **first-exiting** child.

```
A: [──────────]
B:     [──────────]
→      [──────]
```

### `difference` (binary: A − B)

Walk A's intervals, subtract B's intervals:

- Entering A while outside B → A's entry normal (unchanged).
- Exiting A while outside B  → A's exit normal (unchanged).
- B's entry cuts into an A interval → becomes an exit with **B's entry normal flipped** (outward face of result).
- B's exit inside an A interval   → becomes a re-entry with **B's exit normal flipped**.

```
A: [──────────────]
B:      [─────]
→  [────]     [───]
         ↑ B's normals, flipped
```

---

## Material Handling

### Assignment in `hit()`

```python
def hit(self, ray, t_min, t_max):
    intervals = self.hit_intervals(ray, t_min, t_max)
    if not intervals:
        return None
    iv = intervals[0]
    return HitRecord(
        t=iv.t_enter,
        point=ray.point_at(iv.t_enter),
        normal=iv.enter_normal,
        mat_obj=self if self._has_material() else iv.enter_obj,
    )
```

### Renderer change (`renderer.py`)

One-line change in `_trace` — introduce a `mat` local:

```python
hit, obj = _find_hit(ray, scene)
mat = hit.mat_obj if hit.mat_obj is not None else obj
# use mat.color, mat.opacity, mat.reflect, mat.ior everywhere obj was used
```

All existing scenes are unaffected (`mat_obj` is `None` for primitives → `mat = obj`).

Shadow rays iterate `scene.objects` and call `obj.hit()` + `obj.opacity`. CSG nodes participate automatically. No shadow-ray changes needed.

---

## BVH Integration

CSG nodes implement `bounding_box()` and participate in the BVH as first-class bounded shapes. The BVH never looks inside a CSG node.

| Operation | `bounding_box()` |
|-----------|----------------|
| `union` | AABB union of all children |
| `intersection` | AABB intersection of all children (fall back to union if degenerate) |
| `difference` | Same as left child A (conservative over-approximation) |

No BVH code changes required.

---

## POW Language Syntax

### Block types

```
union {
  fuse yes              // optional, default no
  material <name>       // optional material override
  color (r,g,b)         // or inline fields
  opacity N
  reflect N
  ior     N

  sphere { ... }        // n-ary: any number of children
  box    { ... }
  union  { ... }        // nesting: any shape or CSG node
  difference { ... }
}

intersection {
  // optional material fields
  sphere { ... }        // n-ary
  box    { ... }
}

difference {
  // optional material fields
  box    { ... }        // child 1 = A  (exactly 2 required — parse error otherwise)
  sphere { ... }        // child 2 = B
}
```

### Example

```
let glass = material { opacity 0.0  ior 1.5  color (0.8, 0.9, 1.0) }

// Glass sphere with a cylindrical tunnel bored through it
difference {
  material glass
  sphere   { center (0,1,0)  radius 1.2 }
  cylinder { bottom (0,-2,0)  top (0,3,0)  radius 0.4 }
}

// Three overlapping glass spheres fused into one blob (no internal seams)
union {
  fuse yes
  material glass
  sphere { center (0,1,0)    radius 0.8 }
  sphere { center (0.6,1,0)  radius 0.8 }
  sphere { center (0.3,1.6,0) radius 0.8 }
}

// CSG inside a loop
for i in range(4) {
  difference {
    sphere { center (i*2.5, 1, 0)  radius 1.0  color (1,0.3,0.3) }
    box    { min (-0.3,0,-0.3)  max (0.3,2,0.3)  color (1,1,1) }
  }
}
```

### Parser changes (`lang_parser.py`)

- Recognise `union`, `intersection`, `difference` as block keywords.
- Inside a CSG block, children may be any shape block (sphere, box, cylinder, cone, torus) or another CSG block — parsing recurses.
- `fuse` is a boolean field valid only inside `union` (parse warning/error elsewhere).
- `difference` validates exactly 2 children after parsing (parse error if not).

---

## Files Changed

| File | Change |
|------|--------|
| `src/shapes.py` | Add `HitInterval`; extend `HitRecord` with `mat_obj`; add `hit_intervals()` to all 5 bounded shapes; add `CSGUnion`, `CSGIntersection`, `CSGDifference` |
| `src/renderer.py` | Introduce `mat` local in `_trace`; use `mat` for all material property lookups |
| `src/lang_parser.py` | Parse `union`, `intersection`, `difference` blocks; handle `fuse`; validate `difference` arity |
| `src/scene.py` | No changes expected |
| `docs/pow-reference.md` | Document CSG syntax, operations, `fuse`, examples |
| `tests/test_csg.py` | Unit tests: interval operations, `hit()` integration, material override, bounding boxes |

---

## Future Extensions

- `Plane` as a CSG child (half-space slicing)
- CSG objects as first-class language values (assignable, returnable from functions)
