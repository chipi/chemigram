"""Integration: parameterized colorbalancergb (saturation_global) apply path.

Mirrors test_parameterize_exposure.py and test_parameterize_vignette.py
for the third parameterized module (Phase 4 / RFC-021). Validates that
``apply_entry`` with a saturation value patches the dtstyle's
``op_params`` byte-correctly and the resulting XMP carries those bytes
through write/parse round-trip.

Composition with mask is exercised here too — saturation_global is a
per-pixel color op, so it composes with drawn masks (unlike vignette,
which is documented as a dead pairing with masks).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.colorbalancergb import _SATURATION_GLOBAL_FIELD_INDEX, decode
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp, write_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def saturation_entry():
    """The shipped parameterized ``saturation_global`` entry from the
    expressive-baseline pack."""
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("saturation_global")
    assert entry is not None
    assert entry.parameters is not None, "saturation_global entry missing 'parameters' declaration"
    return entry


@pytest.mark.parametrize("sat", [-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0])
def test_apply_entry_with_saturation_patches_op_params(
    baseline_xmp, saturation_entry, sat: float
) -> None:
    """Applying saturation_global with a value produces an XMP whose
    colorbalancergb plugin's op_params decodes to that saturation."""
    new_xmp = apply_entry(
        baseline_xmp, saturation_entry, parameter_values={"saturation_global": sat}
    )
    plugins = [p for p in new_xmp.history if p.operation == "colorbalancergb"]
    assert plugins, "no colorbalancergb plugin in synthesized XMP history"
    fields = decode(plugins[-1].params)
    assert fields[_SATURATION_GLOBAL_FIELD_INDEX] == pytest.approx(sat, abs=1e-5)


def test_apply_entry_round_trips_through_xmp_writer(
    baseline_xmp, saturation_entry, tmp_path: Path
) -> None:
    """The patched op_params survive a full write → parse cycle."""
    new_xmp = apply_entry(
        baseline_xmp, saturation_entry, parameter_values={"saturation_global": -0.7}
    )
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)

    text = out_path.read_text()
    matches = re.findall(
        r'darktable:operation="colorbalancergb"[^/]*?darktable:params="([0-9a-f]+)"',
        text,
    )
    assert matches, "no colorbalancergb op_params in serialized XMP"
    fields = decode(matches[-1])
    assert fields[_SATURATION_GLOBAL_FIELD_INDEX] == pytest.approx(-0.7, abs=1e-5)

    parsed = parse_xmp(out_path)
    re_plugins = [p for p in parsed.history if p.operation == "colorbalancergb"]
    assert re_plugins
    fields = decode(re_plugins[-1].params)
    assert fields[_SATURATION_GLOBAL_FIELD_INDEX] == pytest.approx(-0.7, abs=1e-5)


def test_apply_entry_no_values_uses_dtstyle_default(baseline_xmp, saturation_entry) -> None:
    """Without parameter_values, the dtstyle's default
    saturation_global=0.0 carries through."""
    new_xmp = apply_entry(baseline_xmp, saturation_entry)
    plugins = [p for p in new_xmp.history if p.operation == "colorbalancergb"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_SATURATION_GLOBAL_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)


def test_apply_entry_with_saturation_and_mask_composes(baseline_xmp, saturation_entry) -> None:
    """Both axes (parameter value + drawn mask) compose: the resulting
    XMP carries the patched op_params AND a masks_history element.
    Saturation x mask is a real photographic combination (kill saturation
    in a region, boost it elsewhere)."""
    mask_spec = {
        "dt_form": "ellipse",
        "dt_params": {
            "center_x": 0.5,
            "center_y": 0.5,
            "radius_x": 0.3,
            "radius_y": 0.3,
            "border": 0.05,
        },
    }
    new_xmp = apply_entry(
        baseline_xmp,
        saturation_entry,
        parameter_values={"saturation_global": -1.0},
        mask_spec=mask_spec,
    )

    plugins = [p for p in new_xmp.history if p.operation == "colorbalancergb"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_SATURATION_GLOBAL_FIELD_INDEX] == pytest.approx(-1.0, abs=1e-5)

    masks_elems = [
        v
        for kind, qname, v in new_xmp.raw_extra_fields
        if kind == "elem" and qname == "darktable:masks_history"
    ]
    assert len(masks_elems) == 1
    assert 'darktable:mask_type="' in masks_elems[0]
