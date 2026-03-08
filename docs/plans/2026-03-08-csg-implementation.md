# CSG Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add union, intersection, and difference CSG operations to the raytracer and POW language.

**Architecture:** Add a `HitInterval` dataclass and `hit_intervals()` method to all bounded shapes, returning the full `[t_enter, t_exit]` interval per ray traversal. Three CSG node classes (`CSGUnion`, `CSGIntersection`, `CSGDifference`) implement the same protocol, combining child intervals with boolean set logic. Extend `HitRecord` with `mat_obj` for per-hit material routing, wire it into the renderer in one line, and add `union`/`intersection`/`difference` block parsing to `lang_parser.py` + `new_parser.py`.

**Tech Stack:** Python 3.11, existing `shapes.py` / `renderer.py` / `lang_parser.py` / `new_parser.py`, pytest.

---

## How to run tests

```bash
cd /Users/fuzzyalej/Code/raytrac1ng
pytest tests/ -x -q
```

Run a single file: `pytest tests/test_csg.py -x -v`

---

## Task 1: Data structures — `HitInterval` + `HitRecord.mat_obj`

**Files:**
- Modify: `src/shapes.py` (top of file, after existing imports)
- Test: `tests/test_csg.py` (create)

**Step 1: Write the failing test**

Create `tests/test_csg.py`:

```python
"""Tests for CSG — data structures, interval operations, and shape classes."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from shapes import HitInterval, HitRecord
from vector import Vec3


def test_hit_interval_fields():
    n = Vec3(1, 0, 0)
    iv = HitInterval(1.0, 3.0, n, Vec3(-1, 0, 0), None, None)
    assert iv.t_enter == 1.0
    assert iv.t_exit == 3.0
    assert iv.enter_normal == n


def test_hit_record_mat_obj_default():
    rec = HitRecord(t=1.0, point=Vec3(0,0,0), normal=Vec3(0,1,0))
    assert rec.mat_obj is None
```

**Step 2: Run — expect FAIL**

```bash
pytest tests/test_csg.py -x -v
```
Expected: `ImportError: cannot import name 'HitInterval'`

**Step 3: Add `HitInterval` to `shapes.py` and `mat_obj` to `HitRecord`**

In `src/shapes.py`, replace the existing `HitRecord` dataclass and add `HitInterval` right after the imports block:

```python
@dataclass
class HitInterval:
    """A contiguous segment [t_enter, t_exit] of ray–solid overlap."""
    t_enter:      float
    t_exit:       float
    enter_normal: Vec3    # outward normal at the entry face
    exit_normal:  Vec3    # outward normal at the exit face
    enter_obj:    object  # source shape for material at entry
    exit_obj:     object  # source shape for material at exit


@dataclass
class HitRecord:
    """Information about a ray–object intersection."""
    t:       float
    point:   Vec3
    normal:  Vec3
    mat_obj: object = None  # if set, renderer uses this for material instead of obj
```

**Step 4: Run — expect PASS**

```bash
pytest tests/test_csg.py::test_hit_interval_fields tests/test_csg.py::test_hit_record_mat_obj_default -v
```

**Step 5: Full test suite must stay green**

```bash
pytest tests/ -x -q
```

**Step 6: Commit**

```bash
git add src/shapes.py tests/test_csg.py
git commit -m "feat(csg): add HitInterval dataclass and mat_obj field on HitRecord"
```

---

## Task 2: `Sphere.hit_intervals()`

**Files:**
- Modify: `src/shapes.py` — add method to `Sphere`
- Test: `tests/test_csg.py`

**Step 1: Write the failing test**

Append to `tests/test_csg.py`:

```python
from shapes import Sphere
from ray import VisionRay


def _ray(ox, oy, oz, dx, dy, dz):
    return VisionRay(Vec3(ox, oy, oz), Vec3(dx, dy, dz))


def test_sphere_hit_intervals_normal():
    s = Sphere(Vec3(0, 0, 0), 1.0)
    ray = _ray(-3, 0, 0, 1, 0, 0)  # along +x, enters at x=-1 (t=2), exits at x=1 (t=4)
    ivs = s.hit_intervals(ray)
    assert len(ivs) == 1
    assert abs(ivs[0].t_enter - 2.0) < 1e-5
    assert abs(ivs[0].t_exit  - 4.0) < 1e-5
    assert ivs[0].enter_normal.x < -0.9  # points left (outward at x=-1)
    assert ivs[0].exit_normal.x  >  0.9  # points right (outward at x=+1)
    assert ivs[0].enter_obj is s
    assert ivs[0].exit_obj  is s


def test_sphere_hit_intervals_ray_inside():
    """Ray starts at center — t_enter is negative, t_exit is positive."""
    s = Sphere(Vec3(0, 0, 0), 1.0)
    ray = _ray(0, 0, 0, 1, 0, 0)
    ivs = s.hit_intervals(ray, t_min=1e-9)
    assert len(ivs) == 1
    assert ivs[0].t_enter < 0        # behind origin
    assert abs(ivs[0].t_exit - 1.0) < 1e-5


def test_sphere_hit_intervals_miss():
    s = Sphere(Vec3(0, 0, 0), 1.0)
    ray = _ray(-3, 5, 0, 1, 0, 0)   # passes far above
    assert s.hit_intervals(ray) == []
```

**Step 2: Run — expect FAIL** (`AttributeError: 'Sphere' object has no attribute 'hit_intervals'`)

**Step 3: Add `hit_intervals()` to `Sphere` in `src/shapes.py`**

Add after the existing `hit()` method and before `bounding_box()`:

```python
def hit_intervals(self, ray, t_min: float = 1e-9,
                  t_max: float = float('inf')) -> list:
    """Return 0 or 1 HitInterval for this ray.

    t_min should be a tiny epsilon (1e-9) — NOT the usual 0.001 ray bias.
    t_enter may be negative when the ray origin is inside the sphere;
    CSG operations handle that case in their own hit() method.
    """
    oc = ray.origin - self.center
    a  = ray.direction.dot(ray.direction)
    b  = 2.0 * oc.dot(ray.direction)
    c  = oc.dot(oc) - self.radius * self.radius
    disc = b * b - 4 * a * c
    if disc < 0:
        return []
    sq = math.sqrt(disc)
    t1 = (-b - sq) / (2.0 * a)   # smaller root (entry)
    t2 = (-b + sq) / (2.0 * a)   # larger root  (exit)
    if t2 < t_min or t1 > t_max:
        return []   # interval entirely invisible
    n1 = (ray.point_at(t1) - self.center) / self.radius   # outward at entry
    n2 = (ray.point_at(t2) - self.center) / self.radius   # outward at exit
    return [HitInterval(t1, t2, n1, n2, self, self)]
```

**Step 4: Run — expect PASS**

```bash
pytest tests/test_csg.py -k "sphere" -v
```

**Step 5: Full suite green**

```bash
pytest tests/ -x -q
```

**Step 6: Commit**

```bash
git add src/shapes.py tests/test_csg.py
git commit -m "feat(csg): Sphere.hit_intervals()"
```

---

## Task 3: `Box.hit_intervals()`

**Files:**
- Modify: `src/shapes.py` — add method to `Box`
- Test: `tests/test_csg.py`

**Step 1: Write the failing test**

Append to `tests/test_csg.py`:

```python
from shapes import Box


def test_box_hit_intervals_normal():
    b = Box(Vec3(-1, -1, -1), Vec3(1, 1, 1))
    ray = _ray(-3, 0, 0, 1, 0, 0)   # enters at x=-1 (t=2), exits at x=1 (t=4)
    ivs = b.hit_intervals(ray)
    assert len(ivs) == 1
    assert abs(ivs[0].t_enter - 2.0) < 1e-5
    assert abs(ivs[0].t_exit  - 4.0) < 1e-5
    assert ivs[0].enter_normal.x < -0.9
    assert ivs[0].exit_normal.x  >  0.9


def test_box_hit_intervals_miss():
    b = Box(Vec3(-1, -1, -1), Vec3(1, 1, 1))
    ray = _ray(-3, 5, 0, 1, 0, 0)
    assert b.hit_intervals(ray) == []


def test_box_hit_intervals_ray_inside():
    b = Box(Vec3(-1, -1, -1), Vec3(1, 1, 1))
    ray = _ray(0, 0, 0, 1, 0, 0)    # starts at center
    ivs = b.hit_intervals(ray, t_min=1e-9)
    assert len(ivs) == 1
    assert ivs[0].t_enter < 0
    assert abs(ivs[0].t_exit - 1.0) < 1e-5
```

**Step 2: Run — expect FAIL**

**Step 3: Add `hit_intervals()` to `Box` in `src/shapes.py`**

Add after `Box.hit()`, before `Box.bounding_box()`. This is a refactor of the slab logic that returns BOTH entry and exit:

```python
def hit_intervals(self, ray, t_min: float = 1e-9,
                  t_max: float = float('inf')) -> list:
    """Return 0 or 1 HitInterval. t_enter may be negative (ray starts inside)."""
    t_enter = -float('inf')
    t_exit  =  float('inf')
    enter_axis = 0;  enter_sign = -1.0
    exit_axis  = 0;  exit_sign  =  1.0

    ro = (ray.origin.x,    ray.origin.y,    ray.origin.z)
    rd = (ray.direction.x, ray.direction.y, ray.direction.z)
    lo = (self.min_pt.x,   self.min_pt.y,   self.min_pt.z)
    hi = (self.max_pt.x,   self.max_pt.y,   self.max_pt.z)

    for axis in range(3):
        if abs(rd[axis]) < 1e-8:
            if ro[axis] < lo[axis] or ro[axis] > hi[axis]:
                return []
            continue
        t0 = (lo[axis] - ro[axis]) / rd[axis]
        t1 = (hi[axis] - ro[axis]) / rd[axis]
        if t0 <= t1:
            s0, s1 = -1.0, 1.0
        else:
            t0, t1 = t1, t0
            s0, s1 =  1.0, -1.0
        if t0 > t_enter:
            t_enter = t0;  enter_axis = axis;  enter_sign = s0
        if t1 < t_exit:
            t_exit  = t1;  exit_axis  = axis;  exit_sign  = s1
        if t_enter > t_exit:
            return []

    if t_exit < t_min or t_enter > t_max:
        return []

    en = [0.0, 0.0, 0.0];  en[enter_axis] = enter_sign
    ex = [0.0, 0.0, 0.0];  ex[exit_axis]  = exit_sign
    return [HitInterval(t_enter, t_exit, Vec3(*en), Vec3(*ex), self, self)]
```

**Step 4: Run — expect PASS**

```bash
pytest tests/test_csg.py -k "box" -v
```

**Step 5: Full suite green, then commit**

```bash
pytest tests/ -x -q
git add src/shapes.py tests/test_csg.py
git commit -m "feat(csg): Box.hit_intervals()"
```

---

## Task 4: `Cylinder.hit_intervals()`

**Files:**
- Modify: `src/shapes.py` — add method to `Cylinder`
- Test: `tests/test_csg.py`

**Step 1: Write the failing test**

Append to `tests/test_csg.py`:

```python
from shapes import Cylinder


def test_cylinder_hit_intervals_normal():
    # Vertical cylinder from y=0 to y=2, radius=1, centered on x=z=0
    cyl = Cylinder(Vec3(0, 0, 0), Vec3(0, 2, 0), 1.0)
    ray = _ray(-3, 1, 0, 1, 0, 0)   # horizontal through mid-height
    ivs = cyl.hit_intervals(ray)
    assert len(ivs) == 1
    assert abs(ivs[0].t_enter - 2.0) < 1e-4   # enters curved surface at x=-1
    assert abs(ivs[0].t_exit  - 4.0) < 1e-4   # exits  curved surface at x=+1


def test_cylinder_hit_intervals_miss():
    cyl = Cylinder(Vec3(0, 0, 0), Vec3(0, 2, 0), 1.0)
    ray = _ray(-3, 5, 0, 1, 0, 0)   # above cylinder
    assert cyl.hit_intervals(ray) == []
```

**Step 2: Run — expect FAIL**

**Step 3: Add `hit_intervals()` to `Cylinder` in `src/shapes.py`**

The key change from `hit()`: collect ALL valid intersection t-values (no t_min filtering on individual candidates — only on the final interval), then return [min, max] as the interval.

Add after `Cylinder.hit()`, before `Cylinder.bounding_box()`:

```python
def hit_intervals(self, ray, t_min: float = 1e-9,
                  t_max: float = float('inf')) -> list:
    """Return 0 or 1 HitInterval. Collects all surface hits, returns [min, max]."""
    D  = self.axis
    P  = self.bottom
    r2 = self.radius * self.radius
    oc = ray.origin - P

    d_proj  = D.dot(ray.direction)
    oc_proj = D.dot(oc)
    d_perp  = ray.direction - D * d_proj
    oc_perp = oc - D * oc_proj

    hits = []   # list of (t, normal)

    # ---- Curved surface ----
    a = d_perp.dot(d_perp)
    if abs(a) > 1e-8:
        b    = 2.0 * oc_perp.dot(d_perp)
        c    = oc_perp.dot(oc_perp) - r2
        disc = b * b - 4.0 * a * c
        if disc >= 0:
            sq = math.sqrt(disc)
            for t_cand in [(-b - sq) / (2.0 * a), (-b + sq) / (2.0 * a)]:
                point = ray.point_at(t_cand)
                h     = D.dot(point - P)
                if 0.0 <= h <= self.height:
                    n = (point - P - D * h).normalize()
                    hits.append((t_cand, n))

    # ---- Caps ----
    for cap_centre, cap_normal in [
        (self.bottom, D * -1.0),
        (self.top,    D),
    ]:
        denom = ray.direction.dot(cap_normal)
        if abs(denom) < 1e-8:
            continue
        t_cand = (cap_centre - ray.origin).dot(cap_normal) / denom
        point  = ray.point_at(t_cand)
        radial = point - cap_centre
        rp     = radial - D * D.dot(radial)
        if rp.dot(rp) <= r2:
            hits.append((t_cand, cap_normal))

    if not hits:
        return []

    hits.sort(key=lambda x: x[0])
    t_e, n_e = hits[0]
    t_x, n_x = hits[-1]

    if t_x < t_min or t_e > t_max:
        return []

    return [HitInterval(t_e, t_x, n_e, n_x, self, self)]
```

**Step 4: Run — expect PASS**

```bash
pytest tests/test_csg.py -k "cylinder" -v
```

**Step 5: Full suite green, then commit**

```bash
pytest tests/ -x -q
git add src/shapes.py tests/test_csg.py
git commit -m "feat(csg): Cylinder.hit_intervals()"
```

---

## Task 5: `Cone.hit_intervals()`

**Files:**
- Modify: `src/shapes.py` — add method to `Cone`
- Test: `tests/test_csg.py`

**Step 1: Write the failing test**

Append to `tests/test_csg.py`:

```python
from shapes import Cone


def test_cone_hit_intervals_normal():
    # Cylinder-like cone (equal radii) from y=0 to y=2, radius=1
    cone = Cone(Vec3(0, 0, 0), Vec3(0, 2, 0), 1.0, 1.0)
    ray  = _ray(-3, 1, 0, 1, 0, 0)
    ivs  = cone.hit_intervals(ray)
    assert len(ivs) == 1
    assert abs(ivs[0].t_enter - 2.0) < 1e-4
    assert abs(ivs[0].t_exit  - 4.0) < 1e-4


def test_cone_hit_intervals_miss():
    cone = Cone(Vec3(0, 0, 0), Vec3(0, 2, 0), 1.0, 0.0)
    ray  = _ray(-3, 5, 0, 1, 0, 0)
    assert cone.hit_intervals(ray) == []
```

**Step 2: Run — expect FAIL**

**Step 3: Add `hit_intervals()` to `Cone` in `src/shapes.py`**

Same pattern as Cylinder — collect all surface hits, return `[min, max]`:

```python
def hit_intervals(self, ray, t_min: float = 1e-9,
                  t_max: float = float('inf')) -> list:
    D     = self.axis
    P     = self.bottom
    slope = self.slope
    R0    = self.bottom_radius
    oc    = ray.origin - P

    d_proj  = D.dot(ray.direction)
    oc_proj = D.dot(oc)
    d_perp  = ray.direction - D * d_proj
    oc_perp = oc - D * oc_proj

    hits = []   # list of (t, normal)

    # ---- Curved surface ----
    a = d_perp.dot(d_perp) - (slope * d_proj) ** 2
    b = 2.0 * (oc_perp.dot(d_perp)
               - (R0 + slope * oc_proj) * slope * d_proj)
    c = oc_perp.dot(oc_perp) - (R0 + slope * oc_proj) ** 2

    if abs(a) > 1e-8:
        disc = b * b - 4.0 * a * c
        if disc >= 0:
            sq = math.sqrt(disc)
            for t_cand in [(-b - sq)/(2.0*a), (-b + sq)/(2.0*a)]:
                point = ray.point_at(t_cand)
                h_y   = D.dot(point - P)
                if 0.0 <= h_y <= self.height:
                    radial     = (point - P) - D * h_y
                    radial_len = radial.length()
                    if radial_len > 1e-10:
                        n = (radial / radial_len - D * slope).normalize()
                    else:
                        n = -D
                    hits.append((t_cand, n))
    elif abs(b) > 1e-8:
        t_cand = -c / b
        point  = ray.point_at(t_cand)
        h_y    = D.dot(point - P)
        if 0.0 <= h_y <= self.height:
            radial     = (point - P) - D * h_y
            radial_len = radial.length()
            if radial_len > 1e-10:
                n = (radial / radial_len - D * slope).normalize()
                hits.append((t_cand, n))

    # ---- Caps ----
    for cap_centre, cap_radius, cap_normal in [
        (self.bottom, self.bottom_radius, D * -1.0),
        (self.top,    self.top_radius,    D),
    ]:
        if cap_radius <= 0.0:
            continue
        denom = ray.direction.dot(cap_normal)
        if abs(denom) < 1e-8:
            continue
        t_cand = (cap_centre - ray.origin).dot(cap_normal) / denom
        point  = ray.point_at(t_cand)
        radial = point - cap_centre
        rp     = radial - D * D.dot(radial)
        if rp.dot(rp) <= cap_radius ** 2:
            hits.append((t_cand, cap_normal))

    if not hits:
        return []

    hits.sort(key=lambda x: x[0])
    t_e, n_e = hits[0]
    t_x, n_x = hits[-1]

    if t_x < t_min or t_e > t_max:
        return []

    return [HitInterval(t_e, t_x, n_e, n_x, self, self)]
```

**Step 4: Run — expect PASS**

```bash
pytest tests/test_csg.py -k "cone" -v
```

**Step 5: Full suite green, then commit**

```bash
pytest tests/ -x -q
git add src/shapes.py tests/test_csg.py
git commit -m "feat(csg): Cone.hit_intervals()"
```

---

## Task 6: `Torus.hit_intervals()`

**Files:**
- Modify: `src/shapes.py` — add method to `Torus`
- Test: `tests/test_csg.py`

**Step 1: Write the failing test**

Append to `tests/test_csg.py`:

```python
from shapes import Torus


def test_torus_hit_intervals_two_intervals():
    """Ray through the torus hole → 2 intervals."""
    t = Torus(Vec3(0, 0, 0), Vec3(0, 1, 0), major_radius=2.0, minor_radius=0.5)
    ray = _ray(0, 0, -5, 0, 0, 1)   # along +z through center hole
    ivs = t.hit_intervals(ray)
    assert len(ivs) == 2             # enters tube, exits, enters again, exits


def test_torus_hit_intervals_one_interval():
    """Ray through the outer wall → 1 interval."""
    t = Torus(Vec3(0, 0, 0), Vec3(0, 1, 0), major_radius=2.0, minor_radius=0.5)
    ray = _ray(4, 0, 0, -1, 0, 0)   # along -x, through outer wall only
    ivs = t.hit_intervals(ray)
    assert len(ivs) == 1
    assert abs(ivs[0].t_enter - 1.5) < 1e-4   # outer surface at x=2.5 (t=1.5)


def test_torus_hit_intervals_miss():
    t = Torus(Vec3(0, 0, 0), Vec3(0, 1, 0), major_radius=2.0, minor_radius=0.5)
    ray = _ray(0, 5, 0, 0, 1, 0)    # above torus
    assert t.hit_intervals(ray) == []
```

**Step 2: Run — expect FAIL**

**Step 3: Add `hit_intervals()` to `Torus` in `src/shapes.py`**

The quartic gives up to 4 roots; pair them as `[t0,t1]` and `[t2,t3]` (sorted).

Add after `Torus.hit()`, before `Torus.bounding_box()`:

```python
def hit_intervals(self, ray, t_min: float = 1e-9,
                  t_max: float = float('inf')) -> list:
    """Return 0, 1, or 2 HitIntervals (torus quartic gives up to 4 roots → 2 pairs)."""
    q = self._to_local(ray.origin - self.center)
    d = self._to_local(ray.direction)
    R, r = self.major_radius, self.minor_radius

    d2          = d.dot(d)
    dq          = d.dot(q)
    q2          = q.dot(q)
    d_radial_sq = d.x * d.x + d.z * d.z
    dq_radial   = d.x * q.x + d.z * q.z
    q_radial_sq = q.x * q.x + q.z * q.z
    K           = q2 + R * R - r * r

    c4 = d2 * d2
    c3 = 4.0 * d2 * dq
    c2 = 4.0 * dq * dq + 2.0 * d2 * K - 4.0 * R * R * d_radial_sq
    c1 = 4.0 * dq * K  - 8.0 * R * R * dq_radial
    c0 = K * K          - 4.0 * R * R * q_radial_sq

    roots = sorted(_solve_quartic_ferrari(c4, c3, c2, c1, c0))

    def _normal_at(t):
        p_world = ray.point_at(t)
        p_loc   = self._to_local(p_world - self.center)
        rho     = math.sqrt(p_loc.x * p_loc.x + p_loc.z * p_loc.z)
        if rho < 1e-10:
            return None
        cx, cz = R * p_loc.x / rho, R * p_loc.z / rho
        n_loc  = Vec3(p_loc.x - cx, p_loc.y, p_loc.z - cz).normalize()
        return self._from_local(n_loc)

    intervals = []
    i = 0
    while i + 1 < len(roots):
        t_e, t_x = roots[i], roots[i + 1]
        if t_x < t_min or t_e > t_max:
            i += 2
            continue
        n_e = _normal_at(t_e)
        n_x = _normal_at(t_x)
        if n_e is not None and n_x is not None:
            intervals.append(HitInterval(t_e, t_x, n_e, n_x, self, self))
        i += 2

    return intervals
```

**Step 4: Run — expect PASS**

```bash
pytest tests/test_csg.py -k "torus" -v
```

**Step 5: Full suite green, then commit**

```bash
pytest tests/ -x -q
git add src/shapes.py tests/test_csg.py
git commit -m "feat(csg): Torus.hit_intervals()"
```

---

## Task 7: CSG helpers + `CSGUnion`

**Files:**
- Modify: `src/shapes.py` — add helper functions and `CSGUnion` class at the bottom
- Test: `tests/test_csg.py`

**Step 1: Write the failing test**

Append to `tests/test_csg.py`:

```python
from shapes import CSGUnion


def test_union_two_separate_spheres_hit_closer():
    """Union of two non-overlapping spheres: ray hits the closer one."""
    a = Sphere(Vec3(-2, 0, 0), 0.5)
    b = Sphere(Vec3( 2, 0, 0), 0.5)
    u = CSGUnion([a, b])
    ray = _ray(-5, 0, 0, 1, 0, 0)
    hit = u.hit(ray)
    assert hit is not None
    assert abs(hit.t - 2.5) < 1e-4    # enters 'a' at x=-2.5


def test_union_two_overlapping_spheres_one_interval():
    """Overlapping spheres merge into a single interval."""
    a = Sphere(Vec3(-0.3, 0, 0), 1.0)
    b = Sphere(Vec3( 0.3, 0, 0), 1.0)
    u = CSGUnion([a, b])
    ray = _ray(-3, 0, 0, 1, 0, 0)
    ivs = u.hit_intervals(ray)
    assert len(ivs) == 1              # merged into one


def test_union_bounding_box():
    a = Sphere(Vec3(-2, 0, 0), 1.0)
    b = Sphere(Vec3( 2, 0, 0), 1.0)
    u = CSGUnion([a, b])
    bb = u.bounding_box()
    assert bb.min.x <= -3.0
    assert bb.max.x >=  3.0


def test_union_inherits_child_material():
    """When CSGUnion has no material override, child material is used."""
    from color import Color
    a = Sphere(Vec3(0, 0, 0), 1.0, color=Color(1, 0, 0))
    u = CSGUnion([a])
    ray = _ray(-3, 0, 0, 1, 0, 0)
    hit = u.hit(ray)
    assert hit is not None
    assert hit.mat_obj is a           # child is the material source


def test_union_material_override():
    """CSGUnion color override takes precedence over child."""
    from color import Color
    a = Sphere(Vec3(0, 0, 0), 1.0, color=Color(1, 0, 0))
    u = CSGUnion([a], color=Color(0, 0, 1))
    ray = _ray(-3, 0, 0, 1, 0, 0)
    hit = u.hit(ray)
    assert hit is not None
    # mat_obj should be a _ResolvedMat with color=(0,0,1)
    assert hit.mat_obj.color == Color(0, 0, 1)
```

**Step 2: Run — expect FAIL**

**Step 3: Add helpers and `CSGUnion` to `src/shapes.py`**

Add at the bottom of `shapes.py` (after `Torus`):

```python
# ---------------------------------------------------------------------------
# CSG helpers
# ---------------------------------------------------------------------------

_CSG_FUSE_EPS = 0.002  # intervals within this distance are fused


def _merge_intervals(intervals: list, fuse: bool = False) -> list:
    """Merge a list of HitIntervals into non-overlapping sorted intervals.

    fuse=True also merges intervals that are within _CSG_FUSE_EPS of each other
    (suppresses internal seams for glass-on-glass unions).
    """
    if not intervals:
        return []
    eps = _CSG_FUSE_EPS if fuse else 0.0
    intervals = sorted(intervals, key=lambda iv: iv.t_enter)
    result = [intervals[0]]
    for iv in intervals[1:]:
        last = result[-1]
        if iv.t_enter <= last.t_exit + eps:
            # overlap or touch — extend
            if iv.t_exit > last.t_exit:
                result[-1] = HitInterval(
                    t_enter=last.t_enter,
                    t_exit=iv.t_exit,
                    enter_normal=last.enter_normal,
                    exit_normal=iv.exit_normal,
                    enter_obj=last.enter_obj,
                    exit_obj=iv.exit_obj,
                )
        else:
            result.append(iv)
    return result


class _ResolvedMat:
    """Transient per-hit object that merges a CSG node's overrides with a child's material."""
    __slots__ = ('color', 'opacity', 'reflect', 'ior')

    def __init__(self, csg, child):
        self.color   = csg.color   if csg.color   is not None else child.color
        self.opacity = csg.opacity if csg.opacity is not None else child.opacity
        self.reflect = csg.reflect if csg.reflect is not None else child.reflect
        self.ior     = csg.ior     if csg.ior     is not None else child.ior


# ---------------------------------------------------------------------------
# CSGUnion
# ---------------------------------------------------------------------------

class CSGUnion:
    """n-ary union of bounded shapes.

    fuse=True suppresses internal seams (use for transparent/glass children).
    Optional color/opacity/reflect/ior override child materials per-field.
    """

    def __init__(self, children: list, fuse: bool = False,
                 color=None, opacity=None, reflect=None, ior=None):
        if not children:
            raise ValueError("CSGUnion requires at least one child")
        self.children = children
        self.fuse     = fuse
        self.color    = color
        self.opacity  = opacity
        self.reflect  = reflect
        self.ior      = ior

    def _has_material(self) -> bool:
        return any(v is not None for v in (self.color, self.opacity,
                                           self.reflect, self.ior))

    def _resolve_mat(self, child_obj):
        if not self._has_material():
            return child_obj
        return _ResolvedMat(self, child_obj)

    def hit_intervals(self, ray, t_min: float = 1e-9,
                      t_max: float = float('inf')) -> list:
        all_ivs = []
        for child in self.children:
            all_ivs.extend(child.hit_intervals(ray, t_min, t_max))
        return _merge_intervals(all_ivs, fuse=self.fuse)

    def hit(self, ray, t_min: float = 0.001,
            t_max: float = float('inf')) -> Optional[HitRecord]:
        for iv in self.hit_intervals(ray, 1e-9, t_max):
            if iv.t_enter >= t_min:
                return HitRecord(t=iv.t_enter,
                                 point=ray.point_at(iv.t_enter),
                                 normal=iv.enter_normal,
                                 mat_obj=self._resolve_mat(iv.enter_obj))
            if iv.t_exit >= t_min:
                # ray started inside this interval
                return HitRecord(t=iv.t_exit,
                                 point=ray.point_at(iv.t_exit),
                                 normal=iv.exit_normal,
                                 mat_obj=self._resolve_mat(iv.exit_obj))
        return None

    def bounding_box(self):
        from bvh import AABB
        boxes = [c.bounding_box() for c in self.children]
        mn = Vec3(min(b.min.x for b in boxes),
                  min(b.min.y for b in boxes),
                  min(b.min.z for b in boxes))
        mx = Vec3(max(b.max.x for b in boxes),
                  max(b.max.y for b in boxes),
                  max(b.max.z for b in boxes))
        return AABB(mn, mx)
```

**Step 4: Run — expect PASS**

```bash
pytest tests/test_csg.py -k "union" -v
```

**Step 5: Full suite green, then commit**

```bash
pytest tests/ -x -q
git add src/shapes.py tests/test_csg.py
git commit -m "feat(csg): _merge_intervals helper and CSGUnion class"
```

---

## Task 8: `CSGIntersection`

**Files:**
- Modify: `src/shapes.py` — add `CSGIntersection` class after `CSGUnion`
- Test: `tests/test_csg.py`

**Step 1: Write the failing test**

Append to `tests/test_csg.py`:

```python
from shapes import CSGIntersection


def test_intersection_two_overlapping_spheres():
    """
    a: center=(-0.3, 0, 0), r=1  → enters at x=-1.3 (t=1.7), exits at x=0.7 (t=3.7)
    b: center=( 0.3, 0, 0), r=1  → enters at x=-0.7 (t=2.3), exits at x=1.3 (t=4.3)
    intersection: enters at t=2.3 (b's entry), exits at t=3.7 (a's exit)
    """
    a = Sphere(Vec3(-0.3, 0, 0), 1.0)
    b = Sphere(Vec3( 0.3, 0, 0), 1.0)
    inter = CSGIntersection([a, b])
    ray = _ray(-3, 0, 0, 1, 0, 0)
    hit = inter.hit(ray)
    assert hit is not None
    assert abs(hit.t - 2.3) < 1e-4   # enters at b's entry (last-entering child)


def test_intersection_no_overlap():
    """Two non-overlapping spheres → no intersection."""
    a = Sphere(Vec3(-2, 0, 0), 0.5)
    b = Sphere(Vec3( 2, 0, 0), 0.5)
    inter = CSGIntersection([a, b])
    ray = _ray(-5, 0, 0, 1, 0, 0)
    assert inter.hit(ray) is None


def test_intersection_bounding_box():
    a = Sphere(Vec3(0, 0, 0), 2.0)
    b = Sphere(Vec3(0, 0, 0), 1.0)
    inter = CSGIntersection([a, b])
    bb = inter.bounding_box()
    # Should be tighter than a's box
    assert bb.max.x <= 2.0 + 1e-6
```

**Step 2: Run — expect FAIL**

**Step 3: Add `CSGIntersection` to `src/shapes.py`**

Add after `CSGUnion`:

```python
# ---------------------------------------------------------------------------
# CSGIntersection
# ---------------------------------------------------------------------------

def _intersect_intervals(lists_of_intervals: list) -> list:
    """Compute the n-ary intersection of multiple interval lists.

    Returns regions covered by ALL lists simultaneously.
    Entry point: the latest entry among all lists (that child's normal).
    Exit  point: the earliest exit (that child's normal).
    """
    if not lists_of_intervals:
        return []

    # Start with the first list, intersect with each subsequent list
    result = lists_of_intervals[0]
    for other in lists_of_intervals[1:]:
        new_result = []
        for iv_a in result:
            for iv_b in other:
                t_enter = max(iv_a.t_enter, iv_b.t_enter)
                t_exit  = min(iv_a.t_exit,  iv_b.t_exit)
                if t_enter >= t_exit:
                    continue
                # Entry normal: from whichever child entered last
                if iv_a.t_enter >= iv_b.t_enter:
                    en, eo = iv_a.enter_normal, iv_a.enter_obj
                else:
                    en, eo = iv_b.enter_normal, iv_b.enter_obj
                # Exit normal: from whichever child exits first
                if iv_a.t_exit <= iv_b.t_exit:
                    xn, xo = iv_a.exit_normal, iv_a.exit_obj
                else:
                    xn, xo = iv_b.exit_normal, iv_b.exit_obj
                new_result.append(HitInterval(t_enter, t_exit, en, xn, eo, xo))
        result = new_result

    return sorted(result, key=lambda iv: iv.t_enter)


class CSGIntersection:
    """n-ary intersection of bounded shapes."""

    def __init__(self, children: list,
                 color=None, opacity=None, reflect=None, ior=None):
        if len(children) < 2:
            raise ValueError("CSGIntersection requires at least 2 children")
        self.children = children
        self.color    = color
        self.opacity  = opacity
        self.reflect  = reflect
        self.ior      = ior

    def _has_material(self) -> bool:
        return any(v is not None for v in (self.color, self.opacity,
                                           self.reflect, self.ior))

    def _resolve_mat(self, child_obj):
        if not self._has_material():
            return child_obj
        return _ResolvedMat(self, child_obj)

    def hit_intervals(self, ray, t_min: float = 1e-9,
                      t_max: float = float('inf')) -> list:
        lists = [c.hit_intervals(ray, t_min, t_max) for c in self.children]
        return _intersect_intervals(lists)

    def hit(self, ray, t_min: float = 0.001,
            t_max: float = float('inf')) -> Optional[HitRecord]:
        for iv in self.hit_intervals(ray, 1e-9, t_max):
            if iv.t_enter >= t_min:
                return HitRecord(t=iv.t_enter,
                                 point=ray.point_at(iv.t_enter),
                                 normal=iv.enter_normal,
                                 mat_obj=self._resolve_mat(iv.enter_obj))
            if iv.t_exit >= t_min:
                return HitRecord(t=iv.t_exit,
                                 point=ray.point_at(iv.t_exit),
                                 normal=iv.exit_normal,
                                 mat_obj=self._resolve_mat(iv.exit_obj))
        return None

    def bounding_box(self):
        from bvh import AABB
        boxes = [c.bounding_box() for c in self.children]
        mn = Vec3(max(b.min.x for b in boxes),
                  max(b.min.y for b in boxes),
                  max(b.min.z for b in boxes))
        mx = Vec3(min(b.max.x for b in boxes),
                  min(b.max.y for b in boxes),
                  min(b.max.z for b in boxes))
        # Guard against degenerate (non-overlapping) bounding boxes
        mn = Vec3(min(mn.x, mx.x), min(mn.y, mx.y), min(mn.z, mx.z))
        return AABB(mn, mx)
```

**Step 4: Run — expect PASS**

```bash
pytest tests/test_csg.py -k "intersection" -v
```

**Step 5: Full suite green, then commit**

```bash
pytest tests/ -x -q
git add src/shapes.py tests/test_csg.py
git commit -m "feat(csg): CSGIntersection class"
```

---

## Task 9: `CSGDifference`

**Files:**
- Modify: `src/shapes.py` — add `CSGDifference` class after `CSGIntersection`
- Test: `tests/test_csg.py`

**Step 1: Write the failing test**

Append to `tests/test_csg.py`:

```python
from shapes import CSGDifference


def test_difference_sphere_minus_inner_sphere():
    """
    A: big sphere, center=0, r=1.5  → t_enter=1.5, t_exit=4.5  (ray from x=-3)
    B: small sphere, center=0, r=0.8 → t_enter=2.2, t_exit=3.8
    A-B → intervals [1.5, 2.2] and [3.8, 4.5]
    """
    a = Sphere(Vec3(0, 0, 0), 1.5)
    b = Sphere(Vec3(0, 0, 0), 0.8)
    d = CSGDifference(a, b)
    ray = _ray(-3, 0, 0, 1, 0, 0)
    ivs = d.hit_intervals(ray)
    assert len(ivs) == 2
    assert abs(ivs[0].t_enter - 1.5) < 1e-4
    assert abs(ivs[0].t_exit  - 2.2) < 1e-4
    assert abs(ivs[1].t_enter - 3.8) < 1e-4
    assert abs(ivs[1].t_exit  - 4.5) < 1e-4


def test_difference_hit_returns_first_entry():
    a = Sphere(Vec3(0, 0, 0), 1.5)
    b = Sphere(Vec3(0, 0, 0), 0.8)
    d = CSGDifference(a, b)
    ray = _ray(-3, 0, 0, 1, 0, 0)
    hit = d.hit(ray)
    assert hit is not None
    assert abs(hit.t - 1.5) < 1e-4     # first interval, A's entry


def test_difference_b_normal_flipped():
    """At B's entry (becoming A-B exit), normal points inward (flipped from B's outward)."""
    a = Sphere(Vec3(0, 0, 0), 1.5)
    b = Sphere(Vec3(0, 0, 0), 0.8)
    d = CSGDifference(a, b)
    ray = _ray(-3, 0, 0, 1, 0, 0)
    ivs = d.hit_intervals(ray)
    # ivs[0].exit_normal is B's entry normal flipped → should point in +x (outward from result)
    assert ivs[0].exit_normal.x > 0.9


def test_difference_no_overlap():
    """B entirely misses A → result equals A."""
    a = Sphere(Vec3(0, 0, 0), 1.0)
    b = Sphere(Vec3(10, 0, 0), 0.5)   # far away
    d = CSGDifference(a, b)
    ray = _ray(-3, 0, 0, 1, 0, 0)
    ivs = d.hit_intervals(ray)
    assert len(ivs) == 1
    assert abs(ivs[0].t_enter - 2.0) < 1e-4
    assert abs(ivs[0].t_exit  - 4.0) < 1e-4


def test_difference_requires_exactly_two_children():
    import pytest
    a = Sphere(Vec3(0,0,0), 1.0)
    with pytest.raises(ValueError):
        CSGDifference(a, a, a)   # 3 args not allowed
```

**Step 2: Run — expect FAIL**

**Step 3: Add `CSGDifference` to `src/shapes.py`**

Add after `CSGIntersection`:

```python
# ---------------------------------------------------------------------------
# CSGDifference
# ---------------------------------------------------------------------------

def _subtract_intervals(a_ivs: list, b_ivs: list) -> list:
    """Subtract B intervals from A intervals: return regions in A but not in B.

    At B's entry (cutting into A): that point becomes A-B exit, B normal flipped.
    At B's exit  (still in A):    that point becomes A-B entry, B normal flipped.
    """
    result = []
    for a in a_ivs:
        # Start with A's interval, carve out each B segment
        remaining = [a]
        for b in b_ivs:
            new_remaining = []
            for seg in remaining:
                # B entirely before or after this A segment → unchanged
                if b.t_exit <= seg.t_enter or b.t_enter >= seg.t_exit:
                    new_remaining.append(seg)
                    continue
                # Left fragment: [seg.t_enter, b.t_enter] if positive width
                if b.t_enter > seg.t_enter:
                    new_remaining.append(HitInterval(
                        t_enter=seg.t_enter,
                        t_exit=b.t_enter,
                        enter_normal=seg.enter_normal,
                        exit_normal=Vec3(-b.enter_normal.x,
                                         -b.enter_normal.y,
                                         -b.enter_normal.z),  # B entry flipped
                        enter_obj=seg.enter_obj,
                        exit_obj=b.enter_obj,
                    ))
                # Right fragment: [b.t_exit, seg.t_exit] if positive width
                if b.t_exit < seg.t_exit:
                    new_remaining.append(HitInterval(
                        t_enter=b.t_exit,
                        t_exit=seg.t_exit,
                        enter_normal=Vec3(-b.exit_normal.x,
                                          -b.exit_normal.y,
                                          -b.exit_normal.z),  # B exit flipped
                        exit_normal=seg.exit_normal,
                        enter_obj=b.exit_obj,
                        exit_obj=seg.exit_obj,
                    ))
            remaining = new_remaining
        result.extend(remaining)

    return sorted(result, key=lambda iv: iv.t_enter)


class CSGDifference:
    """Binary difference: first child minus second child (A − B).

    Raises ValueError if anything other than exactly 2 positional args are given.
    """

    def __init__(self, left, right, _sentinel=None,
                 color=None, opacity=None, reflect=None, ior=None):
        if _sentinel is not None:
            raise ValueError("CSGDifference is binary: supply exactly 2 children")
        self.left    = left
        self.right   = right
        self.color   = color
        self.opacity = opacity
        self.reflect = reflect
        self.ior     = ior

    def _has_material(self) -> bool:
        return any(v is not None for v in (self.color, self.opacity,
                                           self.reflect, self.ior))

    def _resolve_mat(self, child_obj):
        if not self._has_material():
            return child_obj
        return _ResolvedMat(self, child_obj)

    def hit_intervals(self, ray, t_min: float = 1e-9,
                      t_max: float = float('inf')) -> list:
        a_ivs = self.left.hit_intervals(ray, t_min, t_max)
        b_ivs = self.right.hit_intervals(ray, t_min, t_max)
        return _subtract_intervals(a_ivs, b_ivs)

    def hit(self, ray, t_min: float = 0.001,
            t_max: float = float('inf')) -> Optional[HitRecord]:
        for iv in self.hit_intervals(ray, 1e-9, t_max):
            if iv.t_enter >= t_min:
                return HitRecord(t=iv.t_enter,
                                 point=ray.point_at(iv.t_enter),
                                 normal=iv.enter_normal,
                                 mat_obj=self._resolve_mat(iv.enter_obj))
            if iv.t_exit >= t_min:
                return HitRecord(t=iv.t_exit,
                                 point=ray.point_at(iv.t_exit),
                                 normal=iv.exit_normal,
                                 mat_obj=self._resolve_mat(iv.exit_obj))
        return None

    def bounding_box(self):
        # Conservative: same as A (we can't know what B carved out)
        return self.left.bounding_box()
```

**Note on `CSGDifference.__init__` signature:** The `_sentinel=None` trick catches the 3-arg case (`CSGDifference(a, b, c)`) by binding `c` to `_sentinel`. The test above calls `CSGDifference(a, a, a)` — Python maps the third `a` to `_sentinel`, which is not `None`, so the `ValueError` is raised.

**Step 4: Run — expect PASS**

```bash
pytest tests/test_csg.py -k "difference" -v
```

**Step 5: Full suite green, then commit**

```bash
pytest tests/ -x -q
git add src/shapes.py tests/test_csg.py
git commit -m "feat(csg): CSGDifference class with interval subtraction"
```

---

## Task 10: Renderer `mat_obj` wiring

**Files:**
- Modify: `src/renderer.py` — introduce `mat` local in `_trace`
- Test: `tests/test_csg.py` (integration smoke test)

**Step 1: Write the failing test**

Append to `tests/test_csg.py`:

```python
from renderer import _trace
from scene import Scene, Camera, Light
from ray import VisionRay
from color import Color


def _make_scene(*objects):
    scene = Scene()
    scene.camera = Camera(Vec3(0, 3, -9), Vec3(0, 1, 0))
    scene.lights = [Light(Vec3(4, 8, -4))]
    scene.objects = list(objects)
    return scene


def test_renderer_traces_csg_union():
    """A CSGUnion in the scene renders without error and produces a non-background color."""
    from color import Color as C
    BG = Color(0.05, 0.05, 0.08)
    a = Sphere(Vec3(0, 1, 0), 0.8, color=C(1, 0, 0))
    b = Sphere(Vec3(0.5, 1, 0), 0.8, color=C(0, 0, 1))
    u = CSGUnion([a, b])
    scene = _make_scene(u)
    ray = VisionRay(Vec3(0, 1, -5), Vec3(0, 0, 1))
    color = _trace(ray, scene, depth=3)
    assert color != BG   # hit something


def test_renderer_csg_difference_correct_color():
    """CSGDifference material falls back to A's child color."""
    from color import Color as C
    big   = Sphere(Vec3(0, 0, 0), 1.5, color=C(1, 0, 0))   # red
    small = Sphere(Vec3(0, 0, 0), 0.8, color=C(0, 0, 1))   # blue
    diff  = CSGDifference(big, small)
    scene = _make_scene(diff)
    # Ray hits the outer shell of 'big' — should be red-ish
    ray = VisionRay(Vec3(-3, 0, 0), Vec3(1, 0, 0))
    color = _trace(ray, scene, depth=1)
    assert color.r > color.b   # red component dominates
```

**Step 2: Run — expect FAIL** (renderer uses `obj.color` etc., ignores `mat_obj`)

**Step 3: Update `_trace` in `src/renderer.py`**

Find the line in `_trace` that reads:
```python
    hit, obj = _find_hit(ray, scene)
```

Immediately after it, add one line:
```python
    mat = hit.mat_obj if (hit is not None and hit.mat_obj is not None) else obj
```

Then replace every occurrence of `obj.color`, `obj.reflect`, `obj.opacity`, `obj.ior` in `_trace` with `mat.color`, `mat.reflect`, `mat.opacity`, `mat.ior`.

The specific lines to change (all within `_trace`):

```python
# BEFORE:
    surface_color = _shade(hit, obj.color, scene) if obj.ior == 1.0 else Color(0.0, 0.0, 0.0)
    if obj.reflect > 0.0 and obj.ior == 1.0 and depth > 0:
    ...
        surface_color = (surface_color * (1.0 - obj.reflect)
                         + reflected_color * obj.reflect).clamp()
    if obj.opacity >= 1.0 or depth <= 0:
    ...
    if obj.ior == 1.0:
        continuation = Ray(hit.point + ray.direction * 0.002, ray.direction)
        behind_color = _trace(continuation, scene, depth - 1)
        blended = surface_color * obj.opacity + behind_color * (1.0 - obj.opacity)
    ...
    if D.dot(N) < 0.0:
        n1, n2 = 1.0, obj.ior
    else:
        n1, n2 = obj.ior, 1.0

# AFTER (replace obj → mat for all material property accesses):
    mat = hit.mat_obj if hit.mat_obj is not None else obj
    surface_color = _shade(hit, mat.color, scene) if mat.ior == 1.0 else Color(0.0, 0.0, 0.0)
    if mat.reflect > 0.0 and mat.ior == 1.0 and depth > 0:
    ...
        surface_color = (surface_color * (1.0 - mat.reflect)
                         + reflected_color * mat.reflect).clamp()
    if mat.opacity >= 1.0 or depth <= 0:
    ...
    if mat.ior == 1.0:
        continuation = Ray(hit.point + ray.direction * 0.002, ray.direction)
        behind_color = _trace(continuation, scene, depth - 1)
        blended = surface_color * mat.opacity + behind_color * (1.0 - mat.opacity)
    ...
    if D.dot(N) < 0.0:
        n1, n2 = 1.0, mat.ior
    else:
        n1, n2 = mat.ior, 1.0
```

**Step 4: Run — expect PASS**

```bash
pytest tests/test_csg.py -v
```

**Step 5: Full suite green, then commit**

```bash
pytest tests/ -x -q
git add src/renderer.py tests/test_csg.py
git commit -m "feat(csg): wire mat_obj into renderer _trace for CSG material routing"
```

---

## Task 11: Lang parser — CSG dataclasses + `_block_stmt_csg()`

**Files:**
- Modify: `src/lang_parser.py`
- Test: `tests/test_csg.py` (parser-level tests)

**Step 1: Write the failing test**

Append to `tests/test_csg.py`:

```python
from lang_parser import parse_source, SceneCSGUnion, SceneCSGIntersection, SceneCSGDifference


def test_parse_union_block():
    src = """
    union {
      sphere { center (0,1,0)  radius 1.0  color (1,0,0) }
      box    { min (-1,0,-1)  max (1,2,1)  color (0,1,0) }
    }
    """
    items = parse_source(src)
    assert len(items) == 1
    u = items[0]
    assert isinstance(u, SceneCSGUnion)
    assert len(u.children) == 2
    assert u.fuse is False


def test_parse_union_fuse():
    src = """
    union {
      fuse yes
      sphere { center (0,0,0)  radius 1.0 }
      sphere { center (1,0,0)  radius 1.0 }
    }
    """
    items = parse_source(src)
    assert items[0].fuse is True


def test_parse_intersection_block():
    src = """
    intersection {
      sphere { center (0,0,0)  radius 1.5 }
      sphere { center (0,0,0)  radius 0.8 }
    }
    """
    items = parse_source(src)
    assert isinstance(items[0], SceneCSGIntersection)
    assert len(items[0].children) == 2


def test_parse_difference_block():
    src = """
    difference {
      sphere { center (0,0,0)  radius 1.5 }
      sphere { center (0,0,0)  radius 0.8 }
    }
    """
    items = parse_source(src)
    assert isinstance(items[0], SceneCSGDifference)
    assert items[0].left is not None
    assert items[0].right is not None


def test_parse_difference_wrong_arity():
    import pytest
    src = """
    difference {
      sphere { center (0,0,0)  radius 1.0 }
      sphere { center (1,0,0)  radius 1.0 }
      sphere { center (2,0,0)  radius 1.0 }
    }
    """
    with pytest.raises(Exception):
        parse_source(src)


def test_parse_csg_with_material_override():
    src = """
    union {
      color (1, 0, 0)
      sphere { center (0,0,0)  radius 1.0 }
    }
    """
    items = parse_source(src)
    assert items[0].color == (1.0, 0.0, 0.0)


def test_parse_nested_csg():
    src = """
    union {
      sphere { center (0,0,0)  radius 1.0 }
      difference {
        sphere { center (2,0,0)  radius 1.0 }
        sphere { center (2,0,0)  radius 0.5 }
      }
    }
    """
    items = parse_source(src)
    u = items[0]
    assert isinstance(u, SceneCSGUnion)
    assert isinstance(u.children[1], SceneCSGDifference)
```

**Step 2: Run — expect FAIL**

**Step 3: Add CSG dataclasses and parsing to `src/lang_parser.py`**

**3a. Add dataclasses** after `SceneTorus`:

```python
@dataclass
class SceneCSGUnion:
    children: list
    fuse:     bool  = False
    color:    tuple = None
    opacity:  float = None
    reflect:  float = None
    ior:      float = None


@dataclass
class SceneCSGIntersection:
    children: list
    color:    tuple = None
    opacity:  float = None
    reflect:  float = None
    ior:      float = None


@dataclass
class SceneCSGDifference:
    left:    object
    right:   object
    color:   tuple = None
    opacity: float = None
    reflect: float = None
    ior:     float = None
```

**3b. Add `"union"`, `"intersection"`, `"difference"` to `_BLOCK_KEYWORDS`:**

```python
_BLOCK_KEYWORDS = {
    "camera", "light",
    "sphere", "plane", "box", "cylinder", "cone", "torus",
    "union", "intersection", "difference",
}
```

**3c. Add `_block_stmt_csg()` method to `_ProgramParser`:**

```python
def _block_stmt_csg(self, kind: str):
    """Parse a CSG block (union / intersection / difference).

    Children may be any shape block OR another CSG block.
    Handles optional material fields and the fuse flag (union only).
    """
    self._expect(TT.LBRACE)

    fuse    = False
    color   = None
    opacity = None
    reflect = None
    ior     = None
    mat_ref = None
    children = []

    _CHILD_KEYWORDS = {
        "sphere", "plane", "box", "cylinder", "cone", "torus",
        "union", "intersection", "difference",
    }

    while not self._check(TT.RBRACE):
        key_tok = self._expect(TT.IDENT)
        key     = key_tok.value

        if key == "fuse":
            val = self._expect(TT.IDENT).value
            if val not in ("yes", "no"):
                raise ParseError(f"fuse value must be 'yes' or 'no', got {val!r}")
            fuse = (val == "yes")

        elif key == "material":
            name_tok = self._expect(TT.IDENT)
            mat_name = name_tok.value
            if mat_name not in self._env:
                raise ParseError(f"undefined material {mat_name!r}")
            mat_ref = self._env[mat_name]
            if not isinstance(mat_ref, dict):
                raise ParseError(f"{mat_name!r} is not a material")

        elif key in _MATERIAL_FIELDS:
            val = self._expr()
            if key == "color":   color   = val
            if key == "opacity": opacity = float(val)
            if key == "reflect": reflect = float(val)
            if key == "ior":     ior     = float(val)

        elif key in _CHILD_KEYWORDS:
            # Push the keyword back and parse a child block
            # (we already consumed the IDENT token, so we reconstruct it)
            child = self._parse_csg_child(key)
            children.append(child)

        else:
            raise ParseError(f"unexpected field {key!r} in {kind} block")

    self._expect(TT.RBRACE)

    # Apply mat_ref defaults, then inline overrides (colour wins over mat_ref)
    if mat_ref:
        if color   is None: color   = mat_ref.get("color")
        if opacity is None: opacity = mat_ref.get("opacity")
        if reflect is None: reflect = mat_ref.get("reflect")
        if ior     is None: ior     = mat_ref.get("ior")

    if kind == "union":
        return SceneCSGUnion(children=children, fuse=fuse,
                             color=color, opacity=opacity,
                             reflect=reflect, ior=ior)

    if kind == "intersection":
        if len(children) < 2:
            raise ParseError("intersection requires at least 2 children")
        return SceneCSGIntersection(children=children,
                                    color=color, opacity=opacity,
                                    reflect=reflect, ior=ior)

    if kind == "difference":
        if len(children) != 2:
            raise ParseError(
                f"difference requires exactly 2 children, got {len(children)}"
            )
        return SceneCSGDifference(left=children[0], right=children[1],
                                  color=color, opacity=opacity,
                                  reflect=reflect, ior=ior)


def _parse_csg_child(self, kind: str):
    """Parse a child of a CSG block: either a primitive block or a nested CSG block."""
    _CSG_KINDS = {"union", "intersection", "difference"}
    if kind in _CSG_KINDS:
        return self._block_stmt_csg(kind)
    # Primitive: reuse existing _block_stmt logic but we've already consumed the IDENT
    # Simulate re-entering _block_stmt by calling _build_scene_item directly
    self._expect(TT.LBRACE)
    props   = {}
    mat_ref = None
    while not self._check(TT.RBRACE):
        key_tok = self._expect(TT.IDENT)
        key     = key_tok.value
        if key == "material":
            name_tok = self._expect(TT.IDENT)
            mat_name = name_tok.value
            if mat_name not in self._env:
                raise ParseError(f"undefined material {mat_name!r}")
            mat_ref = self._env[mat_name]
        else:
            props[key] = self._expr()
    self._expect(TT.RBRACE)

    merged = dict(_MAT_DEFAULTS)
    if mat_ref:
        merged.update(mat_ref)
    merged.update({k: v for k, v in props.items() if k in _MATERIAL_FIELDS})

    try:
        return _build_scene_item(kind, props, merged)
    except KeyError as e:
        raise ParseError(f"missing required field {e} in {kind} block")
```

**3d. Update `_block_stmt` to route CSG keywords:**

In `_block_stmt`, after consuming `kind_tok`, add a check before the existing `props = {}` line:

```python
def _block_stmt(self, env: dict):
    kind_tok = self._advance()
    kind = kind_tok.value

    # Route CSG blocks to their dedicated parser
    if kind in ("union", "intersection", "difference"):
        return self._block_stmt_csg(kind)

    # ... existing code continues unchanged ...
    self._expect(TT.LBRACE)
    props = {}
    ...
```

**Step 4: Run — expect PASS**

```bash
pytest tests/test_csg.py -k "parse" -v
```

**Step 5: Full suite green, then commit**

```bash
pytest tests/ -x -q
git add src/lang_parser.py tests/test_csg.py
git commit -m "feat(csg): lang_parser CSG dataclasses and block parsing"
```

---

## Task 12: `new_parser.py` conversion + example scene

**Files:**
- Modify: `src/new_parser.py` — convert `SceneCSGUnion/Intersection/Difference` to shape objects
- Create: `examples/13-csg.pow`
- Modify: `docs/pow-reference.md` — add CSG section

**Step 1: Write the failing test**

Append to `tests/test_csg.py`:

```python
import tempfile, os


def test_new_parser_builds_csg_scene():
    from new_parser import parse_scene
    src = """
camera { location (0, 0, -5)  look_at (0, 0, 0)  fov 60 }
light  { position (4, 8, -4) }
difference {
  sphere { center (0, 0, 0)  radius 1.5  color (1, 0, 0) }
  sphere { center (0, 0, 0)  radius 0.8  color (0, 0, 1) }
}
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pow',
                                     delete=False) as f:
        f.write(src)
        tmp = f.name
    try:
        scene = parse_scene(tmp)
        assert len(scene.objects) == 1
        from shapes import CSGDifference
        assert isinstance(scene.objects[0], CSGDifference)
    finally:
        os.unlink(tmp)
```

**Step 2: Run — expect FAIL**

**Step 3: Update `src/new_parser.py`**

Add imports at the top:

```python
from lang_parser import (
    parse_source,
    SceneCamera, SceneLight,
    SceneSphere, ScenePlane, SceneBox,
    SceneCylinder, SceneCone, SceneTorus,
    SceneCSGUnion, SceneCSGIntersection, SceneCSGDifference,
)
from shapes import Sphere, Plane, Box, Cylinder, Cone, Torus
from shapes import CSGUnion, CSGIntersection, CSGDifference
```

Add a recursive helper function and the three `elif` branches in `parse_scene`:

```python
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
```

Then in `parse_scene`, replace the large `for item in items` loop with:

```python
    for item in items:
        if isinstance(item, SceneCamera):
            scene.camera = Camera(location=_v(item.location),
                                  look_at=_v(item.look_at), fov=item.fov)
        elif isinstance(item, SceneLight):
            scene.lights.append(Light(position=_v(item.position),
                                      radius=item.radius, samples=item.samples))
        elif isinstance(item, ScenePlane):
            scene.objects.append(Plane(normal=_v(item.normal), offset=item.offset,
                                       color=_c(item.color), opacity=item.opacity,
                                       reflect=item.reflect, ior=item.ior))
        else:
            # All bounded shapes (primitives and CSG) go through _build_shape
            try:
                scene.objects.append(_build_shape(item))
            except ValueError:
                raise RuntimeError(f"unrecognised scene item: {type(item)}")
```

**Step 4: Create `examples/13-csg.pow`**

```pow
// CSG demo — three operations in one scene
camera { location (0, 3, -9)  look_at (0, 1, 0)  fov 55 }
light  { position (4, 8, -4)  radius 1.0  samples 16 }

// Ground
plane { normal (0,1,0)  offset 0  color (0.6, 0.6, 0.6) }

// Left: sphere with cylindrical tunnel (difference)
difference {
  color (0.9, 0.3, 0.2)
  sphere   { center (-3, 1, 0)  radius 1.2 }
  cylinder { bottom (-3,-2,0)  top (-3,4,0)  radius 0.5 }
}

// Centre: intersection of two offset spheres (lens shape)
intersection {
  color (0.3, 0.7, 0.3)
  sphere { center (-0.4, 1, 0)  radius 1.2 }
  sphere { center ( 0.4, 1, 0)  radius 1.2 }
}

// Right: three glass spheres fused (no internal seams)
union {
  fuse yes
  opacity 0.0
  ior     1.5
  color   (0.8, 0.9, 1.0)
  sphere { center (2.5, 1.0,  0.0)  radius 0.7 }
  sphere { center (3.2, 1.0,  0.3)  radius 0.7 }
  sphere { center (2.9, 1.6, -0.1)  radius 0.7 }
}
```

**Step 5: Add CSG section to `docs/pow-reference.md`**

After the `torus` block section, add:

````markdown
### CSG blocks — Constructive Solid Geometry

CSG blocks combine bounded shapes using boolean set operations.
`Plane` is not allowed as a CSG child.

#### union

```
union {
  fuse yes              // optional — suppresses internal seams (default: no)
  material <name>       // optional material override
  color (r,g,b)         // or inline fields
  opacity N
  reflect N
  ior     N

  sphere { ... }        // n-ary: any number of child shapes or CSG nodes
  box    { ... }
  union  { ... }        // nesting is allowed
}
```

#### intersection

```
intersection {
  // same optional material fields as union
  sphere { ... }        // n-ary: at least 2 children required
  box    { ... }
}
```

#### difference

```
difference {
  // same optional material fields as union
  sphere { ... }        // child 1 = A   (exactly 2 children required)
  box    { ... }        // child 2 = B   (parse error if ≠ 2)
}
```

**Material:** If a CSG block specifies material fields, those override the child's
material per-field (unspecified fields fall back to the hit child's material).
If no material fields are specified, the material comes entirely from whichever
child shape was actually intersected.

**fuse:** Only valid on `union`. When `fuse yes`, intervals from touching or
slightly-overlapping children are merged, removing internal boundary surfaces.
Essential for transparent glass objects (prevents double-refraction seams).
````

**Step 6: Run — expect PASS**

```bash
pytest tests/test_csg.py -v
pytest tests/ -x -q
```

**Step 7: Smoke-render the example scene**

```bash
cd /Users/fuzzyalej/Code/raytrac1ng
python3 main.py examples/13-csg.pow -W 400 -H 300 -o examples/13-csg.png
```

Expected output: renders without error, produces `examples/13-csg.png`.

**Step 8: Commit**

```bash
git add src/new_parser.py examples/13-csg.pow docs/pow-reference.md tests/test_csg.py
git commit -m "feat(csg): new_parser conversion, example scene, POW reference docs"
```

---

## Done

All tests pass, the example scene renders. CSG is complete:

- `hit_intervals()` on all 5 bounded shapes
- `CSGUnion` (with `fuse`), `CSGIntersection`, `CSGDifference`
- `mat_obj` material routing in the renderer
- `union`, `intersection`, `difference` blocks in the POW language
- Nesting, loops, and function-emitting support automatically inherited
- BVH integration via `bounding_box()` on all CSG nodes
