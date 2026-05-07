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

# Parameterized axes (RFC-021 / RFC-022 Tier 2 + #86 brilliance + #91 Bucket A.5).
# Field indices in the 33-tuple returned by decode(); byte offsets in the blob.
_SATURATION_GLOBAL_FIELD_INDEX = 19  # offset 76 — global saturation
_SATURATION_GLOBAL_OFFSET = 76
_CHROMA_GLOBAL_FIELD_INDEX = 17  # offset 68 — global chroma
_CHROMA_GLOBAL_OFFSET = 68
_HUE_ANGLE_FIELD_INDEX = 23  # offset 92 — global hue rotation
_HUE_ANGLE_OFFSET = 92
_VIBRANCE_FIELD_INDEX = 29  # offset 116 — vibrance
_VIBRANCE_OFFSET = 116
# Brilliance axes (#86): per-zone luminance shaping
_BRILLIANCE_GLOBAL_FIELD_INDEX = 24  # offset 96
_BRILLIANCE_GLOBAL_OFFSET = 96
_BRILLIANCE_HIGHLIGHTS_FIELD_INDEX = 25  # offset 100
_BRILLIANCE_HIGHLIGHTS_OFFSET = 100
_BRILLIANCE_MIDTONES_FIELD_INDEX = 26  # offset 104
_BRILLIANCE_MIDTONES_OFFSET = 104
_BRILLIANCE_SHADOWS_FIELD_INDEX = 27  # offset 108
_BRILLIANCE_SHADOWS_OFFSET = 108
# Per-zone hue (#91 Bucket A.5): Lightroom Color Grading wheels
_HUE_SHADOWS_FIELD_INDEX = 2  # offset 8
_HUE_SHADOWS_OFFSET = 8
_HUE_MIDTONES_FIELD_INDEX = 5  # offset 20
_HUE_MIDTONES_OFFSET = 20
_HUE_HIGHLIGHTS_FIELD_INDEX = 8  # offset 32
_HUE_HIGHLIGHTS_OFFSET = 32
# Per-zone saturation (#91 Bucket A.5)
_SATURATION_HIGHLIGHTS_FIELD_INDEX = 20  # offset 80
_SATURATION_HIGHLIGHTS_OFFSET = 80
_SATURATION_MIDTONES_FIELD_INDEX = 21  # offset 84
_SATURATION_MIDTONES_OFFSET = 84
_SATURATION_SHADOWS_FIELD_INDEX = 22  # offset 88
_SATURATION_SHADOWS_OFFSET = 88
# Blending + Balance (#91 Bucket A.5): Lightroom Color Grading panel's
# bottom two sliders. shadows_weight and highlights_weight control the
# falloff into each zone (Lightroom calls this "Blending"); white_fulcrum
# shifts where the shadow/highlight midpoint sits (Lightroom "Balance").
_SHADOWS_WEIGHT_FIELD_INDEX = 12  # offset 48
_SHADOWS_WEIGHT_OFFSET = 48
_WHITE_FULCRUM_FIELD_INDEX = 13  # offset 52
_WHITE_FULCRUM_OFFSET = 52
_HIGHLIGHTS_WEIGHT_FIELD_INDEX = 14  # offset 56
_HIGHLIGHTS_WEIGHT_OFFSET = 56

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


# Map every parameterized axis to its struct field index. Used by patch()
# to drive a single loop instead of branching per-axis (otherwise C901
# complexity grows linearly with the number of axes — 17 axes triggers it).
_AXIS_FIELD_INDICES: dict[str, int] = {
    "saturation_global": _SATURATION_GLOBAL_FIELD_INDEX,
    "chroma_global": _CHROMA_GLOBAL_FIELD_INDEX,
    "hue_angle": _HUE_ANGLE_FIELD_INDEX,
    "vibrance": _VIBRANCE_FIELD_INDEX,
    "brilliance_global": _BRILLIANCE_GLOBAL_FIELD_INDEX,
    "brilliance_highlights": _BRILLIANCE_HIGHLIGHTS_FIELD_INDEX,
    "brilliance_midtones": _BRILLIANCE_MIDTONES_FIELD_INDEX,
    "brilliance_shadows": _BRILLIANCE_SHADOWS_FIELD_INDEX,
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


def patch(
    op_params: str,
    *,
    saturation_global: float | None = None,
    chroma_global: float | None = None,
    hue_angle: float | None = None,
    vibrance: float | None = None,
    brilliance_global: float | None = None,
    brilliance_highlights: float | None = None,
    brilliance_midtones: float | None = None,
    brilliance_shadows: float | None = None,
    # #91 Bucket A.5: Lightroom Color Grading parity
    hue_shadows: float | None = None,
    hue_midtones: float | None = None,
    hue_highlights: float | None = None,
    saturation_shadows: float | None = None,
    saturation_midtones: float | None = None,
    saturation_highlights: float | None = None,
    shadows_weight: float | None = None,
    highlights_weight: float | None = None,
    white_fulcrum: float | None = None,
) -> str:
    """Patch any combination of colorbalancergb's parameterized axes.

    Multi-axis partial-update: caller may supply any subset of the
    declared parameters. Unspecified axes preserved from the input.
    Every other field in the 132-byte struct (chroma per zone, output
    gamma, the ``saturation_formula`` enum, etc.) is always preserved.

    Parameterized axes (RFC-021 / RFC-022 Tier 2 + #86 brilliance + #91 Bucket A.5):

    - ``saturation_global``    (offset 76; range [-1.0, +1.0]).
    - ``chroma_global``        (offset 68; range [-1.0, +1.0]).
    - ``hue_angle``            (offset 92; range [-180.0, +180.0]; degrees).
    - ``vibrance``             (offset 116; range [-1.0, +1.0]).
    - ``brilliance_global``    (offset 96; range [-1.0, +1.0]; per-zone luma).
    - ``brilliance_highlights`` (offset 100; range [-1.0, +1.0]).
    - ``brilliance_midtones``  (offset 104; range [-1.0, +1.0]).
    - ``brilliance_shadows``   (offset 108; range [-1.0, +1.0]).
    - ``hue_shadows``          (offset 8; degrees, 0..360).
    - ``hue_midtones``         (offset 20; degrees).
    - ``hue_highlights``       (offset 32; degrees).
    - ``saturation_shadows``   (offset 88; range [-1.0, +1.0]).
    - ``saturation_midtones``  (offset 84; range [-1.0, +1.0]).
    - ``saturation_highlights`` (offset 80; range [-1.0, +1.0]).
    - ``shadows_weight``       (offset 48; Lightroom "Blending" bottom).
    - ``highlights_weight``    (offset 56; Lightroom "Blending" top).
    - ``white_fulcrum``        (offset 52; Lightroom "Balance"; default 0.0).

    Args:
        op_params: hex-encoded source ``op_params`` (132 bytes / 264 hex
            chars).
        Each axis is independently optional; ``None`` preserves the
        dtstyle's encoded value.

    Returns:
        New hex-encoded ``op_params`` (132 bytes / 264 hex chars).

    Raises:
        ValueError: input blob is not 132 bytes after hex-decode.
    """
    supplied = {
        "saturation_global": saturation_global,
        "chroma_global": chroma_global,
        "hue_angle": hue_angle,
        "vibrance": vibrance,
        "brilliance_global": brilliance_global,
        "brilliance_highlights": brilliance_highlights,
        "brilliance_midtones": brilliance_midtones,
        "brilliance_shadows": brilliance_shadows,
        "hue_shadows": hue_shadows,
        "hue_midtones": hue_midtones,
        "hue_highlights": hue_highlights,
        "saturation_shadows": saturation_shadows,
        "saturation_midtones": saturation_midtones,
        "saturation_highlights": saturation_highlights,
        "shadows_weight": shadows_weight,
        "highlights_weight": highlights_weight,
        "white_fulcrum": white_fulcrum,
    }
    fields = list(decode(op_params))
    for axis_name, value in supplied.items():
        if value is not None:
            fields[_AXIS_FIELD_INDICES[axis_name]] = float(value)
    return encode(tuple(fields))
