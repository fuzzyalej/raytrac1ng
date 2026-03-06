"""BVH (Bounding Volume Hierarchy) spatial acceleration for the raytracer."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from vector import Vec3


@dataclass(slots=True)
class AABB:
    """Axis-aligned bounding box — used as BVH node volumes."""
    min_pt: Vec3
    max_pt: Vec3

    def hit(self, ray, t_min: float, t_max: float) -> bool:
        """Slab method — returns bool (no normal needed)."""
        ro = (ray.origin.x, ray.origin.y, ray.origin.z)
        rd = (ray.direction.x, ray.direction.y, ray.direction.z)
        lo = (self.min_pt.x, self.min_pt.y, self.min_pt.z)
        hi = (self.max_pt.x, self.max_pt.y, self.max_pt.z)

        for axis in range(3):
            if abs(rd[axis]) < 1e-8:
                if ro[axis] < lo[axis] or ro[axis] > hi[axis]:
                    return False
                continue
            t0 = (lo[axis] - ro[axis]) / rd[axis]
            t1 = (hi[axis] - ro[axis]) / rd[axis]
            if t0 > t1:
                t0, t1 = t1, t0
            # Narrow the intersection interval to the overlap of all three slabs.
            t_min = max(t_min, t0)
            t_max = min(t_max, t1)
            if t_min > t_max:
                return False
        return True

    def union(self, other: AABB) -> AABB:
        """Return the smallest AABB enclosing both self and other."""
        return AABB(
            Vec3(min(self.min_pt.x, other.min_pt.x),
                 min(self.min_pt.y, other.min_pt.y),
                 min(self.min_pt.z, other.min_pt.z)),
            Vec3(max(self.max_pt.x, other.max_pt.x),
                 max(self.max_pt.y, other.max_pt.y),
                 max(self.max_pt.z, other.max_pt.z)),
        )

    def surface_area(self) -> float:
        """2*(dx*dy + dy*dz + dz*dx)."""
        dx = self.max_pt.x - self.min_pt.x
        dy = self.max_pt.y - self.min_pt.y
        dz = self.max_pt.z - self.min_pt.z
        return 2.0 * (dx * dy + dy * dz + dz * dx)

    def centroid(self) -> Vec3:
        """Geometric centre of the box."""
        return (self.min_pt + self.max_pt) * 0.5


class BVHNode:
    """A single node in the BVH tree.

    Internal nodes: left + right set, objects = [].
    Leaves:         left = right = None, objects holds 1-N shapes.
    """
    __slots__ = ('aabb', 'left', 'right', 'objects')

    def __init__(self, aabb: AABB,
                 left: Optional['BVHNode'],
                 right: Optional['BVHNode'],
                 objects: list):
        self.aabb    = aabb
        self.left    = left
        self.right   = right
        self.objects = objects


class BVH:
    """SAH Bounding Volume Hierarchy for fast ray-object intersection."""

    def __init__(self, root: Optional[BVHNode]):
        self.root = root

    # ------------------------------------------------------------------ build

    @classmethod
    def build(cls, objects: list) -> 'BVH':
        """Build a SAH BVH from a list of bounded shapes.

        Each shape must have a .bounding_box() -> AABB method.
        Returns BVH(root=None) for an empty list.
        """
        if not objects:
            return cls(None)
        return cls(cls._build_node(objects))

    @classmethod
    def _build_node(cls, objects: list) -> BVHNode:
        # Leaf: single object
        if len(objects) == 1:
            aabb = objects[0].bounding_box()
            return BVHNode(aabb, None, None, list(objects))

        # Precompute bounding boxes once — each shape may compute them lazily
        boxes = [obj.bounding_box() for obj in objects]

        # Compute AABB of all objects
        parent_aabb = boxes[0]
        for box in boxes[1:]:
            parent_aabb = parent_aabb.union(box)

        # Try SAH split with 8 bins across each of the 3 axes
        NUM_BINS = 8
        best_cost = float('inf')
        best_axis = 0
        best_split_idx = 1  # split bucket index

        # SAH leaf cost: SA(parent) × N — same units as the unnormalised split costs
        # (the 1/SA_parent normalisation cancels when comparing splits to each other,
        #  so we keep it only for the leaf comparison; result is slightly more eager to
        #  split than textbook SAH, which is fine for our target scene sizes).
        parent_sa = parent_aabb.surface_area()
        leaf_cost  = parent_sa * len(objects)

        for axis in range(3):
            # Centroid extents along this axis
            axis_key = ('x', 'y', 'z')[axis]
            centroids = [box.centroid() for box in boxes]
            axis_vals = [getattr(c, axis_key) for c in centroids]
            c_min = min(axis_vals)
            c_max = max(axis_vals)

            if c_max - c_min < 1e-10:
                continue  # all centroids coincide on this axis — skip

            # Assign objects to bins
            bins_aabb  = [None] * NUM_BINS
            bins_count = [0]   * NUM_BINS
            for (obj, box), val in zip(zip(objects, boxes), axis_vals):
                b = int((val - c_min) / (c_max - c_min) * NUM_BINS)
                b = min(b, NUM_BINS - 1)
                bins_count[b] += 1
                bins_aabb[b] = box if bins_aabb[b] is None else bins_aabb[b].union(box)

            # Sweep left-right for 7 candidate splits
            for split in range(1, NUM_BINS):
                left_aabb  = None
                left_count = 0
                for b in range(split):
                    if bins_aabb[b] is not None:
                        left_count += bins_count[b]
                        left_aabb = bins_aabb[b] if left_aabb is None else left_aabb.union(bins_aabb[b])

                right_aabb  = None
                right_count = 0
                for b in range(split, NUM_BINS):
                    if bins_aabb[b] is not None:
                        right_count += bins_count[b]
                        right_aabb = bins_aabb[b] if right_aabb is None else right_aabb.union(bins_aabb[b])

                if left_count == 0 or right_count == 0:
                    continue
                if left_aabb is None or right_aabb is None:
                    continue

                cost = (left_aabb.surface_area()  * left_count +
                        right_aabb.surface_area() * right_count)
                if cost < best_cost:
                    best_cost = cost
                    best_axis = axis
                    best_split_idx = split

        # Stopping criterion: make a leaf if SAH cost doesn't improve over leaf
        if best_cost >= leaf_cost:
            return BVHNode(parent_aabb, None, None, list(objects))

        # Partition objects by the winning axis/split
        axis_key = ('x', 'y', 'z')[best_axis]
        axis_vals = [getattr(box.centroid(), axis_key) for box in boxes]
        c_min = min(axis_vals)
        c_max = max(axis_vals)
        left_objs  = []
        right_objs = []
        for obj, val in zip(objects, axis_vals):
            b = int((val - c_min) / (c_max - c_min) * NUM_BINS)
            b = min(b, NUM_BINS - 1)
            if b < best_split_idx:
                left_objs.append(obj)
            else:
                right_objs.append(obj)

        # Guard: if partition is degenerate, make a leaf
        if not left_objs or not right_objs:
            return BVHNode(parent_aabb, None, None, list(objects))

        left_node  = cls._build_node(left_objs)
        right_node = cls._build_node(right_objs)
        return BVHNode(parent_aabb, left_node, right_node, [])

    # ------------------------------------------------------------------ hit

    def hit(self, ray, t_min: float, t_max: float):
        """Return (HitRecord, object) or (None, None).

        Updates t_max as closer hits are found, enabling early subtree pruning.
        """
        if self.root is None:
            return None, None
        return self._hit_node(self.root, ray, t_min, t_max)

    @classmethod
    def _hit_node(cls, node: BVHNode, ray, t_min: float, t_max: float):
        if not node.aabb.hit(ray, t_min, t_max):
            return None, None

        # Leaf: linear scan over objects in this leaf
        if node.left is None:
            closest_hit = None
            closest_obj = None
            for obj in node.objects:
                h = obj.hit(ray, t_min=t_min, t_max=t_max)
                if h:
                    t_max = h.t
                    closest_hit = h
                    closest_obj = obj
            return closest_hit, closest_obj

        # Internal node: visit nearer child first (by centroid projection onto ray)
        left_c  = node.left.aabb.centroid()
        right_c = node.right.aabb.centroid()
        ray_origin = ray.origin
        ray_dir    = ray.direction

        # Nearer-child-first heuristic: project centroid offset onto ray direction.
        # Negative projection means the centroid is behind the origin — both AABB
        # tests will still handle this correctly; the ordering is best-effort only.
        def proj(c):
            return ((c.x - ray_origin.x) * ray_dir.x +
                    (c.y - ray_origin.y) * ray_dir.y +
                    (c.z - ray_origin.z) * ray_dir.z)

        if proj(left_c) <= proj(right_c):
            first, second = node.left, node.right
        else:
            first, second = node.right, node.left

        hit1, obj1 = cls._hit_node(first, ray, t_min, t_max)
        if hit1:
            t_max = hit1.t
        hit2, obj2 = cls._hit_node(second, ray, t_min, t_max)
        if hit2:
            return hit2, obj2
        return hit1, obj1
