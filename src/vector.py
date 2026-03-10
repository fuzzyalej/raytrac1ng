"""3D Vector class — foundation for all raytracer math."""

import math


class Vec3:
    """A simple 3D vector with operator overloads."""

    __slots__ = ('x', 'y', 'z')

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    # --- Arithmetic ---

    def __add__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> 'Vec3':
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> 'Vec3':
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> 'Vec3':
        inv = 1.0 / scalar
        return Vec3(self.x * inv, self.y * inv, self.z * inv)

    def __neg__(self) -> 'Vec3':
        return Vec3(-self.x, -self.y, -self.z)

    # --- Vector operations ---

    def dot(self, other: 'Vec3') -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: 'Vec3') -> 'Vec3':
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self) -> float:
        return math.sqrt(self.dot(self))

    def length_squared(self) -> float:
        return self.dot(self)

    def normalize(self) -> 'Vec3':
        lng = self.length()
        if lng == 0:
            return Vec3(0, 0, 0)
        return self / lng

    # --- Utility ---

    def __repr__(self) -> str:
        return f"Vec3({self.x:.4f}, {self.y:.4f}, {self.z:.4f})"

    def __len__(self) -> int:
        return 3

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z


class Matrix4x4:
    """Row-major 4x4 matrix for affine transforms.

    Stored as a flat list of 16 floats in row-major order:
        m[row*4 + col]
    """

    __slots__ = ('m',)

    def __init__(self, m=None):
        """m: iterable of 16 floats (row-major). Default: identity."""
        if m is None:
            self.m = [1.0,0.0,0.0,0.0,
                      0.0,1.0,0.0,0.0,
                      0.0,0.0,1.0,0.0,
                      0.0,0.0,0.0,1.0]
        else:
            self.m = [float(x) for x in m]
            if len(self.m) != 16:
                raise ValueError(f"Matrix4x4 requires exactly 16 values, got {len(self.m)}")

    def __matmul__(self, other: 'Matrix4x4') -> 'Matrix4x4':
        a, b = self.m, other.m
        result = [0.0] * 16
        for row in range(4):
            for col in range(4):
                result[row*4+col] = sum(a[row*4+k] * b[k*4+col] for k in range(4))
        return Matrix4x4(result)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Matrix4x4):
            return NotImplemented
        return all(abs(a - b) < 1e-9 for a, b in zip(self.m, other.m))

    def __repr__(self) -> str:
        rows = [self.m[r*4:(r+1)*4] for r in range(4)]
        inner = ",\n           ".join(
            "[" + ", ".join(f"{v:.4f}" for v in row) + "]" for row in rows
        )
        return f"Matrix4x4([{inner}])"

    def transform_point(self, v: 'Vec3') -> 'Vec3':
        """Apply full matrix (including translation) to a point."""
        m = self.m
        x = m[0]*v.x + m[1]*v.y + m[2]*v.z + m[3]
        y = m[4]*v.x + m[5]*v.y + m[6]*v.z + m[7]
        z = m[8]*v.x + m[9]*v.y + m[10]*v.z + m[11]
        w = m[12]*v.x + m[13]*v.y + m[14]*v.z + m[15]
        # w is 1.0 for pure affine matrices; divide only when it drifts (perspective or numerical noise)
        if abs(w - 1.0) > 1e-9 and abs(w) > 1e-12:
            return Vec3(x/w, y/w, z/w)
        return Vec3(x, y, z)

    def transform_direction(self, v: 'Vec3') -> 'Vec3':
        """Apply rotation/scale only (no translation) to a direction vector.

        NOTE: Do NOT use this for surface normals. Normals require transformation
        by the transpose of the inverse matrix to remain perpendicular under
        non-uniform scale. Use: inv.transpose().transform_direction(normal)
        """
        m = self.m
        x = m[0]*v.x + m[1]*v.y + m[2]*v.z
        y = m[4]*v.x + m[5]*v.y + m[6]*v.z
        z = m[8]*v.x + m[9]*v.y + m[10]*v.z
        return Vec3(x, y, z)

    def transpose(self) -> 'Matrix4x4':
        m = self.m
        return Matrix4x4([
            m[0],  m[4],  m[8],  m[12],
            m[1],  m[5],  m[9],  m[13],
            m[2],  m[6],  m[10], m[14],
            m[3],  m[7],  m[11], m[15],
        ])

    def inverse(self) -> 'Matrix4x4':
        """Gauss-Jordan elimination on augmented [M | I]."""
        aug = []
        for r in range(4):
            row = [float(self.m[r*4+c]) for c in range(4)]
            row += [1.0 if c == r else 0.0 for c in range(4)]
            aug.append(row)

        for col in range(4):
            pivot_row = max(range(col, 4), key=lambda r: abs(aug[r][col]))
            if abs(aug[pivot_row][col]) < 1e-12:
                raise ValueError("Matrix4x4.inverse: singular matrix")
            aug[col], aug[pivot_row] = aug[pivot_row], aug[col]
            pivot = aug[col][col]
            aug[col] = [x / pivot for x in aug[col]]
            for r in range(4):
                if r != col:
                    f = aug[r][col]
                    aug[r] = [aug[r][c] - f * aug[col][c] for c in range(8)]

        result = []
        for r in range(4):
            result.extend(aug[r][4:])
        return Matrix4x4(result)

    @staticmethod
    def from_trs(scale: tuple, rotate: tuple, translate: tuple) -> 'Matrix4x4':
        """Build combined TRS matrix: Scale -> Rotate (XYZ euler) -> Translate.

        rotate: (rx, ry, rz) euler angles in degrees.
        Rotation order: Rx * Ry * Rz  (intrinsic XYZ).
        Full matrix: T * Rx * Ry * Rz * S
        """
        scale_x, scale_y, scale_z = scale
        rx_d, ry_d, rz_d = rotate
        tx, ty, tz = translate

        rx = math.radians(rx_d)
        ry = math.radians(ry_d)
        rz = math.radians(rz_d)

        cos_x, sin_x = math.cos(rx), math.sin(rx)
        cos_y, sin_y = math.cos(ry), math.sin(ry)
        cos_z, sin_z = math.cos(rz), math.sin(rz)

        Rx = Matrix4x4([1, 0,      0,       0,
                        0, cos_x,  -sin_x,  0,
                        0, sin_x,   cos_x,  0,
                        0, 0,      0,       1])
        Ry = Matrix4x4([cos_y,   0, sin_y, 0,
                        0,       1, 0,     0,
                        -sin_y,  0, cos_y, 0,
                        0,       0, 0,     1])
        Rz = Matrix4x4([cos_z, -sin_z, 0, 0,
                        sin_z,  cos_z, 0, 0,
                        0,      0,     1, 0,
                        0,      0,     0, 1])

        S = Matrix4x4([scale_x, 0,       0,       0,
                       0,       scale_y, 0,       0,
                       0,       0,       scale_z, 0,
                       0,       0,       0,       1])
        T = Matrix4x4([1, 0, 0, tx,
                       0, 1, 0, ty,
                       0, 0, 1, tz,
                       0, 0, 0, 1])

        # TRS = T * Rx * Ry * Rz * S
        return T @ Rx @ Ry @ Rz @ S
