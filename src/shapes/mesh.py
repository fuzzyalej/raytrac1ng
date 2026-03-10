"""Mesh shapes — Triangle and TriangleMesh."""

from __future__ import annotations
import math
from .primitives import HitRecord
from vector import Vec3
from color import Color
from material import Material
from typing import Optional


# ---------------------------------------------------------------------------
# Triangle  (used by TriangleMesh)
# ---------------------------------------------------------------------------

class Triangle:
    """A single triangle for mesh rendering.

    v0, v1, v2: Vec3 vertices in world space.
    n0, n1, n2: optional Vec3 vertex normals for smooth shading.
    """

    def __init__(self, v0: Vec3, v1: Vec3, v2: Vec3,
                 n0: Vec3 = None, n1: Vec3 = None, n2: Vec3 = None,
                 material: Material = None):
        self.v0 = v0
        self.v1 = v1
        self.v2 = v2
        self.n0 = n0
        self.n1 = n1
        self.n2 = n2
        self.material = material if material is not None else Material()
        normals_provided = [n for n in (n0, n1, n2) if n is not None]
        if 0 < len(normals_provided) < 3:
            raise ValueError("Triangle: provide either all three vertex normals or none")

    def hit(self, ray, t_min: float = 0.001, t_max: float = float('inf')) -> Optional[HitRecord]:
        """Möller–Trumbore ray-triangle intersection."""
        edge1 = self.v1 - self.v0
        edge2 = self.v2 - self.v0
        h = ray.direction.cross(edge2)
        a = edge1.dot(h)
        if abs(a) < 1e-8:
            return None  # ray parallel to triangle
        f = 1.0 / a
        s = ray.origin - self.v0
        u = f * s.dot(h)
        if u < 0.0 or u > 1.0:
            return None
        q = s.cross(edge1)
        v = f * ray.direction.dot(q)
        if v < 0.0 or u + v > 1.0:
            return None
        t = f * edge2.dot(q)
        if t < t_min or t > t_max:
            return None
        point = ray.point_at(t)
        if self.n0 is not None:
            w = 1.0 - u - v
            normal = (self.n0 * w + self.n1 * u + self.n2 * v).normalize()
        else:
            normal = edge1.cross(edge2).normalize()
        if normal.dot(ray.direction) > 0:
            normal = -normal
        return HitRecord(t=t, point=point, normal=normal, mat_obj=self)

    def bounding_box(self):
        from bvh import AABB
        eps = 1e-4
        return AABB(
            Vec3(min(self.v0.x, self.v1.x, self.v2.x) - eps,
                 min(self.v0.y, self.v1.y, self.v2.y) - eps,
                 min(self.v0.z, self.v1.z, self.v2.z) - eps),
            Vec3(max(self.v0.x, self.v1.x, self.v2.x) + eps,
                 max(self.v0.y, self.v1.y, self.v2.y) + eps,
                 max(self.v0.z, self.v1.z, self.v2.z) + eps),
        )


# ---------------------------------------------------------------------------
# TriangleMesh  (per-mesh BVH wrapper)
# ---------------------------------------------------------------------------

class TriangleMesh:
    """A collection of Triangle objects with a dedicated internal BVH.

    Acts as a single bounded shape in the scene-level BVH. The internal BVH
    accelerates ray-triangle intersections within the mesh.
    """

    def __init__(self, triangles: 'list[Triangle]'):
        from bvh import BVH, AABB
        self._triangles = triangles
        self._bvh = BVH.build(triangles)
        if self._bvh.root is not None:
            self._aabb = self._bvh.root.aabb
        else:
            self._aabb = AABB(Vec3(0, 0, 0), Vec3(0, 0, 0))

    def hit(self, ray, t_min: float = 0.001, t_max: float = float('inf')) -> Optional[HitRecord]:
        hit_rec, _obj = self._bvh.hit(ray, t_min, t_max)
        return hit_rec  # mat_obj already set to Triangle by Triangle.hit()

    def bounding_box(self):
        return self._aabb
