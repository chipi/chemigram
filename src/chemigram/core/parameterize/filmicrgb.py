"""Path C decoder/encoder for darktable's ``filmicrgb`` (filmic v6) module (mv6).

Closes #97 — modern darktable tone-mapping module. Filmic ships parallel
to ``sigmoid`` (already parameterized as ``sigmoid_contrast``); the two
are alternative tone-mapping paths and chemigram exposes both. Per
``capability-survey.md``, ``sigmoid`` covers ~80% of the photographic
tone-mapping use case; filmic is the path for users who want explicit
log-encoding control with separate shadow/highlight curve modes.

Struct layout (verified against darktable 5.4.1 ``src/iop/filmicrgb.c``
``dt_iop_filmicrgb_params_t`` v6):

    Magnitude axes — input range definition (parameterized)
    offset 0..3   : float grey_point_source        ← parameterized (default 18.45%)
    offset 4..7   : float black_point_source       ← parameterized (default -8.0 EV)
    offset 8..11  : float white_point_source       ← parameterized (default 4.0 EV)

    Highlight reconstruction (preserved verbatim)
    offset 12..15 : float reconstruct_threshold       (default 0.0)
    offset 16..19 : float reconstruct_feather         (default 3.0)
    offset 20..23 : float reconstruct_bloom_vs_details (default 100.0)
    offset 24..27 : float reconstruct_grey_vs_color   (default 100.0)
    offset 28..31 : float reconstruct_structure_vs_texture (default 0.0)

    More magnitude axes
    offset 32..35 : float security_factor            (preserved; default 0.0)
    offset 36..39 : float grey_point_target          (preserved; default 18.45)
    offset 40..43 : float black_point_target         (preserved; default 0.01517634)
    offset 44..47 : float white_point_target         (preserved; default 100.0)
    offset 48..51 : float output_power              ← parameterized (default 4.0)
    offset 52..55 : float latitude                  ← parameterized (default 0.01)
    offset 56..59 : float contrast                  ← parameterized (default 1.0)
    offset 60..63 : float saturation                ← parameterized (default 0.0)
    offset 64..67 : float balance                   ← parameterized (default 0.0)
    offset 68..71 : float noise_level                (preserved; default 0.2)

    Mode/enum/gboolean fields — all preserved verbatim
    offset 72..75   : enum  preserve_color             (default DT_FILMIC_METHOD_POWER_NORM = 3)
    offset 76..79   : enum  version                    (default DT_FILMIC_COLORSCIENCE_V5 = 4)
    offset 80..83   : gbool auto_hardness              (default TRUE = 1)
    offset 84..87   : gbool custom_grey                (default FALSE = 0)
    offset 88..91   : int   high_quality_reconstruction (default 1)
    offset 92..95   : enum  noise_distribution         (default DT_NOISE_GAUSSIAN = 1)
    offset 96..99   : enum  shadows                    (default DT_FILMIC_CURVE_POLY_4 = 0)
    offset 100..103 : enum  highlights                 (default DT_FILMIC_CURVE_POLY_4 = 0)
    offset 104..107 : gbool compensate_icc_black       (default FALSE = 0)
    offset 108..111 : enum  spline_version             (default DT_FILMIC_SPLINE_VERSION_V3 = 2)
    offset 112..115 : gbool enable_highlight_reconstruction (default FALSE = 0)

Total size: 116 bytes (18 floats + 11 4-byte int-shaped fields).

Eight parameterized axes — the magnitude knobs a photographer reaches
for. All other fields (curve modes, color science version, spline
version, gbool toggles, reconstruction tuning) are preserved verbatim
through patch(). Mode-switching across the enum fields is intentionally
NOT exposed as parameterization: those are categorical choices, not
magnitude axes; users wanting different filmic modes can author distinct
discrete dtstyle entries.
"""

from __future__ import annotations

import struct

# Struct format: 18 floats + 11 signed-int 4-byte fields = 116 bytes.
_STRUCT_FORMAT = "<18f11i"
_STRUCT_SIZE = 116

SUPPORTED_MODVERSION = 6

# Map every parameterized axis to its struct field index.
# Mode/enum/gboolean fields (18..28) are NOT parameterized and never
# exposed to vocabulary entries — they're pinned at construction time.
_AXIS_FIELD_INDICES: dict[str, int] = {
    "grey_point_source": 0,
    "black_point_source": 1,
    "white_point_source": 2,
    "output_power": 12,
    "latitude": 13,
    "contrast": 14,
    "saturation": 15,
    "balance": 16,
}

# Byte offsets for documentation and tests (always 4 * field_index).
_AXIS_OFFSETS: dict[str, int] = {name: idx * 4 for name, idx in _AXIS_FIELD_INDICES.items()}


def decode(op_params: str) -> tuple[float | int, ...]:
    """Decode a 116-byte filmicrgb ``op_params`` hex blob.

    Returns a 29-tuple in struct order. Raises :class:`ValueError` on
    size mismatch (most often a different modversion than mv6).
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"filmicrgb op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv6"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float | int, ...]) -> str:
    """Encode a 29-tuple back to a 116-byte filmicrgb ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(op_params: str, **values: float | None) -> str:
    """Patch any combination of filmicrgb's 8 parameterized magnitude axes.

    Multi-axis partial-update: caller may supply any subset of the 8
    parameterized axes via keyword arguments. Unknown keys raise
    :class:`TypeError` (catches typos like ``contras=`` for ``contrast=``).
    Unspecified axes are preserved from the input.

    Mode/enum/gboolean fields (``preserve_color``, ``version``, ``auto_hardness``,
    ``custom_grey``, ``high_quality_reconstruction``, ``noise_distribution``,
    ``shadows``, ``highlights``, ``compensate_icc_black``, ``spline_version``,
    ``enable_highlight_reconstruction``) and the reconstruction-tuning floats
    are always preserved through patch().

    Parameterized axes (8 total):

    - ``grey_point_source`` (default 18.45%; range typically [0.1, 50.0]; the
      gray-anchor of the input filmic curve)
    - ``black_point_source`` (default -8.0 EV; range [-16.0, -0.1]; how dark
      the input curve's "black" sits relative to the gray point)
    - ``white_point_source`` (default 4.0 EV; range [0.1, 16.0]; how bright
      the input curve's "white" sits)
    - ``output_power`` (default 4.0; range [0.5, 8.0]; output gamma)
    - ``latitude`` (default 0.01; range [0.0, 100.0]; width of the linear
      midtone region as percent of dynamic range)
    - ``contrast`` (default 1.0; range [0.0, 5.0]; midtone slope)
    - ``saturation`` (default 0.0; range [-100.0, 100.0]; output chroma boost)
    - ``balance`` (default 0.0; range [-50.0, 50.0]; tilts midtone toward
      shadows or highlights)

    Args:
        op_params: hex-encoded source ``op_params`` (116 bytes / 232 hex chars).
        **values: any subset of the 8 axis names listed above.

    Returns:
        New hex-encoded ``op_params`` (116 bytes / 232 hex chars).

    Raises:
        ValueError: input blob is not 116 bytes after hex-decode.
        TypeError: an unrecognized keyword argument was passed.
    """
    unknown = set(values.keys()) - set(_AXIS_FIELD_INDICES.keys())
    if unknown:
        raise TypeError(
            f"filmicrgb.patch() got unexpected keyword argument(s): {sorted(unknown)}; "
            f"valid axes: {sorted(_AXIS_FIELD_INDICES.keys())}"
        )
    fields = list(decode(op_params))
    for axis_name, value in values.items():
        if value is not None:
            fields[_AXIS_FIELD_INDICES[axis_name]] = float(value)
    return encode(tuple(fields))
