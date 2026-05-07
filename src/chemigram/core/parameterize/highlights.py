"""Path C decoder/encoder for darktable's ``highlights`` module (mv4).

Struct layout (verified against darktable 5.4.1 ``src/iop/highlights.c``
``dt_iop_highlights_params_t`` v4; cross-checked empirically against the
shipped ``highlights_recovery_subtle`` / ``highlights_recovery_strong``
``.dtstyle`` entries):

    offset 0..3   : enum  mode             (recovery method)
    offset 4..7   : float blendL           (unused; default 1.0)
    offset 8..11  : float blendC           (unused; default 0.0)
    offset 12..15 : float strength         (0..1; default 0.0)
    offset 16..19 : float clip             (0..2; default 1.0)  ← parameterized
    offset 20..23 : float noise_level      (0..0.5; default 0.0)
    offset 24..27 : int   iterations       (1..256; default 30)
    offset 28..31 : enum  scales           (default WAVELETS_7_SCALE)
    offset 32..35 : float candidating      (0..1; default 0.4)
    offset 36..39 : float combine          (0..8; default 2.0)
    offset 40..43 : enum  recovery         (default DT_RECOVERY_MODE_OFF)
    offset 44..47 : float solid_color      (0..1; default 0.0)

Total size: 48 bytes (4 enums/ints + 8 floats).

Per the capability survey § 10, only the ``clip`` axis is parameterized
("highlights-clip-threshold"). Strength + combine + mode are preserved
from the dtstyle's encoded baseline.

The :func:`patch` function decodes the hex blob, edits the ``clip``
field at offset 16, re-encodes.
"""

from __future__ import annotations

import struct

# Struct format (little-endian): mode(I) + 5 floats + iterations(i) + scales(I)
# + 2 floats + recovery(I) + solid_color(f) = 48 bytes total.
_STRUCT_FORMAT = "<I5fiI2fIf"
_STRUCT_SIZE = 48
_CLIP_FIELD_INDEX = 4  # clip is the 5th field (mode + blendL + blendC + strength + clip)
_CLIP_OFFSET = 16

SUPPORTED_MODVERSION = 4


def decode(op_params: str) -> tuple[float | int, ...]:
    """Decode a 48-byte highlights ``op_params`` hex blob to a 12-tuple.

    Returns ``(mode, blendL, blendC, strength, clip, noise_level,
    iterations, scales, candidating, combine, recovery, solid_color)``.
    Raises :class:`ValueError` on size mismatch.
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"highlights op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv4"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float | int, ...]) -> str:
    """Encode a 12-tuple back to a 48-byte highlights ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(op_params: str, *, clip_threshold: float) -> str:
    """Patch the ``clip`` field in a 48-byte highlights blob.

    Decodes the hex blob, replaces the ``clip`` field at byte offset 16
    with the supplied value, re-encodes. All other fields preserved.

    Args:
        op_params: hex-encoded source ``op_params`` (48 bytes / 96 hex
            chars).
        clip_threshold: new ``clip`` value. Range validation is the
            caller's responsibility (manifest declares range [0.0, 2.0]).
            Lower values trigger more aggressive highlight recovery
            (more pixels treated as "clipped"); 1.0 is darktable default.

    Returns:
        New hex-encoded ``op_params`` (48 bytes / 96 hex chars).

    Raises:
        ValueError: input blob is not 48 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    fields[_CLIP_FIELD_INDEX] = float(clip_threshold)
    return encode(tuple(fields))
