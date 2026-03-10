from __future__ import annotations
from dataclasses import dataclass, field
from color import Color


@dataclass
class Material:
    color:   Color = field(default_factory=lambda: Color(1, 1, 1))
    opacity: float = 1.0
    reflect: float = 0.0
    ior:     float = 1.0

    def __post_init__(self):
        self.opacity = max(0.0, min(1.0, float(self.opacity)))
        self.reflect = max(0.0, min(1.0, float(self.reflect)))
        self.ior     = max(1.0, float(self.ior))
