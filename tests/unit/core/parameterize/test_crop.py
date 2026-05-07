"""Round-trip and patching tests for the crop Path C decoder.

The first workflow-primitive parameterized entry (RFC-022 Tier 2) and
the second multi-parameter entry (after temperature). 4 independent
margin axes (cx, cy, cw, ch) with partial-update semantics.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.crop import (
    _CH_FIELD_INDEX,
    _CH_OFFSET,
    _CW_FIELD_INDEX,
    _CW_OFFSET,
    _CX_FIELD_INDEX,
    _CX_OFFSET,
    _CY_FIELD_INDEX,
    _CY_OFFSET,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

_SHIPPED_DTSTYLE = _REPO_ROOT / "vocabulary/packs/expressive-baseline/layers/L3/crop/crop.dtstyle"


def _read_op_params(dtstyle_path: Path) -> str:
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_three() -> None:
    assert SUPPORTED_MODVERSION == 3


def test_round_trip_on_shipped_dtstyle() -> None:
    op_params = _read_op_params(_SHIPPED_DTSTYLE)
    assert encode(decode(op_params)) == op_params


def test_decode_extracts_default_no_crop() -> None:
    """Default cx=cy=0.0, cw=ch=1.0 (full image, no crop)."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    assert fields[_CX_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)
    assert fields[_CY_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)
    assert fields[_CW_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)
    assert fields[_CH_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)


def test_decode_default_aspect_ratio_is_free() -> None:
    """ratio_n = ratio_d = -1 (free aspect ratio default)."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    assert fields[4] == -1
    assert fields[5] == -1


def test_patch_sets_full_crop_rectangle() -> None:
    """All 4 margins patched simultaneously (typical use)."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    out = patch(src, cx=0.1, cy=0.2, cw=0.9, ch=0.8)
    fields = decode(out)
    assert fields[_CX_FIELD_INDEX] == pytest.approx(0.1, abs=1e-5)
    assert fields[_CY_FIELD_INDEX] == pytest.approx(0.2, abs=1e-5)
    assert fields[_CW_FIELD_INDEX] == pytest.approx(0.9, abs=1e-5)
    assert fields[_CH_FIELD_INDEX] == pytest.approx(0.8, abs=1e-5)


@pytest.mark.parametrize(
    "axis,value",
    [("cx", 0.15), ("cy", 0.25), ("cw", 0.85), ("ch", 0.75)],
)
def test_patch_partial_update_one_axis(axis: str, value: float) -> None:
    """Patching a single axis leaves other 3 at the source values."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_fields = decode(src)
    out = patch(src, **{axis: value})
    fields = decode(out)
    field_indices = {
        "cx": _CX_FIELD_INDEX,
        "cy": _CY_FIELD_INDEX,
        "cw": _CW_FIELD_INDEX,
        "ch": _CH_FIELD_INDEX,
    }
    for ax, idx in field_indices.items():
        if ax == axis:
            assert fields[idx] == pytest.approx(value, abs=1e-5)
        else:
            assert fields[idx] == pytest.approx(src_fields[idx], abs=1e-5)


def test_patch_with_no_args_is_identity() -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    assert patch(src) == src


def test_patch_preserves_aspect_ratio_fields() -> None:
    """ratio_n / ratio_d (offsets 16 / 20) must survive any patch."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_fields = decode(src)
    patched_fields = decode(patch(src, cx=0.1, cy=0.1, cw=0.9, ch=0.9))
    assert patched_fields[4] == src_fields[4]  # ratio_n
    assert patched_fields[5] == src_fields[5]  # ratio_d


def test_patch_preserves_bytes_outside_margin_fields() -> None:
    """Bytes 16..23 (ratio_n + ratio_d) preserved verbatim."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_bytes = bytes.fromhex(src)
    patched_bytes = bytes.fromhex(patch(src, cx=0.2, cw=0.8))
    assert src_bytes[16:24] == patched_bytes[16:24]


def test_field_offsets_match_struct_layout() -> None:
    """Sanity: declared offsets line up with struct field positions."""
    assert _CX_OFFSET == 0
    assert _CY_OFFSET == 4
    assert _CW_OFFSET == 8
    assert _CH_OFFSET == 12


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 24 bytes"):
        decode("00" * 8)


def test_decode_rejects_wrong_size_blob() -> None:
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 28)


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE
