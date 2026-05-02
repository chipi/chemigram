"""End-to-end: synthesizer Path B drives darktable to a different render.

Closes the loop on the Path B unblock (RFC-018, issue #44):
``synthesize_xmp`` now appends new-instance entries; this test proves the
appended entry produces a measurably different rendered image vs the
baseline. Pairs with the empirical evidence in
``tests/fixtures/preflight-evidence/`` — the raw bash test there proves
darktable accepts iop-order-less Path B XMPs; this test proves the
*synthesizer* produces such XMPs correctly when fed a vocabulary entry
whose ``(operation, multi_priority)`` is absent from the baseline.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from chemigram.core.dtstyle import DtstyleEntry, PluginEntry
from chemigram.core.pipeline import render
from chemigram.core.xmp import parse_xmp, synthesize_xmp, write_xmp

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINE_XMP = _REPO_ROOT / "src" / "chemigram" / "core" / "_baseline_v1.xmp"

# A real grain plugin op_params blob — same one validated in the
# preflight-evidence shell script. Module not in the bundled baseline.
_GRAIN_PARAMS = "0000a040000080400000a043"


def _band_mean(band: Image.Image) -> float:
    hist = band.histogram()
    return sum(i * c for i, c in enumerate(hist)) / max(sum(hist), 1)


def _luma(jpeg_bytes: bytes) -> float:
    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    r, g, b = img.split()
    return 0.2126 * _band_mean(r) + 0.7152 * _band_mean(g) + 0.0722 * _band_mean(b)


def _make_grain_entry() -> DtstyleEntry:
    """Synthetic grain dtstyle entry — sidesteps fixture authoring.
    The op_params bytes are real (from the preflight evidence script);
    the wrapping DtstyleEntry shape is the same as a parsed file."""
    plugin = PluginEntry(
        operation="grain",
        num=0,
        module=1,  # darktable 5.4.1's grain modversion
        op_params=_GRAIN_PARAMS,
        blendop_params="",
        blendop_version=14,
        multi_priority=0,
        multi_name="",
        enabled=True,
    )
    return DtstyleEntry(
        name="grain_pathb_test",
        description="grain Path B test",
        iop_list=None,
        plugins=(plugin,),
    )


def test_synthesizer_path_b_grain_appends_and_renders(
    test_raw: Path,
    configdir: Path,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """Synthesize ``grain`` (Path B) onto the bundled baseline, render
    via real darktable, assert the output differs from a baseline-only
    render. Catches regressions in: the synthesizer's append branch,
    the iop_order=None bypass, the history_end recompute, the on-disk
    XMP write, or darktable's pipeline-order resolution.
    """
    _ = darktable_binary
    baseline = parse_xmp(_BASELINE_XMP)

    # Render baseline alone
    baseline_xmp_path = tmp_path / "baseline.xmp"
    write_xmp(baseline, baseline_xmp_path)
    baseline_jpg = tmp_path / "baseline.jpg"
    r1 = render(
        raw_path=test_raw,
        xmp_path=baseline_xmp_path,
        output_path=baseline_jpg,
        width=512,
        height=512,
        high_quality=False,
        configdir=configdir,
    )
    assert r1.success, f"baseline render failed: {r1.error_message}"

    # Synthesize Path B and render
    synthesized = synthesize_xmp(baseline, [_make_grain_entry()])
    # Sanity: synthesize did append (history grew by 1)
    assert len(synthesized.history) == len(baseline.history) + 1
    appended = synthesized.history[-1]
    assert appended.operation == "grain"
    assert appended.iop_order is None
    assert synthesized.history_end == len(synthesized.history)

    pathb_xmp_path = tmp_path / "pathb.xmp"
    write_xmp(synthesized, pathb_xmp_path)
    pathb_jpg = tmp_path / "pathb.jpg"
    r2 = render(
        raw_path=test_raw,
        xmp_path=pathb_xmp_path,
        output_path=pathb_jpg,
        width=512,
        height=512,
        high_quality=False,
        configdir=configdir,
    )
    assert r2.success, f"path-b render failed: {r2.error_message}"

    # The grain-applied render must differ from baseline. Identical bytes
    # would mean darktable silently dropped the entry — the failure mode
    # the empirical preflight evidence ruled out, but worth re-asserting
    # on the synthesizer's specific output.
    baseline_bytes = baseline_jpg.read_bytes()
    pathb_bytes = pathb_jpg.read_bytes()
    assert baseline_bytes != pathb_bytes, (
        "Path B render is byte-identical to baseline; darktable may have "
        "dropped the appended grain entry, or the synthesizer's append "
        "branch isn't producing a valid XMP."
    )

    # Bonus sanity: both images render valid bytes.
    assert _luma(baseline_bytes) > 5
    assert _luma(pathb_bytes) > 5
