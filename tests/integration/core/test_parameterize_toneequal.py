"""Integration: parameterized toneequalizer (9-band) apply path.

The most complex multi-parameter ship — exercises the apply path's
per-module value grouping with 9 independently-patchable axes.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.toneequalizer import _NODE_FIELDS, decode
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp, write_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def toneequalizer_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("toneequalizer")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 9, "toneequalizer ships 9 parameterized axes"
    return entry


@pytest.mark.parametrize(
    "node_name,value",
    [
        ("noise", -0.5),
        ("ultra_deep_blacks", 0.3),
        ("deep_blacks", -0.7),
        ("blacks", 0.4),
        ("shadows", 0.8),
        ("midtones", -0.2),
        ("highlights", -0.6),
        ("whites", 1.0),
        ("speculars", -1.5),
    ],
)
def test_apply_entry_single_node_patches_op_params(
    baseline_xmp, toneequalizer_entry, node_name: str, value: float
) -> None:
    new_xmp = apply_entry(baseline_xmp, toneequalizer_entry, parameter_values={node_name: value})
    plugins = [p for p in new_xmp.history if p.operation == "toneequal"]
    assert plugins
    fields = decode(plugins[-1].params)
    target_idx, _ = _NODE_FIELDS[node_name]
    assert fields[target_idx] == pytest.approx(value, abs=1e-5)
    # Other 8 nodes at default 0.0
    for name in _NODE_FIELDS:
        if name == node_name:
            continue
        idx, _ = _NODE_FIELDS[name]
        assert fields[idx] == pytest.approx(0.0, abs=1e-5)


def test_apply_entry_full_curve_patches_all_nodes(baseline_xmp, toneequalizer_entry) -> None:
    """Apply a synthetic s-curve across all 9 nodes simultaneously."""
    s_curve = {
        "noise": -0.8,
        "ultra_deep_blacks": -0.6,
        "deep_blacks": -0.4,
        "blacks": -0.2,
        "shadows": 0.0,
        "midtones": 0.2,
        "highlights": 0.4,
        "whites": 0.6,
        "speculars": 0.8,
    }
    new_xmp = apply_entry(baseline_xmp, toneequalizer_entry, parameter_values=s_curve)
    plugins = [p for p in new_xmp.history if p.operation == "toneequal"]
    assert plugins
    fields = decode(plugins[-1].params)
    for name, target in s_curve.items():
        idx, _ = _NODE_FIELDS[name]
        assert fields[idx] == pytest.approx(target, abs=1e-5), f"node {name}"


def test_apply_entry_partial_update_two_nodes(baseline_xmp, toneequalizer_entry) -> None:
    """Caller can supply just shadows + highlights — other 7 at default 0.0."""
    new_xmp = apply_entry(
        baseline_xmp,
        toneequalizer_entry,
        parameter_values={"shadows": 0.7, "highlights": -0.3},
    )
    plugins = [p for p in new_xmp.history if p.operation == "toneequal"]
    assert plugins
    fields = decode(plugins[-1].params)
    shadows_idx, _ = _NODE_FIELDS["shadows"]
    highlights_idx, _ = _NODE_FIELDS["highlights"]
    assert fields[shadows_idx] == pytest.approx(0.7, abs=1e-5)
    assert fields[highlights_idx] == pytest.approx(-0.3, abs=1e-5)
    # Other 7 nodes at default
    for name in (
        "noise",
        "ultra_deep_blacks",
        "deep_blacks",
        "blacks",
        "midtones",
        "whites",
        "speculars",
    ):
        idx, _ = _NODE_FIELDS[name]
        assert fields[idx] == pytest.approx(0.0, abs=1e-5)


def test_apply_entry_round_trips_through_xmp_writer(
    baseline_xmp, toneequalizer_entry, tmp_path: Path
) -> None:
    new_xmp = apply_entry(
        baseline_xmp,
        toneequalizer_entry,
        parameter_values={"shadows": 0.5, "highlights": -0.5, "midtones": 0.1},
    )
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)
    text = out_path.read_text()
    matches = re.findall(
        r'darktable:operation="toneequal"[^/]*?darktable:params="([0-9a-f]+)"', text
    )
    assert matches
    fields = decode(matches[-1])
    shadows_idx, _ = _NODE_FIELDS["shadows"]
    highlights_idx, _ = _NODE_FIELDS["highlights"]
    midtones_idx, _ = _NODE_FIELDS["midtones"]
    assert fields[shadows_idx] == pytest.approx(0.5, abs=1e-5)
    assert fields[highlights_idx] == pytest.approx(-0.5, abs=1e-5)
    assert fields[midtones_idx] == pytest.approx(0.1, abs=1e-5)


def test_apply_entry_no_values_uses_dtstyle_default(baseline_xmp, toneequalizer_entry) -> None:
    """All 9 nodes at default 0.0 → no-op tone shift."""
    new_xmp = apply_entry(baseline_xmp, toneequalizer_entry)
    plugins = [p for p in new_xmp.history if p.operation == "toneequal"]
    assert plugins
    fields = decode(plugins[-1].params)
    for name in _NODE_FIELDS:
        idx, _ = _NODE_FIELDS[name]
        assert fields[idx] == pytest.approx(0.0, abs=1e-5)
