"""Round-trip and patching tests for the vignette Path C decoder.

Mirrors test_exposure.py for the second parameterized module. Validates
the same byte-level guarantees: round-trip preserves bytes, patch sets
the named field, bytes outside the field are preserved.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.vignette import (
    _BRIGHTNESS_OFFSET,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

# Reference op_params hex from the v1.5.x discrete vignette entries —
# kept here for fixture stability (the .dtstyle files themselves were
# removed in v1.6.0 along with the magnitude-ladder cleanup). Values
# match the brightness column verified empirically pre-removal:
# vignette_subtle = -0.25, vignette_medium = -0.50, vignette_heavy = -0.80.
# Generated programmatically from the canonical vignette_blob() encoder.

_SHIPPED_VIGNETTE_DTSTYLE = (
    _REPO_ROOT / "vocabulary/packs/expressive-baseline/layers/L3/vignette/vignette.dtstyle"
)


def _read_op_params(dtstyle_path: Path) -> str:
    """Extract the <op_params> hex from a .dtstyle file."""
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_four() -> None:
    assert SUPPORTED_MODVERSION == 4


def test_round_trip_on_shipped_dtstyle() -> None:
    """The shipped parameterized vignette.dtstyle round-trips byte-for-byte."""
    op_params = _read_op_params(_SHIPPED_VIGNETTE_DTSTYLE)
    assert encode(decode(op_params)) == op_params


def test_decode_extracts_default_brightness() -> None:
    """The shipped vignette.dtstyle ships with brightness=-0.25 (the
    parameter default)."""
    fields = decode(_read_op_params(_SHIPPED_VIGNETTE_DTSTYLE))
    assert fields[2] == pytest.approx(-0.25, abs=1e-5)


@pytest.mark.parametrize("brightness", [-1.0, -0.8, -0.5, -0.25, 0.0, 0.5, 1.0])
def test_patch_sets_brightness_value(brightness: float) -> None:
    """``patch(blob, brightness=v)`` produces a blob whose brightness
    field equals v."""
    src = _read_op_params(_SHIPPED_VIGNETTE_DTSTYLE)
    out = patch(src, brightness=brightness)
    fields = decode(out)
    assert fields[2] == pytest.approx(brightness, abs=1e-5)


def test_patch_preserves_bytes_outside_brightness_field() -> None:
    """Bytes 0..7 and 12..43 are byte-identical before and after patching."""
    src = _read_op_params(_SHIPPED_VIGNETTE_DTSTYLE)
    src_bytes = bytes.fromhex(src)
    patched_bytes = bytes.fromhex(patch(src, brightness=0.7))
    assert src_bytes[:_BRIGHTNESS_OFFSET] == patched_bytes[:_BRIGHTNESS_OFFSET]
    assert src_bytes[_BRIGHTNESS_OFFSET + 4 :] == patched_bytes[_BRIGHTNESS_OFFSET + 4 :]


def test_patch_preserves_other_fields() -> None:
    """All decoded fields except brightness equal the source's."""
    src = _read_op_params(_SHIPPED_VIGNETTE_DTSTYLE)
    src_fields = decode(src)
    patched_fields = decode(patch(src, brightness=0.3))
    for i in range(len(src_fields)):
        if i == 2:
            continue
        assert patched_fields[i] == src_fields[i], (
            f"field {i} changed: {src_fields[i]} -> {patched_fields[i]}"
        )


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 44 bytes"):
        decode("00" * 16)


def test_decode_rejects_wrong_size_blob() -> None:
    """A blob of the wrong size raises with a modversion-hint message."""
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 28)  # exposure-sized; not vignette


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE
