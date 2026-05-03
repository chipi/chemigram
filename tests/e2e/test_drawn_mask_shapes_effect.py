"""End-to-end: drawn-mask XMP serialization (path 4a) actually shapes
the rendered effect under real darktable.

Distinct from ``test_mask_shaping.py`` which uses the legacy PNG-file
path that was discovered (in v1.4.0 follow-up) to not actually wire to
darktable's masking system. That test passes for the wrong reason —
scene asymmetry in the Phase 0 raw, not real masking.

This test uses the new ``apply_with_drawn_mask`` helper that injects a
real darktable drawn form into ``<darktable:masks_history>`` and patches
``blendop_params.mask_id``. The discriminating signal: when C is the
masked render and B is the uniform render, the pixel-by-pixel
difference ``C - B`` must NOT be spatially uniform — at the mask peak,
``C ≈ B`` (effect fully applied); at the mask edge / off, ``C ≠ B``
(effect attenuated or absent).

A uniform render with no mask binding produces ``C - B`` that's flat
across the image (just rendering noise). A masked render produces
``C - B`` with high spatial variance.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from chemigram.core.helpers import apply_with_drawn_mask
from chemigram.core.pipeline import render
from chemigram.core.versioning import ImageRepo
from chemigram.core.versioning.ops import snapshot
from chemigram.core.vocab import load_starter
from chemigram.core.workspace import Workspace, init_workspace_root
from chemigram.core.xmp import parse_xmp, synthesize_xmp, write_xmp

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINE_XMP = _REPO_ROOT / "src" / "chemigram" / "core" / "_baseline_v1.xmp"


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
        width=512,
        height=512,
        high_quality=False,
        configdir=configdir,
    )
    assert result.success, (
        f"darktable-cli failed: {result.error_message}\n"
        f"stderr (last 1000 chars): {result.stderr[-1000:]}"
    )
    return out_path.read_bytes()


def _pixel_grid(jpeg_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(jpeg_bytes)).convert("L")


def _abs_diff_stats(img_a: Image.Image, img_b: Image.Image) -> tuple[float, float, float]:
    """Return (mean_diff, max_diff, std_diff) of |a-b| over all pixels."""
    a_bytes = img_a.tobytes()
    b_bytes = img_b.tobytes()
    diffs = [abs(a - b) for a, b in zip(a_bytes, b_bytes, strict=True)]
    n = len(diffs)
    mean = sum(diffs) / n
    max_d = max(diffs)
    var = sum((d - mean) ** 2 for d in diffs) / n
    return mean, float(max_d), var**0.5


def test_drawn_mask_creates_spatial_variance_vs_uniform(
    test_raw: Path, configdir: Path, darktable_binary: str, tmp_path: Path
) -> None:
    """Discriminating test: a masked render's ``C - B`` (vs uniform B)
    must have HIGH spatial variance (mask shapes the effect spatially),
    while a uniform-vs-uniform render's diff has near-zero variance
    (just darktable rendering noise)."""
    _ = darktable_binary
    ws = _build_workspace(tmp_path, test_raw, configdir)
    baseline_xmp = parse_xmp(_BASELINE_XMP)

    expo = load_starter().lookup_by_name("expo_+0.5")
    assert expo is not None
    expo_dtstyle = expo.dtstyle

    # B: uniform expo_+0.5 applied (no mask, replaces baseline's exposure)
    b_xmp = synthesize_xmp(baseline_xmp, [expo_dtstyle])
    b_xmp_path = tmp_path / "b.xmp"
    b_out = tmp_path / "b.jpg"
    write_xmp(b_xmp, b_xmp_path)
    b_bytes = _render(b_xmp_path, ws.raw_path, b_out, configdir)
    b_img = _pixel_grid(b_bytes)

    # C: same expo_+0.5 with a small ellipse mask in upper-left
    spec = {
        "dt_form": "ellipse",
        "dt_params": {
            "center_x": 0.25,
            "center_y": 0.3,
            "radius_x": 0.1,
            "radius_y": 0.1,
            "border": 0.05,
        },
    }
    c_xmp = apply_with_drawn_mask(baseline_xmp, expo_dtstyle, spec)
    c_xmp_path = tmp_path / "c.xmp"
    c_out = tmp_path / "c.jpg"
    write_xmp(c_xmp, c_xmp_path)
    c_bytes = _render(c_xmp_path, ws.raw_path, c_out, configdir)
    c_img = _pixel_grid(c_bytes)

    # B': second uniform render — diff with B is the noise floor
    b2_xmp_path = tmp_path / "b2.xmp"
    b2_out = tmp_path / "b2.jpg"
    write_xmp(b_xmp, b2_xmp_path)
    b2_bytes = _render(b2_xmp_path, ws.raw_path, b2_out, configdir)
    b2_img = _pixel_grid(b2_bytes)

    noise_mean, noise_max, noise_std = _abs_diff_stats(b_img, b2_img)
    masked_mean, masked_max, masked_std = _abs_diff_stats(b_img, c_img)

    print(
        f"\n  B vs B' (rendering noise floor): mean={noise_mean:.3f} "
        f"max={noise_max:.0f} std={noise_std:.3f}\n"
        f"  B vs C (masked vs uniform):     mean={masked_mean:.3f} "
        f"max={masked_max:.0f} std={masked_std:.3f}"
    )

    # The mask must produce a max diff substantially above the noise floor.
    # If darktable ignored the mask (or applied it at full strength
    # everywhere), C ≈ B and masked_max would equal noise_max.
    assert masked_max > noise_max + 5, (
        f"masked render max diff ({masked_max:.0f}) must exceed noise "
        f"floor max ({noise_max:.0f}) by > 5; got {masked_max - noise_max:.0f}. "
        "The mask isn't actually shaping the effect in darktable."
    )

    # Spatial variance of the diff must also be substantially above noise.
    # If C and B differ by a uniform offset, std would be near noise; for
    # a real mask, the diff varies spatially.
    assert masked_std > noise_std + 1, (
        f"masked diff std ({masked_std:.3f}) must exceed noise std "
        f"({noise_std:.3f}) by > 1; got {masked_std - noise_std:.3f}. "
        "The mask is producing a spatially-uniform offset, not a shape."
    )
