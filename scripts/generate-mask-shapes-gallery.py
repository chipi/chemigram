#!/usr/bin/env python3
"""Generate a visual gallery of build-by-words mask shapes.

Companion to ``scripts/generate-visual-proofs.py`` — that gallery shows
*per-primitive* effects through a fixed centered-ellipse demo mask;
this one shows *per-mask-shape* effects through a fixed loud effect
(exposure +1.0). Side-by-side: phrase from the guide -> rendered
output where the mask region is visibly brighter than the rest.

Renders against the synthetic grayscale ramp (a left-to-right ramp
target). Why grayscale: the spatial structure of any mask shape
becomes immediately visible because the ramp's tonal gradient acts
as a reference. A "bottom third" mask brightens the bottom 1/3 of
the ramp; a "left half" mask brightens the left half of the ramp;
a "center circle" mask brightens a circular region in the middle.

Usage::

    uv run python scripts/generate-mask-shapes-gallery.py

Requires CHEMIGRAM_DT_CONFIGDIR set (or ~/chemigram-phase0/dt-config
exists).

Output:

- ``docs/visual-proofs/mask-shapes/<phrase-slug>.jpg`` — one render
  per shape.
- ``docs/visual-proofs/mask-shapes/_uniform.jpg`` — the reference
  render (expo+1.0, no mask) for visual diff.
- ``docs/visual-proofs/mask-shapes/_baseline.jpg`` — the unmodified
  baseline ramp (no exposure, no mask) so the reader sees what the
  effect attached itself to.
- A ``## Visual reference`` section appended/replaced in
  ``docs/guides/mask-shapes-from-words.md``.

CI is not wired to regenerate this; refresh manually when the
spec table in mask-shapes-from-words.md changes.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from chemigram.core.helpers import apply_entry  # noqa: E402
from chemigram.core.pipeline import render  # noqa: E402
from chemigram.core.vocab import load_packs  # noqa: E402
from chemigram.core.xmp import parse_xmp, write_xmp  # noqa: E402

_BASELINE_XMP = REPO / "src/chemigram/core/_baseline_v1.xmp"
_GRAYSCALE = REPO / "tests/fixtures/reference-targets/grayscale_synthetic_linear.png"
_GUIDE = REPO / "docs/guides/mask-shapes-from-words.md"
_OUT_DIR = REPO / "docs/visual-proofs/mask-shapes"

_RENDER_W = 320
_RENDER_H = 320
_EV = 1.0  # loud effect, makes spatial signature unmistakable


@dataclass
class GalleryEntry:
    slug: str
    phrase: str
    description: str
    spec: dict[str, object]


# 10 representative phrases covering each shape kind. Hand-picked to
# show the spatial-structure variety (gradients, hard rectangles,
# ellipses, paths) and confirm the rotation/anchor convention from
# the guide is rendering-correct.
ENTRIES: list[GalleryEntry] = [
    GalleryEntry(
        slug="bottom-third-gradient",
        phrase='"Bottom third" (gradient)',
        description="anchor_y=0.67, rotation=180. Light side covers bottom 1/3.",
        spec={
            "dt_form": "gradient",
            "dt_params": {
                "anchor_x": 0.5,
                "anchor_y": 0.67,
                "rotation": 180.0,
                "compression": 0.5,
                "state": 2,
            },
        },
    ),
    GalleryEntry(
        slug="top-half-gradient",
        phrase='"Top half" (gradient)',
        description="anchor_y=0.5, rotation=0. Light side covers top half.",
        spec={
            "dt_form": "gradient",
            "dt_params": {
                "anchor_x": 0.5,
                "anchor_y": 0.5,
                "rotation": 0.0,
                "compression": 0.5,
                "state": 2,
            },
        },
    ),
    GalleryEntry(
        slug="left-half-gradient",
        phrase='"Left half" (gradient)',
        description="rotation=90, vertical axis. Light side covers left half.",
        spec={
            "dt_form": "gradient",
            "dt_params": {
                "anchor_x": 0.5,
                "anchor_y": 0.5,
                "rotation": 90.0,
                "compression": 0.5,
                "state": 2,
            },
        },
    ),
    GalleryEntry(
        slug="right-half-gradient",
        phrase='"Right half" (gradient)',
        description="rotation=270, vertical axis. Light side covers right half.",
        spec={
            "dt_form": "gradient",
            "dt_params": {
                "anchor_x": 0.5,
                "anchor_y": 0.5,
                "rotation": 270.0,
                "compression": 0.5,
                "state": 2,
            },
        },
    ),
    GalleryEntry(
        slug="bottom-third-rectangle",
        phrase='"Bottom third (hard edge)" (rectangle)',
        description="x0=0, y0=0.67, x1=1, y1=1. Hard-edged bottom 1/3.",
        spec={
            "dt_form": "rectangle",
            "dt_params": {"x0": 0.0, "y0": 0.67, "x1": 1.0, "y1": 1.0, "border": 0.0},
        },
    ),
    GalleryEntry(
        slug="center-square-rectangle",
        phrase='"Center square" (rectangle)',
        description="50% x 50% center square with subtle feathering.",
        spec={
            "dt_form": "rectangle",
            "dt_params": {"x0": 0.25, "y0": 0.25, "x1": 0.75, "y1": 0.75, "border": 0.02},
        },
    ),
    GalleryEntry(
        slug="center-circle-medium-ellipse",
        phrase='"Center circle, medium" (ellipse)',
        description="center=(0.5, 0.5), radius=0.3, border=0.08.",
        spec={
            "dt_form": "ellipse",
            "dt_params": {
                "center_x": 0.5,
                "center_y": 0.5,
                "radius_x": 0.3,
                "radius_y": 0.3,
                "border": 0.08,
            },
        },
    ),
    GalleryEntry(
        slug="upper-left-thirds-ellipse",
        phrase='"Subject upper-left rule-of-thirds" (ellipse)',
        description="center=(0.33, 0.33), radius=0.2 - subject region at top-left intersection.",
        spec={
            "dt_form": "ellipse",
            "dt_params": {
                "center_x": 0.33,
                "center_y": 0.33,
                "radius_x": 0.2,
                "radius_y": 0.2,
                "border": 0.06,
            },
        },
    ),
    GalleryEntry(
        slug="diagonal-bottom-right-light-gradient",
        phrase='"Diagonal, top-left dim" (gradient, light bottom-right)',
        description="rotation=225, diagonal axis. Light side bottom-right.",
        spec={
            "dt_form": "gradient",
            "dt_params": {
                "anchor_x": 0.5,
                "anchor_y": 0.5,
                "rotation": 225.0,
                "compression": 0.5,
                "state": 2,
            },
        },
    ),
    GalleryEntry(
        slug="centered-triangle-path",
        phrase="Centered triangle (path)",
        description=(
            "3-vertex closed polygon. RFC-026 substrate; same wire AI subject masks will use."
        ),
        spec={
            "dt_form": "path",
            "dt_params": {
                "vertices": [[0.5, 0.2], [0.8, 0.7], [0.2, 0.7]],
                "border": 0.04,
            },
        },
    ),
    # ----- range_filter examples (RFC-024 / ADR-085) ----------------
    GalleryEntry(
        slug="range-luminance-shadows-only",
        phrase='Parametric only: "all dark pixels" (luminance shadows)',
        description=(
            "range_filter only (no dt_form). Affects the dark third "
            "of the tonal range anywhere in the image."
        ),
        spec={
            "range_filter": {
                "kind": "luminance",
                "min": 0.0,
                "max": 0.3,
                "feather": 0.05,
            },
        },
    ),
    GalleryEntry(
        slug="range-luminance-highlights-only",
        phrase='Parametric only: "all bright pixels" (luminance highlights)',
        description=(
            "range_filter only. Affects the upper third of the tonal "
            "range — useful for highlight recovery / dampening."
        ),
        spec={
            "range_filter": {
                "kind": "luminance",
                "min": 0.7,
                "max": 1.0,
                "feather": 0.05,
            },
        },
    ),
    GalleryEntry(
        slug="range-luminance-shadows-inverted",
        phrase='Inverted: "everything except shadows"',
        description=(
            "range_filter with invert=true. Same shadow band, but "
            "pixels OUTSIDE that band get the mask (= midtones + highlights)."
        ),
        spec={
            "range_filter": {
                "kind": "luminance",
                "min": 0.0,
                "max": 0.3,
                "feather": 0.05,
                "invert": True,
            },
        },
    ),
    GalleryEntry(
        slug="range-drawn-bottom-half-shadows",
        phrase='Drawn + parametric: "shadows in the bottom half"',
        description=(
            "Drawn gradient (bottom half) + luminance shadows filter. "
            "Edit applies only where BOTH conditions are true: pixel "
            "is in bottom half AND pixel is dark. The user's mental "
            "model of refining a drawn mask down to specific pixels."
        ),
        spec={
            "dt_form": "gradient",
            "dt_params": {
                "anchor_x": 0.5,
                "anchor_y": 0.5,
                "rotation": 180.0,
                "compression": 0.5,
                "state": 2,
            },
            "range_filter": {
                "kind": "luminance",
                "min": 0.0,
                "max": 0.4,
                "feather": 0.05,
            },
        },
    ),
    GalleryEntry(
        slug="range-drawn-ellipse-highlights",
        phrase='Drawn + parametric: "highlights inside subject ellipse"',
        description=(
            "Drawn ellipse + luminance highlights filter. Brightens "
            "only the bright pixels inside the subject region — "
            "useful for catching catchlights without blowing out the "
            "midtones."
        ),
        spec={
            "dt_form": "ellipse",
            "dt_params": {
                "center_x": 0.5,
                "center_y": 0.5,
                "radius_x": 0.4,
                "radius_y": 0.4,
                "border": 0.05,
            },
            "range_filter": {
                "kind": "luminance",
                "min": 0.6,
                "max": 1.0,
                "feather": 0.05,
            },
        },
    ),
]


def _resolve_configdir() -> Path:
    raw = os.environ.get("CHEMIGRAM_DT_CONFIGDIR")
    if raw:
        return Path(raw).expanduser()
    fallback = Path.home() / "chemigram-phase0" / "dt-config"
    if fallback.exists():
        return fallback
    raise RuntimeError(
        "CHEMIGRAM_DT_CONFIGDIR not set and ~/chemigram-phase0/dt-config "
        "doesn't exist. Set CHEMIGRAM_DT_CONFIGDIR to a pre-bootstrapped "
        "darktable configdir (open the GUI once, quit, that bootstraps it)."
    )


def _render_xmp(xmp_path: Path, out_path: Path, configdir: Path) -> bool:
    result = render(
        raw_path=_GRAYSCALE,
        xmp_path=xmp_path,
        output_path=out_path,
        width=_RENDER_W,
        height=_RENDER_H,
        high_quality=False,
        configdir=configdir,
    )
    if not result.success:
        print(f"  render failed: {result.error_message}", file=sys.stderr)
        return False
    return True


def _render_baseline(configdir: Path, tmp_dir: Path) -> Path:
    """Render the unmodified ramp through baseline (no effect, no mask)."""
    baseline = parse_xmp(_BASELINE_XMP)
    xmp_path = tmp_dir / "_baseline.xmp"
    out_path = _OUT_DIR / "_baseline.jpg"
    write_xmp(baseline, xmp_path)
    print("  rendering baseline (reference, no effect, no mask)")
    if not _render_xmp(xmp_path, out_path, configdir):
        raise RuntimeError("baseline render failed")
    return out_path


def _render_uniform(configdir: Path, tmp_dir: Path) -> Path:
    """Render the ramp through expo+1.0 with NO mask. Visual reference
    for what 'fully on' looks like."""
    vocab = load_packs(["expressive-baseline"])
    expo = vocab.lookup_by_name("exposure")
    assert expo is not None, "expressive-baseline pack missing 'exposure'"
    baseline = parse_xmp(_BASELINE_XMP)
    uniform_xmp = apply_entry(baseline, expo, parameter_values={"ev": _EV})
    xmp_path = tmp_dir / "_uniform.xmp"
    out_path = _OUT_DIR / "_uniform.jpg"
    write_xmp(uniform_xmp, xmp_path)
    print(f"  rendering uniform expo+{_EV} (reference, mask off)")
    if not _render_xmp(xmp_path, out_path, configdir):
        raise RuntimeError("uniform render failed")
    return out_path


def _render_entry(entry: GalleryEntry, configdir: Path, tmp_dir: Path) -> Path:
    vocab = load_packs(["expressive-baseline"])
    expo = vocab.lookup_by_name("exposure")
    assert expo is not None
    baseline = parse_xmp(_BASELINE_XMP)
    masked_xmp = apply_entry(baseline, expo, parameter_values={"ev": _EV}, mask_spec=entry.spec)
    xmp_path = tmp_dir / f"{entry.slug}.xmp"
    out_path = _OUT_DIR / f"{entry.slug}.jpg"
    write_xmp(masked_xmp, xmp_path)
    print(f"  rendering '{entry.phrase}'")
    if not _render_xmp(xmp_path, out_path, configdir):
        raise RuntimeError(f"render failed for {entry.slug}")
    return out_path


def _render_all() -> None:
    configdir = _resolve_configdir()
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp_dir = _OUT_DIR / "_xmp_scratch"
    tmp_dir.mkdir(exist_ok=True)
    _render_baseline(configdir, tmp_dir)
    _render_uniform(configdir, tmp_dir)
    for entry in ENTRIES:
        _render_entry(entry, configdir, tmp_dir)
    # Clean up scratch XMPs
    for f in tmp_dir.glob("*.xmp"):
        f.unlink()
    tmp_dir.rmdir()


def _gallery_md() -> str:
    """Render the markdown for the Visual reference section."""
    lines = [
        "## Visual reference",
        "",
        "Each row below renders **exposure +1.0** through one shape from the "
        "table above, against the synthetic grayscale ramp. The brightened "
        "region reveals where the mask is on; everything else stays at the "
        "ramp's baseline tone.",
        "",
        "Reference renders for visual comparison:",
        "",
        "| Reference | Description |",
        "|-|-|",
        "| ![baseline](../visual-proofs/mask-shapes/_baseline.jpg) | "
        "Baseline ramp — no effect, no mask. The unmodified target. |",
        "| ![uniform](../visual-proofs/mask-shapes/_uniform.jpg) | "
        "expo+1.0 with no mask — uniform brightening everywhere. The "
        '"fully on" reference. |',
        "",
        "Per-shape renders:",
        "",
        "| Phrase | Notes | Render |",
        "|-|-|-|",
    ]
    for entry in ENTRIES:
        img = f"../visual-proofs/mask-shapes/{entry.slug}.jpg"
        lines.append(f"| {entry.phrase} | {entry.description} | ![{entry.slug}]({img}) |")
    lines.append("")
    lines.append(
        "These renders are produced by `scripts/generate-mask-shapes-gallery.py`. "
        "Refresh after changing the spec table above; CI does not regenerate "
        "them automatically."
    )
    lines.append("")
    return "\n".join(lines)


def _splice_gallery_into_guide() -> None:
    text = _GUIDE.read_text()
    section = _gallery_md()
    marker = re.compile(r"\n## Visual reference\n.*?(?=\n## |\Z)", re.DOTALL)
    if marker.search(text):
        text = marker.sub("\n" + section, text)
    else:
        # Insert before the "See also" section if present, else append
        see_also = re.search(r"\n## See also\n", text)
        if see_also:
            insert_at = see_also.start()
            text = text[:insert_at] + "\n" + section + text[insert_at:]
        else:
            text = text.rstrip() + "\n\n" + section
    _GUIDE.write_text(text)
    print(f"  spliced Visual reference section into {_GUIDE}")


def main() -> None:
    print("Rendering build-by-words mask gallery...")
    _render_all()
    _splice_gallery_into_guide()
    print(f"\nDone. {len(ENTRIES) + 2} renders in {_OUT_DIR}/")


if __name__ == "__main__":
    main()
