"""Raytracer entry point.

Usage:
    python3 main.py <scene.pov> [-W WIDTH] [-H HEIGHT] [-o OUTPUT]

Example:
    python3 main.py examples/01-basic.pov -W 1024 -H 768 -o render.png
"""

import os
import sys

# Add src/ to sys.path for the main process, and to PYTHONPATH so that
# worker processes spawned by multiprocessing can also import from src/.
_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, _SRC)
_old_pp = os.environ.get("PYTHONPATH", "")
os.environ["PYTHONPATH"] = (_SRC + os.pathsep + _old_pp) if _old_pp else _SRC

import argparse

from renderer import render

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required.  Install with:  pip install Pillow")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="Mini raytracer")
    ap.add_argument("scene", help="Path to .pov scene file")
    ap.add_argument("-W", "--width", type=int, default=800, help="Image width (default 800)")
    ap.add_argument("-H", "--height", type=int, default=600, help="Image height (default 600)")
    ap.add_argument("-o", "--output", default="output.png", help="Output file (default output.png)")
    ap.add_argument("--aa", type=int, default=0, metavar="N", help="Anti-aliasing samples per pixel (0 = off, 2–4 = good quality)")
    ap.add_argument(
        "-j", "--jobs",
        type=int, default=0, metavar="N",
        help="Worker processes for parallel rendering (default: 1; 0 = all CPU cores)"
    )
    args = ap.parse_args()

    if args.jobs < 0:
        ap.error("--jobs must be 0 (all cores) or a positive integer")

    print(f"Loading scene: {args.scene}")
    if args.scene.endswith(".pow"):
        from new_parser import parse_scene
    else:
        from parser import parse_scene
    scene = parse_scene(args.scene)

    obj_count = len(scene.objects)
    light_count = len(scene.lights)
    print(f"  Camera at {scene.camera.location}, looking at {scene.camera.look_at}")
    print(f"  {obj_count} object(s), {light_count} light(s)")
    aa_info = f" (AA {args.aa}×{args.aa})" if args.aa > 0 else ""
    print(f"Rendering {args.width}x{args.height}{aa_info}…")

    workers = args.jobs if args.jobs > 0 else (os.cpu_count() or 1)
    if workers > 1:
        print(f"  Using {workers} worker processes")
    pixels = render(scene, args.width, args.height, aa_samples=args.aa, workers=workers)

    img = Image.new('RGB', (args.width, args.height))
    img.putdata([p.to_bytes() for p in pixels])
    img.save(args.output)
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
