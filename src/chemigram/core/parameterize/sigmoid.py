"""Path C decoder/encoder for darktable's ``sigmoid`` module (mv3).

Struct layout (verified against darktable 5.4.1 ``src/iop/sigmoid.c``
``dt_iop_sigmoid_params_t`` v3; cross-checked empirically against the
shipped ``contrast_low`` / ``contrast_high`` ``.dtstyle`` entries which
differ only at offset 0):

    offset 0..3   : float middle_grey_contrast    ← parameterized field
    offset 4..7   : float contrast_skewness        (-1.0..+1.0; 0.0 default)
    offset 8..11  : float display_white_target     (20.0..1600.0; 100.0 default)
    offset 12..15 : float display_black_target     (0.0..15.0; 0.0152 default)
    offset 16..19 : enum  color_processing         (uint32; DT_SIGMOID_METHOD_PER_CHANNEL)
    offset 20..23 : float hue_preservation         (0.0..100.0; 100.0 default)
    offset 24..27 : float red_inset
    offset 28..31 : float red_rotation
    offset 32..35 : float green_inset
    offset 36..39 : float green_rotation
    offset 40..43 : float blue_inset
    offset 44..47 : float blue_rotation
    offset 48..51 : float purity
    offset 52..55 : enum  base_primaries           (uint32; DT_SIGMOID_WORK_PROFILE)

Total size: 56 bytes (12 floats + 2 enums).

The :func:`patch` function decodes the hex blob, edits ``contrast``
(``middle_grey_contrast`` at offset 0), re-encodes. Every other field is
preserved from the input — round-trip on an unmodified call returns the
input bytes.
"""

from __future__ import annotations

import struct

# Struct format (little-endian): 4 floats + 1 uint32 + 8 floats + 1 uint32.
_STRUCT_FORMAT = "<4fI8fI"
_STRUCT_SIZE = 56
_CONTRAST_FIELD_INDEX = 0  # middle_grey_contrast — first field
_CONTRAST_OFFSET = 0  # byte offset

# Pinned modversion for v1.6.0 / Phase 4 ship.
SUPPORTED_MODVERSION = 3


def decode(op_params: str) -> tuple[float | int, ...]:
    """Decode a 56-byte sigmoid ``op_params`` hex blob to a 14-tuple.

    Returns ``(middle_grey_contrast, contrast_skewness, display_white_target,
    display_black_target, color_processing, hue_preservation, red_inset,
    red_rotation, green_inset, green_rotation, blue_inset, blue_rotation,
    purity, base_primaries)``. Raises :class:`ValueError` on size mismatch.
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"sigmoid op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv3"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float | int, ...]) -> str:
    """Encode a 14-tuple back to a 56-byte sigmoid ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(op_params: str, *, contrast: float) -> str:
    """Patch the ``middle_grey_contrast`` field in a 56-byte sigmoid blob.

    Decodes the hex blob, replaces the contrast field at byte offset 0
    with the supplied value, re-encodes. Every other field is preserved
    from the input.

    Args:
        op_params: hex-encoded source ``op_params`` (56 bytes / 112 hex
            chars).
        contrast: new ``middle_grey_contrast`` value. Range validation is
            the caller's responsibility; this function applies whatever
            it's given (manifest declares a meaningful photographic range).

    Returns:
        New hex-encoded ``op_params`` (56 bytes / 112 hex chars).

    Raises:
        ValueError: input blob is not 56 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    fields[_CONTRAST_FIELD_INDEX] = float(contrast)
    return encode(tuple(fields))
