"""Round-trip and patching tests for the hazeremoval Path C decoder.

Closes #90 Bucket A.2 — Lightroom Dehaze parity. The hazeremoval mv3
struct is 16 bytes (2 floats + 2 gint). ``strength`` and ``distance``
are independently patchable; ``compatibility_mode`` and ``adaptive`` are
preserved verbatim.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.hazeremoval import (
    _DISTANCE_FIELD_INDEX,
    _DISTANCE_OFFSET,
    _STRENGTH_FIELD_INDEX,
    _STRENGTH_OFFSET,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SHIPPED_DTSTYLE = (
    _REPO_ROOT / "vocabulary/packs/expressive-baseline/layers/L3/hazeremoval/dehaze.dtstyle"
)


def _read_op_params(dtstyle_path: Path) -> str:
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_three() -> None:
    assert SUPPORTED_MODVERSION == 3


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE


def test_round_trip_on_shipped_dtstyle() -> None:
    op_params = _read_op_params(_SHIPPED_DTSTYLE)
    assert encode(decode(op_params)) == op_params


def test_decode_extracts_default_values_from_shipped_dtstyle() -> None:
    """The shipped dehaze.dtstyle uses darktable defaults: strength=0.2,
    distance=0.2, compatibility_mode=FALSE (0), adaptive=TRUE (1)."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    assert fields[_STRENGTH_FIELD_INDEX] == pytest.approx(0.2, abs=1e-5)
    assert fields[_DISTANCE_FIELD_INDEX] == pytest.approx(0.2, abs=1e-5)
    assert fields[2] == 0  # compatibility_mode FALSE
    assert fields[3] == 1  # adaptive TRUE


@pytest.mark.parametrize("strength", [-1.0, -0.5, 0.0, 0.2, 0.6, 1.0])
def test_patch_sets_strength_only(strength: float) -> None:
    """Patching only strength leaves distance at the source value."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_distance = decode(src)[_DISTANCE_FIELD_INDEX]
    out = patch(src, strength=strength)
    fields = decode(out)
    assert fields[_STRENGTH_FIELD_INDEX] == pytest.approx(strength, abs=1e-5)
    assert fields[_DISTANCE_FIELD_INDEX] == pytest.approx(src_distance, abs=1e-5)


@pytest.mark.parametrize("distance", [0.0, 0.2, 0.5, 1.0])
def test_patch_sets_distance_only(distance: float) -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_strength = decode(src)[_STRENGTH_FIELD_INDEX]
    out = patch(src, distance=distance)
    fields = decode(out)
    assert fields[_DISTANCE_FIELD_INDEX] == pytest.approx(distance, abs=1e-5)
    assert fields[_STRENGTH_FIELD_INDEX] == pytest.approx(src_strength, abs=1e-5)


def test_patch_sets_both_axes() -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    out = patch(src, strength=0.7, distance=0.4)
    fields = decode(out)
    assert fields[_STRENGTH_FIELD_INDEX] == pytest.approx(0.7, abs=1e-5)
    assert fields[_DISTANCE_FIELD_INDEX] == pytest.approx(0.4, abs=1e-5)


def test_patch_with_no_args_is_identity() -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    assert patch(src) == src


def test_patch_preserves_compatibility_mode_and_adaptive() -> None:
    """compatibility_mode and adaptive (boolean ints at offsets 8, 12) must
    survive every patch — they're behavior-mode flags darktable's runtime
    relies on."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_fields = decode(src)
    patched = decode(patch(src, strength=-0.5, distance=0.8))
    assert patched[2] == src_fields[2]
    assert patched[3] == src_fields[3]


def test_patch_preserves_bytes_outside_strength_distance() -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_bytes = bytes.fromhex(src)
    patched_bytes = bytes.fromhex(patch(src, strength=0.9, distance=0.6))
    assert src_bytes[8:16] == patched_bytes[8:16]
    assert (
        src_bytes[_STRENGTH_OFFSET : _STRENGTH_OFFSET + 4]
        != patched_bytes[_STRENGTH_OFFSET : _STRENGTH_OFFSET + 4]
    )
    assert (
        src_bytes[_DISTANCE_OFFSET : _DISTANCE_OFFSET + 4]
        != patched_bytes[_DISTANCE_OFFSET : _DISTANCE_OFFSET + 4]
    )


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 16 bytes"):
        decode("00" * 8)


def test_decode_rejects_wrong_size_blob() -> None:
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 28)
