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
from chemigram.core.parameterize.colorbalancergb import (
    _BRILLIANCE_GLOBAL_FIELD_INDEX,
    _BRILLIANCE_HIGHLIGHTS_FIELD_INDEX,
    _BRILLIANCE_MIDTONES_FIELD_INDEX,
    _BRILLIANCE_SHADOWS_FIELD_INDEX,
    _CHROMA_GLOBAL_FIELD_INDEX,
    _HIGHLIGHTS_WEIGHT_FIELD_INDEX,
    _HUE_ANGLE_FIELD_INDEX,
    _HUE_HIGHLIGHTS_FIELD_INDEX,
    _HUE_MIDTONES_FIELD_INDEX,
    _HUE_SHADOWS_FIELD_INDEX,
    _SATURATION_GLOBAL_FIELD_INDEX,
    _SATURATION_HIGHLIGHTS_FIELD_INDEX,
    _SATURATION_MIDTONES_FIELD_INDEX,
    _SATURATION_SHADOWS_FIELD_INDEX,
    _SHADOWS_WEIGHT_FIELD_INDEX,
    _VIBRANCE_FIELD_INDEX,
    _WHITE_FULCRUM_FIELD_INDEX,
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


# ---------------------------------------------------------------------------
# Tier 2 additional axes: vibrance, chroma_global, hue_angle.
# Each is a separate manifest entry whose ``parameters`` block declares
# its own single axis. The decoder is shared.
# ---------------------------------------------------------------------------


@pytest.fixture
def vibrance_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("vibrance")
    assert entry is not None
    assert entry.parameters is not None
    return entry


@pytest.fixture
def chroma_global_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("chroma_global")
    assert entry is not None
    assert entry.parameters is not None
    return entry


@pytest.fixture
def hue_angle_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("hue_angle")
    assert entry is not None
    assert entry.parameters is not None
    return entry


@pytest.mark.parametrize("v", [-1.0, -0.3, 0.0, 0.3, 1.0])
def test_apply_entry_vibrance_patches_op_params(baseline_xmp, vibrance_entry, v: float) -> None:
    new_xmp = apply_entry(baseline_xmp, vibrance_entry, parameter_values={"vibrance": v})
    plugins = [p for p in new_xmp.history if p.operation == "colorbalancergb"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_VIBRANCE_FIELD_INDEX] == pytest.approx(v, abs=1e-5)


@pytest.mark.parametrize("v", [-1.0, -0.3, 0.0, 0.5, 1.0])
def test_apply_entry_chroma_global_patches_op_params(
    baseline_xmp, chroma_global_entry, v: float
) -> None:
    new_xmp = apply_entry(baseline_xmp, chroma_global_entry, parameter_values={"chroma_global": v})
    plugins = [p for p in new_xmp.history if p.operation == "colorbalancergb"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_CHROMA_GLOBAL_FIELD_INDEX] == pytest.approx(v, abs=1e-5)


@pytest.mark.parametrize("v", [-180.0, -30.0, 0.0, 30.0, 180.0])
def test_apply_entry_hue_angle_patches_op_params(baseline_xmp, hue_angle_entry, v: float) -> None:
    new_xmp = apply_entry(baseline_xmp, hue_angle_entry, parameter_values={"hue_angle": v})
    plugins = [p for p in new_xmp.history if p.operation == "colorbalancergb"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_HUE_ANGLE_FIELD_INDEX] == pytest.approx(v, abs=1e-5)


def test_apply_entry_vibrance_default_is_no_op(baseline_xmp, vibrance_entry) -> None:
    """Default vibrance=0.0."""
    new_xmp = apply_entry(baseline_xmp, vibrance_entry)
    plugins = [p for p in new_xmp.history if p.operation == "colorbalancergb"]
    assert plugins
    assert decode(plugins[-1].params)[_VIBRANCE_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)


def test_apply_entry_hue_angle_default_is_no_op(baseline_xmp, hue_angle_entry) -> None:
    """Default hue_angle=0.0 (no rotation)."""
    new_xmp = apply_entry(baseline_xmp, hue_angle_entry)
    plugins = [p for p in new_xmp.history if p.operation == "colorbalancergb"]
    assert plugins
    assert decode(plugins[-1].params)[_HUE_ANGLE_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)


# ---------------------------------------------------------------------------
# Brilliance axes (#86): 4 separate single-axis manifest entries on the
# same shared decoder.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "entry_name,param_name,field_index",
    [
        ("brilliance_global", "brilliance_global", _BRILLIANCE_GLOBAL_FIELD_INDEX),
        ("brilliance_highlights", "brilliance_highlights", _BRILLIANCE_HIGHLIGHTS_FIELD_INDEX),
        ("brilliance_midtones", "brilliance_midtones", _BRILLIANCE_MIDTONES_FIELD_INDEX),
        ("brilliance_shadows", "brilliance_shadows", _BRILLIANCE_SHADOWS_FIELD_INDEX),
    ],
)
@pytest.mark.parametrize("v", [-1.0, -0.3, 0.0, 0.3, 1.0])
def test_apply_entry_brilliance_axis_patches_op_params(
    baseline_xmp, entry_name: str, param_name: str, field_index: int, v: float
) -> None:
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name(entry_name)
    assert entry is not None
    assert entry.parameters is not None
    new_xmp = apply_entry(baseline_xmp, entry, parameter_values={param_name: v})
    plugins = [p for p in new_xmp.history if p.operation == "colorbalancergb"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[field_index] == pytest.approx(v, abs=1e-5)


@pytest.mark.parametrize(
    "entry_name",
    ["brilliance_global", "brilliance_highlights", "brilliance_midtones", "brilliance_shadows"],
)
def test_apply_entry_brilliance_default_is_no_op(baseline_xmp, entry_name: str) -> None:
    """Each brilliance entry's default is 0.0 (no luminance shift)."""
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name(entry_name)
    assert entry is not None
    new_xmp = apply_entry(baseline_xmp, entry)
    plugins = [p for p in new_xmp.history if p.operation == "colorbalancergb"]
    assert plugins
    # Find which field this entry parameterizes and verify it defaults to 0
    spec = entry.parameters[0]
    field_idx_map = {
        "brilliance_global": _BRILLIANCE_GLOBAL_FIELD_INDEX,
        "brilliance_highlights": _BRILLIANCE_HIGHLIGHTS_FIELD_INDEX,
        "brilliance_midtones": _BRILLIANCE_MIDTONES_FIELD_INDEX,
        "brilliance_shadows": _BRILLIANCE_SHADOWS_FIELD_INDEX,
    }
    assert decode(plugins[-1].params)[field_idx_map[spec.name]] == pytest.approx(0.0, abs=1e-5)


# ---------------------------------------------------------------------------
# #91 Bucket A.5: per-zone hue/sat + blending/balance apply paths
# ---------------------------------------------------------------------------


_COLOR_GRADING_AXIS_FIELD_INDICES = {
    "hue_shadows": _HUE_SHADOWS_FIELD_INDEX,
    "hue_midtones": _HUE_MIDTONES_FIELD_INDEX,
    "hue_highlights": _HUE_HIGHLIGHTS_FIELD_INDEX,
    "saturation_shadows": _SATURATION_SHADOWS_FIELD_INDEX,
    "saturation_midtones": _SATURATION_MIDTONES_FIELD_INDEX,
    "saturation_highlights": _SATURATION_HIGHLIGHTS_FIELD_INDEX,
    "shadows_weight": _SHADOWS_WEIGHT_FIELD_INDEX,
    "highlights_weight": _HIGHLIGHTS_WEIGHT_FIELD_INDEX,
    "white_fulcrum": _WHITE_FULCRUM_FIELD_INDEX,
}


@pytest.mark.parametrize(
    "entry_name,test_value",
    [
        ("hue_shadows", 210.0),
        ("hue_midtones", 30.0),
        ("hue_highlights", 45.0),
        ("saturation_shadows", 0.3),
        ("saturation_midtones", 0.2),
        ("saturation_highlights", 0.25),
        ("shadows_weight", 1.5),
        ("highlights_weight", 2.0),
        ("white_fulcrum", 0.5),
    ],
)
def test_apply_entry_color_grading_axis_patches_op_params(
    baseline_xmp, entry_name: str, test_value: float
) -> None:
    """Each #91 Bucket A.5 vocabulary entry patches the correct field in
    the colorbalancergb mv5 struct."""
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name(entry_name)
    assert entry is not None
    assert entry.parameters is not None
    new_xmp = apply_entry(baseline_xmp, entry, parameter_values={entry_name: test_value})
    plugins = [p for p in new_xmp.history if p.operation == "colorbalancergb"]
    assert plugins
    fields = decode(plugins[-1].params)
    field_index = _COLOR_GRADING_AXIS_FIELD_INDICES[entry_name]
    assert fields[field_index] == pytest.approx(test_value, abs=1e-5)


@pytest.mark.parametrize(
    "entry_name,default",
    [
        ("hue_shadows", 0.0),
        ("hue_midtones", 0.0),
        ("hue_highlights", 0.0),
        ("saturation_shadows", 0.0),
        ("saturation_midtones", 0.0),
        ("saturation_highlights", 0.0),
        ("shadows_weight", 1.0),
        ("highlights_weight", 1.0),
        ("white_fulcrum", 0.0),
    ],
)
def test_apply_entry_color_grading_default_matches_baseline(
    baseline_xmp, entry_name: str, default: float
) -> None:
    """Each #91 Bucket A.5 entry's no-args default matches the dtstyle baseline."""
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name(entry_name)
    assert entry is not None
    new_xmp = apply_entry(baseline_xmp, entry)
    plugins = [p for p in new_xmp.history if p.operation == "colorbalancergb"]
    assert plugins
    field_index = _COLOR_GRADING_AXIS_FIELD_INDICES[entry_name]
    assert decode(plugins[-1].params)[field_index] == pytest.approx(default, abs=1e-5)
