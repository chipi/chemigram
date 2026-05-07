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

The :func:`patch` function accepts:

- Coefficient axes (raw bytes-level): ``red_coeff``, ``green_coeff``,
  ``blue_coeff`` — direct multiplier overrides.
- Photographic-units delta axes (#102 / Kelvin UX wrapper): ``kelvin_delta``,
  ``tint_delta`` — apply a relative shift on top of the source coefficients.
  Linear approximation, daily-use accurate.

When both a coefficient axis and the corresponding delta axis are supplied,
the explicit coefficient wins (last-write semantics — the coefficient kwarg
overrides the delta-derived value).

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

# Linear approximation factor for the photographic-units delta axes
# (#102 / Kelvin UX wrapper). 0.0001 yields ~10% coefficient shift per
# 1000K — a daily-use-accurate photographic feel; not a chromatic-
# adaptation-perfect mapping. Real CAT02/Bradford conversion would be
# camera-primaries-aware, which is out of scope for the UX wrapper.
_KELVIN_PER_COEFF_UNIT = 0.0001
_TINT_PER_COEFF_UNIT = 0.0001


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
    kelvin_delta: float | None = None,
    tint_delta: float | None = None,
) -> str:
    """Patch ``red``, ``green`` and/or ``blue`` coefficient fields in a
    20-byte temperature blob.

    Two parameterization shapes are supported:

    1. **Direct coefficient kwargs** (``red_coeff``, ``green_coeff``,
       ``blue_coeff``) — overwrite the source field with the supplied
       multiplier. Range validation is the caller's responsibility
       (manifest declares range [0.5, 4.0] for each).

    2. **Photographic-units delta kwargs** (``kelvin_delta``, ``tint_delta``)
       — apply a relative linear shift on top of the source coefficients.
       Linear approximation:
       - ``kelvin_delta`` ↑ → red_coeff ↑, blue_coeff ↓ (warmer Kelvin).
         red_coeff *= 1 + kelvin_delta * 0.0001
         blue_coeff *= 1 + (-kelvin_delta * 0.0001)
       - ``tint_delta`` ↑ → green_coeff ↑ (magenta-shifted).
         green_coeff *= 1 + tint_delta * 0.0001
       Daily-use accurate; not chromatic-adaptation-perfect (real CAT02 /
       Bradford conversion would be camera-primaries-aware, which is out
       of scope for the UX wrapper).

    When both a coefficient kwarg and the corresponding delta kwarg are
    supplied, the explicit coefficient wins (last-write semantics — the
    delta is computed first, then the coefficient overwrites).

    Multi-parameter partial-update: caller may supply any subset of the
    five kwargs. Unspecified axes preserved. ``various`` (often +inf
    sentinel) and ``preset`` always preserved.

    Args:
        op_params: hex-encoded source ``op_params`` (20 bytes / 40 hex chars).
        red_coeff, green_coeff, blue_coeff: direct coefficient overrides.
        kelvin_delta: relative warmth shift; positive = warmer. Typical
            range [-3000, 3000]; default 0 (no change).
        tint_delta: relative tint shift; positive = magenta-shifted.
            Typical range [-200, 200]; default 0.

    Returns:
        New hex-encoded ``op_params`` (20 bytes / 40 hex chars).

    Raises:
        ValueError: input blob is not 20 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    # Apply photographic-units deltas first (relative to source).
    if kelvin_delta is not None and kelvin_delta != 0:
        factor = 1.0 + (kelvin_delta * _KELVIN_PER_COEFF_UNIT)
        fields[_RED_FIELD_INDEX] = float(fields[_RED_FIELD_INDEX]) * factor
        fields[_BLUE_FIELD_INDEX] = float(fields[_BLUE_FIELD_INDEX]) * (
            2.0 - factor  # inverse direction; equivalent to *= (1 - kelvin_delta * c)
        )
    if tint_delta is not None and tint_delta != 0:
        factor = 1.0 + (tint_delta * _TINT_PER_COEFF_UNIT)
        fields[_GREEN_FIELD_INDEX] = float(fields[_GREEN_FIELD_INDEX]) * factor
    # Direct coefficient kwargs override any delta-derived values.
    if red_coeff is not None:
        fields[_RED_FIELD_INDEX] = float(red_coeff)
    if green_coeff is not None:
        fields[_GREEN_FIELD_INDEX] = float(green_coeff)
    if blue_coeff is not None:
        fields[_BLUE_FIELD_INDEX] = float(blue_coeff)
    return encode(tuple(fields))
