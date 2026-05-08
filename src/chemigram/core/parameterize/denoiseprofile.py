"""Path C decoder/encoder for darktable's ``denoiseprofile`` module (mv12).

Closes #96 (Tier 3 → Tier 2 promotion). Real workflow gap: every high-ISO
/ low-light / astrophotography user wants denoising. Lightroom has its
Detail panel's Noise Reduction; chemigram had no equivalent until this
ship. Note: the wavelet-curve baseline shipped here is **constructed,
not empirically captured from darktable's GUI** — see the closing note
below and the empirical-verification tracking issue.

Struct layout (verified against darktable 5.4.1 ``src/iop/denoiseprofile.c``
``dt_iop_denoiseprofile_params_t`` v12):

    Magnitude axes (parameterized)
    offset 0..3   : float radius                ← parameterized (default 1.0)
    offset 4..7   : float nbhood                 (preserved; default 7.0)
    offset 8..11  : float strength              ← parameterized (default 1.0; primary axis)
    offset 12..15 : float shadows               ← parameterized (default 1.0)
    offset 16..19 : float bias                   (preserved; default 0.0)
    offset 20..23 : float scattering            ← parameterized (default 0.0)
    offset 24..27 : float central_pixel_weight   (preserved; default 0.1)
    offset 28..31 : float overshooting           (preserved; default 1.0)

    Per-channel noise calibration (preserved; auto-populated by darktable
    from camera+ISO database when known)
    offset 32..43 : float a[3]                   (default 0.0, 0.0, 0.0)
    offset 44..55 : float b[3]                   (default 0.0, 0.0, 0.0)

    Mode (preserved)
    offset 56..59 : enum  mode                   (default MODE_NLMEANS = 0)

    Wavelet frequency curves (preserved verbatim; UNUSED at apply time
    because mode=NLMEANS skips the wavelet path)
    offset 60..227  : float x[6][7]              (zeroed; not consulted in NLMEANS mode)
    offset 228..395 : float y[6][7]              (zeroed; not consulted)

    Mode flags (preserved verbatim)
    offset 396..399 : gbool wb_adaptive_anscombe          (default TRUE)
    offset 400..403 : gbool fix_anscombe_and_nlmeans_norm (default TRUE)
    offset 404..407 : gbool use_new_vst                   (default TRUE)
    offset 408..411 : enum  wavelet_color_mode            (default MODE_Y0U0V0 = 1)
    offset 412..415 : gbool compensate_hilite_pres        (default TRUE)

Total size: 416 bytes (98 floats + 5 4-byte int-shaped fields).

Four parameterized magnitude axes (the photographic knobs). Axis names
carry a ``denoise_`` prefix to disambiguate from same-named axes on
other parameterized modules (notably ``strength`` on dehaze):

- ``denoise_strength`` — primary noise-level slider; maps to C field
  ``strength``; range [0.001, 1000.0], default 1.0
- ``denoise_shadows`` — preserves shadow noise vs detail; maps to C
  field ``shadows``; range [0.0, 1.8], default 1.0
- ``denoise_radius`` — patch size for non-local means / wavelet; maps
  to C field ``radius``; range [0.0, 12.0], default 1.0
- ``denoise_scattering`` — spreads the search zone; maps to C field
  ``scattering``; range [0.0, 20.0], default 0.0

Other 13 fields preserved verbatim. The per-channel noise calibration
``a[3]/b[3]`` is camera/ISO-specific; darktable auto-populates it when
the camera profile is known. The mode enum is pinned at WAVELETS.

## Mode choice — NLMEANS (not WAVELETS)

The shipped baseline pins ``mode=MODE_NLMEANS`` (non-local means)
rather than darktable's runtime-default ``MODE_WAVELETS``. The
parameterized magnitude axes work in both modes; the choice is
photographic, not architectural.

Why NLMEANS for the v1.8.0 ship:

- WAVELETS mode requires an empirically-correct ``x[6][7]/y[6][7]``
  curve baseline. Without one captured from a darktable GUI session,
  zero-filled or constructed curves can crash darktable's wavelet path
  (the visual-proof sweep produces pure-black output with constructed
  curves).
- NLMEANS mode ignores the wavelet curves entirely — the constructed-
  baseline issue is moot. The parameterized strength axes operate
  identically.
- Lightroom's Noise Reduction is patch-similarity-based, which is
  conceptually closer to NLMEANS than to wavelet-band denoising.

If a photographer wants wavelet-mode denoising, they author a discrete
``.dtstyle`` from darktable's GUI with the curves correctly populated,
then this decoder lets them override the strength axes via parameterized
values. The wavelet-mode baseline capture is tracked under #100's
darktable-session umbrella as task C — confirm the empirical curve
defaults, optionally ship a second ``denoise_wavelets`` entry.
"""

from __future__ import annotations

import struct

# Struct: 8 mag + 6 calibration floats + mode + 84 curve floats + 5 ints
# = 14 + 84 = 98 floats + 5 ints = 416 bytes total.
_STRUCT_FORMAT = "<8f6fi42f42f3iii"
_STRUCT_SIZE = 416

SUPPORTED_MODVERSION = 12

# Map every parameterized axis to its struct field index.
# Field order: 0 radius, 1 nbhood, 2 strength, 3 shadows, 4 bias,
# 5 scattering, 6 central_pixel_weight, 7 overshooting,
# 8-10 a[3], 11-13 b[3], 14 mode, 15-56 x curves, 57-98 y curves,
# 99-103 5 int-shaped fields.
# Axis names use the ``denoise_`` prefix to disambiguate from same-named
# axes on other parameterized modules (notably ``strength`` on dehaze /
# hazeremoval, which has different range and semantics). The C struct
# field names are ``radius``, ``strength``, ``shadows``, ``scattering``;
# the rename is purely for vocabulary discoverability.
_AXIS_FIELD_INDICES: dict[str, int] = {
    "denoise_radius": 0,
    "denoise_strength": 2,
    "denoise_shadows": 3,
    "denoise_scattering": 5,
}

_AXIS_OFFSETS: dict[str, int] = {name: idx * 4 for name, idx in _AXIS_FIELD_INDICES.items()}


def decode(op_params: str) -> tuple[float | int, ...]:
    """Decode a 416-byte denoiseprofile ``op_params`` hex blob.

    Returns a 104-tuple in struct order. Raises :class:`ValueError` on
    size mismatch (most often a different modversion than mv12).
    """
    raw = bytes.fromhex(op_params)
    if len(raw) != _STRUCT_SIZE:
        raise ValueError(
            f"denoiseprofile op_params: expected {_STRUCT_SIZE} bytes, got {len(raw)}; "
            f"likely a different modversion than mv12"
        )
    return struct.unpack(_STRUCT_FORMAT, raw)


def encode(fields: tuple[float | int, ...]) -> str:
    """Encode a 104-tuple back to a 416-byte denoiseprofile ``op_params`` hex blob."""
    return struct.pack(_STRUCT_FORMAT, *fields).hex()


def patch(op_params: str, **values: float | None) -> str:
    """Patch any combination of denoiseprofile's 4 parameterized magnitude axes.

    Multi-axis partial-update: caller may supply any subset of the 4
    parameterized axes. Unknown keys raise :class:`TypeError`.
    Unspecified axes preserved.

    The 13 non-parameterized fields — ``nbhood``, ``bias``,
    ``central_pixel_weight``, ``overshooting``, the ``a[3]/b[3]`` noise
    calibration arrays, ``mode``, the ``x[6][7]/y[6][7]`` wavelet curves,
    and the 5 mode flags — are preserved verbatim through patch().

    Parameterized axes (4 total — the photographic knobs):

    - ``denoise_strength`` (default 1.0; range [0.001, 1000.0]; primary noise slider)
    - ``denoise_shadows`` (default 1.0; range [0.0, 1.8]; preserve shadow noise vs detail)
    - ``denoise_radius`` (default 1.0; range [0.0, 12.0]; patch size)
    - ``denoise_scattering`` (default 0.0; range [0.0, 20.0]; search-zone spread)

    Args:
        op_params: hex-encoded source ``op_params`` (416 bytes / 832 hex chars).
        **values: any subset of the 4 axis names listed above.

    Returns:
        New hex-encoded ``op_params`` (416 bytes / 832 hex chars).

    Raises:
        ValueError: input blob is not 416 bytes after hex-decode.
        TypeError: an unrecognized keyword argument was passed.
    """
    unknown = set(values.keys()) - set(_AXIS_FIELD_INDICES.keys())
    if unknown:
        raise TypeError(
            f"denoiseprofile.patch() got unexpected keyword argument(s): {sorted(unknown)}; "
            f"valid axes: {sorted(_AXIS_FIELD_INDICES.keys())}"
        )
    fields = list(decode(op_params))
    for axis_name, value in values.items():
        if value is not None:
            fields[_AXIS_FIELD_INDICES[axis_name]] = float(value)
    return encode(tuple(fields))
