"""End-to-end: build-by-words mask shapes (RFC-029 / ADR-084) produce
the spatial signature their phrase claims when rendered by darktable.

Sister to ``test_drawn_mask_shapes_effect.py``: that one proves *some*
mask shapes the effect (spatial variance discriminator); this one
proves the *named* mask shapes from
``docs/guides/mask-shapes-from-words.md`` shape the effect *in the
expected region*. "Bottom third" must brighten the bottom; "left
half" must brighten the left; "center circle medium" must brighten
the center vs corners.

The discriminating signal: render expo +1.0 through each named mask,
divide the rendered output into a 4x4 grid, compute mean luma per
cell, and assert the cells in the masked region are brighter than
the cells outside.

This catches the failure mode where the encoder produces valid bytes
but the *parameters* for a given phrase are wrong (wrong rotation,
wrong anchor, wrong sign convention) — the lint test in
``tests/unit/core/masking/test_mask_shapes_from_words_guide.py``
verifies bytes; this verifies meaning.
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

# A "loud" effect makes the spatial signature unmistakable. expo+1.0
# brightens by ~1 stop where the mask is on; off the mask, baseline
# luma. The 4x4 grid means we can compare cells with a 32-pixel
# minimum (at 128x128 render). Larger renders give cleaner signals
# but cost more time per case.
_RENDER_SIZE = 256
_GRID_ROWS = 4
_GRID_COLS = 4
# Spatial-signature floor: the minimum luma-delta diff between
# masked-region cells and unmasked-region cells in the (masked -
# uniform) grid. Floor must be:
# - Above darktable rendering noise (~3-5 luma in this config)
# - Strict enough to catch sign flips (rotation 0 vs 180, etc.) —
#   a flipped sign produces NEGATIVE delta_diff, which fails loudly
# - Loose enough that "half" masks (gradual sigmoidal transition
#   over the full image) still pass — those produce diffs around
#   8-12, smaller than "third" / "circle" masks which hit 30+
_DELTA_FLOOR = 10.0


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


def _luma_grid(jpeg_bytes: bytes) -> list[list[float]]:
    """Divide image into ``_GRID_ROWS x _GRID_COLS`` cells; return mean
    luma per cell (Rec. 709). Cells indexed [row][col]; row 0 = top,
    col 0 = left."""
    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    w, h = img.size
    cell_w = w // _GRID_COLS
    cell_h = h // _GRID_ROWS
    grid: list[list[float]] = []
    for row in range(_GRID_ROWS):
        row_cells: list[float] = []
        for col in range(_GRID_COLS):
            box = (col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h)
            cell = img.crop(box)
            r, g, b = cell.split()

            def _mean(band: Image.Image) -> float:
                hist = band.histogram()
                total = sum(i * c for i, c in enumerate(hist))
                n = sum(hist)
                return total / max(n, 1)

            luma = 0.2126 * _mean(r) + 0.7152 * _mean(g) + 0.0722 * _mean(b)
            row_cells.append(luma)
        grid.append(row_cells)
    return grid


def _row_means(grid: list[list[float]]) -> list[float]:
    return [sum(r) / len(r) for r in grid]


def _col_means(grid: list[list[float]]) -> list[float]:
    cols = list(zip(*grid, strict=True))
    return [sum(c) / len(c) for c in cols]


def _render_uniform_exposure(
    *, tmp_path: Path, raw_path: Path, configdir: Path, ev: float = 1.0
) -> list[list[float]]:
    """Render the parameterized exposure entry at the given EV with NO
    mask — the effect applies uniformly everywhere. This is the
    reference for the masked-vs-uniform diff: cells inside the mask
    have ~0 delta vs uniform; cells outside have negative delta
    (uniform was lifted, masked wasn't)."""
    vocab = load_packs(["expressive-baseline"])
    expo = vocab.lookup_by_name("exposure")
    assert expo is not None, "expressive-baseline pack missing 'exposure' entry"

    baseline = parse_xmp(_BASELINE_XMP)
    uniform_xmp = apply_entry(baseline, expo, parameter_values={"ev": ev})
    xmp_path = tmp_path / "uniform.xmp"
    out_path = tmp_path / "uniform.jpg"
    write_xmp(uniform_xmp, xmp_path)
    jpeg = _render(xmp_path, raw_path, out_path, configdir)
    return _luma_grid(jpeg)


def _render_with_mask(
    spec: Mapping[str, object],
    *,
    tmp_path: Path,
    raw_path: Path,
    configdir: Path,
    label: str,
    ev: float = 1.0,
) -> list[list[float]]:
    """Render the parameterized exposure entry at the given EV through
    the given mask spec; return its luma grid."""
    vocab = load_packs(["expressive-baseline"])
    expo = vocab.lookup_by_name("exposure")
    assert expo is not None, "expressive-baseline pack missing 'exposure' entry"

    baseline = parse_xmp(_BASELINE_XMP)
    masked_xmp = apply_entry(
        baseline,
        expo,
        parameter_values={"ev": ev},
        mask_spec=cast("dict[str, object]", spec),
    )
    xmp_path = tmp_path / f"{label}.xmp"
    out_path = tmp_path / f"{label}.jpg"
    write_xmp(masked_xmp, xmp_path)
    jpeg = _render(xmp_path, raw_path, out_path, configdir)
    return _luma_grid(jpeg)


def _delta_grid(masked: list[list[float]], reference: list[list[float]]) -> list[list[float]]:
    """Per-cell luma delta (masked - reference). Used as masked vs
    uniform: cells inside the mask have delta ≈ 0 (effect applied in
    both); cells outside the mask have negative delta (reference was
    lifted, masked was not). The spatial pattern of *less negative*
    deltas reveals the mask's region."""
    return [
        [m - r for m, r in zip(mr, rr, strict=True)]
        for mr, rr in zip(masked, reference, strict=True)
    ]


# ---------------------------------------------------------------------
# Spatial-signature tests, one per representative phrase
# ---------------------------------------------------------------------


def test_bottom_third_gradient_brightens_bottom_rows(
    test_raw: Path, configdir: Path, darktable_binary: str, tmp_path: Path
) -> None:
    """The "bottom third" gradient (anchor_y=0.67, rotation=0) must
    brighten the bottom of the rendered image more than the top
    (relative to baseline), proving anchor_y + rotation produce
    a bottom-light gradient."""
    _ = darktable_binary
    _build_workspace(tmp_path, test_raw, configdir)

    reference = _render_uniform_exposure(tmp_path=tmp_path, raw_path=test_raw, configdir=configdir)

    spec = {
        "dt_form": "gradient",
        "dt_params": {
            "anchor_x": 0.5,
            "anchor_y": 0.67,
            "rotation": 180.0,
            "compression": 0.5,
            "state": 2,
        },
    }
    masked = _render_with_mask(
        spec, tmp_path=tmp_path, raw_path=test_raw, configdir=configdir, label="bottom_third"
    )
    delta = _delta_grid(masked, reference)
    delta_rows = _row_means(delta)

    # Bottom row delta vs top row delta — bottom should be brightened MORE
    delta_diff = delta_rows[-1] - delta_rows[0]
    print(
        f"\n  bottom_third: per-row mask delta = {[f'{r:+.1f}' for r in delta_rows]}, "
        f"bot-top delta = {delta_diff:+.2f}"
    )
    assert delta_diff > _DELTA_FLOOR, (
        f"'bottom third' gradient should brighten bottom rows MORE than "
        f"top rows; got bot-top mask-delta diff = {delta_diff:.2f} "
        f"(floor: {_DELTA_FLOOR}). Likely cause: rotation sign convention "
        f"wrong, or anchor_y interpretation flipped. Per-row deltas: "
        f"{delta_rows}"
    )


def test_top_half_gradient_brightens_top_rows(
    test_raw: Path, configdir: Path, darktable_binary: str, tmp_path: Path
) -> None:
    """The "top half" gradient (anchor_y=0.5, rotation=180) must
    brighten the top of the rendered image more than the bottom."""
    _ = darktable_binary
    _build_workspace(tmp_path, test_raw, configdir)

    reference = _render_uniform_exposure(tmp_path=tmp_path, raw_path=test_raw, configdir=configdir)

    spec = {
        "dt_form": "gradient",
        "dt_params": {
            "anchor_x": 0.5,
            "anchor_y": 0.5,
            "rotation": 0.0,
            "compression": 0.5,
            "state": 2,
        },
    }
    masked = _render_with_mask(
        spec, tmp_path=tmp_path, raw_path=test_raw, configdir=configdir, label="top_half"
    )
    delta = _delta_grid(masked, reference)
    delta_rows = _row_means(delta)

    delta_diff = delta_rows[0] - delta_rows[-1]
    print(
        f"\n  top_half: per-row mask delta = {[f'{r:+.1f}' for r in delta_rows]}, "
        f"top-bot delta = {delta_diff:+.2f}"
    )
    assert delta_diff > _DELTA_FLOOR, (
        f"'top half' gradient should brighten top rows MORE than bottom "
        f"rows; got top-bot mask-delta diff = {delta_diff:.2f} "
        f"(floor: {_DELTA_FLOOR}). Per-row deltas: {delta_rows}"
    )


def test_left_half_gradient_brightens_left_columns(
    test_raw: Path, configdir: Path, darktable_binary: str, tmp_path: Path
) -> None:
    """The "left half" gradient (rotation=90) must brighten the left
    columns more than the right columns."""
    _ = darktable_binary
    _build_workspace(tmp_path, test_raw, configdir)

    reference = _render_uniform_exposure(tmp_path=tmp_path, raw_path=test_raw, configdir=configdir)

    spec = {
        "dt_form": "gradient",
        "dt_params": {
            "anchor_x": 0.5,
            "anchor_y": 0.5,
            "rotation": 90.0,
            "compression": 0.5,
            "state": 2,
        },
    }
    masked = _render_with_mask(
        spec, tmp_path=tmp_path, raw_path=test_raw, configdir=configdir, label="left_half"
    )
    delta = _delta_grid(masked, reference)
    delta_cols = _col_means(delta)

    delta_diff = delta_cols[0] - delta_cols[-1]
    print(
        f"\n  left_half: per-col mask delta = {[f'{c:+.1f}' for c in delta_cols]}, "
        f"left-right delta = {delta_diff:+.2f}"
    )
    assert delta_diff > _DELTA_FLOOR, (
        f"'left half' gradient should brighten left columns MORE than "
        f"right columns; got left-right mask-delta diff = {delta_diff:.2f} "
        f"(floor: {_DELTA_FLOOR}). Likely cause: rotation 90 vs 270 "
        f"confusion (wrong light side). Per-col deltas: {delta_cols}"
    )


def test_center_circle_medium_brightens_center_vs_corners(
    test_raw: Path, configdir: Path, darktable_binary: str, tmp_path: Path
) -> None:
    """The "center circle medium" ellipse (radius 0.3) must brighten
    the center cells more than the corner cells."""
    _ = darktable_binary
    _build_workspace(tmp_path, test_raw, configdir)

    reference = _render_uniform_exposure(tmp_path=tmp_path, raw_path=test_raw, configdir=configdir)

    spec = {
        "dt_form": "ellipse",
        "dt_params": {
            "center_x": 0.5,
            "center_y": 0.5,
            "radius_x": 0.3,
            "radius_y": 0.3,
            "border": 0.08,
        },
    }
    masked = _render_with_mask(
        spec,
        tmp_path=tmp_path,
        raw_path=test_raw,
        configdir=configdir,
        label="center_circle_medium",
    )
    delta = _delta_grid(masked, reference)

    center_cells = [delta[1][1], delta[1][2], delta[2][1], delta[2][2]]
    corner_cells = [delta[0][0], delta[0][3], delta[3][0], delta[3][3]]
    center_mean = sum(center_cells) / 4
    corner_mean = sum(corner_cells) / 4
    delta_diff = center_mean - corner_mean

    print(
        f"\n  center_circle_medium: center mask-delta mean = {center_mean:+.2f}, "
        f"corner mask-delta mean = {corner_mean:+.2f}, diff = {delta_diff:+.2f}"
    )
    assert delta_diff > _DELTA_FLOOR, (
        f"'center circle medium' ellipse should brighten center MORE than "
        f"corners; got center-corner mask-delta diff = {delta_diff:.2f} "
        f"(floor: {_DELTA_FLOOR}). Likely cause: center_x/center_y sign or "
        f"radius interpretation wrong. center deltas: {center_cells}, "
        f"corner deltas: {corner_cells}"
    )


def test_path_polygon_centered_triangle_brightens_center(
    test_raw: Path, configdir: Path, darktable_binary: str, tmp_path: Path
) -> None:
    """A 3-vertex path forming a centered triangle must brighten the
    center region MORE than the corners. Validates the path-shape
    branch (RFC-026 substrate surfaced via RFC-029) end-to-end
    through darktable, not just the byte encoder."""
    _ = darktable_binary
    _build_workspace(tmp_path, test_raw, configdir)

    reference = _render_uniform_exposure(tmp_path=tmp_path, raw_path=test_raw, configdir=configdir)

    spec = {
        "dt_form": "path",
        "dt_params": {
            "vertices": [
                [0.5, 0.2],  # top center
                [0.8, 0.7],  # bottom right
                [0.2, 0.7],  # bottom left
            ],
            "border": 0.04,
        },
    }
    masked = _render_with_mask(
        spec, tmp_path=tmp_path, raw_path=test_raw, configdir=configdir, label="path_triangle"
    )
    delta = _delta_grid(masked, reference)

    center_cells = [delta[1][1], delta[1][2], delta[2][1], delta[2][2]]
    corner_cells = [delta[0][0], delta[0][3], delta[3][0], delta[3][3]]
    center_mean = sum(center_cells) / 4
    corner_mean = sum(corner_cells) / 4
    delta_diff = center_mean - corner_mean

    print(
        f"\n  path_triangle: center mask-delta mean = {center_mean:+.2f}, "
        f"corner mask-delta mean = {corner_mean:+.2f}, diff = {delta_diff:+.2f}"
    )
    # Triangle covers a smaller fraction of the center 2x2 cells than
    # an ellipse does, so we soften the floor.
    assert delta_diff > _DELTA_FLOOR / 2, (
        f"path-form triangle should brighten center MORE than corners; "
        f"got center-corner mask-delta diff = {delta_diff:.2f} "
        f"(floor: {_DELTA_FLOOR / 2}). Likely cause: path-form encoder "
        f"bug, or schema enum still missing 'path'. center deltas: "
        f"{center_cells}, corner deltas: {corner_cells}"
    )
