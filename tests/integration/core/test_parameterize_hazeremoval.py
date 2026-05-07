"""Integration: parameterized dehaze (hazeremoval) apply path.

Closes #90 Bucket A.2 — Lightroom Dehaze parity. Two axes (strength,
distance) routed through the parameterize registry; apply path must
preserve compatibility_mode and adaptive flags.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.hazeremoval import (
    _DISTANCE_FIELD_INDEX,
    _STRENGTH_FIELD_INDEX,
    decode,
)
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp, write_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def dehaze_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("dehaze")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 2, "dehaze multi-axis: expected 2 params (strength, distance)"
    return entry


@pytest.mark.parametrize(
    "values",
    [
        {"strength": 0.6},
        {"strength": -0.4},  # negative → adds atmospheric haze
        {"distance": 0.5},
        {"strength": 0.7, "distance": 0.4},
        {"strength": 0.2, "distance": 0.2},  # darktable defaults
    ],
)
def test_apply_entry_with_multi_param_patches_op_params(
    baseline_xmp, dehaze_entry, values: dict
) -> None:
    new_xmp = apply_entry(baseline_xmp, dehaze_entry, parameter_values=values)
    plugins = [p for p in new_xmp.history if p.operation == "hazeremoval"]
    assert plugins
    fields = decode(plugins[-1].params)
    if "strength" in values:
        assert fields[_STRENGTH_FIELD_INDEX] == pytest.approx(values["strength"], abs=1e-5)
    if "distance" in values:
        assert fields[_DISTANCE_FIELD_INDEX] == pytest.approx(values["distance"], abs=1e-5)


def test_apply_entry_round_trips_through_xmp_writer(
    baseline_xmp, dehaze_entry, tmp_path: Path
) -> None:
    new_xmp = apply_entry(
        baseline_xmp, dehaze_entry, parameter_values={"strength": 0.55, "distance": 0.3}
    )
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)
    text = out_path.read_text()
    matches = re.findall(
        r'darktable:operation="hazeremoval"[^/]*?darktable:params="([0-9a-f]+)"', text
    )
    assert matches
    fields = decode(matches[-1])
    assert fields[_STRENGTH_FIELD_INDEX] == pytest.approx(0.55, abs=1e-5)
    assert fields[_DISTANCE_FIELD_INDEX] == pytest.approx(0.3, abs=1e-5)


def test_apply_entry_partial_update_preserves_unspecified_axis(baseline_xmp, dehaze_entry) -> None:
    """Supplying only strength leaves distance at the dtstyle default."""
    new_xmp = apply_entry(baseline_xmp, dehaze_entry, parameter_values={"strength": 0.8})
    plugins = [p for p in new_xmp.history if p.operation == "hazeremoval"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_STRENGTH_FIELD_INDEX] == pytest.approx(0.8, abs=1e-5)
    # distance was not supplied → preserved at dtstyle default 0.2
    assert fields[_DISTANCE_FIELD_INDEX] == pytest.approx(0.2, abs=1e-5)


def test_apply_entry_no_values_uses_dtstyle_default(baseline_xmp, dehaze_entry) -> None:
    """Default strength=0.2, distance=0.2 (darktable's stated defaults)."""
    new_xmp = apply_entry(baseline_xmp, dehaze_entry)
    plugins = [p for p in new_xmp.history if p.operation == "hazeremoval"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_STRENGTH_FIELD_INDEX] == pytest.approx(0.2, abs=1e-5)
    assert fields[_DISTANCE_FIELD_INDEX] == pytest.approx(0.2, abs=1e-5)


def test_apply_entry_preserves_mode_flags(baseline_xmp, dehaze_entry) -> None:
    """compatibility_mode (FALSE) and adaptive (TRUE) survive the apply path."""
    new_xmp = apply_entry(
        baseline_xmp, dehaze_entry, parameter_values={"strength": 0.6, "distance": 0.4}
    )
    plugins = [p for p in new_xmp.history if p.operation == "hazeremoval"]
    fields = decode(plugins[-1].params)
    assert fields[2] == 0  # compatibility_mode FALSE
    assert fields[3] == 1  # adaptive TRUE
