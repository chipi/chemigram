"""Path C decoder/encoder for darktable's ``colorbalancergb`` module (mv5).

Struct layout (verified against darktable 5.4.1 ``src/iop/colorbalancergb.c``
``dt_iop_colorbalancergb_params_t`` v5; cross-checked empirically against
the shipped ``sat_kill`` / ``sat_boost_moderate`` / ``sat_boost_strong``
``.dtstyle`` entries which differ only at offset 76):

    offset 0..3    : float shadows_Y
    offset 4..7    : float shadows_C
    offset 8..11   : float shadows_H
    offset 12..15  : float midtones_Y
    offset 16..19  : float midtones_C
    offset 20..23  : float midtones_H
    offset 24..27  : float highlights_Y
    offset 28..31  : float highlights_C
    offset 32..35  : float highlights_H
    offset 36..39  : float global_Y
    offset 40..43  : float global_C
    offset 44..47  : float global_H
    offset 48..51  : float shadows_weight
    offset 52..55  : float white_fulcrum
    offset 56..59  : float highlights_weight
    offset 60..63  : float chroma_shadows
    offset 64..67  : float chroma_highlights
    offset 68..71  : float chroma_global
    offset 72..75  : float chroma_midtones
    offset 76..79  : float saturation_global   ← parameterized field
    offset 80..83  : float saturation_highlights
    offset 84..87  : float saturation_midtones
    offset 88..91  : float saturation_shadows
    offset 92..95  : float hue_angle
    offset 96..99  : float brilliance_global
    offset 100..103: float brilliance_highlights
    offset 104..107: float brilliance_midtones
    offset 108..111: float brilliance_shadows
    offset 112..115: float mask_grey_fulcrum
    offset 116..119: float vibrance
    offset 120..123: float grey_fulcrum
    offset 124..127: float contrast
    offset 128..131: enum  saturation_formula (uint32)

Total size: 132 bytes (32 floats + 1 enum).

The :func:`patch` function decodes the hex blob, edits ``saturation_global``
(field at offset 76), re-encodes. Every other field is preserved from the
input — round-trip on an unmodified call returns the input bytes.
"""

from __future__ import annotations

import struct

# Struct format (little-endian): 32 floats + 1 uint32 (saturation_formula enum).
_STRUCT_FORMAT = "<32fI"
_STRUCT_SIZE = 132

# Parameterized axes (RFC-021 / RFC-022 Tier 2). Field indices in the
# 33-tuple returned by decode(); byte offsets in the packed blob.
_SATURATION_GLOBAL_FIELD_INDEX = 19  # offset 76 — global saturation
_SATURATION_GLOBAL_OFFSET = 76
_CHROMA_GLOBAL_FIELD_INDEX = 17  # offset 68 — global chroma
_CHROMA_GLOBAL_OFFSET = 68
_HUE_ANGLE_FIELD_INDEX = 23  # offset 92 — global hue rotation
_HUE_ANGLE_OFFSET = 92
_VIBRANCE_FIELD_INDEX = 29  # offset 116 — vibrance
_VIBRANCE_OFFSET = 116

# Pinned modversion for v1.6.0 / Phase 4 ship.
SUPPORTED_MODVERSION = 5


def decode(op_params: str) -> tuple[float | int, ...]:
    """Decode a 132-byte colorbalancergb ``op_params`` hex blob.

    Returns a 33-tuple: 32 floats (in struct order, see module docstring)
    followed by the ``saturation_formula`` enum as a uint32. Raises
    :class:`ValueError` on size mismatch (most often a different
    modversion than mv5).
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"colorbalancergb op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv5"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float | int, ...]) -> str:
    """Encode a 33-tuple back to a 132-byte colorbalancergb ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(
    op_params: str,
    *,
    saturation_global: float | None = None,
    chroma_global: float | None = None,
    hue_angle: float | None = None,
    vibrance: float | None = None,
) -> str:
    """Patch any combination of colorbalancergb's parameterized axes.

    Multi-axis partial-update: caller may supply any subset of the
    declared parameters. Unspecified axes preserved from the input.
    Every other field in the 132-byte struct (per-zone saturation,
    brilliance, chroma per zone, grading angles, output gamma, the
    ``saturation_formula`` enum, etc.) is always preserved.

    The four parameterized axes per RFC-021 / RFC-022 Tier 2:

    - ``saturation_global`` (offset 76; range [-1.0, +1.0]; -1.0 →
      monochrome, +0.5 → strong boost). Replaces v1.5.x sat_kill /
      sat_boost_moderate / sat_boost_strong.
    - ``chroma_global``    (offset 68; range [-1.0, +1.0]; vibrance-like
      chroma push that protects already-saturated pixels less than
      vibrance does).
    - ``hue_angle``        (offset 92; range [-180.0, +180.0]; degrees of
      global hue rotation).
    - ``vibrance``         (offset 116; range [-1.0, +1.0]; protects
      saturated pixels). Replaces v1.5.x vibrance_+0.3.

    Args:
        op_params: hex-encoded source ``op_params`` (132 bytes / 264 hex
            chars).
        saturation_global: new global saturation, or None to preserve.
        chroma_global: new global chroma, or None to preserve.
        hue_angle: new hue-rotation angle in degrees, or None to preserve.
        vibrance: new vibrance, or None to preserve.

    Returns:
        New hex-encoded ``op_params`` (132 bytes / 264 hex chars).

    Raises:
        ValueError: input blob is not 132 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    if saturation_global is not None:
        fields[_SATURATION_GLOBAL_FIELD_INDEX] = float(saturation_global)
    if chroma_global is not None:
        fields[_CHROMA_GLOBAL_FIELD_INDEX] = float(chroma_global)
    if hue_angle is not None:
        fields[_HUE_ANGLE_FIELD_INDEX] = float(hue_angle)
    if vibrance is not None:
        fields[_VIBRANCE_FIELD_INDEX] = float(vibrance)
    return encode(tuple(fields))
