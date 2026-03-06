"""Tests for AABB, BVHNode, and BVH."""
import math
import random
import pytest
from bvh import AABB, BVHNode, BVH
from vector import Vec3
from ray import VisionRay


def make_ray(ox, oy, oz, dx, dy, dz):
    return VisionRay(Vec3(ox, oy, oz), Vec3(dx, dy, dz))


# ------------------------------------------------------------------ AABB.hit
class TestAABBHit:
    def test_ray_hits_box(self):
        box = AABB(Vec3(-1, -1, -1), Vec3(1, 1, 1))
        ray = make_ray(5, 0, 0, -1, 0, 0)  # straight at it
        assert box.hit(ray, 0.0, float('inf')) is True

    def test_ray_misses_box(self):
        box = AABB(Vec3(-1, -1, -1), Vec3(1, 1, 1))
        ray = make_ray(5, 5, 0, -1, 0, 0)  # passes above
        assert box.hit(ray, 0.0, float('inf')) is False

    def test_ray_parallel_outside_slab(self):
        box = AABB(Vec3(-1, -1, -1), Vec3(1, 1, 1))
        ray = make_ray(0, 5, 0, 1, 0, 0)  # parallel to X, above box in Y
        assert box.hit(ray, 0.0, float('inf')) is False

    def test_ray_starts_inside(self):
        box = AABB(Vec3(-1, -1, -1), Vec3(1, 1, 1))
        ray = make_ray(0, 0, 0, 1, 0, 0)  # origin inside the box
        assert box.hit(ray, 0.0, float('inf')) is True

    def test_t_max_prunes(self):
        """Ray hits the box but t_max is set before the hit — should miss."""
        box = AABB(Vec3(-1, -1, -1), Vec3(1, 1, 1))
        ray = make_ray(5, 0, 0, -1, 0, 0)  # enters at t=4
        assert box.hit(ray, 0.0, 3.0) is False

    def test_ray_negative_direction(self):
        """Ray traveling in negative direction can still hit."""
        box = AABB(Vec3(-1, -1, -1), Vec3(1, 1, 1))
        ray = make_ray(-5, 0, 0, 1, 0, 0)  # from the left, going right — hits at x=-1 (t=4)
        assert box.hit(ray, 0.0, float('inf')) is True

    def test_ray_parallel_inside_slab(self):
        """Ray parallel to an axis but within the slab should still hit (other axes decide)."""
        box = AABB(Vec3(-1, -1, -1), Vec3(1, 1, 1))
        # Parallel to X axis (dx=1, dy=0, dz=0) but at y=0 (inside Y slab) and z=0 (inside Z slab)
        ray = make_ray(-5, 0, 0, 1, 0, 0)  # parallel to X, inside Y and Z slabs
        assert box.hit(ray, 0.0, float('inf')) is True


# --------------------------------------------------------------- AABB.union
class TestAABBUnion:
    def test_union_produces_enclosing_box(self):
        a = AABB(Vec3(0, 0, 0), Vec3(1, 1, 1))
        b = AABB(Vec3(-1, -1, -1), Vec3(0.5, 0.5, 0.5))
        u = a.union(b)
        assert u.min_pt.x == -1 and u.min_pt.y == -1 and u.min_pt.z == -1
        assert u.max_pt.x == 1  and u.max_pt.y == 1  and u.max_pt.z == 1

    def test_union_disjoint_boxes(self):
        """Union of non-overlapping boxes encloses both."""
        a = AABB(Vec3(0, 0, 0), Vec3(1, 1, 1))
        b = AABB(Vec3(3, 3, 3), Vec3(4, 4, 4))
        u = a.union(b)
        assert u.min_pt.x == 0 and u.min_pt.y == 0 and u.min_pt.z == 0
        assert u.max_pt.x == 4 and u.max_pt.y == 4 and u.max_pt.z == 4


# ----------------------------------------------------------- AABB.surface_area
class TestAABBSurfaceArea:
    def test_unit_cube(self):
        box = AABB(Vec3(0, 0, 0), Vec3(1, 1, 1))
        assert abs(box.surface_area() - 6.0) < 1e-9

    def test_flat_box(self):
        # 2×3×0 slab: SA = 2*(2*3 + 3*0 + 0*2) = 12
        box = AABB(Vec3(0, 0, 0), Vec3(2, 3, 0))
        assert abs(box.surface_area() - 12.0) < 1e-9


# ------------------------------------------------------------- AABB.centroid
class TestAABBCentroid:
    def test_unit_cube_centroid(self):
        box = AABB(Vec3(0, 0, 0), Vec3(2, 4, 6))
        c = box.centroid()
        assert abs(c.x - 1) < 1e-9
        assert abs(c.y - 2) < 1e-9
        assert abs(c.z - 3) < 1e-9

    def test_centroid_offset_box(self):
        """Centroid of a box not anchored at origin."""
        box = AABB(Vec3(2, 4, 6), Vec3(4, 8, 12))
        c = box.centroid()
        assert abs(c.x - 3) < 1e-9
        assert abs(c.y - 6) < 1e-9
        assert abs(c.z - 9) < 1e-9


# ------------------------------------------------------- BVH build edge cases
class TestBVHBuild:
    def _make_sphere(self, cx, cy, cz, r=0.5):
        from shapes import Sphere
        from color import Color
        return Sphere(Vec3(cx, cy, cz), r, Color(1, 1, 1))

    def test_build_empty(self):
        bvh = BVH.build([])
        assert bvh.root is None

    def test_build_one_object(self):
        s = self._make_sphere(0, 0, 0)
        bvh = BVH.build([s])
        assert bvh.root is not None
        assert bvh.root.objects == [s]  # single-object leaf

    def test_build_two_objects(self):
        a = self._make_sphere(0, 0, 0)
        b = self._make_sphere(5, 0, 0)
        bvh = BVH.build([a, b])
        assert bvh.root is not None  # no crash

    def test_build_100_random_spheres(self):
        """Smoke test — no crash, root covers all objects."""
        rng = random.Random(42)
        from shapes import Sphere
        from color import Color
        spheres = [
            Sphere(Vec3(rng.uniform(-10, 10),
                        rng.uniform(-10, 10),
                        rng.uniform(-10, 10)), 0.5, Color(1, 1, 1))
            for _ in range(100)
        ]
        bvh = BVH.build(spheres)
        assert bvh.root is not None
        # Root AABB must contain every sphere centre
        for s in spheres:
            assert bvh.root.aabb.min_pt.x <= s.center.x <= bvh.root.aabb.max_pt.x
            assert bvh.root.aabb.min_pt.y <= s.center.y <= bvh.root.aabb.max_pt.y
            assert bvh.root.aabb.min_pt.z <= s.center.z <= bvh.root.aabb.max_pt.z


# --------------------------------------------------- BVH.hit correctness
class TestBVHHit:
    def _build_scene(self, n=50, seed=7):
        rng = random.Random(seed)
        from shapes import Sphere
        from color import Color
        return [
            Sphere(Vec3(rng.uniform(-8, 8),
                        rng.uniform(0, 5),
                        rng.uniform(-8, 8)), 0.4, Color(1, 1, 1))
            for _ in range(n)
        ]

    def _brute_hit(self, ray, objects):
        closest_hit = None
        closest_t = float('inf')
        closest_obj = None
        for obj in objects:
            h = obj.hit(ray, t_min=0.001, t_max=closest_t)
            if h and h.t < closest_t:
                closest_t = h.t
                closest_hit = h
                closest_obj = obj
        return closest_hit, closest_obj

    def test_bvh_matches_brute_force(self):
        """BVH and brute-force produce the same closest hit on 20 random rays."""
        objects = self._build_scene(50)
        bvh = BVH.build(objects)
        rng = random.Random(99)
        for _ in range(20):
            ray = make_ray(
                rng.uniform(-5, 5), rng.uniform(10, 15), rng.uniform(-5, 5),
                rng.uniform(-0.2, 0.2), -1, rng.uniform(-0.2, 0.2)
            )
            bvh_hit, bvh_obj = bvh.hit(ray, 0.001, float('inf'))
            bf_hit,  bf_obj  = self._brute_hit(ray, objects)

            if bf_hit is None:
                assert bvh_hit is None
            else:
                assert bvh_hit is not None
                assert abs(bvh_hit.t - bf_hit.t) < 1e-6

    def test_bvh_empty_returns_none(self):
        bvh = BVH.build([])
        ray = make_ray(0, 5, 0, 0, -1, 0)
        hit, obj = bvh.hit(ray, 0.001, float('inf'))
        assert hit is None and obj is None

    def test_bvh_hit_updates_t_max(self):
        """BVH returns the nearer hit, not the farther one."""
        from shapes import Sphere
        from color import Color
        near = Sphere(Vec3(0, 0, 2), 0.5, Color(1, 0, 0))
        far  = Sphere(Vec3(0, 0, 8), 0.5, Color(0, 1, 0))
        bvh  = BVH.build([near, far])
        ray  = make_ray(0, 0, 0, 0, 0, 1)
        hit, obj = bvh.hit(ray, 0.001, float('inf'))
        assert hit is not None
        assert hit.t < 3.0  # must be the near sphere, not the far one


# ----------------------------------------------- bounding_box() per shape
class TestBoundingBox:
    """For each shape, verify the AABB actually contains key surface points."""

    def _contains(self, aabb, pt, eps=1e-6) -> bool:
        return (aabb.min_pt.x - eps <= pt.x <= aabb.max_pt.x + eps and
                aabb.min_pt.y - eps <= pt.y <= aabb.max_pt.y + eps and
                aabb.min_pt.z - eps <= pt.z <= aabb.max_pt.z + eps)

    def test_sphere_bounding_box(self):
        from shapes import Sphere
        from color import Color
        s = Sphere(Vec3(1, 2, 3), 1.5, Color(1, 1, 1))
        bb = s.bounding_box()
        for pt in [Vec3(2.5, 2, 3), Vec3(-0.5, 2, 3),
                   Vec3(1, 3.5, 3), Vec3(1, 0.5, 3),
                   Vec3(1, 2, 4.5), Vec3(1, 2, 1.5)]:
            assert self._contains(bb, pt), f"Point {pt} not in sphere AABB {bb}"

    def test_box_bounding_box(self):
        from shapes import Box
        from color import Color
        b = Box(Vec3(-1, -2, -3), Vec3(4, 5, 6), Color(1, 1, 1))
        bb = b.bounding_box()
        assert bb.min_pt.x == -1 and bb.min_pt.y == -2 and bb.min_pt.z == -3
        assert bb.max_pt.x ==  4 and bb.max_pt.y ==  5 and bb.max_pt.z ==  6

    def test_cylinder_bounding_box(self):
        from shapes import Cylinder
        from color import Color
        c = Cylinder(Vec3(0, 0, 0), Vec3(0, 3, 0), 1.0, Color(1, 1, 1))
        bb = c.bounding_box()
        # Bottom cap circumference and top cap points must be inside
        for pt in [Vec3(1, 0, 0), Vec3(-1, 0, 0),
                   Vec3(0, 3, 0), Vec3(1, 3, 0)]:
            assert self._contains(bb, pt), f"Point {pt} not in cylinder AABB {bb}"

    def test_cone_bounding_box(self):
        from shapes import Cone
        from color import Color
        c = Cone(Vec3(0, 0, 0), Vec3(0, 4, 0), 2.0, 0.0, Color(1, 1, 1))
        bb = c.bounding_box()
        # Bottom rim and apex must be inside
        for pt in [Vec3(2, 0, 0), Vec3(-2, 0, 0),
                   Vec3(0, 0, 2), Vec3(0, 0, -2),
                   Vec3(0, 4, 0)]:  # apex
            assert self._contains(bb, pt), f"Point {pt} not in cone AABB {bb}"

    def test_torus_bounding_box(self):
        from shapes import Torus
        from color import Color
        t = Torus(Vec3(0, 0, 0), Vec3(0, 1, 0), 2.0, 0.5, Color(1, 1, 1))
        bb = t.bounding_box()
        # Outer ring points and tube-top must be inside
        for pt in [Vec3(2.5, 0, 0), Vec3(-2.5, 0, 0),
                   Vec3(0, 0, 2.5), Vec3(0, 0, -2.5),
                   Vec3(0, 0.5, 0)]:  # top of tube
            assert self._contains(bb, pt), f"Point {pt} not in torus AABB {bb}"

    def test_plane_has_no_bounding_box(self):
        """Plane must NOT have a bounding_box() method — it's unbounded."""
        from shapes import Plane
        from color import Color
        p = Plane(Vec3(0, 1, 0), 0, Color(1, 1, 1))
        assert not hasattr(p, 'bounding_box'), "Plane must not have bounding_box()"
