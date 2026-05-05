"""Integration: ``apply_with_drawn_mask`` end-to-end XMP synthesis.

Validates that the wire format produced by the path 4a code (drawn-mask
serialization, blendop_params patching) round-trips through the XMP
writer + parser cleanly. Verifying that darktable actually APPLIES the
mask is left to E2E (needs a real darktable install).
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_with_drawn_mask
from chemigram.core.masking.dt_serialize import (
    _BLEND_PARAMS_SIZE,
    _OFFSET_MASK_ID,
    _OFFSET_MASK_MODE,
    _decode_default_blendop_blob,
)
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp, write_xmp

FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(FIXTURE_BASELINE)


@pytest.fixture
def expo_dtstyle():
    """The expressive-baseline pack's parameterized exposure dtstyle —
    single exposure plugin. (Post-v1.6.0: replaced the previous
    expo_+0.5 reference; the discrete entry was removed when the
    parameterized form shipped per RFC-021.)"""
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("exposure")
    assert entry is not None
    return entry.dtstyle


def test_apply_with_gradient_mask_produces_valid_xmp(
    baseline_xmp, expo_dtstyle, tmp_path: Path
) -> None:
    """End-to-end: synthesize → write → parse round-trips cleanly with
    the masks_history element preserved and the exposure plugin's
    blendop_params patched."""
    spec = {
        "dt_form": "gradient",
        "dt_params": {"anchor_x": 0.5, "anchor_y": 0.5, "rotation": 90.0},
    }
    new_xmp = apply_with_drawn_mask(baseline_xmp, expo_dtstyle, spec)

    # 1. The exposure history entry is present
    exposure_entries = [h for h in new_xmp.history if h.operation == "exposure"]
    assert exposure_entries, "exposure plugin missing from synthesized history"

    # 2. Its blendop_params decodes to a 420-byte struct with mask_mode=3
    encoded = exposure_entries[-1].blendop_params
    raw = _decode_default_blendop_blob(encoded)
    assert len(raw) == _BLEND_PARAMS_SIZE
    (mask_mode,) = struct.unpack_from("<I", raw, _OFFSET_MASK_MODE)
    (mask_id,) = struct.unpack_from("<I", raw, _OFFSET_MASK_ID)
    assert mask_mode == 3, "mask_mode should be ENABLED|MASK = 3 for drawn-mask binding"
    assert mask_id != 0, "mask_id should be set to a non-zero allocated value"
    assert mask_id != 0xFFFFFFFF, "mask_id should not be the sentinel"

    # 3. masks_history is in raw_extra_fields with the matching mask_id
    masks_history_elems = [
        v for k, q, v in new_xmp.raw_extra_fields if k == "elem" and q == "darktable:masks_history"
    ]
    assert len(masks_history_elems) == 1
    xml_text = masks_history_elems[0]
    assert f'darktable:mask_id="{mask_id}"' in xml_text
    assert "darktable:mask_type=" in xml_text

    # 4. Round-trip via write_xmp + parse_xmp
    out_path = tmp_path / "test.xmp"
    write_xmp(new_xmp, out_path)
    parsed = parse_xmp(out_path)
    # Same exposure entry survives
    parsed_exposure = [h for h in parsed.history if h.operation == "exposure"]
    assert parsed_exposure
    # blendop_params survives byte-for-byte
    assert parsed_exposure[-1].blendop_params == encoded
    # masks_history element survives
    parsed_masks = [
        v for k, q, v in parsed.raw_extra_fields if k == "elem" and q == "darktable:masks_history"
    ]
    assert len(parsed_masks) == 1


def test_apply_with_ellipse_mask(baseline_xmp, expo_dtstyle) -> None:
    spec = {
        "dt_form": "ellipse",
        "dt_params": {
            "center_x": 0.5,
            "center_y": 0.5,
            "radius_x": 0.3,
            "radius_y": 0.3,
        },
    }
    new_xmp = apply_with_drawn_mask(baseline_xmp, expo_dtstyle, spec)
    masks_history = [
        v for k, q, v in new_xmp.raw_extra_fields if k == "elem" and q == "darktable:masks_history"
    ]
    assert len(masks_history) == 1
    # Ellipse is mask_type=32
    assert 'darktable:mask_type="32"' in masks_history[0]


def test_apply_with_rectangle_mask(baseline_xmp, expo_dtstyle) -> None:
    spec = {
        "dt_form": "rectangle",
        "dt_params": {"x0": 0.1, "y0": 0.1, "x1": 0.9, "y1": 0.9},
    }
    new_xmp = apply_with_drawn_mask(baseline_xmp, expo_dtstyle, spec)
    masks_history = [
        v for k, q, v in new_xmp.raw_extra_fields if k == "elem" and q == "darktable:masks_history"
    ]
    assert len(masks_history) == 1
    # Rectangle (DT_MASKS_PATH) is mask_type=2
    assert 'darktable:mask_type="2"' in masks_history[0]


def test_apply_replaces_existing_masks_history(baseline_xmp, expo_dtstyle) -> None:
    """If raw_extra_fields already has a masks_history elem (the baseline
    fixture has an empty one), it must be REPLACED, not duplicated."""
    spec = {"dt_form": "gradient", "dt_params": {"rotation": 90.0}}
    new_xmp = apply_with_drawn_mask(baseline_xmp, expo_dtstyle, spec)
    masks_count = sum(
        1 for k, q, _ in new_xmp.raw_extra_fields if k == "elem" and q == "darktable:masks_history"
    )
    assert masks_count == 1


def test_apply_rejects_unknown_form(baseline_xmp, expo_dtstyle) -> None:
    with pytest.raises(ValueError, match="unknown mask_spec dt_form"):
        apply_with_drawn_mask(baseline_xmp, expo_dtstyle, {"dt_form": "spline", "dt_params": {}})


def test_apply_rejects_missing_form(baseline_xmp, expo_dtstyle) -> None:
    with pytest.raises(ValueError, match="missing/invalid 'dt_form'"):
        apply_with_drawn_mask(baseline_xmp, expo_dtstyle, {"dt_params": {}})
