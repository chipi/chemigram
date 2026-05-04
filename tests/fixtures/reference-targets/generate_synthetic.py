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
_CLIPPED_PNG = _HERE / "clipped_gradient_synthetic.png"


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
    """24-step linear sRGB ramp, 25 px wide x 400 px tall per step.
    Total dimensions 600x400 (matches the ColorChecker chart so visual-
    proofs renders fit on the same page row, and so vertical-axis masks
    like ``gradient_bottom_lift_shadows`` have y-range to act on).
    sRGB values evenly spaced across [0, 255].
    """
    steps = 24
    step_width = 25
    height = 400
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


def _generate_clipped_gradient() -> None:
    """Continuous-tone gradient with a clipped band — the fixture for
    ``highlights_recovery_*`` and ``grain_*`` direction-of-change tests.

    Layout (600x400):

    - Top half (rows 0..199): a vertical sRGB gradient from 0,0,0 (top) to
      255,255,255 (bottom). Continuous tone, no clipping. Useful for
      grain primitives (texture has uniform tone to ride on) and as
      reference for tone-curve moves on midtones.
    - Bottom half (rows 200..399): a 60% region pinned at 255,255,255
      (clipped highlights), then a 40% smooth ramp from 200..255. Useful
      for highlights_recovery primitives — the clipped band is what the
      module actually has to work on.

    sRGB 8-bit. Fixture is intentionally synthetic (per RFC-019 / ADR-067:
    no physical-chart dependency); chart-pipeline path treats this as a
    display-referred PNG just like the CC24 and grayscale-ramp fixtures.
    """
    width, height = 600, 400
    img = Image.new("RGB", (width, height), (0, 0, 0))

    # Top half: vertical 0..255 gradient (continuous tone).
    half_h = height // 2
    for y in range(half_h):
        v = round(y * 255 / max(half_h - 1, 1))
        for x in range(width):
            img.putpixel((x, y), (v, v, v))

    # Bottom half: clipped band on the left 60%, ramp 200..255 on right 40%.
    clipped_w = int(width * 0.6)
    for y in range(half_h, height):
        for x in range(clipped_w):
            img.putpixel((x, y), (255, 255, 255))  # blown
        ramp_w = width - clipped_w
        for x in range(clipped_w, width):
            t = (x - clipped_w) / max(ramp_w - 1, 1)
            v = round(200 + t * 55)  # 200..255 linear
            img.putpixel((x, y), (v, v, v))

    img.save(_CLIPPED_PNG, format="PNG", optimize=True)
    print(f"wrote {_CLIPPED_PNG.relative_to(_HERE.parents[2])}")


def main() -> int:
    _generate_cc24()
    _generate_grayscale()
    _generate_clipped_gradient()
    return 0


if __name__ == "__main__":
    sys.exit(main())
