"""Tests for CSG — data structures, interval operations, and shape classes."""
from shapes import HitInterval, HitRecord
from shapes import Sphere, Box, Cylinder, Cone, Torus
from ray import VisionRay
from vector import Vec3


def _ray(ox, oy, oz, dx, dy, dz):
    return VisionRay(Vec3(ox, oy, oz), Vec3(dx, dy, dz))


def test_hit_interval_fields():
    n = Vec3(1, 0, 0)
    iv = HitInterval(1.0, 3.0, n, Vec3(-1, 0, 0), None, None)
    assert iv.t_enter == 1.0
    assert iv.t_exit == 3.0
    assert iv.enter_normal == n


def test_hit_record_mat_obj_default():
    rec = HitRecord(t=1.0, point=Vec3(0,0,0), normal=Vec3(0,1,0))
    assert rec.mat_obj is None


# ---------------------------------------------------------------------------
# Task 2: Sphere.hit_intervals()
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Task 3: Box.hit_intervals()
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Task 4: Cylinder.hit_intervals()
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Task 5: Cone.hit_intervals()
# ---------------------------------------------------------------------------

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


def test_cylinder_hit_intervals_ray_inside():
    cyl = Cylinder(Vec3(0, 0, 0), Vec3(0, 2, 0), 1.0)
    ray = _ray(0, 1, 0, 1, 0, 0)    # starts at center, mid-height
    ivs = cyl.hit_intervals(ray, t_min=1e-9)
    assert len(ivs) == 1
    assert ivs[0].t_enter < 0
    assert abs(ivs[0].t_exit - 1.0) < 1e-4


def test_cone_hit_intervals_ray_inside():
    cone = Cone(Vec3(0, 0, 0), Vec3(0, 2, 0), 1.0, 1.0)
    ray  = _ray(0, 1, 0, 1, 0, 0)   # starts at center, mid-height
    ivs  = cone.hit_intervals(ray, t_min=1e-9)
    assert len(ivs) == 1
    assert ivs[0].t_enter < 0


# ---------------------------------------------------------------------------
# Task 6: Torus.hit_intervals()
# ---------------------------------------------------------------------------

def test_torus_hit_intervals_two_intervals():
    """Ray through the torus hole -> 2 intervals."""
    t = Torus(Vec3(0, 0, 0), Vec3(0, 1, 0), major_radius=2.0, minor_radius=0.5)
    ray = _ray(0, 0, -5, 0, 0, 1)   # along +z through center hole
    ivs = t.hit_intervals(ray)
    assert len(ivs) == 2             # enters tube, exits, enters again, exits


def test_torus_hit_intervals_one_interval():
    """Ray through exactly one tube of the torus -> 1 interval.

    Ray along +z at x=major_radius (2.0) threads through the single tube
    whose ring center is at (2, 0, 0). The tube surface at x=2 is at
    rho=sqrt(x^2+z^2)=2.5, giving z=+-1.5.  So t_enter=3.5, t_exit=6.5
    (ray origin at z=-5).
    """
    t = Torus(Vec3(0, 0, 0), Vec3(0, 1, 0), major_radius=2.0, minor_radius=0.5)
    # NOTE: A ray from (4,0,0) along (-1,0,0) passes through both the outer
    # and inner torus walls, producing 2 intervals — not 1. This ray at
    # x=major_radius threads through only the single x>0 tube, giving 1 interval.
    ray = _ray(2, 0, -5, 0, 0, 1)
    ivs = t.hit_intervals(ray)
    assert len(ivs) == 1
    assert abs(ivs[0].t_enter - 3.5) < 1e-4   # tube enters at z=-1.5, t=(-5+5)+(-1.5+5)=3.5
    assert abs(ivs[0].t_exit  - 6.5) < 1e-4   # tube exits  at z=+1.5, t=6.5


def test_torus_hit_intervals_miss():
    t = Torus(Vec3(0, 0, 0), Vec3(0, 1, 0), major_radius=2.0, minor_radius=0.5)
    ray = _ray(0, 5, 0, 0, 1, 0)    # above torus
    assert t.hit_intervals(ray) == []


# ---------------------------------------------------------------------------
# Task 7: CSGUnion
# ---------------------------------------------------------------------------

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
    assert bb.min_pt.x <= -3.0
    assert bb.max_pt.x >=  3.0


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


# ---------------------------------------------------------------------------
# Task 8: CSGIntersection
# ---------------------------------------------------------------------------

from shapes import CSGIntersection


def test_intersection_two_overlapping_spheres():
    """
    a: center=(-0.3, 0, 0), r=1  -> enters at x=-1.3 (t=1.7), exits at x=0.7 (t=3.7)
    b: center=( 0.3, 0, 0), r=1  -> enters at x=-0.7 (t=2.3), exits at x=1.3 (t=4.3)
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
    """Two non-overlapping spheres -> no intersection."""
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
    assert bb.max_pt.x <= 2.0 + 1e-6


# ---------------------------------------------------------------------------
# Task 9: CSGDifference
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Task 10: Renderer integration smoke tests
# ---------------------------------------------------------------------------

from renderer import _trace
from scene import Scene, Camera, Light
from color import Color


def _make_scene(*objects):
    scene = Scene()
    scene.camera = Camera(Vec3(0, 3, -9), Vec3(0, 1, 0))
    scene.lights = [Light(Vec3(4, 8, -4))]
    scene.objects = list(objects)
    return scene


def test_renderer_traces_csg_union():
    """A CSGUnion in the scene renders without error and produces a non-background color."""
    BG = Color(0.05, 0.05, 0.08)
    a = Sphere(Vec3(0, 1, 0), 0.8, color=Color(1, 0, 0))
    b = Sphere(Vec3(0.5, 1, 0), 0.8, color=Color(0, 0, 1))
    u = CSGUnion([a, b])
    scene = _make_scene(u)
    ray = VisionRay(Vec3(0, 1, -5), Vec3(0, 0, 1))
    color = _trace(ray, scene, depth=3)
    assert color != BG   # hit something
    assert color.r > color.b  # 'a' (red) is the entry point


def test_renderer_csg_difference_correct_color():
    """CSGDifference material falls back to A's child color."""
    big   = Sphere(Vec3(0, 0, 0), 1.5, color=Color(1, 0, 0))   # red
    small = Sphere(Vec3(0, 0, 0), 0.8, color=Color(0, 0, 1))   # blue
    diff  = CSGDifference(big, small)
    scene = _make_scene(diff)
    # Ray hits the outer shell of 'big' — should be red-ish
    ray = VisionRay(Vec3(-3, 0, 0), Vec3(1, 0, 0))
    color = _trace(ray, scene, depth=1)
    assert color.r > color.b   # red component dominates
