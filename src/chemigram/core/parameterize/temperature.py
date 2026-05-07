"""Path C decoder/encoder for darktable's ``temperature`` (white balance) module (mv4).

Struct layout (verified against darktable 5.4.1 ``src/iop/temperature.c``
``dt_iop_temperature_params_t`` v4; cross-checked empirically against the
shipped ``wb_warm_subtle`` / ``wb_cool_subtle`` ``.dtstyle`` entries):

    offset 0..3   : float red       (0..8; multiplier coefficient)  ← parameterized
    offset 4..7   : float green     (0..8; multiplier coefficient)  ← parameterized (tint)
    offset 8..11  : float blue      (0..8; multiplier coefficient)  ← parameterized
    offset 12..15 : float various   (0..8; 4Bayer/CYGM 4th channel; +inf sentinel)
    offset 16..19 : int   preset

Total size: 20 bytes (4 floats + 1 int).

Three photographic axes (#90 Bucket A.3 — Lightroom WB Tint parity):

- **Warmth (Kelvin)**: red↑ + blue↓ → warmer; red↓ + blue↑ → cooler.
  Driven by ``red_coeff`` and ``blue_coeff``.
- **Tint (green-magenta)**: green↑ → magenta-shifted (less green); green↓ → green-shifted.
  Driven by ``green_coeff``. Lightroom's Tint slider maps directly here.

Storage is RGB coefficients, not temperature/tint photographically. The
mapping is camera-specific (depends on primaries). This decoder operates
in the coefficient space directly.

The :func:`patch` function accepts ``red_coeff``, ``green_coeff`` and/or
``blue_coeff`` keyword arguments — all optional, partial-update semantics.
``various`` and ``preset`` are always preserved.
"""

from __future__ import annotations

import struct

# Struct format (little-endian): 4 floats + 1 int32.
_STRUCT_FORMAT = "<4fi"
_STRUCT_SIZE = 20
_RED_FIELD_INDEX = 0
_RED_OFFSET = 0
_GREEN_FIELD_INDEX = 1
_GREEN_OFFSET = 4
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
    green_coeff: float | None = None,
    blue_coeff: float | None = None,
) -> str:
    """Patch ``red``, ``green`` and/or ``blue`` coefficient fields in a
    20-byte temperature blob.

    Multi-parameter partial-update: caller may supply any subset of
    coefficients. Unspecified coefficients are preserved from the input.
    ``various`` (often +inf sentinel) and ``preset`` are always preserved.

    Args:
        op_params: hex-encoded source ``op_params`` (20 bytes / 40 hex
            chars).
        red_coeff: new ``red`` coefficient. Range validation is the
            caller's responsibility (manifest declares range [0.5, 4.0]).
        green_coeff: new ``green`` coefficient (Lightroom Tint axis). Same
            range as red_coeff. Default in shipped raws is 1.0.
        blue_coeff: new ``blue`` coefficient. Same range as red_coeff.

    Returns:
        New hex-encoded ``op_params`` (20 bytes / 40 hex chars).

    Raises:
        ValueError: input blob is not 20 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    if red_coeff is not None:
        fields[_RED_FIELD_INDEX] = float(red_coeff)
    if green_coeff is not None:
        fields[_GREEN_FIELD_INDEX] = float(green_coeff)
    if blue_coeff is not None:
        fields[_BLUE_FIELD_INDEX] = float(blue_coeff)
    return encode(tuple(fields))
