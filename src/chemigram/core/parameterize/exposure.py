"""Path C decoder/encoder for darktable's ``exposure`` module (mv7).

Struct layout (verified empirically against shipped ``.dtstyle`` entries
in ``vocabulary/starter/`` and ``vocabulary/packs/expressive-baseline/``;
matches darktable 5.4.1 ``src/iop/exposure.c`` ``dt_iop_exposure_params_t``):

    offset 0..3   : float black_level
    offset 4..7   : float (deprecated — varies across entries; round-trip
                    preserves whatever the source dtstyle stored)
    offset 8..11  : float exposure  ← the parameterized "ev" field
    offset 12..15 : float deflicker_percentile (default 50.0)
    offset 16..19 : float deflicker_target_level (default -4.0)
    offset 20..23 : int   mode
    offset 24..27 : int   compensate (or similar; preserved verbatim)

Total size: 28 bytes.

The :func:`patch` function decodes the hex blob, edits ``exposure``
(field at offset 8), re-encodes. Every other field is preserved from
the input — round-trip on an unmodified call returns the input bytes.
"""

from __future__ import annotations

import struct

# Struct format (little-endian): 5 floats + 2 ints = 28 bytes total.
_STRUCT_FORMAT = "<fffffii"
_STRUCT_SIZE = 28
_EV_FIELD_INDEX = 2  # third field in struct.unpack output
_EV_OFFSET = 8  # byte offset of the EV field in the packed blob

# Pinned modversion for v1.6.0 ship; bumping requires re-verifying the
# struct layout.
SUPPORTED_MODVERSION = 7


def decode(op_params: str) -> tuple[float, float, float, float, float, int, int]:
    """Decode a 28-byte exposure ``op_params`` hex blob to a 7-tuple.

    Returns ``(black_level, _deprecated, ev, deflicker_pct, deflicker_target,
    mode, compensate)``. Raises :class:`ValueError` on size mismatch.
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"exposure op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv7"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float, float, float, float, float, int, int]) -> str:
    """Encode a 7-tuple back to a 28-byte exposure ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(op_params: str, *, ev: float) -> str:
    """Patch the ``exposure`` field in a 28-byte exposure ``op_params`` blob.

    Decodes the hex blob, replaces the ``ev`` (exposure) field at byte
    offset 8 with the supplied value, re-encodes. Every other field is
    preserved from the input.

    Args:
        op_params: hex-encoded source ``op_params`` (28 bytes / 56 hex chars).
        ev: new exposure value in EV (stops). Range validation is the
            caller's responsibility; this function applies whatever it's
            given.

    Returns:
        New hex-encoded ``op_params`` (28 bytes / 56 hex chars).

    Raises:
        ValueError: input blob is not 28 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    fields[_EV_FIELD_INDEX] = float(ev)
    return encode(tuple(fields))  # type: ignore[arg-type]
