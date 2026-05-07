"""Path C decoder/encoder for darktable's ``sharpen`` module (mv1).

Struct layout (verified against darktable 5.4.1 ``src/iop/sharpen.c``
``dt_iop_sharpen_params_t`` v1):

    offset 0..3  : float radius     (0..99; default 2.0)
    offset 4..7  : float amount     (0..2; default 0.5)   ← parameterized
    offset 8..11 : float threshold  (0..100; default 0.5)

Total size: 12 bytes (3 floats).

The ``amount`` axis is the photographic "strength of the sharpen" axis —
the natural single-parameter agent surface. Radius (spatial extent) and
threshold (activation point) are preserved at the dtstyle's encoded
defaults; advanced workflows that need to vary those would author a
separate dtstyle or a personal pack entry.

The :func:`patch` function decodes the hex blob, edits the ``amount``
field at offset 4, re-encodes.
"""

from __future__ import annotations

import struct

# Struct format (little-endian): 3 floats.
_STRUCT_FORMAT = "<3f"
_STRUCT_SIZE = 12
_AMOUNT_FIELD_INDEX = 1
_AMOUNT_OFFSET = 4

SUPPORTED_MODVERSION = 1


def decode(op_params: str) -> tuple[float, ...]:
    """Decode a 12-byte sharpen ``op_params`` hex blob.

    Returns ``(radius, amount, threshold)``. Raises :class:`ValueError`
    on size mismatch.
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"sharpen op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv1"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float, ...]) -> str:
    """Encode a 3-tuple back to a 12-byte sharpen ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(op_params: str, *, amount: float) -> str:
    """Patch the ``amount`` field in a 12-byte sharpen blob.

    Decodes the hex blob, replaces the ``amount`` field at byte offset 4
    with the supplied value, re-encodes. Radius + threshold preserved.

    Args:
        op_params: hex-encoded source ``op_params`` (12 bytes / 24 hex
            chars).
        amount: new sharpening strength. Range validation is the caller's
            responsibility (manifest declares range [0.0, 2.0]).

    Returns:
        New hex-encoded ``op_params`` (12 bytes / 24 hex chars).

    Raises:
        ValueError: input blob is not 12 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    fields[_AMOUNT_FIELD_INDEX] = float(amount)
    return encode(tuple(fields))
