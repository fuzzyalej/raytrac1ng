"""RGB color representation and named color palette."""

import math
from dataclasses import dataclass


@dataclass
class Color:
    """An RGB color with components in [0.0, 1.0]."""
    r: float
    g: float
    b: float

    def __add__(self, other: 'Color') -> 'Color':
        return Color(self.r + other.r, self.g + other.g, self.b + other.b)

    def __mul__(self, other):
        if isinstance(other, Color):
            return Color(self.r * other.r, self.g * other.g, self.b * other.b)
        if isinstance(other, (int, float)):
            return Color(self.r * other, self.g * other, self.b * other)
        return NotImplemented

    def __rmul__(self, scalar: float) -> 'Color':
        return self.__mul__(scalar)

    def clamp(self) -> 'Color':
        """Clamp each channel to [0.0, 1.0]."""
        return Color(
            max(0.0, min(1.0, self.r)),
            max(0.0, min(1.0, self.g)),
            max(0.0, min(1.0, self.b)),
        )

    def to_bytes(self) -> tuple[int, int, int]:
        """Convert to an (R, G, B) tuple of integers in [0, 255]."""
        return (
            int(self.r * 255),
            int(self.g * 255),
            int(self.b * 255),
        )


def color_from_kelvin(k: float) -> 'Color':
    """Convert color temperature in Kelvin to an RGB Color.

    Uses Tanner Helland's piecewise approximation (valid ~1000K–40000K).
    """
    # Reference: https://tannerhelland.com/2012/09/18/convert-temperature-rgb-algorithm-code.html
    t = max(1000.0, min(40000.0, float(k))) / 100.0

    # Red
    if t <= 66:
        r = 1.0
    else:
        r = max(0.0, min(1.0, 329.698727446 * ((t - 60) ** -0.1332047592) / 255.0))

    # Green
    if t <= 66:
        g = max(0.0, min(1.0, (99.4708025861 * math.log(t) - 161.1195681661) / 255.0))
    else:
        g = max(0.0, min(1.0, 288.1221695283 * ((t - 60) ** -0.0755148492) / 255.0))

    # Blue
    if t >= 66:
        b = 1.0
    # Helland's algorithm: blue is 0 below ~1900K
    elif t <= 19:
        b = 0.0
    else:
        b = max(0.0, min(1.0, (138.5177312231 * math.log(t - 10) - 305.0447927307) / 255.0))

    return Color(r, g, b)


# ---------------------------------------------------------------------------
# Named color palette
# ---------------------------------------------------------------------------

NAMED_COLORS: dict[str, Color] = {
    # Primary
    'red':     Color(1.0, 0.0, 0.0),
    'green':   Color(0.0, 0.8, 0.0),
    'blue':    Color(0.0, 0.0, 1.0),
    # Secondary
    'yellow':  Color(1.0, 1.0, 0.0),
    'cyan':    Color(0.0, 1.0, 1.0),
    'magenta': Color(1.0, 0.0, 1.0),
    # Rainbow extras
    'orange':  Color(1.0, 0.5, 0.0),
    'purple':  Color(0.5, 0.0, 0.5),
    'pink':    Color(1.0, 0.4, 0.7),
    'indigo':  Color(0.29, 0.0, 0.51),
    'violet':  Color(0.56, 0.0, 1.0),
    # Neutrals
    'white':   Color(1.0, 1.0, 1.0),
    'black':   Color(0.0, 0.0, 0.0),
    'gray':    Color(0.5, 0.5, 0.5),
    'brown':   Color(0.6, 0.3, 0.1),
}
