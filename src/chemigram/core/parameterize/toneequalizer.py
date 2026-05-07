"""Path C decoder/encoder for darktable's ``toneequal`` module (mv2).

Struct layout (verified against darktable 5.4.1 ``src/iop/toneequal.c``
``dt_iop_toneequalizer_params_t`` v2). The 9 tone-band nodes are
parameterized; algorithm + mask + enum fields are preserved.

    offset 0..3   : float noise               (-2..2 EV)  ← parameterized
    offset 4..7   : float ultra_deep_blacks   (-2..2 EV)  ← parameterized
    offset 8..11  : float deep_blacks         (-2..2 EV)  ← parameterized
    offset 12..15 : float blacks              (-2..2 EV)  ← parameterized
    offset 16..19 : float shadows             (-2..2 EV)  ← parameterized
    offset 20..23 : float midtones            (-2..2 EV)  ← parameterized
    offset 24..27 : float highlights          (-2..2 EV)  ← parameterized
    offset 28..31 : float whites              (-2..2 EV)  ← parameterized
    offset 32..35 : float speculars           (-2..2 EV)  ← parameterized
    offset 36..39 : float blending            (smoothing diameter; default 5.0)
    offset 40..43 : float smoothing           (sigma; default sqrt(2))
    offset 44..47 : float feathering          (edge refinement; default 1.0)
    offset 48..51 : float quantization        (mask quantization; default 0.0)
    offset 52..55 : float contrast_boost      (default 0.0)
    offset 56..59 : float exposure_boost      (default 0.0)
    offset 60..63 : enum  details             (DT_TONEEQ_EIGF)
    offset 64..67 : enum  method              (DT_TONEEQ_NORM_2)
    offset 68..71 : int   iterations          (default 1)

Total size: 72 bytes (15 floats + 2 enums + 1 int).

The 9 tone-band nodes span roughly -8..0 EV in luminance. Each can be
shifted independently in [-2, +2] EV. Multi-parameter partial-update
semantics: caller may supply any subset of the 9 nodes.

This is the **most complex** parameterized entry in the project: 9
photographic axes plus 6 algorithm fields preserved. Stress-tests the
RFC-021 multi-parameter apply path (helpers._apply_parameter_values_to_dtstyle).
"""

from __future__ import annotations

import struct

# Struct format (little-endian): 15 floats + 2 uint32 + 1 int32.
_STRUCT_FORMAT = "<15f2Ii"
_STRUCT_SIZE = 72

# Tone-band node offsets and field indices in the unpacked tuple.
_NODE_FIELDS: dict[str, tuple[int, int]] = {
    # name -> (field_index_in_unpacked_tuple, byte_offset)
    "noise": (0, 0),
    "ultra_deep_blacks": (1, 4),
    "deep_blacks": (2, 8),
    "blacks": (3, 12),
    "shadows": (4, 16),
    "midtones": (5, 20),
    "highlights": (6, 24),
    "whites": (7, 28),
    "speculars": (8, 32),
}

SUPPORTED_MODVERSION = 2


def decode(op_params: str) -> tuple[float | int, ...]:
    """Decode a 72-byte toneequalizer ``op_params`` hex blob.

    Returns an 18-tuple in struct order (9 nodes, 6 algorithm floats,
    2 enums, 1 int). Raises :class:`ValueError` on size mismatch.
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"toneequalizer op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv2"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float | int, ...]) -> str:
    """Encode an 18-tuple back to a 72-byte toneequalizer ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(
    op_params: str,
    *,
    noise: float | None = None,
    ultra_deep_blacks: float | None = None,
    deep_blacks: float | None = None,
    blacks: float | None = None,
    shadows: float | None = None,
    midtones: float | None = None,
    highlights: float | None = None,
    whites: float | None = None,
    speculars: float | None = None,
) -> str:
    """Patch any of the 9 tone-band nodes in a 72-byte toneequalizer blob.

    Multi-parameter partial-update: caller may supply any subset of the
    9 nodes by name. Unspecified nodes preserved from the input.
    Algorithm fields (blending, smoothing, feathering, quantization,
    contrast_boost, exposure_boost), enum fields (details, method), and
    iterations are always preserved — the parameterized surface is the
    photographic tone-band shifts only.

    Args:
        op_params: hex-encoded source ``op_params`` (72 bytes / 144 hex
            chars).
        noise..speculars: per-node EV shift, or None to preserve.
            Range validation is the caller's responsibility (manifest
            declares each in [-2.0, +2.0]).

    Returns:
        New hex-encoded ``op_params`` (72 bytes / 144 hex chars).

    Raises:
        ValueError: input blob is not 72 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    updates = {
        "noise": noise,
        "ultra_deep_blacks": ultra_deep_blacks,
        "deep_blacks": deep_blacks,
        "blacks": blacks,
        "shadows": shadows,
        "midtones": midtones,
        "highlights": highlights,
        "whites": whites,
        "speculars": speculars,
    }
    for name, value in updates.items():
        if value is not None:
            field_idx, _offset = _NODE_FIELDS[name]
            fields[field_idx] = float(value)
    return encode(tuple(fields))
