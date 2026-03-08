"""Geometric primitives — HitRecord and all shape classes."""

import math
from dataclasses import dataclass
from typing import Optional

from vector import Vec3
from color import Color


# ---------------------------------------------------------------------------
# Hit record and interval
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

class Sphere:
    """Sphere defined by center and radius."""

    def __init__(self, center: Vec3, radius: float, color: Color = None,
                 opacity: float = 1.0, reflect: float = 0.0, ior: float = 1.0):
        self.center = center
        self.radius = radius
        self.color = color if color is not None else Color(1.0, 1.0, 1.0)
        self.opacity = max(0.0, min(1.0, float(opacity)))
        self.reflect = max(0.0, min(1.0, float(reflect)))
        self.ior = max(1.0, float(ior))

    def hit(self, ray, t_min: float = 0.001, t_max: float = float('inf')) -> Optional[HitRecord]:
        oc = ray.origin - self.center
        a = ray.direction.dot(ray.direction)
        b = 2.0 * oc.dot(ray.direction)
        c = oc.dot(oc) - self.radius * self.radius
        discriminant = b * b - 4 * a * c

        if discriminant < 0:
            return None

        sqrt_disc = math.sqrt(discriminant)
        t = (-b - sqrt_disc) / (2.0 * a)
        if t < t_min or t > t_max:
            t = (-b + sqrt_disc) / (2.0 * a)
            if t < t_min or t > t_max:
                return None

        point = ray.point_at(t)
        normal = (point - self.center) / self.radius
        return HitRecord(t=t, point=point, normal=normal)

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

    def bounding_box(self):
        from bvh import AABB  # lazy import avoids shapes ↔ bvh circular dependency
        r = Vec3(self.radius, self.radius, self.radius)
        return AABB(self.center - r, self.center + r)


class Plane:
    """Infinite plane defined by normal and offset from origin.

    The plane equation is: dot(point, normal) = offset
    """

    def __init__(self, normal: Vec3, offset: float, color: Color = None,
                 opacity: float = 1.0, reflect: float = 0.0, ior: float = 1.0):
        self.normal = normal.normalize()
        self.offset = offset
        self.color = color if color is not None else Color(1.0, 1.0, 1.0)
        self.opacity = max(0.0, min(1.0, float(opacity)))
        self.reflect = max(0.0, min(1.0, float(reflect)))
        self.ior = max(1.0, float(ior))

    def hit(self, ray, t_min: float = 0.001, t_max: float = float('inf')) -> Optional[HitRecord]:
        denom = ray.direction.dot(self.normal)
        if abs(denom) < 1e-8:
            return None  # Ray is parallel to the plane

        t = (self.offset - ray.origin.dot(self.normal)) / denom
        if t < t_min or t > t_max:
            return None

        point = ray.point_at(t)
        return HitRecord(t=t, point=point, normal=self.normal)


class Box:
    """Axis-aligned bounding box (AABB).

    Uses the slab method: intersect 3 pairs of axis-aligned planes.
    """

    def __init__(self, min_pt: Vec3, max_pt: Vec3, color: Color = None,
                 opacity: float = 1.0, reflect: float = 0.0, ior: float = 1.0):
        self.min_pt = min_pt
        self.max_pt = max_pt
        if (self.min_pt.x > self.max_pt.x or
                self.min_pt.y > self.max_pt.y or
                self.min_pt.z > self.max_pt.z):
            raise ValueError("Box: min_pt must be <= max_pt on all axes")
        self.color = color if color is not None else Color(1.0, 1.0, 1.0)
        self.opacity = max(0.0, min(1.0, float(opacity)))
        self.reflect = max(0.0, min(1.0, float(reflect)))
        self.ior = max(1.0, float(ior))

    def hit(self, ray, t_min: float = 0.001,
            t_max: float = float('inf')) -> Optional[HitRecord]:
        t_enter = -float('inf')
        t_exit  =  float('inf')
        enter_axis = 0
        enter_sign = -1.0
        exit_axis  = 0
        exit_sign  =  1.0

        ro = (ray.origin.x,    ray.origin.y,    ray.origin.z)
        rd = (ray.direction.x, ray.direction.y, ray.direction.z)
        lo = (self.min_pt.x,   self.min_pt.y,   self.min_pt.z)
        hi = (self.max_pt.x,   self.max_pt.y,   self.max_pt.z)

        for axis in range(3):
            if abs(rd[axis]) < 1e-8:
                # Ray parallel to this slab — must lie between the planes
                if ro[axis] < lo[axis] or ro[axis] > hi[axis]:
                    return None
                continue

            t0 = (lo[axis] - ro[axis]) / rd[axis]
            t1 = (hi[axis] - ro[axis]) / rd[axis]

            # t0 is the entry slab hit, t1 is the exit slab hit (sort them)
            if t0 <= t1:
                s0, s1 = -1.0, 1.0   # min face → outward normal -axis; max face +axis
            else:
                t0, t1 = t1, t0
                s0, s1 = 1.0, -1.0   # swapped

            if t0 > t_enter:
                t_enter     = t0
                enter_axis  = axis
                enter_sign  = s0
            if t1 < t_exit:
                t_exit      = t1
                exit_axis   = axis
                exit_sign   = s1

            if t_enter > t_exit:
                return None

        if t_exit < t_min:
            return None   # entire box is behind the ray

        if t_enter >= t_min:
            t = t_enter
            n = [0.0, 0.0, 0.0]
            n[enter_axis] = enter_sign
        else:
            # Ray starts inside — return exit face
            t = t_exit
            n = [0.0, 0.0, 0.0]
            n[exit_axis] = exit_sign

        if t > t_max:
            return None

        normal = Vec3(*n)
        point  = ray.point_at(t)
        return HitRecord(t=t, point=point, normal=normal)

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

    def bounding_box(self):
        from bvh import AABB  # lazy import avoids shapes ↔ bvh circular dependency
        return AABB(self.min_pt, self.max_pt)


class Cylinder:
    """Capped cylinder defined by two endpoint centres and a radius.

    The axis direction is (top − bottom).normalise().
    Both end caps are closed disks.
    """

    def __init__(self, bottom: Vec3, top: Vec3, radius: float,
                 color: Color = None, opacity: float = 1.0,
                 reflect: float = 0.0, ior: float = 1.0):
        self.bottom = bottom
        self.top    = top
        self.radius = max(0.0, float(radius))
        if self.radius <= 0.0:
            raise ValueError("Cylinder: radius must be positive")
        axis_vec    = top - bottom
        self.height = axis_vec.length()
        if self.height < 1e-10:
            raise ValueError("Cylinder: top and bottom must be distinct points")
        self.axis   = axis_vec / self.height        # unit axis direction D
        self.color   = color if color is not None else Color(1.0, 1.0, 1.0)
        self.opacity = max(0.0, min(1.0, float(opacity)))
        self.reflect = max(0.0, min(1.0, float(reflect)))
        self.ior     = max(1.0, float(ior))

    def hit(self, ray, t_min: float = 0.001,
            t_max: float = float('inf')) -> Optional[HitRecord]:
        D  = self.axis
        P  = self.bottom
        r2 = self.radius * self.radius
        oc = ray.origin - P

        d_proj  = D.dot(ray.direction)
        oc_proj = D.dot(oc)
        d_perp  = ray.direction - D * d_proj
        oc_perp = oc - D * oc_proj

        best_t      = float('inf')
        best_normal = None

        # ---- Curved surface (infinite cylinder quadratic) ----
        a = d_perp.dot(d_perp)
        if abs(a) > 1e-8:
            b    = 2.0 * oc_perp.dot(d_perp)
            c    = oc_perp.dot(oc_perp) - r2
            disc = b * b - 4.0 * a * c
            if disc >= 0:
                sqrt_disc = math.sqrt(disc)
                for t_cand in [(-b - sqrt_disc) / (2.0 * a),
                               (-b + sqrt_disc) / (2.0 * a)]:
                    if t_min <= t_cand <= t_max and t_cand < best_t:
                        point = ray.point_at(t_cand)
                        h     = D.dot(point - P)
                        if 0.0 <= h <= self.height:
                            n = (point - P - D * h).normalize()
                            best_t      = t_cand
                            best_normal = n
                            break   # smallest valid hit first

        # ---- Caps ----
        # bottom cap: outward normal = -D; top cap: outward normal = +D
        for cap_centre, cap_normal in [
            (self.bottom, D * (-1.0)),
            (self.top,    D),
        ]:
            denom = ray.direction.dot(cap_normal)
            if abs(denom) < 1e-8:
                continue
            t_cand = (cap_centre - ray.origin).dot(cap_normal) / denom
            if t_min <= t_cand <= t_max and t_cand < best_t:
                point       = ray.point_at(t_cand)
                radial      = point - cap_centre
                radial_perp = radial - D * D.dot(radial)
                if radial_perp.dot(radial_perp) <= r2:
                    best_t      = t_cand
                    best_normal = cap_normal

        if best_normal is None:
            return None
        return HitRecord(t=best_t, point=ray.point_at(best_t), normal=best_normal)

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

    def bounding_box(self):
        from bvh import AABB  # lazy import avoids shapes ↔ bvh circular dependency
        # Tight bounds: for a disk at centre c with axis D,
        # the half-extent along world axis i is radius * sqrt(1 - D.i²).
        # We union the two cap disks (bottom + top) to get the full cylinder AABB.
        D = self.axis
        ex = self.radius * math.sqrt(max(0.0, 1.0 - D.x * D.x))
        ey = self.radius * math.sqrt(max(0.0, 1.0 - D.y * D.y))
        ez = self.radius * math.sqrt(max(0.0, 1.0 - D.z * D.z))
        return AABB(
            Vec3(min(self.bottom.x, self.top.x) - ex,
                 min(self.bottom.y, self.top.y) - ey,
                 min(self.bottom.z, self.top.z) - ez),
            Vec3(max(self.bottom.x, self.top.x) + ex,
                 max(self.bottom.y, self.top.y) + ey,
                 max(self.bottom.z, self.top.z) + ez),
        )


class Cone:
    """Generalised cone (frustum) from bottom to top with two radii.

    R(h) = bottom_radius + slope * h  where  slope = (top_radius − bottom_radius) / height.
    Setting top_radius=0 gives a true pointed cone.  Equal radii give a cylinder.
    Caps are only added when their radius > 0.
    """

    def __init__(self, bottom: Vec3, top: Vec3,
                 bottom_radius: float, top_radius: float,
                 color: Color = None, opacity: float = 1.0,
                 reflect: float = 0.0, ior: float = 1.0):
        self.bottom        = bottom
        self.top           = top
        self.bottom_radius = max(0.0, float(bottom_radius))
        self.top_radius    = max(0.0, float(top_radius))
        axis_vec     = top - bottom
        self.height  = axis_vec.length()
        if self.height < 1e-10:
            raise ValueError("Cone: top and bottom must be distinct points")
        self.axis    = axis_vec / self.height
        self.slope   = (self.top_radius - self.bottom_radius) / self.height
        self.color   = color if color is not None else Color(1.0, 1.0, 1.0)
        self.opacity = max(0.0, min(1.0, float(opacity)))
        self.reflect = max(0.0, min(1.0, float(reflect)))
        self.ior     = max(1.0, float(ior))

    def hit(self, ray, t_min: float = 0.001,
            t_max: float = float('inf')) -> Optional[HitRecord]:
        D     = self.axis
        P     = self.bottom
        slope = self.slope
        R0    = self.bottom_radius
        oc    = ray.origin - P

        d_proj  = D.dot(ray.direction)
        oc_proj = D.dot(oc)
        d_perp  = ray.direction - D * d_proj
        oc_perp = oc - D * oc_proj

        # Quadratic: |d_perp + t*d_perp|² = (R0 + slope*(oc_proj + t*d_proj))²
        a = d_perp.dot(d_perp) - (slope * d_proj) ** 2
        b = 2.0 * (oc_perp.dot(d_perp)
                   - (R0 + slope * oc_proj) * slope * d_proj)
        c = oc_perp.dot(oc_perp) - (R0 + slope * oc_proj) ** 2

        best_t      = float('inf')
        best_normal = None

        # ---- Curved surface ----
        if abs(a) > 1e-8:
            disc = b * b - 4.0 * a * c
            if disc >= 0:
                sqrt_disc = math.sqrt(disc)
                for t_cand in sorted([(-b - sqrt_disc) / (2.0 * a),
                                      (-b + sqrt_disc) / (2.0 * a)]):
                    if t_min <= t_cand <= t_max and t_cand < best_t:
                        point = ray.point_at(t_cand)
                        h_y   = D.dot(point - P)
                        if 0.0 <= h_y <= self.height:
                            radial     = (point - P) - D * h_y
                            radial_len = radial.length()
                            if radial_len > 1e-10:
                                n = (radial / radial_len - D * slope).normalize()
                            else:
                                n = -D   # degenerate: at the apex
                            best_t      = t_cand
                            best_normal = n
                            break

        elif abs(b) > 1e-8:
            # Linear case (a ≈ 0): ray direction nearly parallel to surface
            t_cand = -c / b
            if t_min <= t_cand <= t_max:
                point = ray.point_at(t_cand)
                h_y   = D.dot(point - P)
                if 0.0 <= h_y <= self.height:
                    radial     = (point - P) - D * h_y
                    radial_len = radial.length()
                    if radial_len > 1e-10:
                        n = (radial / radial_len - D * slope).normalize()
                        best_t      = t_cand
                        best_normal = n

        # ---- Caps ----
        for cap_centre, cap_radius, cap_normal in [
            (self.bottom, self.bottom_radius, D * (-1.0)),
            (self.top,    self.top_radius,    D),
        ]:
            if cap_radius <= 0.0:
                continue
            denom = ray.direction.dot(cap_normal)
            if abs(denom) < 1e-8:
                continue
            t_cand = (cap_centre - ray.origin).dot(cap_normal) / denom
            if t_min <= t_cand <= t_max and t_cand < best_t:
                point       = ray.point_at(t_cand)
                radial      = point - cap_centre
                radial_perp = radial - D * D.dot(radial)
                if radial_perp.dot(radial_perp) <= cap_radius ** 2:
                    best_t      = t_cand
                    best_normal = cap_normal

        if best_normal is None:
            return None
        return HitRecord(t=best_t, point=ray.point_at(best_t), normal=best_normal)

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

    def bounding_box(self):
        from bvh import AABB  # lazy import avoids shapes ↔ bvh circular dependency
        # Conservative: use max of the two end radii.
        # Tight per-axis: half-extent along world axis i is max_r * sqrt(1 - D.i²).
        D = self.axis
        max_r = max(self.bottom_radius, self.top_radius)
        ex = max_r * math.sqrt(max(0.0, 1.0 - D.x * D.x))
        ey = max_r * math.sqrt(max(0.0, 1.0 - D.y * D.y))
        ez = max_r * math.sqrt(max(0.0, 1.0 - D.z * D.z))
        return AABB(
            Vec3(min(self.bottom.x, self.top.x) - ex,
                 min(self.bottom.y, self.top.y) - ey,
                 min(self.bottom.z, self.top.z) - ez),
            Vec3(max(self.bottom.x, self.top.x) + ex,
                 max(self.bottom.y, self.top.y) + ey,
                 max(self.bottom.z, self.top.z) + ez),
        )


# ---------------------------------------------------------------------------
# Quartic solver (Ferrari's analytical method) — used by Torus
# ---------------------------------------------------------------------------

def _solve_cubic_real(a: float, b: float, c: float, d: float):
    """Real roots of a·x³ + b·x² + c·x + d = 0 (returned sorted)."""
    if abs(a) < 1e-12:
        if abs(b) < 1e-12:
            return [] if abs(c) < 1e-12 else [-d / c]
        disc = c * c - 4.0 * b * d
        if disc < 0:
            return []
        sq = math.sqrt(max(0.0, disc))
        return sorted([(-c - sq) / (2.0 * b), (-c + sq) / (2.0 * b)])

    inv = 1.0 / a
    p, q, r = b * inv, c * inv, d * inv

    p3 = p / 3.0
    A  = q - p * p3
    B  = 2.0 * p3 ** 3 - p3 * q + r

    disc = -(4.0 * A ** 3 + 27.0 * B ** 2)

    if disc > 0:
        m     = 2.0 * math.sqrt(-A / 3.0)
        arg   = max(-1.0, min(1.0, 3.0 * B / (A * m)))
        theta = math.acos(arg) / 3.0
        ts = [m * math.cos(theta - 2.0 * k * math.pi / 3.0) for k in range(3)]
    elif abs(disc) < 1e-10:
        ts = [0.0] if abs(A) < 1e-12 else [3.0 * B / A, -3.0 * B / (2.0 * A)]
    else:
        sq   = math.sqrt(max(0.0, -disc / 108.0))
        u_a  = -B / 2.0 + sq
        v_a  = -B / 2.0 - sq
        u    = math.copysign(abs(u_a) ** (1.0 / 3.0), u_a)
        v    = math.copysign(abs(v_a) ** (1.0 / 3.0), v_a)
        ts   = [u + v]

    return sorted(t - p3 for t in ts)


def _solve_quartic_ferrari(a4: float, a3: float, a2: float,
                           a1: float, a0: float):
    """Real roots of a4·t⁴ + a3·t³ + a2·t² + a1·t + a0 = 0 (sorted).

    Uses Ferrari's analytical method.  Returns [] when a4 ≈ 0.
    """
    if abs(a4) < 1e-12:
        return _solve_cubic_real(a3, a2, a1, a0)

    inv = 1.0 / a4
    b, c, d, e = a3 * inv, a2 * inv, a1 * inv, a0 * inv

    b2   = b * b
    b4   = b / 4.0
    p    = c - 3.0 * b2 / 8.0
    q    = b2 * b / 8.0 - b * c / 2.0 + d
    r    = -3.0 * b2 * b2 / 256.0 + b2 * c / 16.0 - b * d / 4.0 + e

    roots_u = []

    if abs(q) < 1e-10:
        disc = p * p - 4.0 * r
        if disc < 0:
            return []
        sq = math.sqrt(max(0.0, disc))
        for u2 in [(-p - sq) / 2.0, (-p + sq) / 2.0]:
            if u2 > 1e-10:
                sq_u2 = math.sqrt(u2)
                roots_u.extend([-sq_u2, sq_u2])
            elif u2 >= -1e-10:
                roots_u.append(0.0)
    else:
        cubic_roots = _solve_cubic_real(8.0, -4.0 * p, -8.0 * r,
                                        4.0 * p * r - q * q)

        m0 = None
        for m in sorted(cubic_roots, reverse=True):
            if 2.0 * m - p >= -1e-10:
                m0 = m
                break
        if m0 is None:
            m0 = max(cubic_roots) if cubic_roots else 0.0

        sq2mp = math.sqrt(max(0.0, 2.0 * m0 - p))
        # NOTE: when sq2mp ≈ 0 the two quadratics nearly coincide (grazing ray).
        # A biquadratic fallback could recover tangent roots; for now we return []
        # which may cause a missed silhouette pixel at extreme grazing angles.
        if abs(sq2mp) < 1e-12:
            return []

        for sign in (1.0, -1.0):
            B_q = sign * sq2mp
            C_q = m0 + sign * q / (2.0 * sq2mp)
            disc = B_q * B_q - 4.0 * C_q
            if disc >= 0:
                sq = math.sqrt(max(0.0, disc))
                roots_u.extend([(-B_q - sq) / 2.0, (-B_q + sq) / 2.0])

    return sorted(u - b4 for u in roots_u)


class Torus:
    """Torus defined by centre, axis direction, major radius R, and minor radius r.

    The torus is the set of points at distance r from the ring of radius R
    centred at `centre` and lying in the plane perpendicular to `axis`.

    Intersection is found by solving a quartic polynomial analytically
    (Ferrari's method) after transforming the ray into the torus local frame.
    """

    def __init__(self, center: Vec3, axis: Vec3,
                 major_radius: float, minor_radius: float,
                 color: Color = None, opacity: float = 1.0,
                 reflect: float = 0.0, ior: float = 1.0):
        self.center       = center
        self.major_radius = float(major_radius)
        self.minor_radius = float(minor_radius)
        if self.major_radius <= 0.0:
            raise ValueError("Torus: major_radius must be positive")
        if self.minor_radius <= 0.0:
            raise ValueError("Torus: minor_radius must be positive")
        if self.minor_radius >= self.major_radius:
            raise ValueError("Torus: minor_radius must be less than major_radius "
                             "to avoid a self-intersecting surface")
        self.color   = color if color is not None else Color(1.0, 1.0, 1.0)
        self.opacity = max(0.0, min(1.0, float(opacity)))
        self.reflect = max(0.0, min(1.0, float(reflect)))
        self.ior     = max(1.0, float(ior))

        # Build orthonormal frame  (W = axis → local Y)
        self.W = axis.normalize()
        arb    = (Vec3(0, 0, 1)
                  if abs(self.W.dot(Vec3(0, 1, 0))) > 0.999
                  else Vec3(0, 1, 0))
        self.U = self.W.cross(arb).normalize()   # local X
        self.V = self.W.cross(self.U).normalize() # local Z

    def _to_local(self, v: Vec3) -> Vec3:
        return Vec3(v.dot(self.U), v.dot(self.W), v.dot(self.V))

    def _from_local(self, v: Vec3) -> Vec3:
        return self.U * v.x + self.W * v.y + self.V * v.z

    def hit(self, ray, t_min: float = 0.001,
            t_max: float = float('inf')) -> Optional[HitRecord]:
        # Transform ray to local frame (axis → Y)
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

        # (|q+td|² + R²−r²)² = 4R²((qx+tdx)² + (qz+tdz)²)
        c4 = d2 * d2
        c3 = 4.0 * d2 * dq
        c2 = 4.0 * dq * dq + 2.0 * d2 * K - 4.0 * R * R * d_radial_sq
        c1 = 4.0 * dq * K  - 8.0 * R * R * dq_radial
        c0 = K * K          - 4.0 * R * R * q_radial_sq

        for t in _solve_quartic_ferrari(c4, c3, c2, c1, c0):
            if t_min <= t <= t_max:
                p_world = ray.point_at(t)
                p_loc   = self._to_local(p_world - self.center)
                rho     = math.sqrt(p_loc.x * p_loc.x + p_loc.z * p_loc.z)
                if rho < 1e-10:
                    continue
                cx, cz  = R * p_loc.x / rho, R * p_loc.z / rho
                n_loc   = Vec3(p_loc.x - cx, p_loc.y, p_loc.z - cz).normalize()
                normal  = self._from_local(n_loc)
                return HitRecord(t=t, point=p_world, normal=normal)

        return None

    def hit_intervals(self, ray, t_min: float = 1e-9,
                      t_max: float = float('inf')) -> list:
        """Return 0, 1, or 2 HitIntervals (torus quartic gives up to 4 roots -> 2 pairs)."""
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
            # else: degenerate root at torus axis (rho ≈ 0); interval silently dropped
            i += 2

        return intervals

    def bounding_box(self):
        from bvh import AABB  # lazy import avoids shapes ↔ bvh circular dependency
        extent = self.major_radius + self.minor_radius
        r = Vec3(extent, extent, extent)
        return AABB(self.center - r, self.center + r)


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
