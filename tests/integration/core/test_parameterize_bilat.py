"""Integration: parameterized bilat (clarity strength) apply path."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.bilat import _DETAIL_FIELD_INDEX, decode
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp, write_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def bilat_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("bilat_clarity_strength")
    assert entry is not None
    assert entry.parameters is not None
    return entry


@pytest.mark.parametrize("strength", [-1.0, 0.0, 0.5, 1.5, 2.5, 4.0])
def test_apply_entry_with_strength_patches_op_params(
    baseline_xmp, bilat_entry, strength: float
) -> None:
    new_xmp = apply_entry(
        baseline_xmp, bilat_entry, parameter_values={"clarity_strength": strength}
    )
    plugins = [p for p in new_xmp.history if p.operation == "bilat"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_DETAIL_FIELD_INDEX] == pytest.approx(strength, abs=1e-5)


def test_apply_entry_round_trips_through_xmp_writer(
    baseline_xmp, bilat_entry, tmp_path: Path
) -> None:
    new_xmp = apply_entry(baseline_xmp, bilat_entry, parameter_values={"clarity_strength": 1.8})
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)
    text = out_path.read_text()
    matches = re.findall(r'darktable:operation="bilat"[^/]*?darktable:params="([0-9a-f]+)"', text)
    assert matches
    fields = decode(matches[-1])
    assert fields[_DETAIL_FIELD_INDEX] == pytest.approx(1.8, abs=1e-5)


def test_apply_entry_no_values_uses_dtstyle_default(baseline_xmp, bilat_entry) -> None:
    """Default strength=0.0 (no-op clarity)."""
    new_xmp = apply_entry(baseline_xmp, bilat_entry)
    plugins = [p for p in new_xmp.history if p.operation == "bilat"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_DETAIL_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)
