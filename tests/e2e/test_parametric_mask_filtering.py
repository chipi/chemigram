"""End-to-end: parametric (range_filter) masks actually filter pixels
in darktable's pipeline (RFC-024 / ADR-085).

Sister to ``test_build_by_words_mask_shapes.py``: that test proves
named drawn shapes shape the effect *spatially*; this test proves
``range_filter`` shapes the effect *tonally* — the user's mental model
of "in this drawn mask, only affect the dark pixels."

Discriminating signal: render expo +1.0 through three masks against
the synthetic grayscale ramp (a left-to-right luminance gradient),
divide the rendered output into a 4-cell horizontal grid, and compare:

1. Drawn-only gradient (whole bottom half) — every cell in the bottom
   half brightens uniformly relative to baseline.
2. Drawn gradient + luminance shadows filter — only the *dark* cells
   in the bottom half brighten; bright cells stay unchanged.
3. Parametric-only luminance shadows — every dark pixel anywhere
   brightens; bright pixels untouched (no spatial mask, just tonal).

The test asserts case (2) brightens fewer cells than case (1) — the
parametric filter further restricted the drawn mask.
"""

from __future__ import annotations

import io
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from PIL import Image

from chemigram.core.helpers import apply_entry
from chemigram.core.pipeline import render
from chemigram.core.versioning import ImageRepo
from chemigram.core.versioning.ops import snapshot
from chemigram.core.vocab import load_packs
from chemigram.core.workspace import Workspace, init_workspace_root
from chemigram.core.xmp import parse_xmp, write_xmp

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINE_XMP = _REPO_ROOT / "src" / "chemigram" / "core" / "_baseline_v1.xmp"
_GRAYSCALE_RAMP = (
    _REPO_ROOT / "tests" / "fixtures" / "reference-targets" / "grayscale_synthetic_linear.png"
)

_RENDER_SIZE = 256
_GRID_COLS = 8  # finer than 4 for tonal resolution along the ramp's left-to-right axis


def _build_workspace(tmp_path: Path, raw_path: Path, configdir: Path) -> Workspace:
    root = tmp_path / "ws"
    init_workspace_root(root)
    repo = ImageRepo.init(root)
    workspace_raw = root / "raw" / raw_path.name
    if not workspace_raw.exists():
        workspace_raw.symlink_to(raw_path.resolve())
    snapshot(repo, parse_xmp(_BASELINE_XMP), label="baseline")
    return Workspace(
        image_id="phase0",
        root=root,
        repo=repo,
        raw_path=workspace_raw,
        configdir=configdir,
    )


def _render(xmp_path: Path, raw_path: Path, out_path: Path, configdir: Path) -> bytes:
    result = render(
        raw_path=raw_path,
        xmp_path=xmp_path,
        output_path=out_path,
        width=_RENDER_SIZE,
        height=_RENDER_SIZE,
        high_quality=False,
        configdir=configdir,
    )
    assert result.success, (
        f"darktable-cli failed: {result.error_message}\n"
        f"stderr (last 1000 chars): {result.stderr[-1000:]}"
    )
    return out_path.read_bytes()


def _column_luma(jpeg_bytes: bytes) -> list[float]:
    """Divide image into ``_GRID_COLS`` vertical columns; return mean
    Rec. 709 luma per column. Column 0 = leftmost (darkest on the
    ramp); column N-1 = rightmost (brightest)."""
    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    w, h = img.size
    col_w = w // _GRID_COLS
    cols: list[float] = []
    for col in range(_GRID_COLS):
        box = (col * col_w, 0, (col + 1) * col_w, h)
        region = img.crop(box)
        r, g, b = region.split()

        def _mean(band: Image.Image) -> float:
            hist = band.histogram()
            total = sum(i * c for i, c in enumerate(hist))
            return total / max(sum(hist), 1)

        cols.append(0.2126 * _mean(r) + 0.7152 * _mean(g) + 0.0722 * _mean(b))
    return cols


def _render_with_spec(
    spec: Mapping[str, object] | None,
    *,
    tmp_path: Path,
    configdir: Path,
    label: str,
    ev: float = 1.0,
) -> list[float]:
    """Render expo+EV through the given mask spec (or no mask if spec is
    None) against the synthetic grayscale ramp. Returns per-column
    luma."""
    vocab = load_packs(["expressive-baseline"])
    expo = vocab.lookup_by_name("exposure")
    assert expo is not None, "expressive-baseline pack missing 'exposure'"

    baseline = parse_xmp(_BASELINE_XMP)
    if spec is None:
        rendered_xmp = apply_entry(baseline, expo, parameter_values={"ev": ev})
    else:
        rendered_xmp = apply_entry(
            baseline,
            expo,
            parameter_values={"ev": ev},
            mask_spec=cast("dict[str, object]", spec),
        )
    xmp_path = tmp_path / f"{label}.xmp"
    out_path = tmp_path / f"{label}.jpg"
    write_xmp(rendered_xmp, xmp_path)
    jpeg = _render(xmp_path, _GRAYSCALE_RAMP, out_path, configdir)
    return _column_luma(jpeg)


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------


def test_parametric_only_luminance_shadows_brightens_dark_columns(
    configdir: Path, darktable_binary: str, tmp_path: Path
) -> None:
    """Parametric-only luminance_range covering shadows (0..0.3) +
    expo+1.0 must brighten the dark side of the ramp more than the
    bright side. Across a left-to-right luminance ramp:
      - Left columns (dark): mask is on → brightened
      - Right columns (bright): mask is off → near-unchanged
    """
    _ = darktable_binary
    _build_workspace(tmp_path, _GRAYSCALE_RAMP, configdir)

    uniform = _render_with_spec(None, tmp_path=tmp_path, configdir=configdir, label="uniform")

    spec = {
        "range_filter": {
            "kind": "luminance",
            "min": 0.0,
            "max": 0.3,
            "feather": 0.05,
        },
    }
    masked = _render_with_spec(spec, tmp_path=tmp_path, configdir=configdir, label="param_shadows")

    delta = [m - u for m, u in zip(masked, uniform, strict=True)]
    print(f"\n  param_shadows vs uniform per-col delta: {[f'{d:+.1f}' for d in delta]}")

    # Dark side (cols 0-1) should be ~0 (mask on, both renders apply
    # expo+1.0 there). Bright side (cols 6-7) should be NEGATIVE
    # (uniform got the lift, masked didn't). Diff = bright - dark
    # is therefore negative — the bright side is more darkened
    # relative to uniform.
    dark_mean = sum(delta[:2]) / 2
    bright_mean = sum(delta[-2:]) / 2
    print(f"  dark_cols mean delta = {dark_mean:+.2f}, bright_cols mean delta = {bright_mean:+.2f}")
    diff = dark_mean - bright_mean
    assert diff > 10.0, (
        f"parametric-only luminance_range shadows must produce a tonal "
        f"signature: dark cells should be closer to 0 (mask on) than "
        f"bright cells (mask off). Got diff = {diff:.2f} (floor 10.0). "
        f"All deltas: {delta}"
    )


def test_drawn_plus_parametric_filters_within_drawn_region(
    configdir: Path, darktable_binary: str, tmp_path: Path
) -> None:
    """The user's mental model: drawn mask + parametric filter =
    intersection. With a centered ellipse mask + a luminance shadows
    range filter, only the DARK pixels INSIDE the ellipse should
    brighten. Bright pixels inside the ellipse and all pixels outside
    the ellipse should be unchanged relative to uniform expo+1.0."""
    _ = darktable_binary
    _build_workspace(tmp_path, _GRAYSCALE_RAMP, configdir)

    uniform = _render_with_spec(None, tmp_path=tmp_path, configdir=configdir, label="uniform")

    # Drawn-only (large centered ellipse covers the middle of the ramp)
    drawn_only_spec = {
        "dt_form": "ellipse",
        "dt_params": {
            "center_x": 0.5,
            "center_y": 0.5,
            "radius_x": 0.45,
            "radius_y": 0.45,
            "border": 0.05,
        },
    }
    drawn_only = _render_with_spec(
        drawn_only_spec, tmp_path=tmp_path, configdir=configdir, label="drawn_only"
    )

    # Drawn + parametric (same ellipse + shadows-only filter)
    composite_spec = {
        **drawn_only_spec,
        "range_filter": {
            "kind": "luminance",
            "min": 0.0,
            "max": 0.4,
            "feather": 0.05,
        },
    }
    composite = _render_with_spec(
        composite_spec, tmp_path=tmp_path, configdir=configdir, label="drawn_and_param"
    )

    drawn_delta = [d - u for d, u in zip(drawn_only, uniform, strict=True)]
    composite_delta = [c - u for c, u in zip(composite, uniform, strict=True)]
    print(f"\n  drawn_only - uniform per-col: {[f'{d:+.1f}' for d in drawn_delta]}")
    print(f"  drawn+param - uniform per-col: {[f'{d:+.1f}' for d in composite_delta]}")

    # Discriminator: in the MIDDLE of the ramp (cols 3-4), where the
    # ellipse is on AND the ramp is mid-to-bright tones, drawn-only
    # shows ~0 delta vs uniform (mask on, both got the lift). drawn+param
    # shows MORE NEGATIVE delta there — the parametric shadows filter
    # excludes those bright pixels even though they're inside the drawn
    # mask. (Cols 6-7 sit OUTSIDE the ellipse so don't show the
    # refinement; the refinement only matters where the drawn mask is on.)
    inside_drawn_only = sum(drawn_delta[3:5]) / 2
    inside_composite = sum(composite_delta[3:5]) / 2
    refinement = inside_drawn_only - inside_composite
    print(
        f"  inside-drawn-bright cols (3-4): drawn_only delta = {inside_drawn_only:+.2f}, "
        f"composite delta = {inside_composite:+.2f}, refinement = {refinement:+.2f}"
    )
    assert refinement > 10.0, (
        f"drawn+parametric should attenuate bright pixels INSIDE the "
        f"drawn mask. Got refinement = {refinement:.2f} (floor 10.0). "
        f"The parametric filter isn't taking effect, or the wire is "
        f"wrong. drawn_only delta: {drawn_delta}, composite delta: "
        f"{composite_delta}"
    )


def test_parametric_invert_flips_the_mask_region(
    configdir: Path, darktable_binary: str, tmp_path: Path
) -> None:
    """range_filter.invert=True should produce the opposite tonal
    pattern from invert=False. Shadows-only-non-inverted brightens
    dark cells; shadows-only-inverted brightens bright cells (the
    inverse selection)."""
    _ = darktable_binary
    _build_workspace(tmp_path, _GRAYSCALE_RAMP, configdir)

    uniform = _render_with_spec(None, tmp_path=tmp_path, configdir=configdir, label="uniform")

    spec_normal = {
        "range_filter": {
            "kind": "luminance",
            "min": 0.0,
            "max": 0.3,
            "feather": 0.05,
            "invert": False,
        },
    }
    spec_inverted = {
        "range_filter": {
            "kind": "luminance",
            "min": 0.0,
            "max": 0.3,
            "feather": 0.05,
            "invert": True,
        },
    }
    normal = _render_with_spec(
        spec_normal, tmp_path=tmp_path, configdir=configdir, label="invert_off"
    )
    inverted = _render_with_spec(
        spec_inverted, tmp_path=tmp_path, configdir=configdir, label="invert_on"
    )

    normal_delta = [n - u for n, u in zip(normal, uniform, strict=True)]
    inverted_delta = [i - u for i, u in zip(inverted, uniform, strict=True)]
    print(f"\n  normal (shadows on) per-col: {[f'{d:+.1f}' for d in normal_delta]}")
    print(f"  inverted (highlights on) per-col: {[f'{d:+.1f}' for d in inverted_delta]}")

    # Normal pattern: dark cells (col 0-1) ≈ 0, bright cells (col 6-7) negative
    # Inverted pattern: dark cells (col 0-1) negative, bright cells (col 6-7) ≈ 0
    normal_dark = sum(normal_delta[:2]) / 2
    normal_bright = sum(normal_delta[-2:]) / 2
    inverted_dark = sum(inverted_delta[:2]) / 2
    inverted_bright = sum(inverted_delta[-2:]) / 2

    # The normal pattern's tonal direction (dark - bright) should be POSITIVE
    # (dark closer to 0 = mask on; bright more negative = mask off).
    # The inverted pattern's tonal direction should be NEGATIVE
    # (dark more negative = mask off; bright closer to 0 = mask on).
    normal_dir = normal_dark - normal_bright
    inverted_dir = inverted_dark - inverted_bright
    print(f"  normal direction (dark-bright) = {normal_dir:+.2f}")
    print(f"  inverted direction (dark-bright) = {inverted_dir:+.2f}")
    assert normal_dir > 5.0, (
        f"non-inverted shadows should brighten dark cells more than "
        f"bright cells; got {normal_dir:.2f}"
    )
    assert inverted_dir < -5.0, (
        f"inverted shadows (= highlights selection) should brighten "
        f"bright cells more than dark cells; got {inverted_dir:.2f}"
    )
