"""Path C decoder/encoder for darktable's ``colorequal`` (HSL Color Mixer) module (mv4).

Closes RFC-023 (Draft v0.1) — Lightroom HSL Color Mixer parity. ``colorequal``
is darktable 5.x's modern HSL module, replacing the older ``colorzones``
spline-curve approach with a flat per-color scalar struct. RFC-023 chose
``colorequal`` over ``colorzones`` on three grounds: (1) flat 128-byte
struct is the same shape as ``colorbalancergb`` (Tier 2 in ADR-081);
(2) curve-composition semantics in ``colorzones`` fight Path C's
"patch this byte at this offset" model; (3) darktable's docs steer new
users to ``colorequal``.

Struct layout (verified against darktable 5.4.1 ``src/iop/colorequal.c``
``dt_iop_colorequal_params_t`` v4):

    Globals (offsets 0..27)
    offset 0..3   : float    threshold        (default 0.1)
    offset 4..7   : float    smoothing_hue    (default 1.0)
    offset 8..11  : float    contrast         (default 0.0)
    offset 12..15 : float    white_level      (default 1.0)
    offset 16..19 : float    chroma_size      (default 1.5)
    offset 20..23 : float    param_size       (default 1.0)
    offset 24..27 : gboolean use_filter       (default TRUE)

    Saturation per color (offsets 28..59) — Lightroom HSL Saturation row
    offset 28..31 : float sat_red             ← parameterized
    offset 32..35 : float sat_orange          ← parameterized
    offset 36..39 : float sat_yellow          ← parameterized
    offset 40..43 : float sat_green           ← parameterized
    offset 44..47 : float sat_cyan            ← parameterized
    offset 48..51 : float sat_blue            ← parameterized
    offset 52..55 : float sat_lavender        ← parameterized
    offset 56..59 : float sat_magenta         ← parameterized

    Hue shift per color (offsets 60..91) — Lightroom HSL Hue row
    offset 60..63 : float hue_red             ← parameterized
    offset 64..67 : float hue_orange          ← parameterized
    offset 68..71 : float hue_yellow          ← parameterized
    offset 72..75 : float hue_green           ← parameterized
    offset 76..79 : float hue_cyan            ← parameterized
    offset 80..83 : float hue_blue            ← parameterized
    offset 84..87 : float hue_lavender        ← parameterized
    offset 88..91 : float hue_magenta         ← parameterized

    Brightness per color (offsets 92..123) — Lightroom HSL Luminance row
    offset 92..95   : float bright_red        ← parameterized
    offset 96..99   : float bright_orange     ← parameterized
    offset 100..103 : float bright_yellow     ← parameterized
    offset 104..107 : float bright_green      ← parameterized
    offset 108..111 : float bright_cyan       ← parameterized
    offset 112..115 : float bright_blue       ← parameterized
    offset 116..119 : float bright_lavender   ← parameterized
    offset 120..123 : float bright_magenta    ← parameterized

    Final global
    offset 124..127 : float hue_shift         (default 0.0)

Total size: 128 bytes (31 floats + 1 uint32 use_filter).

Three multi-axis vocabulary entries (per RFC-023): ``hsl_saturation``,
``hsl_hue``, ``hsl_luminance`` — 8 axes each, mirroring how Lightroom
users describe their workflow (channel-pass at a time). The 7 global
fields (threshold / smoothing_hue / contrast / white_level / chroma_size
/ param_size / use_filter / hue_shift) are preserved verbatim through
patch().
"""

from __future__ import annotations

import struct

# Struct format (little-endian):
#   6 floats (globals) + 1 uint32 (use_filter gboolean)
# + 24 floats (8 sat + 8 hue + 8 bright)
# + 1 float (hue_shift)
# = 32 items, 128 bytes.
_STRUCT_FORMAT = "<6fI24ff"
_STRUCT_SIZE = 128

SUPPORTED_MODVERSION = 4

# Map every parameterized axis to its struct field index.
# Globals (0..6) are preserved, not exposed to vocabulary.
# Per-color HSL axes (7..30) are the 24 user-facing parameters.
_AXIS_FIELD_INDICES: dict[str, int] = {
    # Saturation (Lightroom HSL Saturation row) — offsets 28..59
    "sat_red": 7,
    "sat_orange": 8,
    "sat_yellow": 9,
    "sat_green": 10,
    "sat_cyan": 11,
    "sat_blue": 12,
    "sat_lavender": 13,
    "sat_magenta": 14,
    # Hue shift per color (Lightroom HSL Hue row) — offsets 60..91
    "hue_red": 15,
    "hue_orange": 16,
    "hue_yellow": 17,
    "hue_green": 18,
    "hue_cyan": 19,
    "hue_blue": 20,
    "hue_lavender": 21,
    "hue_magenta": 22,
    # Brightness per color (Lightroom HSL Luminance row) — offsets 92..123
    "bright_red": 23,
    "bright_orange": 24,
    "bright_yellow": 25,
    "bright_green": 26,
    "bright_cyan": 27,
    "bright_blue": 28,
    "bright_lavender": 29,
    "bright_magenta": 30,
}

# Byte offsets for documentation and tests (always 4 * field_index).
_AXIS_OFFSETS: dict[str, int] = {name: idx * 4 for name, idx in _AXIS_FIELD_INDICES.items()}


def decode(op_params: str) -> tuple[float | int, ...]:
    """Decode a 128-byte colorequal ``op_params`` hex blob.

    Returns a 32-tuple in struct order. Raises :class:`ValueError` on
    size mismatch (most often a different modversion than mv4).
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"colorequal op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv4"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float | int, ...]) -> str:
    """Encode a 32-tuple back to a 128-byte colorequal ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(op_params: str, **values: float | None) -> str:
    """Patch any combination of colorequal's 24 per-color HSL axes.

    Multi-axis partial-update: caller may supply any subset of the 24
    parameterized axes via keyword arguments. Unknown keys raise
    :class:`TypeError`. Unspecified axes preserved from the input.
    The 7 global fields (threshold, smoothing_hue, contrast, white_level,
    chroma_size, param_size, use_filter) and the trailing ``hue_shift``
    are always preserved.

    Parameterized axes (24 total — one per Lightroom HSL slider):

    Saturation row (Lightroom HSL Saturation, range [-1.0, 1.0]):
      sat_red, sat_orange, sat_yellow, sat_green,
      sat_cyan, sat_blue, sat_lavender, sat_magenta

    Hue row (Lightroom HSL Hue, range [-180, 180] degrees):
      hue_red, hue_orange, hue_yellow, hue_green,
      hue_cyan, hue_blue, hue_lavender, hue_magenta

    Luminance row (Lightroom HSL Luminance, range [-1.0, 1.0]):
      bright_red, bright_orange, bright_yellow, bright_green,
      bright_cyan, bright_blue, bright_lavender, bright_magenta

    Args:
        op_params: hex-encoded source ``op_params`` (128 bytes / 256 hex chars).
        **values: any subset of the 24 axis names listed above.

    Returns:
        New hex-encoded ``op_params`` (128 bytes / 256 hex chars).

    Raises:
        ValueError: input blob is not 128 bytes after hex-decode.
        TypeError: an unrecognized keyword argument was passed.
    """
    unknown = set(values.keys()) - set(_AXIS_FIELD_INDICES.keys())
    if unknown:
        raise TypeError(
            f"colorequal.patch() got unexpected keyword argument(s): {sorted(unknown)}; "
            f"valid axes: {sorted(_AXIS_FIELD_INDICES.keys())}"
        )
    fields = list(decode(op_params))
    for axis_name, value in values.items():
        if value is not None:
            fields[_AXIS_FIELD_INDICES[axis_name]] = float(value)
    return encode(tuple(fields))
