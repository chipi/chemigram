"""Round-trip and patching tests for the diffuse Path C decoder.

Closes #92 Bucket A.6 — Lightroom Texture parity. The diffuse-or-sharpen
module exposes detail enhancement at four scales (first/second/third/fourth)
plus a global sharpness axis. We parameterize the three axes most relevant
to Lightroom Texture: first (finest scale), second (next-up scale), and
sharpness (global).

Other axes (anisotropy, regularization, threshold, radius, iterations,
radius_center) are preserved through patch().
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.diffuse import (
    _FIRST_FIELD_INDEX,
    _FIRST_OFFSET,
    _SECOND_FIELD_INDEX,
    _SECOND_OFFSET,
    _SHARPNESS_FIELD_INDEX,
    _SHARPNESS_OFFSET,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SHIPPED_DTSTYLE = (
    _REPO_ROOT / "vocabulary/packs/expressive-baseline/layers/L3/diffuse/texture.dtstyle"
)


def _read_op_params(dtstyle_path: Path) -> str:
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_two() -> None:
    assert SUPPORTED_MODVERSION == 2


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE


def test_round_trip_on_shipped_dtstyle() -> None:
    op_params = _read_op_params(_SHIPPED_DTSTYLE)
    assert encode(decode(op_params)) == op_params


def test_decode_extracts_default_values_from_shipped_dtstyle() -> None:
    """Shipped texture.dtstyle uses darktable defaults: iterations=1, radius=8,
    everything else 0."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    assert fields[0] == 1  # iterations
    assert fields[1] == pytest.approx(0.0, abs=1e-5)  # sharpness
    assert fields[2] == 8  # radius
    assert fields[_FIRST_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)
    assert fields[_SECOND_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)
    assert fields[14] == 0  # radius_center


@pytest.mark.parametrize("first", [-1.0, -0.5, 0.0, 0.3, 0.5, 1.0])
def test_patch_sets_first_only(first: float) -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    out = patch(src, first=first)
    fields = decode(out)
    src_fields = decode(src)
    assert fields[_FIRST_FIELD_INDEX] == pytest.approx(first, abs=1e-5)
    # Every other field unchanged
    for i in range(len(src_fields)):
        if i == _FIRST_FIELD_INDEX:
            continue
        assert fields[i] == src_fields[i]


@pytest.mark.parametrize("second", [-0.5, 0.0, 0.3, 0.7])
def test_patch_sets_second_only(second: float) -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    out = patch(src, second=second)
    fields = decode(out)
    assert fields[_SECOND_FIELD_INDEX] == pytest.approx(second, abs=1e-5)
    src_fields = decode(src)
    for i in range(len(src_fields)):
        if i == _SECOND_FIELD_INDEX:
            continue
        assert fields[i] == src_fields[i]


@pytest.mark.parametrize("sharpness", [-1.0, 0.0, 0.5, 1.0])
def test_patch_sets_sharpness_only(sharpness: float) -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    out = patch(src, sharpness=sharpness)
    fields = decode(out)
    assert fields[_SHARPNESS_FIELD_INDEX] == pytest.approx(sharpness, abs=1e-5)
    src_fields = decode(src)
    for i in range(len(src_fields)):
        if i == _SHARPNESS_FIELD_INDEX:
            continue
        assert fields[i] == src_fields[i]


def test_patch_sets_all_three_axes_simultaneously() -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    out = patch(src, first=0.5, second=0.3, sharpness=0.7)
    fields = decode(out)
    assert fields[_FIRST_FIELD_INDEX] == pytest.approx(0.5, abs=1e-5)
    assert fields[_SECOND_FIELD_INDEX] == pytest.approx(0.3, abs=1e-5)
    assert fields[_SHARPNESS_FIELD_INDEX] == pytest.approx(0.7, abs=1e-5)


def test_patch_with_no_args_is_identity() -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    assert patch(src) == src


def test_patch_preserves_other_fields() -> None:
    """iterations, radius, anisotropy_*, threshold, radius_center, third,
    fourth all preserved across any patch combination."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_fields = decode(src)
    out_fields = decode(patch(src, first=0.5, second=-0.3, sharpness=0.8))
    # Preserved field indices: 0 (iterations), 2 (radius), 3-9 (regularization,
    # variance_threshold, anisotropy x4, threshold), 12-13 (third, fourth), 14 (radius_center)
    preserved_indices = [0, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 14]
    for i in preserved_indices:
        assert out_fields[i] == src_fields[i], f"field {i} should be preserved"


def test_field_offsets_match_indices() -> None:
    """Sanity: byte offsets are 4 * field index."""
    assert _FIRST_OFFSET == _FIRST_FIELD_INDEX * 4
    assert _SECOND_OFFSET == _SECOND_FIELD_INDEX * 4
    assert _SHARPNESS_OFFSET == _SHARPNESS_FIELD_INDEX * 4


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 60 bytes"):
        decode("00" * 8)


def test_decode_rejects_wrong_size_blob() -> None:
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 100)
