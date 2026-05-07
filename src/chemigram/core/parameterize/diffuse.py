"""Path C decoder/encoder for darktable's ``diffuse`` (diffuse-or-sharpen) module (mv2).

Closes #92 Bucket A.6 — Lightroom Texture parity. Picked over the older
``equalizer`` (atrous) module on three grounds:

1. **Simpler struct.** ``diffuse`` is 60 bytes of flat scalars (15 fields).
   ``equalizer`` is ~248 bytes with nested 5x6 float arrays — significantly
   harder to verify for byte-correctness without empirical baseline.
2. **Modern recommendation.** darktable's docs recommend diffuse-or-sharpen
   for texture/sharpening/denoise as of 4.x; the equalizer is now a legacy
   path retained for compatibility.
3. **Multi-purpose.** A single decoder unlocks Lightroom Texture, sharpening,
   and (eventually) noise reduction parity from one struct ship.

Struct layout (verified against darktable 5.4.1 ``src/iop/diffuse.c``
``dt_iop_diffuse_params_t`` v2):

    offset 0..3   : int   iterations          (default 1; range [0, 500])
    offset 4..7   : float sharpness           (default 0.0; range [-1.0, 1.0])
    offset 8..11  : int   radius              (default 8; range [0, 2048])
    offset 12..15 : float regularization      (default 0.0; range [0.0, 4.0])
    offset 16..19 : float variance_threshold  (default 0.0; range [-2.0, 2.0])
    offset 20..23 : float anisotropy_first    (default 0.0; range [-10.0, 10.0])
    offset 24..27 : float anisotropy_second   (default 0.0)
    offset 28..31 : float anisotropy_third    (default 0.0)
    offset 32..35 : float anisotropy_fourth   (default 0.0)
    offset 36..39 : float threshold           (default 0.0; range [0.0, 8.0])
    offset 40..43 : float first               ← parameterized (Texture)
                              (default 0.0; range [-1.0, 1.0])
    offset 44..47 : float second              ← parameterized
                              (default 0.0)
    offset 48..51 : float third               (default 0.0)
    offset 52..55 : float fourth              (default 0.0)
    offset 56..59 : int   radius_center       (default 0)

Total size: 60 bytes (3 ints + 12 floats).

Lightroom-Texture mapping (#92 Bucket A.6): the four ``first``/``second``/
``third``/``fourth`` fields control texture enhancement at successive
detail scales (fine → coarse). ``first`` is the closest equivalent to
Lightroom's Texture slider — fine-frequency detail enhancement at the
single-pixel scale. ``sharpness`` is exposed as a secondary axis for
global sharpening intensity.

Other axes (anisotropy, regularization, variance_threshold, threshold,
radius, iterations, radius_center) are preserved verbatim through patch().
"""

from __future__ import annotations

import struct

# Struct format: 1 int + 1 float + 1 int + 11 floats + 1 int = 60 bytes.
_STRUCT_FORMAT = "<ifi11fi"
_STRUCT_SIZE = 60

# Parameterized axes (#92 Bucket A.6: Lightroom Texture parity).
_FIRST_FIELD_INDEX = 10  # offset 40 — finest detail scale (Texture)
_FIRST_OFFSET = 40
_SECOND_FIELD_INDEX = 11  # offset 44 — next-up detail scale
_SECOND_OFFSET = 44
_SHARPNESS_FIELD_INDEX = 1  # offset 4 — global sharpening intensity
_SHARPNESS_OFFSET = 4

SUPPORTED_MODVERSION = 2


def decode(op_params: str) -> tuple[int | float, ...]:
    """Decode a 60-byte diffuse ``op_params`` hex blob.

    Returns a 15-tuple in struct order (see module docstring).
    Raises :class:`ValueError` on size mismatch.
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"diffuse op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv2"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[int | float, ...]) -> str:
    """Encode a 15-tuple back to a 60-byte diffuse ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(
    op_params: str,
    *,
    first: float | None = None,
    second: float | None = None,
    sharpness: float | None = None,
) -> str:
    """Patch the Lightroom-Texture-parity axes in a 60-byte diffuse blob.

    Multi-axis partial-update: caller may supply any subset.
    Unspecified axes are preserved.

    Args:
        op_params: hex-encoded source ``op_params`` (60 bytes / 120 hex chars).
        first: finest-scale detail enhancement. Range [-1.0, 1.0]. This is
            the primary Lightroom Texture axis.
        second: next-up detail scale. Range [-1.0, 1.0]. Useful for slightly
            larger-grain texture work (closer to Lightroom Clarity at lower
            radius).
        sharpness: global sharpening intensity. Range [-1.0, 1.0].

    Returns:
        New hex-encoded ``op_params`` (60 bytes / 120 hex chars).

    Raises:
        ValueError: input blob is not 60 bytes after hex-decode.
    """
    fields = list(decode(op_params))
    if first is not None:
        fields[_FIRST_FIELD_INDEX] = float(first)
    if second is not None:
        fields[_SECOND_FIELD_INDEX] = float(second)
    if sharpness is not None:
        fields[_SHARPNESS_FIELD_INDEX] = float(sharpness)
    return encode(tuple(fields))
