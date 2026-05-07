"""Round-trip and patching tests for the temperature Path C decoder.

The first multi-parameter parameterized module (Phase 4 / RFC-021).
``red_coeff``, ``green_coeff`` (Lightroom Tint axis, #90 Bucket A.3) and
``blue_coeff`` are independently patchable; ``various`` (often +inf) and
``preset`` are preserved.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.temperature import (
    _BLUE_FIELD_INDEX,
    _BLUE_OFFSET,
    _GREEN_FIELD_INDEX,
    _GREEN_OFFSET,
    _RED_FIELD_INDEX,
    _RED_OFFSET,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

# Reference op_params from the v1.5.x discrete WB entries. wb_warm_subtle
# remains in the starter pack (teaching artifact); wb_cool_subtle was
# removed in v1.6.0+ when ``temperature`` shipped. Each is a 20-byte
# (40-hex-char) temperature mv4 blob.
_REFERENCE_OP_PARAMS_BY_LABEL = {
    # (red_coeff, blue_coeff)
    "wb_warm_subtle": ("fc8009408fce9a3f8fce9a3f0000807f02000000", (2.1485, 1.2094)),
    "wb_cool_subtle": ("83c09a3f0000803f9cc408400000807f02000000", (1.2090, 2.1370)),
}

_SHIPPED_DTSTYLE = (
    _REPO_ROOT / "vocabulary/packs/expressive-baseline/layers/L3/temperature/temperature.dtstyle"
)


def _read_op_params(dtstyle_path: Path) -> str:
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_four() -> None:
    assert SUPPORTED_MODVERSION == 4


def test_round_trip_on_shipped_v1_6_dtstyle() -> None:
    op_params = _read_op_params(_SHIPPED_DTSTYLE)
    assert encode(decode(op_params)) == op_params


def test_decode_extracts_default_coeffs_from_shipped_dtstyle() -> None:
    """The shipped temperature.dtstyle ships with red=blue=1.0 (no shift)."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    assert fields[_RED_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)


@pytest.mark.parametrize("red", [0.5, 1.0, 1.5, 2.148, 4.0])
def test_patch_sets_red_only(red: float) -> None:
    """Patching only red_coeff leaves blue at the source value."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_blue = decode(src)[_BLUE_FIELD_INDEX]
    out = patch(src, red_coeff=red)
    fields = decode(out)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(red, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(src_blue, abs=1e-5)


@pytest.mark.parametrize("blue", [0.5, 1.0, 1.5, 2.137, 4.0])
def test_patch_sets_blue_only(blue: float) -> None:
    """Patching only blue_coeff leaves red at the source value."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_red = decode(src)[_RED_FIELD_INDEX]
    out = patch(src, blue_coeff=blue)
    fields = decode(out)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(blue, abs=1e-5)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(src_red, abs=1e-5)


@pytest.mark.parametrize("green", [0.5, 0.85, 1.0, 1.15, 4.0])
def test_patch_sets_green_only(green: float) -> None:
    """Patching only green_coeff (Lightroom Tint) leaves red & blue
    unchanged. Closes #90 Bucket A.3."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_red = decode(src)[_RED_FIELD_INDEX]
    src_blue = decode(src)[_BLUE_FIELD_INDEX]
    out = patch(src, green_coeff=green)
    fields = decode(out)
    assert fields[_GREEN_FIELD_INDEX] == pytest.approx(green, abs=1e-5)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(src_red, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(src_blue, abs=1e-5)


def test_patch_sets_all_three_coeffs() -> None:
    """Multi-parameter patch: red, green, blue update simultaneously."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    out = patch(src, red_coeff=2.148, green_coeff=1.07, blue_coeff=1.209)
    fields = decode(out)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(2.148, abs=1e-5)
    assert fields[_GREEN_FIELD_INDEX] == pytest.approx(1.07, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(1.209, abs=1e-5)


def test_patch_sets_both_coeffs() -> None:
    """Two-axis legacy call still works: red+blue with green untouched."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_green = decode(src)[_GREEN_FIELD_INDEX]
    out = patch(src, red_coeff=2.148, blue_coeff=1.209)
    fields = decode(out)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(2.148, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(1.209, abs=1e-5)
    assert fields[_GREEN_FIELD_INDEX] == pytest.approx(src_green, abs=1e-5)


def test_patch_with_no_args_is_identity() -> None:
    """``patch(blob)`` with no kwargs returns the input unchanged."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    assert patch(src) == src


def test_patch_preserves_various_preset() -> None:
    """various (+inf at offset 12), preset (offset 16) must survive any
    patch — these are sentinel values darktable's runtime relies on.
    (Green is now patchable as the Tint axis; was previously preserved.)"""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_fields = decode(src)
    patched_fields = decode(patch(src, red_coeff=2.5, green_coeff=1.1, blue_coeff=0.7))
    assert patched_fields[3] == src_fields[3]  # various
    assert patched_fields[4] == src_fields[4]  # preset


def test_patch_preserves_bytes_outside_rgb_fields() -> None:
    """Bytes 12..19 (various + preset) preserved verbatim regardless of
    which RGB coefficients are patched."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_bytes = bytes.fromhex(src)
    patched_bytes = bytes.fromhex(patch(src, red_coeff=3.0, green_coeff=1.2, blue_coeff=0.8))
    # Various + preset region [12..20)
    assert src_bytes[12:20] == patched_bytes[12:20]
    # All three RGB regions were patched
    assert src_bytes[_RED_OFFSET : _RED_OFFSET + 4] != patched_bytes[_RED_OFFSET : _RED_OFFSET + 4]
    assert (
        src_bytes[_GREEN_OFFSET : _GREEN_OFFSET + 4]
        != patched_bytes[_GREEN_OFFSET : _GREEN_OFFSET + 4]
    )
    assert (
        src_bytes[_BLUE_OFFSET : _BLUE_OFFSET + 4] != patched_bytes[_BLUE_OFFSET : _BLUE_OFFSET + 4]
    )


@pytest.mark.parametrize(
    "label,expected",
    [(label, v) for label, (_hex, v) in _REFERENCE_OP_PARAMS_BY_LABEL.items()],
)
def test_decode_extracts_known_coeffs(label: str, expected: tuple[float, float]) -> None:
    op_params = _REFERENCE_OP_PARAMS_BY_LABEL[label][0]
    fields = decode(op_params)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(expected[0], abs=1e-3)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(expected[1], abs=1e-3)


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 20 bytes"):
        decode("00" * 8)


def test_decode_rejects_wrong_size_blob() -> None:
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 28)


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE
