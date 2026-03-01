"""RGB color representation and named color palette."""

from dataclasses import dataclass


@dataclass
class Color:
    """An RGB color with components in [0.0, 1.0]."""
    r: float
    g: float
    b: float

    def __add__(self, other: 'Color') -> 'Color':
        return Color(self.r + other.r, self.g + other.g, self.b + other.b)

    def __mul__(self, scalar: float) -> 'Color':
        return Color(self.r * scalar, self.g * scalar, self.b * scalar)

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
