"""CSG (Constructive Solid Geometry) operations — Union, Intersection, Difference."""

from __future__ import annotations
import math
from .primitives import HitRecord, HitInterval
from vector import Vec3
from color import Color
from material import Material


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
    """Transient per-hit object that merges a CSG node's overrides with a child's Material."""
    __slots__ = ('material',)

    def __init__(self, csg, child_obj):
        base = child_obj.material
        self.material = Material(
            color   = csg.color   if csg.color   is not None else base.color,
            opacity = csg.opacity if csg.opacity is not None else base.opacity,
            reflect = csg.reflect if csg.reflect is not None else base.reflect,
            ior     = csg.ior     if csg.ior     is not None else base.ior,
        )


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
            t_max: float = float('inf')):
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
        mn = Vec3(min(b.min_pt.x for b in boxes),
                  min(b.min_pt.y for b in boxes),
                  min(b.min_pt.z for b in boxes))
        mx = Vec3(max(b.max_pt.x for b in boxes),
                  max(b.max_pt.y for b in boxes),
                  max(b.max_pt.z for b in boxes))
        return AABB(mn, mx)


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
            t_max: float = float('inf')):
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
        mn = Vec3(max(b.min_pt.x for b in boxes),
                  max(b.min_pt.y for b in boxes),
                  max(b.min_pt.z for b in boxes))
        mx = Vec3(min(b.max_pt.x for b in boxes),
                  min(b.max_pt.y for b in boxes),
                  min(b.max_pt.z for b in boxes))
        # Guard against degenerate (non-overlapping) bounding boxes
        mn = Vec3(min(mn.x, mx.x), min(mn.y, mx.y), min(mn.z, mx.z))
        return AABB(mn, mx)


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
    """Binary difference: first child minus second child (A - B).

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
            t_max: float = float('inf')):
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
