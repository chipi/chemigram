"""Integration test for XMP synthesis using real Phase 0 fixtures.

Loads a real .dtstyle (expo_plus_0p5) and the v3 reference XMP (which
has a user-authored exposure entry at +2.0 EV at multi_priority=0,
num=8). Synthesizes the .dtstyle onto the XMP — the existing exposure
entry should be replaced with the .dtstyle's params (+0.5 EV), with
num and iop_order preserved.
"""

from pathlib import Path

from chemigram.core.dtstyle import parse_dtstyle
from chemigram.core.xmp import parse_xmp, synthesize_xmp

_REPO_ROOT = Path(__file__).resolve().parents[3]
DTSTYLES = _REPO_ROOT / "tests" / "fixtures" / "dtstyles"
XMPS = _REPO_ROOT / "tests" / "fixtures" / "xmps"


def test_real_dtstyle_onto_v3_xmp() -> None:
    baseline = parse_xmp(XMPS / "synthesized_v3_reference.xmp")
    expo_plus = parse_dtstyle(DTSTYLES / "expo_plus_0p5.dtstyle")

    # Sanity on the baseline: v3 has exposure at multi_priority=0 with
    # +2.0 EV (op_params contains "00000040" at the EV float offset).
    baseline_exposure = next(
        h for h in baseline.history if h.operation == "exposure" and h.multi_priority == 0
    )
    assert baseline_exposure.num == 8
    assert "00000040" in baseline_exposure.params

    result = synthesize_xmp(baseline, [expo_plus])

    # All 11 entries preserved (no Path B add)
    assert len(result.history) == len(baseline.history) == 11

    # The exposure slot now carries +0.5 EV from the dtstyle (params
    # contain "0000003f" at the float offset)
    new_exposure = next(
        h for h in result.history if h.operation == "exposure" and h.multi_priority == 0
    )
    assert new_exposure.params == expo_plus.plugins[0].op_params
    assert "0000003f" in new_exposure.params

    # SET-replace preserves num and iop_order from the baseline slot
    assert new_exposure.num == baseline_exposure.num
    assert new_exposure.iop_order == baseline_exposure.iop_order

    # Top-level metadata is preserved verbatim
    assert result.rating == baseline.rating
    assert result.history_end == baseline.history_end
    assert result.iop_order_version == baseline.iop_order_version
    assert result.raw_extra_fields == baseline.raw_extra_fields
