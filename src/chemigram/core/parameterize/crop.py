"""Path C decoder/encoder for darktable's ``crop`` module (mv3).

Struct layout (verified against darktable 5.4.1 ``src/iop/crop.c``
``dt_iop_crop_params_t`` v3):

    offset 0..3   : float cx       (left margin; 0.0..1.0)   ← parameterized
    offset 4..7   : float cy       (top margin; 0.0..1.0)    ← parameterized
    offset 8..11  : float cw       (right edge; 0.0..1.0)    ← parameterized
    offset 12..15 : float ch       (bottom edge; 0.0..1.0)   ← parameterized
    offset 16..19 : int   ratio_n  (aspect ratio numerator; default -1 = free)
    offset 20..23 : int   ratio_d  (aspect ratio denominator; default -1)

Total size: 24 bytes (4 floats + 2 ints).

This is the first **workflow-primitive** parameterized entry — crop is
not a magnitude shift on a photographic axis (unlike exposure, vignette,
saturation_global), it's a region selection. Treating it as a 4-parameter
parameterized entry rides the same RFC-021 architecture without inventing
a new pattern; the agent / CLI calls it as
``crop --param cx=0.1 --param cy=0.1 --param cw=0.9 --param ch=0.9``.

The :func:`patch` accepts any subset of ``cx``, ``cy``, ``cw``, ``ch`` —
partial-update semantics. ``ratio_n`` and ``ratio_d`` always preserved
from the input (free-aspect-ratio default).
"""

from __future__ import annotations

import struct

# Struct format (little-endian): 4 floats + 2 int32.
_STRUCT_FORMAT = "<4f2i"
_STRUCT_SIZE = 24
_CX_FIELD_INDEX = 0
_CX_OFFSET = 0
_CY_FIELD_INDEX = 1
_CY_OFFSET = 4
_CW_FIELD_INDEX = 2
_CW_OFFSET = 8
_CH_FIELD_INDEX = 3
_CH_OFFSET = 12

SUPPORTED_MODVERSION = 3


def decode(op_params: str) -> tuple[float | int, ...]:
    """Decode a 24-byte crop ``op_params`` hex blob.

    Returns ``(cx, cy, cw, ch, ratio_n, ratio_d)``.
    Raises :class:`ValueError` on size mismatch.
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"crop op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv3"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float | int, ...]) -> str:
    """Encode a 6-tuple back to a 24-byte crop ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(
    op_params: str,
    *,
    cx: float | None = None,
    cy: float | None = None,
    cw: float | None = None,
    ch: float | None = None,
) -> str:
    """Patch any of the four crop margins in a 24-byte crop blob.

    Multi-parameter partial-update: caller may supply any subset.
    Unspecified margins preserved. ``ratio_n`` / ``ratio_d`` always
    preserved (free aspect ratio at the dtstyle default).

    Args:
        op_params: hex-encoded source ``op_params`` (24 bytes / 48 hex
            chars).
        cx, cy, cw, ch: new normalized margin values (each in [0.0, 1.0]).
            Range validation is the caller's responsibility.

    Returns:
        New hex-encoded ``op_params`` (24 bytes / 48 hex chars).

    Raises:
        ValueError: input blob is not 24 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    if cx is not None:
        fields[_CX_FIELD_INDEX] = float(cx)
    if cy is not None:
        fields[_CY_FIELD_INDEX] = float(cy)
    if cw is not None:
        fields[_CW_FIELD_INDEX] = float(cw)
    if ch is not None:
        fields[_CH_FIELD_INDEX] = float(ch)
    return encode(tuple(fields))
