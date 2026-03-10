from scene import Scene
from . import pov
from . import pow_adapter


def parse(path: str) -> Scene:
    """Dispatch to the correct parser based on file extension."""
    if path.endswith(".pov"):
        return pov.parse_scene(path)
    return pow_adapter.parse_scene(path)


__all__ = ["parse"]
