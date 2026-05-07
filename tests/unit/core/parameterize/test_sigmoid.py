"""Round-trip and patching tests for the sigmoid Path C decoder.

Mirrors test_exposure.py / test_vignette.py / test_colorbalancergb.py
for the fourth parameterized module (Phase 4 / RFC-021). The pre-v1.6
discrete entries (``contrast_low``, ``contrast_high``) are kept here as
reference fixtures with known middle_grey_contrast values (1.0, 2.5).
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.sigmoid import (
    _CONTRAST_FIELD_INDEX,
    _CONTRAST_OFFSET,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

# Reference op_params hex from the v1.5.x discrete contrast_* entries
# (those entries were removed in v1.6.0+ when the parameterized form
# shipped — RFC-021). Each is a 56-byte (112-hex-char) sigmoid mv3
# op_params blob; the only differing field across the two is
# middle_grey_contrast at offset 0.
_REFERENCE_OP_PARAMS_BY_LABEL = {
    "contrast_low": (
        "0000803f000000000000c8426c09793c000000000000c8420000000000000000000000000000000000000000000000000000000000000000",
        1.0,
    ),
    "contrast_high": (
        "00002040000000000000c8426c09793c000000000000c8420000000000000000000000000000000000000000000000000000000000000000",
        2.5,
    ),
}

_SHIPPED_DTSTYLE = (
    _REPO_ROOT / "vocabulary/packs/expressive-baseline/layers/L3/sigmoid/sigmoid_contrast.dtstyle"
)


def _read_op_params(dtstyle_path: Path) -> str:
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_three() -> None:
    assert SUPPORTED_MODVERSION == 3


@pytest.mark.parametrize(
    "label,op_params",
    [(label, hex_) for label, (hex_, _v) in _REFERENCE_OP_PARAMS_BY_LABEL.items()],
)
def test_round_trip_on_reference_op_params(label: str, op_params: str) -> None:
    """Every pre-v1.6 reference op_params blob round-trips byte-for-byte."""
    assert encode(decode(op_params)) == op_params


def test_round_trip_on_shipped_v1_6_dtstyle() -> None:
    """The live v1.6.0+ parameterized ``sigmoid_contrast.dtstyle``
    round-trips byte-for-byte."""
    op_params = _read_op_params(_SHIPPED_DTSTYLE)
    assert encode(decode(op_params)) == op_params


@pytest.mark.parametrize(
    "label,expected",
    [(label, v) for label, (_hex, v) in _REFERENCE_OP_PARAMS_BY_LABEL.items()],
)
def test_decode_extracts_known_contrast(label: str, expected: float) -> None:
    op_params = _REFERENCE_OP_PARAMS_BY_LABEL[label][0]
    fields = decode(op_params)
    assert fields[_CONTRAST_FIELD_INDEX] == pytest.approx(expected, abs=1e-5)


def test_decode_extracts_default_contrast_from_shipped_dtstyle() -> None:
    """The shipped ``sigmoid_contrast.dtstyle`` ships with contrast=1.5
    (darktable's default)."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    assert fields[_CONTRAST_FIELD_INDEX] == pytest.approx(1.5, abs=1e-5)


@pytest.mark.parametrize("contrast", [0.5, 1.0, 1.5, 2.0, 2.5, 3.5, 5.0])
def test_patch_sets_contrast_value(contrast: float) -> None:
    src = _REFERENCE_OP_PARAMS_BY_LABEL["contrast_low"][0]
    out = patch(src, contrast=contrast)
    fields = decode(out)
    assert fields[_CONTRAST_FIELD_INDEX] == pytest.approx(contrast, abs=1e-5)


def test_patch_preserves_bytes_outside_contrast_field() -> None:
    src = _REFERENCE_OP_PARAMS_BY_LABEL["contrast_high"][0]
    src_bytes = bytes.fromhex(src)
    patched_bytes = bytes.fromhex(patch(src, contrast=2.0))
    assert src_bytes[:_CONTRAST_OFFSET] == patched_bytes[:_CONTRAST_OFFSET]
    assert src_bytes[_CONTRAST_OFFSET + 4 :] == patched_bytes[_CONTRAST_OFFSET + 4 :]


def test_patch_preserves_other_fields() -> None:
    src = _REFERENCE_OP_PARAMS_BY_LABEL["contrast_low"][0]
    src_fields = decode(src)
    patched_fields = decode(patch(src, contrast=2.0))
    for i in range(len(src_fields)):
        if i == _CONTRAST_FIELD_INDEX:
            continue
        assert patched_fields[i] == src_fields[i], (
            f"field {i} changed: {src_fields[i]} -> {patched_fields[i]}"
        )


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 56 bytes"):
        decode("00" * 16)


def test_decode_rejects_wrong_size_blob() -> None:
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 28)


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE
