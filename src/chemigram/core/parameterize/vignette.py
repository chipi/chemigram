"""Path C decoder/encoder for darktable's ``vignette`` module (mv4).

Struct layout (verified empirically against shipped ``.dtstyle`` entries
in ``vocabulary/packs/expressive-baseline/layers/L3/vignette/``;
matches darktable 5.4.1 ``src/iop/vignette.c`` ``dt_iop_vignette_params_t``):

    offset 0..3   : float scale            (default 80.0; 0..200)
    offset 4..7   : float falloff_scale    (default 50.0; 0..200)
    offset 8..11  : float brightness       (-1.0..+1.0; **parameterized**)
    offset 12..15 : float saturation       (-1.0..+1.0)
    offset 16..19 : float center_x
    offset 20..23 : float center_y
    offset 24..27 : int   autoratio (0/1)
    offset 28..31 : float whratio
    offset 32..35 : float shape
    offset 36..39 : uint  dithering
    offset 40..43 : int   unbound (0/1)

Total size: 44 bytes.

The :func:`patch` function decodes the hex blob, edits ``brightness``
(field at offset 8), re-encodes. Every other field is preserved from
the input — round-trip on an unmodified call returns the input bytes.
"""

from __future__ import annotations

import struct

# Struct format (little-endian): 6 floats + 1 int + 2 floats + 1 uint + 1 int = 44 bytes.
_STRUCT_FORMAT = "<ffffffiffIi"
_STRUCT_SIZE = 44
_BRIGHTNESS_FIELD_INDEX = 2  # third field in struct.unpack output
_BRIGHTNESS_OFFSET = 8  # byte offset of the brightness field in the packed blob

# Pinned modversion for v1.6.0 ship.
SUPPORTED_MODVERSION = 4


def decode(
    op_params: str,
) -> tuple[float, float, float, float, float, float, int, float, float, int, int]:
    """Decode a 44-byte vignette ``op_params`` hex blob to an 11-tuple.

    Returns ``(scale, falloff_scale, brightness, saturation, center_x,
    center_y, autoratio, whratio, shape, dithering, unbound)``. Raises
    :class:`ValueError` on size mismatch.
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"vignette op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv4"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(
    fields: tuple[float, float, float, float, float, float, int, float, float, int, int],
) -> str:
    """Encode an 11-tuple back to a 44-byte vignette ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(op_params: str, *, brightness: float) -> str:
    """Patch the ``brightness`` field in a 44-byte vignette ``op_params`` blob.

    Decodes the hex blob, replaces the brightness field at byte offset 8
    with the supplied value, re-encodes. Every other field is preserved
    from the input.

    Args:
        op_params: hex-encoded source ``op_params`` (44 bytes / 88 hex chars).
        brightness: new brightness value. Range validation is the
            caller's responsibility; this function applies whatever it's
            given (manifest declares range [-1.0, +1.0]).

    Returns:
        New hex-encoded ``op_params`` (44 bytes / 88 hex chars).

    Raises:
        ValueError: input blob is not 44 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    fields[_BRIGHTNESS_FIELD_INDEX] = float(brightness)
    return encode(tuple(fields))  # type: ignore[arg-type]
