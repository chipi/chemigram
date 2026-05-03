"""E2E: the 4 mask-bound expressive-baseline entries actually shape the
rendered effect under real darktable. Closes #74 + #75 (path 4a).

For each entry:
  1. Load the entry from the expressive-baseline pack.
  2. Apply via apply_with_drawn_mask (the same path apply_primitive uses
     when entry.mask_kind=='drawn' and mask_spec is set).
  3. Render. Compare to a uniform render (same dtstyle, no mask).
  4. Assert spatial variance vs uniform — the mask must shape the effect.

Distinct from test_drawn_mask_shapes_effect.py which uses an ad-hoc
spec; this one exercises the actual shipped manifest entries.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from chemigram.core.helpers import apply_with_drawn_mask
from chemigram.core.pipeline import render
from chemigram.core.versioning import ImageRepo
from chemigram.core.versioning.ops import snapshot
from chemigram.core.vocab import VocabularyIndex
from chemigram.core.workspace import Workspace, init_workspace_root
from chemigram.core.xmp import parse_xmp, synthesize_xmp, write_xmp

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BASELINE_XMP = _REPO_ROOT / "src" / "chemigram" / "core" / "_baseline_v1.xmp"
_EXPRESSIVE_PACK = _REPO_ROOT / "vocabulary" / "packs" / "expressive-baseline"

MASKED_ENTRY_NAMES = (
    "gradient_top_dampen_highlights",
    "gradient_bottom_lift_shadows",
    "radial_subject_lift",
    "rectangle_subject_band_dim",
)


@pytest.fixture(scope="module")
def expressive_index() -> VocabularyIndex:
    return VocabularyIndex(_EXPRESSIVE_PACK)


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
        width=384,
        height=384,
        high_quality=False,
        configdir=configdir,
    )
    assert result.success, (
        f"darktable-cli failed: {result.error_message}\n"
        f"stderr (last 1000 chars): {result.stderr[-1000:]}"
    )
    return out_path.read_bytes()


def _abs_diff(a_bytes: bytes, b_bytes: bytes) -> tuple[float, int, float]:
    a_img = Image.open(io.BytesIO(a_bytes)).convert("L").tobytes()
    b_img = Image.open(io.BytesIO(b_bytes)).convert("L").tobytes()
    diffs = [abs(x - y) for x, y in zip(a_img, b_img, strict=True)]
    n = len(diffs)
    mean = sum(diffs) / n
    var = sum((d - mean) ** 2 for d in diffs) / n
    return mean, max(diffs), var**0.5


@pytest.mark.parametrize("entry_name", MASKED_ENTRY_NAMES)
def test_entry_mask_shapes_effect(
    entry_name: str,
    expressive_index: VocabularyIndex,
    test_raw: Path,
    configdir: Path,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """For each mask-bound entry: the masked render's pixel diff vs a
    same-dtstyle uniform render must have spatial variance > rendering
    noise floor — proving the entry's mask_spec is materialized into a
    real darktable form that shapes the effect spatially."""
    _ = darktable_binary
    ws = _build_workspace(tmp_path, test_raw, configdir)
    baseline_xmp = parse_xmp(_BASELINE_XMP)
    entry = expressive_index.lookup_by_name(entry_name)
    assert entry is not None
    assert entry.mask_kind == "drawn"
    assert entry.mask_spec is not None

    # Uniform: synthesize without the mask
    uniform = synthesize_xmp(baseline_xmp, [entry.dtstyle])
    u_xmp_path = tmp_path / f"{entry_name}_uniform.xmp"
    u_out = tmp_path / f"{entry_name}_uniform.jpg"
    write_xmp(uniform, u_xmp_path)
    u_bytes = _render(u_xmp_path, ws.raw_path, u_out, configdir)

    # Masked: apply_with_drawn_mask using the entry's spec
    masked = apply_with_drawn_mask(baseline_xmp, entry.dtstyle, entry.mask_spec)
    m_xmp_path = tmp_path / f"{entry_name}_masked.xmp"
    m_out = tmp_path / f"{entry_name}_masked.jpg"
    write_xmp(masked, m_xmp_path)
    m_bytes = _render(m_xmp_path, ws.raw_path, m_out, configdir)

    # Second uniform render — defines the noise floor
    u2_out = tmp_path / f"{entry_name}_uniform2.jpg"
    u2_bytes = _render(u_xmp_path, ws.raw_path, u2_out, configdir)

    _noise_mean, noise_max, noise_std = _abs_diff(u_bytes, u2_bytes)
    _masked_mean, masked_max, masked_std = _abs_diff(u_bytes, m_bytes)

    # The mask must produce both elevated max diff AND elevated spatial variance.
    assert masked_max > noise_max + 5, (
        f"{entry_name}: masked max diff {masked_max} must exceed noise max "
        f"{noise_max} by >5; got {masked_max - noise_max}. The mask isn't "
        f"reaching darktable's blendop."
    )
    assert masked_std > noise_std + 0.5, (
        f"{entry_name}: masked diff std {masked_std:.3f} must exceed noise "
        f"std {noise_std:.3f} by >0.5; got {masked_std - noise_std:.3f}. "
        f"The mask isn't shaping spatially."
    )
