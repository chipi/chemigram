"""Path C decoder/encoder for darktable's ``hazeremoval`` (Dehaze) module (mv3).

Struct layout (verified against darktable 5.4.1 ``src/iop/hazeremoval.c``
``dt_iop_hazeremoval_params_t`` v3):

    offset 0..3   : float    strength             ← parameterized
                              ($MIN: -1.0  $MAX: 1.0  $DEFAULT: 0.2)
    offset 4..7   : float    distance             ← parameterized
                              ($MIN:  0.0  $MAX: 1.0  $DEFAULT: 0.2)
    offset 8..11  : gboolean compatibility_mode   (4-byte int; default FALSE)
    offset 12..15 : gboolean adaptive             (4-byte int; default TRUE)

Total size: 16 bytes (2 floats + 2 gint).

This closes the Lightroom Dehaze parity gap (#90 Bucket A.2). Lightroom's
Dehaze slider maps directly to ``strength`` here:

- ``strength`` ↑ → stronger dehaze (negative values *add* haze, photographic
  fog effect; the slider is bidirectional in both Lightroom and darktable).
- ``distance`` controls the falloff range — how aggressively the algorithm
  treats distant pixels. Most users only touch ``strength``.

The :func:`patch` function accepts ``strength`` and/or ``distance`` keyword
arguments — both optional, partial-update semantics. ``compatibility_mode``
and ``adaptive`` are always preserved from the input.
"""

from __future__ import annotations

import struct

# Struct format (little-endian): 2 floats + 2 gint (4-byte ints) = 16 bytes total.
_STRUCT_FORMAT = "<ffii"
_STRUCT_SIZE = 16
_STRENGTH_FIELD_INDEX = 0
_STRENGTH_OFFSET = 0
_DISTANCE_FIELD_INDEX = 1
_DISTANCE_OFFSET = 4

SUPPORTED_MODVERSION = 3


def decode(op_params: str) -> tuple[float, float, int, int]:
    """Decode a 16-byte hazeremoval ``op_params`` hex blob.

    Returns ``(strength, distance, compatibility_mode, adaptive)``.
    Raises :class:`ValueError` on size mismatch.
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"hazeremoval op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv3"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float, float, int, int]) -> str:
    """Encode a 4-tuple back to a 16-byte hazeremoval ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(
    op_params: str,
    *,
    strength: float | None = None,
    distance: float | None = None,
) -> str:
    """Patch ``strength`` and/or ``distance`` fields in a 16-byte
    hazeremoval blob.

    Multi-parameter partial-update: caller may supply either or both
    axes. Unspecified axes are preserved from the input.
    ``compatibility_mode`` and ``adaptive`` are always preserved.

    Args:
        op_params: hex-encoded source ``op_params`` (16 bytes / 32 hex chars).
        strength: new ``strength`` value. Range validation is the caller's
            responsibility (manifest declares range [-1.0, 1.0]).
        distance: new ``distance`` value. Range [0.0, 1.0] per darktable.

    Returns:
        New hex-encoded ``op_params`` (16 bytes / 32 hex chars).

    Raises:
        ValueError: input blob is not 16 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    if strength is not None:
        fields[_STRENGTH_FIELD_INDEX] = float(strength)
    if distance is not None:
        fields[_DISTANCE_FIELD_INDEX] = float(distance)
    return encode(tuple(fields))  # type: ignore[arg-type]
