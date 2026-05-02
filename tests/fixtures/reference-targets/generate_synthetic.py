#!/usr/bin/env python3
"""Generate the synthetic reference PNGs from the published L*a*b* values.

Idempotent: running this script reproduces ``colorchecker_synthetic_srgb.png``
and ``grayscale_synthetic_linear.png`` byte-for-byte on a given Pillow
version. PNG compresses the solid-color patches efficiently (~10 KB total,
well under the 500 KB pre-commit large-file limit). The committed files
in this directory are the canonical output; this script is what you run
to regenerate them after editing the JSON ground truth or the patch-grid
layout.

Usage (from the repo root):

    uv run python tests/fixtures/reference-targets/generate_synthetic.py

Per RFC-019 v0.2.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from chemigram.core.assertions import lab_to_srgb

_HERE = Path(__file__).resolve().parent
_CC24_JSON = _HERE / "colorchecker24_lab_d50.json"
_CC24_PNG = _HERE / "colorchecker_synthetic_srgb.png"
_GRAYSCALE_PNG = _HERE / "grayscale_synthetic_linear.png"


def _generate_cc24() -> None:
    """24 100x100 patches in a 6x4 grid. Index 1 is top-left, then
    left-to-right then top-to-bottom (matches the published CC24 layout).
    """
    raw = json.loads(_CC24_JSON.read_text(encoding="utf-8"))
    grid = raw["synthetic_grid"]
    cols = grid["cols"]
    rows = grid["rows"]
    patch = grid["patch_pixels"]
    width = grid["image_width"]
    height = grid["image_height"]
    assert cols * patch == width
    assert rows * patch == height

    img = Image.new("RGB", (width, height), (0, 0, 0))
    for entry in raw["patches"]:
        idx = entry["index"]
        L, a, b = entry["L"], entry["a"], entry["b"]
        rgb = lab_to_srgb((L, a, b))
        # Patch index 1..24 maps to grid (row, col) = ((idx-1) // cols, (idx-1) % cols)
        row, col = divmod(idx - 1, cols)
        x0, y0 = col * patch, row * patch
        # Fill the patch square
        for y in range(y0, y0 + patch):
            for x in range(x0, x0 + patch):
                img.putpixel((x, y), rgb)
    img.save(_CC24_PNG, format="PNG", optimize=True)
    print(f"wrote {_CC24_PNG.relative_to(_HERE.parents[2])}")


def _generate_grayscale() -> None:
    """24-step linear sRGB ramp, 25 px wide x 100 px tall per step.
    Total width 600 px. sRGB values evenly spaced across [0, 255].
    """
    steps = 24
    step_width = 25
    height = 100
    width = steps * step_width
    img = Image.new("RGB", (width, height), (0, 0, 0))
    for i in range(steps):
        v = round(i * 255 / (steps - 1))
        x0 = i * step_width
        for y in range(height):
            for x in range(x0, x0 + step_width):
                img.putpixel((x, y), (v, v, v))
    img.save(_GRAYSCALE_PNG, format="PNG", optimize=True)
    print(f"wrote {_GRAYSCALE_PNG.relative_to(_HERE.parents[2])}")


def main() -> int:
    _generate_cc24()
    _generate_grayscale()
    return 0


if __name__ == "__main__":
    sys.exit(main())
