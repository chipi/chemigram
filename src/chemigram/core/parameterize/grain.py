"""Path C decoder/encoder for darktable's ``grain`` module (mv2).

Struct layout (verified against darktable 5.4.1 ``src/iop/grain.c``
``dt_iop_grain_params_t`` v2; cross-checked empirically against the
shipped ``grain_fine`` / ``grain_medium`` / ``grain_heavy`` ``.dtstyle``
entries):

    offset 0..3   : enum  channel        (DT_GRAIN_CHANNEL_LIGHTNESS = 2)
    offset 4..7   : float scale          (coarseness; 20/SF..6400/SF; default 1600/SF)
    offset 8..11  : float strength       (0..100; default 25)  ← parameterized
    offset 12..15 : float midtones_bias  (0..100; default 100)

Total size: 16 bytes (1 enum + 3 floats).

The :func:`patch` function decodes the hex blob, edits the ``strength``
field at offset 8, re-encodes. Channel + scale + midtones_bias preserved.
"""

from __future__ import annotations

import struct

# Struct format (little-endian): 1 uint32 + 3 floats.
_STRUCT_FORMAT = "<I3f"
_STRUCT_SIZE = 16
_STRENGTH_FIELD_INDEX = 2
_STRENGTH_OFFSET = 8

SUPPORTED_MODVERSION = 2


def decode(op_params: str) -> tuple[float | int, ...]:
    """Decode a 16-byte grain ``op_params`` hex blob to a 4-tuple.

    Returns ``(channel, scale, strength, midtones_bias)``. Raises
    :class:`ValueError` on size mismatch.
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"grain op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv2"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float | int, ...]) -> str:
    """Encode a 4-tuple back to a 16-byte grain ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(op_params: str, *, grain_strength: float) -> str:
    """Patch the ``strength`` field in a 16-byte grain blob.

    Decodes the hex blob, replaces the ``strength`` field at byte offset 8
    with the supplied value, re-encodes. Channel + scale + midtones_bias
    preserved from the input — so the dtstyle's underlying grain *kind*
    (coarseness, channel) survives parameterization.

    Args:
        op_params: hex-encoded source ``op_params`` (16 bytes / 32 hex
            chars).
        grain_strength: new ``strength`` value. Range validation is the
            caller's responsibility (manifest declares range [0.0, 100.0]).

    Returns:
        New hex-encoded ``op_params`` (16 bytes / 32 hex chars).

    Raises:
        ValueError: input blob is not 16 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    fields[_STRENGTH_FIELD_INDEX] = float(grain_strength)
    return encode(tuple(fields))
