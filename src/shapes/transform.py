"""Transform and TransformedShape — affine transform wrapper for shapes."""

from __future__ import annotations
from .primitives import HitRecord, HitInterval
from vector import Vec3, Matrix4x4
from typing import Optional


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

class Transform:
    """Stores TRS (scale, rotate_deg, translate) components for affine transforms.

    Lazily computes and caches the 4x4 matrix and its inverse so they are only
    built once per transform instance, regardless of how many rays it processes.
    Components are kept separate (not baked into a single matrix) to support
    future per-component animation interpolation.
    """

    __slots__ = ('scale', 'rotate', 'translate', '_mat', '_inv')

    def __init__(self,
                 scale     = (1.0, 1.0, 1.0),   # tuple or scalar float; see body for handling
                 rotate    = (0.0, 0.0, 0.0),
                 translate = (0.0, 0.0, 0.0)):
        # Accept scalar for uniform scale
        if isinstance(scale, (int, float)):
            scale = (float(scale), float(scale), float(scale))
        self.scale     = tuple(float(x) for x in scale)
        self.rotate    = tuple(float(x) for x in rotate)
        self.translate = tuple(float(x) for x in translate)
        if len(self.scale) != 3:
            raise ValueError(f"Transform: scale must have 3 components, got {len(self.scale)}")
        if len(self.rotate) != 3:
            raise ValueError(f"Transform: rotate must have 3 components, got {len(self.rotate)}")
        if len(self.translate) != 3:
            raise ValueError(f"Transform: translate must have 3 components, got {len(self.translate)}")
        self._mat = None   # type: Optional[Matrix4x4]
        self._inv = None   # type: Optional[Matrix4x4]

    def matrix(self) -> Matrix4x4:
        """Return the cached TRS matrix, building it on first call."""
        if self._mat is None:
            self._mat = Matrix4x4.from_trs(self.scale, self.rotate, self.translate)
        return self._mat

    def inverse_matrix(self) -> Matrix4x4:
        """Return the cached inverse TRS matrix, building it on first call."""
        if self._inv is None:
            # matrix() builds and caches _mat as a side-effect; that is intentional.
            self._inv = self.matrix().inverse()
        return self._inv

    def __repr__(self) -> str:
        return (f"Transform(scale={self.scale}, rotate={self.rotate}, "
                f"translate={self.translate})")


# ---------------------------------------------------------------------------
# TransformedShape
# ---------------------------------------------------------------------------

class TransformedShape:
    """Wraps any shape (primitive or CSG) with an affine Transform.

    Ray intersection strategy:
      1. Transform the incoming ray into object space using the inverse matrix.
      2. Intersect with the wrapped shape in object space.
      3. Transform the hit point and normal back to world space.

    The t parameter is correctly scaled so world-space t_min / t_max constraints work:
      - Object-space direction length = |inv * world_dir| = d_obj_len
      - t bounds are scaled by d_obj_len before passing to the child shape
      - Returned t is divided by d_obj_len to recover world-space t
    """

    def __init__(self, shape, transform: 'Transform'):
        self.shape     = shape
        self.transform = transform

    def __repr__(self) -> str:
        return f"TransformedShape(shape={self.shape!r}, transform={self.transform!r})"

    @property
    def material(self):
        """Delegate material access to the wrapped shape."""
        return self.shape.material

    def hit(self, ray, t_min: float, t_max: float):
        from ray import VisionRay as _VisionRay
        inv = self.transform.inverse_matrix()

        # Transform ray origin and direction into object space.
        o_obj     = inv.transform_point(ray.origin)
        d_obj_raw = inv.transform_direction(ray.direction)  # not unit-length after scale
        d_obj_len = d_obj_raw.length()

        if d_obj_len < 1e-12:
            return None

        # VisionRay.__init__ normalises direction to unit length.
        # t values from the child are in terms of that normalised direction.
        # Scaling bounds by d_obj_len and dividing returned t by d_obj_len recovers
        # correct world-space t. This relies on VisionRay normalising internally.
        obj_ray = _VisionRay(o_obj, d_obj_raw)
        rec = self.shape.hit(obj_ray, t_min * d_obj_len, t_max * d_obj_len)
        if rec is None:
            return None

        # Convert t back to world space (t_world = t_obj / d_obj_len).
        t_world = rec.t / d_obj_len

        # Transform hit point to world space.
        fwd_mat  = self.transform.matrix()
        world_pt = fwd_mat.transform_point(rec.point)

        # Normals transform by the transpose of the inverse matrix to remain
        # perpendicular to the surface under non-uniform scale.
        inv_T      = inv.transpose()
        world_n    = inv_T.transform_direction(rec.normal).normalize()

        # If the inner shape didn't set a mat_obj, use the inner shape itself so
        # the renderer can access material attributes (color, ior, opacity, reflect).
        mat_obj = rec.mat_obj if rec.mat_obj is not None else self.shape
        return HitRecord(t=t_world, point=world_pt, normal=world_n,
                         mat_obj=mat_obj)

    def bounding_box(self):
        """Return a world-space AABB enclosing the transformed child AABB."""
        from bvh import AABB as _AABB
        bbox = self.shape.bounding_box()
        if bbox is None:
            return None

        mn, mx = bbox.min_pt, bbox.max_pt
        corners = [
            Vec3(mn.x, mn.y, mn.z), Vec3(mx.x, mn.y, mn.z),
            Vec3(mn.x, mx.y, mn.z), Vec3(mx.x, mx.y, mn.z),
            Vec3(mn.x, mn.y, mx.z), Vec3(mx.x, mn.y, mx.z),
            Vec3(mn.x, mx.y, mx.z), Vec3(mx.x, mx.y, mx.z),
        ]

        mat = self.transform.matrix()
        pts = [mat.transform_point(c) for c in corners]

        return _AABB(
            Vec3(min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)),
            Vec3(max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)),
        )

    def hit_intervals(self, ray, t_min: float = 1e-9, t_max: float = float('inf')):
        """CSG interval interface -- delegates to wrapped shape in object space."""
        if not hasattr(self.shape, 'hit_intervals'):
            raise TypeError(
                f"TransformedShape: wrapped shape {type(self.shape).__name__!r} "
                f"does not implement hit_intervals; cannot be used inside CSG"
            )
        from ray import VisionRay as _VisionRay
        inv = self.transform.inverse_matrix()
        o_obj     = inv.transform_point(ray.origin)
        d_obj_raw = inv.transform_direction(ray.direction)
        d_obj_len = d_obj_raw.length()
        if d_obj_len < 1e-12:
            return []
        obj_ray  = _VisionRay(o_obj, d_obj_raw)
        intervals = self.shape.hit_intervals(obj_ray, t_min * d_obj_len, t_max * d_obj_len)
        inv_T = inv.transpose()
        result = []
        for iv in intervals:
            result.append(HitInterval(
                t_enter      = iv.t_enter / d_obj_len,
                t_exit       = iv.t_exit  / d_obj_len,
                enter_normal = inv_T.transform_direction(iv.enter_normal).normalize(),
                exit_normal  = inv_T.transform_direction(iv.exit_normal).normalize(),
                enter_obj    = iv.enter_obj,
                exit_obj     = iv.exit_obj,
            ))
        return result
