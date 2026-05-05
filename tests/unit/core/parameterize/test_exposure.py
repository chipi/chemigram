"""Round-trip and patching tests for the exposure Path C decoder.

Validates ADR-077 / ADR-078 byte-level patching semantics:

- ``encode(decode(blob)) == blob`` for every shipped exposure dtstyle.
- ``patch(blob, ev=v).<EV field> == v`` across the declared range.
- Bytes outside the EV field are preserved verbatim by ``patch``.
- Size mismatch / wrong-modversion blobs raise ValueError.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.exposure import (
    _EV_OFFSET,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

# Reference op_params hex from the v1.5.x discrete exposure entries (those
# entries themselves were removed in v1.6.0 when the parameterized form
# shipped — RFC-021). Kept here as test fixtures so the round-trip and
# patch contracts can be exercised against the canonical pre-v1.6 byte
# patterns. Each is a 28-byte (56-hex-char) exposure mv7 op_params blob.
_REFERENCE_OP_PARAMS_BY_LABEL = {
    "expo_+0.5": ("00000000000080b90000003f00004842000080c00100000001000000", 0.5),
    "expo_-0.5": ("00000000000080b9000000bf00004842000080c00100000001000000", -0.5),
    "expo_+0.3": ("00000000000000009a99993e00004842000080c00100000001000000", 0.3),
    "expo_-0.3": ("00000000000000009a9999be00004842000080c00100000001000000", -0.3),
}

# Shipped parameterized exposure dtstyle (default ev=0.0). Verifies the
# round-trip + decode contracts against the live v1.6.0+ entry too.
_SHIPPED_EXPOSURE_DTSTYLE = (
    _REPO_ROOT / "vocabulary/packs/expressive-baseline/layers/L3/exposure/exposure.dtstyle"
)


def _read_op_params(dtstyle_path: Path) -> str:
    """Extract the <op_params> hex from a .dtstyle file."""
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_seven() -> None:
    """The decoder is pinned to exposure mv7; this test surfaces a bump."""
    assert SUPPORTED_MODVERSION == 7


@pytest.mark.parametrize(
    "label,op_params",
    [(label, hex_) for label, (hex_, _ev) in _REFERENCE_OP_PARAMS_BY_LABEL.items()],
)
def test_round_trip_on_reference_op_params(label: str, op_params: str) -> None:
    """Every pre-v1.6 reference op_params blob round-trips byte-for-byte
    through decode → encode."""
    assert encode(decode(op_params)) == op_params


def test_round_trip_on_shipped_v1_6_dtstyle() -> None:
    """The live v1.6.0+ parameterized ``exposure.dtstyle`` round-trips
    byte-for-byte. Catches authoring errors that would slip past the
    static reference fixtures above."""
    op_params = _read_op_params(_SHIPPED_EXPOSURE_DTSTYLE)
    assert encode(decode(op_params)) == op_params


@pytest.mark.parametrize(
    "label,expected_ev",
    [(label, ev) for label, (_hex, ev) in _REFERENCE_OP_PARAMS_BY_LABEL.items()],
)
def test_decode_extracts_known_ev(label: str, expected_ev: float) -> None:
    """The pre-v1.6 reference exposure blobs decode to the EV their
    label claims."""
    op_params = _REFERENCE_OP_PARAMS_BY_LABEL[label][0]
    fields = decode(op_params)
    # _EV_FIELD_INDEX is 2 (third position in the unpacked struct)
    assert fields[2] == pytest.approx(expected_ev, abs=1e-5)


def test_decode_extracts_default_ev_from_shipped_dtstyle() -> None:
    """The shipped ``exposure.dtstyle`` ships with ev=0.0 (the parameter
    default per RFC-021)."""
    fields = decode(_read_op_params(_SHIPPED_EXPOSURE_DTSTYLE))
    assert fields[2] == pytest.approx(0.0, abs=1e-5)


@pytest.mark.parametrize("ev", [-3.0, -1.0, -0.7, 0.0, 0.7, 1.0, 3.0])
def test_patch_sets_ev_value(ev: float) -> None:
    """``patch(blob, ev=v)`` produces a blob whose EV field equals v."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["expo_+0.5"][0]
    out = patch(src, ev=ev)
    fields = decode(out)
    assert fields[2] == pytest.approx(ev, abs=1e-5)


def test_patch_preserves_bytes_outside_ev_field() -> None:
    """``patch`` must not touch any byte outside the 4-byte EV field at
    offset 8. Verified by re-decoding both blobs and comparing every
    field except index 2 (EV)."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["expo_+0.5"][0]
    src_fields = decode(src)
    patched_fields = decode(patch(src, ev=1.5))
    for i in range(len(src_fields)):
        if i == 2:
            continue
        assert patched_fields[i] == src_fields[i], (
            f"field {i} changed: {src_fields[i]} -> {patched_fields[i]}"
        )


def test_patch_preserves_bytes_outside_ev_field_at_byte_level() -> None:
    """Stronger guarantee: bytes 0..7 and 12..27 are byte-identical
    before and after patching. Catches any silent endianness / pad
    bug the field-level test might miss."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["expo_+0.5"][0]
    src_bytes = bytes.fromhex(src)
    patched_bytes = bytes.fromhex(patch(src, ev=2.0))
    assert src_bytes[:_EV_OFFSET] == patched_bytes[:_EV_OFFSET]
    assert src_bytes[_EV_OFFSET + 4 :] == patched_bytes[_EV_OFFSET + 4 :]


def test_decode_rejects_short_blob() -> None:
    """A blob shorter than 28 bytes raises ValueError naming the size."""
    with pytest.raises(ValueError, match="expected 28 bytes"):
        decode("00" * 16)


def test_decode_rejects_wrong_size_blob() -> None:
    """A blob of the wrong size (e.g. mv6 exposure was 20 bytes) raises."""
    twenty = "00" * 20
    with pytest.raises(ValueError, match="modversion"):
        decode(twenty)


def test_struct_format_matches_size() -> None:
    """Internal sanity: the format string and size constant agree."""
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE
