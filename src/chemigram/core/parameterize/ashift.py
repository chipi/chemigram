"""Path C decoder/encoder for darktable's ``ashift`` (perspective/transform) module (mv5).

Closes #101 — Lightroom Transform panel parity. Real workflow gap:
architectural correction (verticals leaning), perspective-correct flat-art
reproduction, post-crop scale-up. Lightroom users reach for this every
time they shoot architectural / interior / flat-art subjects.

Struct layout (verified against darktable 5.4.1 ``src/iop/ashift.c``
``dt_iop_ashift_params_t`` v5):

    Magnitude axes (parameterized)
    offset 0..3   : float rotation       ← parameterized (default 0.0)
    offset 4..7   : float lensshift_v    ← parameterized (default 0.0; vertical perspective)
    offset 8..11  : float lensshift_h    ← parameterized (default 0.0; horizontal perspective)
    offset 12..15 : float shear          ← parameterized (default 0.0)

    Lens-tuning floats (preserved; default suits 35mm film)
    offset 16..19 : float f_length       (default 35.0; focal length in mm)
    offset 20..23 : float crop_factor    (default 1.0)
    offset 24..27 : float orthocorr      (default 100.0; lens dependence)
    offset 28..31 : float aspect         ← parameterized (default 1.0; post-transform aspect adjust)

    Mode enums (preserved)
    offset 32..35 : enum  mode           (default ASHIFT_MODE_GENERIC = 0)
    offset 36..39 : enum  cropmode       (default ASHIFT_CROP_LARGEST = 1)

    Auto-crop bounds (preserved; auto-computed when cropmode=LARGEST)
    offset 40..43 : float cl             (default 0.0)
    offset 44..47 : float cr             (default 1.0)
    offset 48..51 : float ct             (default 0.0)
    offset 52..55 : float cb             (default 1.0)

    Reference-line storage (preserved verbatim; user-drawn perspective lines)
    offset 56..855  : float last_drawn_lines[200]  (default all zeros)
    offset 856..859 : int   last_drawn_lines_count  (default 0)
    offset 860..891 : float last_quad_lines[8]      (default all zeros)

Total size: 892 bytes — the largest in the parameterize registry by byte count.
The bulk (800 bytes) is the user-drawn-lines storage which has no photographic
default and isn't parameterized.

Five parameterized magnitude axes (axis names use ``transform_`` prefix
for disambiguation):

- ``transform_rotation`` — image rotation in degrees (range typically [-180, 180])
- ``transform_lensshift_v`` — vertical perspective (keystone) correction
- ``transform_lensshift_h`` — horizontal perspective correction
- ``transform_shear`` — shear correction
- ``transform_aspect`` — post-transform aspect adjustment (default 1.0; range [0.5, 2.0])

Other 218 fields preserved verbatim. Lens-tuning floats (focal length, crop
factor, ortho-correction) and the user-drawn-lines storage flow through
patch() unchanged.
"""

from __future__ import annotations

import struct

# Struct format: 8 floats + 2 enums + 4 floats + 200 floats + 1 int + 8 floats
# = 223 items, 892 bytes total.
_STRUCT_FORMAT = "<8f2i4f200fi8f"
_STRUCT_SIZE = 892

SUPPORTED_MODVERSION = 5

# Map every parameterized axis to its struct field index.
_AXIS_FIELD_INDICES: dict[str, int] = {
    "transform_rotation": 0,
    "transform_lensshift_v": 1,
    "transform_lensshift_h": 2,
    "transform_shear": 3,
    "transform_aspect": 7,
}

_AXIS_OFFSETS: dict[str, int] = {name: idx * 4 for name, idx in _AXIS_FIELD_INDICES.items()}


def decode(op_params: str) -> tuple[float | int, ...]:
    """Decode an 892-byte ashift ``op_params`` hex blob.

    Returns a 223-tuple in struct order. Raises :class:`ValueError` on
    size mismatch (most often a different modversion than mv5).
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"ashift op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv5"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float | int, ...]) -> str:
    """Encode a 223-tuple back to an 892-byte ashift ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(op_params: str, **values: float | None) -> str:
    """Patch any combination of ashift's 5 parameterized magnitude axes.

    Multi-axis partial-update: caller may supply any subset of the 5
    parameterized axes. Unknown keys raise :class:`TypeError`. Unspecified
    axes preserved.

    The 218 non-parameterized fields — lens-tuning floats (f_length,
    crop_factor, orthocorr), mode enums (mode, cropmode), auto-crop
    bounds (cl, cr, ct, cb), and the user-drawn-lines storage — are
    preserved verbatim through patch().

    Parameterized axes (5 total, all using transform_ prefix):

    - ``transform_rotation`` (default 0.0; image rotation in degrees)
    - ``transform_lensshift_v`` (default 0.0; vertical perspective / keystone)
    - ``transform_lensshift_h`` (default 0.0; horizontal perspective)
    - ``transform_shear`` (default 0.0)
    - ``transform_aspect`` (default 1.0; post-transform aspect adjust)

    Args:
        op_params: hex-encoded source ``op_params`` (892 bytes / 1784 hex chars).
        **values: any subset of the 5 axis names listed above.

    Returns:
        New hex-encoded ``op_params`` (892 bytes / 1784 hex chars).

    Raises:
        ValueError: input blob is not 892 bytes after hex-decode.
        TypeError: an unrecognized keyword argument was passed.
    """
    unknown = set(values.keys()) - set(_AXIS_FIELD_INDICES.keys())
    if unknown:
        raise TypeError(
            f"ashift.patch() got unexpected keyword argument(s): {sorted(unknown)}; "
            f"valid axes: {sorted(_AXIS_FIELD_INDICES.keys())}"
        )
    fields = list(decode(op_params))
    for axis_name, value in values.items():
        if value is not None:
            fields[_AXIS_FIELD_INDICES[axis_name]] = float(value)
    return encode(tuple(fields))
