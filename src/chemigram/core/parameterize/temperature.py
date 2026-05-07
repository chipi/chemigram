"""Path C decoder/encoder for darktable's ``temperature`` (white balance) module (mv4).

Struct layout (verified against darktable 5.4.1 ``src/iop/temperature.c``
``dt_iop_temperature_params_t`` v4; cross-checked empirically against the
shipped ``wb_warm_subtle`` / ``wb_cool_subtle`` ``.dtstyle`` entries):

    offset 0..3   : float red       (0..8; multiplier coefficient)  ← parameterized
    offset 4..7   : float green     (0..8; usually fixed at 1.0)
    offset 8..11  : float blue      (0..8; multiplier coefficient)  ← parameterized
    offset 12..15 : float various   (0..8; 4Bayer/CYGM 4th channel; +inf sentinel)
    offset 16..19 : int   preset

Total size: 20 bytes (4 floats + 1 int).

This is the **first multi-parameter** parameterized entry per RFC-021 / Phase 4.
``red`` and ``blue`` are the two photographic axes:

- Warmer image: red↑, blue↓ (or red↑ + blue↑ as in wb_warm_subtle, depending
  on baseline white-balance compensation).
- Cooler image: red↓, blue↑.

Storage is RGB coefficients, not temperature/tint. The temperature ↔
RGB-coefficient mapping is camera-specific (depends on primaries).
This decoder operates in the coefficient space directly; the
photographic-axis abstraction (temp/tint) lives a layer above.

The :func:`patch` function accepts ``red_coeff`` and/or ``blue_coeff``
keyword arguments — both optional, partial-update semantics. ``green``,
``various``, and ``preset`` always preserved.
"""

from __future__ import annotations

import struct

# Struct format (little-endian): 4 floats + 1 int32.
_STRUCT_FORMAT = "<4fi"
_STRUCT_SIZE = 20
_RED_FIELD_INDEX = 0
_RED_OFFSET = 0
_BLUE_FIELD_INDEX = 2
_BLUE_OFFSET = 8

SUPPORTED_MODVERSION = 4


def decode(op_params: str) -> tuple[float | int, ...]:
    """Decode a 20-byte temperature ``op_params`` hex blob.

    Returns ``(red, green, blue, various, preset)``. Raises
    :class:`ValueError` on size mismatch.
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"temperature op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv4"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float | int, ...]) -> str:
    """Encode a 5-tuple back to a 20-byte temperature ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(
    op_params: str,
    *,
    red_coeff: float | None = None,
    blue_coeff: float | None = None,
) -> str:
    """Patch ``red`` and/or ``blue`` coefficient fields in a 20-byte
    temperature blob.

    Multi-parameter partial-update: caller may supply either or both
    coefficients. Unspecified coefficients are preserved from the input.
    ``green`` (usually 1.0), ``various`` (often +inf sentinel), and
    ``preset`` are always preserved.

    Args:
        op_params: hex-encoded source ``op_params`` (20 bytes / 40 hex
            chars).
        red_coeff: new ``red`` coefficient. Range validation is the
            caller's responsibility (manifest declares range [0.5, 4.0]).
        blue_coeff: new ``blue`` coefficient. Same range as red_coeff.

    Returns:
        New hex-encoded ``op_params`` (20 bytes / 40 hex chars).

    Raises:
        ValueError: input blob is not 20 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    if red_coeff is not None:
        fields[_RED_FIELD_INDEX] = float(red_coeff)
    if blue_coeff is not None:
        fields[_BLUE_FIELD_INDEX] = float(blue_coeff)
    return encode(tuple(fields))
