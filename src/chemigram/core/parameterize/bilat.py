"""Path C decoder/encoder for darktable's ``bilat`` (local contrast) module (mv3).

Struct layout (verified against darktable 5.4.1 ``src/iop/bilat.c``
``dt_iop_bilat_params_t`` v3; cross-checked empirically against the
shipped ``clarity_strong`` / ``clarity_painterly`` ``.dtstyle`` entries):

    offset 0..3   : enum  mode    (0 = bilateral grid; 1 = local laplacian)
    offset 4..7   : float sigma_r (0.0..100.0; in laplacian mode = highlights)
    offset 8..11  : float sigma_s (0.0..100.0; in laplacian mode = shadows)
    offset 12..15 : float detail  (-1.0..4.0; the local-contrast STRENGTH)  ← parameterized
    offset 16..19 : float midtone (0.001..1.0; midtone range)

Total size: 20 bytes (1 enum + 4 floats).

Per the capability survey § 10, only the **strength axis** of clarity is
parameterized. ``clarity_painterly`` remains a discrete entry because it
represents a different *kind* of clarity (lower sigma_r/s/midtone shaping)
not a different strength on the same axis.

The :func:`patch` function decodes the hex blob, edits the ``detail``
field at offset 12, re-encodes. Every other field is preserved.
"""

from __future__ import annotations

import struct

# Struct format (little-endian): 1 uint32 (enum) + 4 floats.
_STRUCT_FORMAT = "<I4f"
_STRUCT_SIZE = 20
_DETAIL_FIELD_INDEX = 3  # 4th field in unpack output (after the enum)
_DETAIL_OFFSET = 12

SUPPORTED_MODVERSION = 3


def decode(op_params: str) -> tuple[float | int, ...]:
    """Decode a 20-byte bilat ``op_params`` hex blob to a 5-tuple.

    Returns ``(mode, sigma_r, sigma_s, detail, midtone)``. Raises
    :class:`ValueError` on size mismatch.
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"bilat op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv3"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float | int, ...]) -> str:
    """Encode a 5-tuple back to a 20-byte bilat ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(op_params: str, *, clarity_strength: float) -> str:
    """Patch the ``detail`` field (clarity strength) in a 20-byte bilat blob.

    Decodes the hex blob, replaces the ``detail`` field at byte offset 12
    with the supplied value, re-encodes. Mode + sigma_r + sigma_s +
    midtone are preserved from the input — so the dtstyle's underlying
    *kind* of clarity (typically the local-laplacian shaping baked into
    clarity_strong) survives the parameterization.

    Args:
        op_params: hex-encoded source ``op_params`` (20 bytes / 40 hex
            chars).
        clarity_strength: new ``detail`` value. Range validation is the
            caller's responsibility (manifest declares range [-1.0, 4.0]).

    Returns:
        New hex-encoded ``op_params`` (20 bytes / 40 hex chars).

    Raises:
        ValueError: input blob is not 20 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    fields[_DETAIL_FIELD_INDEX] = float(clarity_strength)
    return encode(tuple(fields))
