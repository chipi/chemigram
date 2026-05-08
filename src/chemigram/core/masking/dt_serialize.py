"""Serialize geometric masks to darktable's drawn-mask XMP wire format.

This is the v1.4.0 replacement for the PNG-file-based mask
materialization. The PNG path was aspirational — darktable's raster
mask system only consumes in-pipeline module masks, never external
PNG files (verified against darktable 5.4.1 source: ``src/develop/blend.c``
calls ``dt_dev_get_raster_mask`` which reads from ``self->raster_mask.sink.source``,
a pipeline pointer, not a filesystem path).

The drawn-mask path actually wires to darktable: each form serialized
into ``<darktable:masks_history>`` is registered in the pipeline's
forms list, and a module's ``blendop_params.mask_id`` references it
via ``dt_masks_get_from_id_ext`` (``blend.c:594``).

This module encodes:

- :func:`encode_gradient_mask_points` — ``dt_masks_point_gradient_t``
- :func:`encode_ellipse_mask_points` — ``dt_masks_point_ellipse_t``
- :func:`encode_path_form_points` — N ``dt_masks_point_path_t`` corners
  for arbitrary closed polygons (AI-detected silhouettes per RFC-026,
  human-supplied outlines, etc.)
- :func:`encode_rectangle_path_points` — 4-corner rectangle wrapper
  over the generic path-form encoder
- :func:`encode_blendop_with_drawn_mask` — modify the default 420-byte
  ``dt_develop_blend_params_t`` blob to bind a drawn mask by id

Source citations (darktable 5.4.1):
- ``src/develop/masks.h`` — struct definitions
- ``src/develop/blend.h`` — blend params struct
- ``src/common/exif.cc:4647`` — XMP write side for masks_history
- ``src/common/exif.cc:3060`` — ``dt_exif_xmp_encode`` (hex / gz-base64)
"""

from __future__ import annotations

import base64
import struct
import zlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

# ---------------------------------------------------------------------------
# darktable enums (src/develop/masks.h)
# ---------------------------------------------------------------------------

DT_MASKS_NONE: Final = 0
DT_MASKS_CIRCLE: Final = 1 << 0
DT_MASKS_PATH: Final = 1 << 1
DT_MASKS_GROUP: Final = 1 << 2
DT_MASKS_CLONE: Final = 1 << 3
DT_MASKS_GRADIENT: Final = 1 << 4
DT_MASKS_ELLIPSE: Final = 1 << 5
DT_MASKS_BRUSH: Final = 1 << 6

DT_MASKS_GRADIENT_STATE_LINEAR: Final = 1
DT_MASKS_GRADIENT_STATE_SIGMOIDAL: Final = 2

DT_MASKS_ELLIPSE_EQUIDISTANT: Final = 0
DT_MASKS_ELLIPSE_PROPORTIONAL: Final = 1

# Path point states (src/develop/masks.h dt_masks_points_states_t — corner kind)
DT_MASKS_POINT_STATE_NORMAL: Final = 1

# ---------------------------------------------------------------------------
# darktable blend mode flags (src/develop/blend.h dt_develop_mask_mode_t)
# ---------------------------------------------------------------------------

DEVELOP_MASK_DISABLED: Final = 0
DEVELOP_MASK_ENABLED: Final = 1 << 0  # 1 — masking machinery on
DEVELOP_MASK_MASK: Final = 1 << 1  # 2 — drawn (form) mask
DEVELOP_MASK_CONDITIONAL: Final = 1 << 2  # 4 — parametric (blendif) mask
DEVELOP_MASK_BOTH: Final = DEVELOP_MASK_MASK | DEVELOP_MASK_CONDITIONAL  # 6
DEVELOP_MASK_RASTER: Final = 1 << 3  # 8 — in-pipeline raster (NOT what we use)

# Current drawn-mask form version (darktable 5.4)
DT_MASKS_VERSION: Final = 3

# Blend struct size (verified by decoding the existing DEFAULT_BLENDOP blob)
_BLEND_PARAMS_SIZE: Final = 420

# Field byte offsets in dt_develop_blend_params_t (verified against
# src/develop/blend.h struct layout + decoded DEFAULT_BLENDOP)
_OFFSET_MASK_MODE: Final = 0
_OFFSET_BLEND_CST: Final = 4
_OFFSET_OPACITY: Final = 16
_OFFSET_MASK_COMBINE: Final = 20
_OFFSET_MASK_ID: Final = 24
_OFFSET_BLENDIF: Final = 28
# Per-channel parametric mask control points: 4 floats * 16 channels = 64 floats
_OFFSET_BLENDIF_PARAMETERS: Final = 68
# Per-channel boost factors: 16 floats (left at default for all v1.9.0 use)
_OFFSET_BLENDIF_BOOST_FACTORS: Final = 324


# ---------------------------------------------------------------------------
# Parametric mask channel IDs (subset relevant for v1.9.0; ADR-085)
# Full enum lives in darktable's dt_develop_blendif_channels_t.
# ---------------------------------------------------------------------------

# Universal: channel 0 is luminance/gray regardless of module color space.
# (DEVELOP_BLENDIF_GRAY_in == DEVELOP_BLENDIF_L_in == 0 by aliasing in the
# darktable enum.)
DEVELOP_BLENDIF_GRAY_in: Final = 0

# HSL color-space channels (when blend_cst is set to IOP_CS_HSL):
DEVELOP_BLENDIF_H_in: Final = 8  # hue
DEVELOP_BLENDIF_S_in: Final = 9  # saturation
DEVELOP_BLENDIF_l_in: Final = 10  # lightness

# darktable iop colorspace constant for HSL (dt_iop_colorspace_type_t).
# Verified: existing default blendop has blend_cst=4 (Lab); HSL=5.
IOP_CS_HSL: Final = 5


# ---------------------------------------------------------------------------
# Retouch module enums (src/iop/retouch.c; mv3) — RFC-025 / ADR-087
# ---------------------------------------------------------------------------

# dt_iop_retouch_algo_type_t
DT_IOP_RETOUCH_NONE: Final = 0
DT_IOP_RETOUCH_CLONE: Final = 1
DT_IOP_RETOUCH_HEAL: Final = 2
DT_IOP_RETOUCH_BLUR: Final = 3  # not exposed in v1.9.0 surface
DT_IOP_RETOUCH_FILL: Final = 4  # not exposed in v1.9.0 surface

# Retouch struct sizing (verified against darktable 5.4.1 src/iop/retouch.c)
RETOUCH_NO_FORMS: Final = 300
RETOUCH_FORM_SIZE: Final = 44  # dt_iop_retouch_form_data_t
RETOUCH_PARAMS_SIZE: Final = 13260  # 300 * 44 + 60-byte tail


# ---------------------------------------------------------------------------
# Drawn-mask form encoders
# ---------------------------------------------------------------------------


def encode_gradient_mask_points(
    *,
    anchor_x: float,
    anchor_y: float,
    rotation: float,
    compression: float = 1.0,
    steepness: float = 0.0,
    curvature: float = 0.0,
    state: int = DT_MASKS_GRADIENT_STATE_SIGMOIDAL,
) -> bytes:
    """``dt_masks_point_gradient_t`` (28 bytes).

    Args:
        anchor_x, anchor_y: Anchor point in normalized image coords
            (0..1; (0.5, 0.5) is centered).
        rotation: Gradient axis rotation in degrees. 0 = horizontal
            (light side on the left), 90 = vertical (light side on top).
        compression: Compression of the gradient (default 1.0).
        steepness: Steepness of the falloff curve (default 0.0).
        curvature: Curvature of the gradient line (default 0.0 = straight).
        state: ``DT_MASKS_GRADIENT_STATE_LINEAR`` or
            ``DT_MASKS_GRADIENT_STATE_SIGMOIDAL`` (default; smoother).
    """
    return struct.pack(
        "<ff f f f f I",
        anchor_x,
        anchor_y,
        rotation,
        compression,
        steepness,
        curvature,
        state,
    )


def encode_ellipse_mask_points(
    *,
    center_x: float,
    center_y: float,
    radius_x: float,
    radius_y: float,
    rotation: float = 0.0,
    border: float = 0.05,
    flags: int = DT_MASKS_ELLIPSE_PROPORTIONAL,
) -> bytes:
    """``dt_masks_point_ellipse_t`` (28 bytes).

    Args:
        center_x, center_y: Ellipse center in normalized image coords.
        radius_x, radius_y: Ellipse radii in normalized image coords.
            Equal values = circle.
        rotation: Rotation in degrees (default 0).
        border: Border / falloff width in normalized image coords
            (default 0.05).
        flags: ``DT_MASKS_ELLIPSE_PROPORTIONAL`` (default; border scales
            with shape) or ``DT_MASKS_ELLIPSE_EQUIDISTANT`` (border is
            a fixed pixel distance regardless of size).
    """
    return struct.pack(
        "<ff ff f f I",
        center_x,
        center_y,
        radius_x,
        radius_y,
        rotation,
        border,
        flags,
    )


def encode_path_form_points(
    vertices: Sequence[tuple[float, float]],
    *,
    border: float = 0.02,
) -> bytes:
    """N ``dt_masks_point_path_t`` corners forming a closed Bézier path.

    Generic encoder for arbitrary N-vertex closed polygons used as
    ``DT_MASKS_PATH`` forms. Each vertex emits a sharp corner
    (degenerate Bézier handles: ctrl1 = ctrl2 = corner). ``border``
    controls the feathering distance, applied uniformly to every side.

    Vertices are in normalized image-space coordinates ([0, 1] in both
    axes). The path is implicitly closed — darktable connects the last
    vertex back to the first when rendering the mask.

    Each ``dt_masks_point_path_t`` is:
        float corner[2];      // anchor
        float ctrl1[2];       // bezier handle 1
        float ctrl2[2];       // bezier handle 2
        float border[2];      // border width per side
        uint32 state;         // corner kind

    Use cases:
    - 4-vertex rectangle (via :func:`encode_rectangle_path_points`)
    - AI-detected subject silhouettes (RFC-026 path), with vertex
      counts typically in the 50-1000 range after Douglas-Peucker
      simplification at the provider boundary
    - Any human-supplied polygon outline
    """
    if len(vertices) < 3:
        raise ValueError(f"path form needs at least 3 vertices, got {len(vertices)}")
    out = b""
    for cx, cy in vertices:
        out += struct.pack(
            "<ff ff ff ff I",
            cx,
            cy,  # corner
            cx,
            cy,  # ctrl1 (degenerate = sharp corner)
            cx,
            cy,  # ctrl2 (degenerate)
            border,
            border,  # per-side border
            DT_MASKS_POINT_STATE_NORMAL,
        )
    return out


def encode_rectangle_path_points(
    *,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    border: float = 0.02,
) -> bytes:
    """4 ``dt_masks_point_path_t`` corners forming a rectangle.

    Thin wrapper over :func:`encode_path_form_points` that builds the
    4-corner closed Bézier path for a rectangle. Kept as a distinct
    convenience because rectangles are a high-traffic mask shape.
    """
    return encode_path_form_points(
        [(x0, y0), (x1, y0), (x1, y1), (x0, y1)],
        border=border,
    )


def encode_circle_mask_points(
    *,
    center_x: float,
    center_y: float,
    radius: float,
    border: float = 0.0,
) -> bytes:
    """``dt_masks_point_circle_t`` (16 bytes).

    A simple radial form used for retouch (RFC-025 / ADR-087) spot
    correction. Coordinates normalized [0, 1]; radius is also in
    normalized image space (0.05 = 5% of the image's smaller axis).

    Args:
        center_x, center_y: Circle center in normalized coords.
        radius: Circle radius in normalized coords.
        border: Feathering width on the falloff (default 0 = hard
            edge; spot correction usually wants a small soft edge
            ~0.02 for natural blending into surrounding pixels).
    """
    return struct.pack("<ffff", center_x, center_y, radius, border)


def encode_clone_mask_src(*, source_x: float, source_y: float) -> bytes:
    """``mask_src`` field for a CLONE form (8 bytes).

    Replaces :func:`empty_mask_src` (which returns 8 zeros) for forms
    that need to specify a clone source. For HEAL forms, mask_src
    stays at zeros (darktable picks the source automatically via the
    wavelet-based heal algorithm).
    """
    return struct.pack("<ff", source_x, source_y)


# ---------------------------------------------------------------------------
# Retouch module encoders (RFC-025 / ADR-087)
# ---------------------------------------------------------------------------


def encode_retouch_form(
    *,
    formid: int,
    algorithm: int,
    scale: int = 0,
    blur_type: int = 0,
    blur_radius: float = 0.0,
    fill_mode: int = 0,
    fill_color: tuple[float, float, float] = (0.0, 0.0, 0.0),
    fill_brightness: float = 0.0,
    distort_mode: int = 0,
) -> bytes:
    """``dt_iop_retouch_form_data_t`` (44 bytes).

    Per-form retouch struct: links a mask form (by ``formid``) to an
    algorithm (HEAL / CLONE / BLUR / FILL) plus per-form parameters.

    Verified against darktable 5.4.1 src/iop/retouch.c:

        struct {
            int32_t formid;          // mask_id reference
            int32_t scale;
            int32_t algorithm;       // DT_IOP_RETOUCH_*
            int32_t blur_type;
            float   blur_radius;
            int32_t fill_mode;
            float   fill_color[3];
            float   fill_brightness;
            int32_t distort_mode;
        }

    For v1.9.0's HEAL / CLONE scope, only formid + algorithm + the
    other defaults matter; blur and fill fields stay at zero.

    Note: ``formid`` is packed as unsigned int32 to match the wire-level
    treatment of mask ids elsewhere (encode_blendop_with_drawn_mask
    masks the id to 0xFFFFFFFF). darktable's source declares formid as
    signed int32 but the byte representation is identical; the
    deterministic-hash mask_id allocator may produce values above
    INT32_MAX.
    """
    return struct.pack(
        "<I i i i f i fff f i",
        formid & 0xFFFFFFFF,
        scale,
        algorithm,
        blur_type,
        blur_radius,
        fill_mode,
        fill_color[0],
        fill_color[1],
        fill_color[2],
        fill_brightness,
        distort_mode,
    )


def encode_retouch_op_params(
    forms: Sequence[bytes],
    *,
    algorithm_default: int = DT_IOP_RETOUCH_NONE,
) -> bytes:
    """``dt_iop_retouch_params_t`` (13260 bytes).

    Constructs the full retouch op_params blob: a 300-form fixed
    array (active forms first, padded with empty 44-byte form slots)
    plus a 60-byte global tail (default algorithm, scales,
    fill/blur defaults, max heal iterations).

    For v1.9.0's single-form-per-call scope, ``forms`` typically
    contains 1 form; the remaining 299 slots are zero-padded. The
    global tail stays at all-zero defaults — darktable reads the
    per-form algorithm field, not the global one, when applying
    retouch operations.

    Args:
        forms: List of 44-byte form blobs (from
            :func:`encode_retouch_form`). Up to 300 entries.
        algorithm_default: Global algorithm field for the params
            tail (default ``DT_IOP_RETOUCH_NONE = 0``). The per-form
            algorithm is what darktable actually uses; this is just
            the UI default.

    Raises:
        ValueError: more than 300 forms supplied; or any form is
            not exactly 44 bytes.
    """
    if len(forms) > RETOUCH_NO_FORMS:
        raise ValueError(f"retouch supports at most {RETOUCH_NO_FORMS} forms, got {len(forms)}")
    for i, form_bytes in enumerate(forms):
        if len(form_bytes) != RETOUCH_FORM_SIZE:
            raise ValueError(f"forms[{i}] is {len(form_bytes)} bytes, expected {RETOUCH_FORM_SIZE}")

    empty_form = b"\x00" * RETOUCH_FORM_SIZE
    form_array = b"".join(forms) + empty_form * (RETOUCH_NO_FORMS - len(forms))

    # Global tail (60 bytes): algorithm, num_scales, curr_scale,
    # merge_from_scale, preview_levels[3], blur_type, blur_radius,
    # fill_mode, fill_color[3], fill_brightness, max_heal_iter
    tail = struct.pack(
        "<i i i i fff i f i fff f i",
        algorithm_default,  # algorithm (UI default; per-form value is what's applied)
        0,  # num_scales
        0,  # curr_scale
        0,  # merge_from_scale
        0.0,
        0.0,
        0.0,  # preview_levels[3]
        0,  # blur_type
        0.0,  # blur_radius
        0,  # fill_mode
        0.0,
        0.0,
        0.0,  # fill_color[3]
        0.0,  # fill_brightness
        0,  # max_heal_iter
    )
    out = form_array + tail
    if len(out) != RETOUCH_PARAMS_SIZE:
        raise RuntimeError(
            f"retouch op_params size mismatch: produced {len(out)}, expected {RETOUCH_PARAMS_SIZE}"
        )
    return out


# ---------------------------------------------------------------------------
# blendop_params encoder (drawn-mask binding)
# ---------------------------------------------------------------------------


def _decode_default_blendop_blob(encoded: str) -> bytes:
    """Decode a ``gz<level><base64>`` blob to raw bytes."""
    if not encoded.startswith("gz"):
        raise ValueError(f"expected gz-prefixed blob, got {encoded[:8]!r}")
    b64 = encoded[4:]
    return zlib.decompress(base64.b64decode(b64))


def _encode_blendop_blob(raw: bytes) -> str:
    """Encode raw bytes back to ``gz<level><base64>`` (matches
    ``dt_exif_xmp_encode`` with compression on)."""
    compressed = zlib.compress(raw, level=9)
    factor = min(len(raw) // len(compressed) + 1, 99)
    b64 = base64.b64encode(compressed).decode("ascii")
    return f"gz{factor:02d}{b64}"


# Decoded once at module load so callers don't repeatedly base64+zlib.
_DEFAULT_BLENDOP_ENCODED: Final = (
    "gz08eJxjYGBgYAFiCQYYOOHEgAZY0QWAgBGLGANDgz0Ej1Q+dlAx68oBEMbFxwX+AwGIBgCbGCeh"
)
_DEFAULT_BLENDOP_BYTES: Final = _decode_default_blendop_blob(_DEFAULT_BLENDOP_ENCODED)
assert len(_DEFAULT_BLENDOP_BYTES) == _BLEND_PARAMS_SIZE, (
    f"DEFAULT_BLENDOP decoded to {len(_DEFAULT_BLENDOP_BYTES)} bytes, expected {_BLEND_PARAMS_SIZE}"
)


@dataclass(frozen=True)
class DrawnMaskBinding:
    """Result of building a mask + blendop pair for a vocab entry application."""

    mask_id: int
    mask_type: int
    mask_version: int
    mask_points: bytes
    mask_nb: int
    mask_src: bytes  # 8 bytes of zeros for non-clone forms
    mask_name: str
    blendop_params: bytes  # 420 bytes; ready to base64+gz-encode
    blendop_version: int


def encode_blendop_with_drawn_mask(
    *,
    mask_id: int,
    opacity: float = 100.0,
    base_blendop: bytes = _DEFAULT_BLENDOP_BYTES,
) -> bytes:
    """Patch the default 420-byte blendop blob to bind a drawn mask.

    Sets ``mask_mode = ENABLED | MASK = 3``, ``mask_id = <id>``, and
    ``opacity = <pct>``. Everything else (blend mode, blend cst,
    blendif params, etc.) stays at the safe defaults.

    Args:
        mask_id: The form id (must match a ``masks_history`` entry's
            ``mask_id``).
        opacity: Opacity in percent (0..100; default 100).
        base_blendop: The 420-byte template (default = the canonical
            "no mask, normal blend, 100% opacity" blob).

    Returns:
        420 bytes ready for ``_encode_blendop_blob`` (gz+base64).
    """
    if len(base_blendop) != _BLEND_PARAMS_SIZE:
        raise ValueError(
            f"base_blendop must be {_BLEND_PARAMS_SIZE} bytes, got {len(base_blendop)}"
        )
    if not 0.0 <= opacity <= 100.0:
        raise ValueError(f"opacity must be in [0, 100], got {opacity}")

    out = bytearray(base_blendop)
    mask_mode = DEVELOP_MASK_ENABLED | DEVELOP_MASK_MASK
    struct.pack_into("<I", out, _OFFSET_MASK_MODE, mask_mode)
    struct.pack_into("<f", out, _OFFSET_OPACITY, float(opacity))
    struct.pack_into("<I", out, _OFFSET_MASK_ID, mask_id & 0xFFFFFFFF)
    return bytes(out)


# ---------------------------------------------------------------------------
# Parametric mask encoder (RFC-024 / ADR-085)
# ---------------------------------------------------------------------------

# Map agent-facing range_filter.kind to (channel_id, is_color_kind)
_RANGE_KIND_TO_CHANNEL: Final[dict[str, int]] = {
    "luminance": DEVELOP_BLENDIF_GRAY_in,
    "color_h": DEVELOP_BLENDIF_H_in,
    "color_s": DEVELOP_BLENDIF_S_in,
    "color_l": DEVELOP_BLENDIF_l_in,
}
_COLOR_KINDS: Final = frozenset({"color_h", "color_s", "color_l"})


def _range_to_control_points(
    *, range_min: float, range_max: float, feather: float
) -> tuple[float, float, float, float]:
    """Map agent-facing {min, max, feather} to darktable's 4-control-point
    trapezoid mask shape.

    Returns ``(low_min, low_max, high_min, high_max)``:

    - Below low_min: outside (mask = 0)
    - low_min..low_max: ramp up (0 -> 1)
    - low_max..high_min: inside (mask = 1)
    - high_min..high_max: ramp down (1 -> 0)
    - Above high_max: outside (mask = 0)

    Default per-channel value is [0, 0, 1, 1] = "always pass."
    """
    if not 0.0 <= range_min <= 1.0:
        raise ValueError(f"range_min must be in [0, 1], got {range_min}")
    if not 0.0 <= range_max <= 1.0:
        raise ValueError(f"range_max must be in [0, 1], got {range_max}")
    if range_min > range_max:
        raise ValueError(f"range_min ({range_min}) > range_max ({range_max})")
    if not 0.0 <= feather <= 0.5:
        raise ValueError(f"feather must be in [0, 0.5], got {feather}")
    low_min = max(0.0, range_min - feather)
    low_max = range_min
    high_min = range_max
    high_max = min(1.0, range_max + feather)
    return low_min, low_max, high_min, high_max


def encode_blendop_with_parametric_mask(
    *,
    range_kind: str,
    range_min: float,
    range_max: float,
    feather: float = 0.05,
    invert: bool = False,
    mask_id: int | None = None,
    opacity: float = 100.0,
    base_blendop: bytes = _DEFAULT_BLENDOP_BYTES,
) -> bytes:
    """Patch the default blendop blob to bind a parametric (range) mask.

    Closes RFC-024 / ADR-085. Supports three composition modes:

    - ``mask_id is None``: parametric only. mask_mode = ENABLED | CONDITIONAL = 5.
    - ``mask_id is not None``: drawn AND parametric. mask_mode = 7.
      Caller must also encode the corresponding form into masks_history.
    - (Drawn-only is handled by :func:`encode_blendop_with_drawn_mask`.)

    Args:
        range_kind: One of ``"luminance"``, ``"color_h"``, ``"color_s"``,
            ``"color_l"``. Selects the channel and (for color kinds) the
            HSL color space.
        range_min: Mask region lower bound, [0, 1].
        range_max: Mask region upper bound, [0, 1].
        feather: Ramp width applied to both edges of the band, [0, 0.5].
            Default 0.05.
        invert: If ``True``, the mask covers OUTSIDE the range. Implemented
            via darktable's per-channel invert bit (channel_id + 16) in
            the ``blendif`` bitmask.
        mask_id: If not None, this is the drawn form's mask_id; mask_mode
            becomes drawn+parametric (=7) and mask_combine stays at 0
            (AND = intersection per ADR-085).
        opacity: 0..100; default 100.
        base_blendop: 420-byte template (default = canonical defaults).

    Returns:
        420 bytes ready for ``_encode_blendop_blob`` (gz+base64).

    Raises:
        ValueError: range_kind unknown; range bounds out of [0, 1];
            range_min > range_max; feather out of range; opacity out of
            [0, 100]; base_blendop wrong size.
    """
    if range_kind not in _RANGE_KIND_TO_CHANNEL:
        raise ValueError(
            f"unknown range_kind {range_kind!r}; one of: {sorted(_RANGE_KIND_TO_CHANNEL)}"
        )
    if len(base_blendop) != _BLEND_PARAMS_SIZE:
        raise ValueError(
            f"base_blendop must be {_BLEND_PARAMS_SIZE} bytes, got {len(base_blendop)}"
        )
    if not 0.0 <= opacity <= 100.0:
        raise ValueError(f"opacity must be in [0, 100], got {opacity}")

    channel_id = _RANGE_KIND_TO_CHANNEL[range_kind]
    low_min, low_max, high_min, high_max = _range_to_control_points(
        range_min=range_min, range_max=range_max, feather=feather
    )

    out = bytearray(base_blendop)

    # mask_mode: ENABLED | CONDITIONAL (5) for parametric-only, plus MASK
    # bit (3 -> 7) when composing with a drawn form.
    if mask_id is None:
        mask_mode = DEVELOP_MASK_ENABLED | DEVELOP_MASK_CONDITIONAL
    else:
        mask_mode = DEVELOP_MASK_ENABLED | DEVELOP_MASK_MASK | DEVELOP_MASK_CONDITIONAL
        struct.pack_into("<I", out, _OFFSET_MASK_ID, mask_id & 0xFFFFFFFF)
    struct.pack_into("<I", out, _OFFSET_MASK_MODE, mask_mode)
    struct.pack_into("<f", out, _OFFSET_OPACITY, float(opacity))

    # mask_combine = 0 (AND/intersect; ADR-085 hardcode for v1.9.0).
    struct.pack_into("<I", out, _OFFSET_MASK_COMBINE, 0)

    # blendif bitmask: set the channel bit (and the +16 invert bit if asked).
    blendif = 1 << channel_id
    if invert:
        blendif |= 1 << (channel_id + 16)
    struct.pack_into("<I", out, _OFFSET_BLENDIF, blendif)

    # blendif_parameters: 4 floats per channel at offset
    # _OFFSET_BLENDIF_PARAMETERS + channel_id * 16.
    field_offset = _OFFSET_BLENDIF_PARAMETERS + channel_id * 16
    struct.pack_into("<ffff", out, field_offset, low_min, low_max, high_min, high_max)

    # blend_cst: HSL for color_* kinds; leave at base default for luminance
    # (channel 0 is universal, works regardless of color space).
    if range_kind in _COLOR_KINDS:
        struct.pack_into("<i", out, _OFFSET_BLEND_CST, IOP_CS_HSL)

    return bytes(out)


# ---------------------------------------------------------------------------
# XMP wire-format helpers (mask_points and mask_src serialization)
# ---------------------------------------------------------------------------


def encode_mask_blob_for_xmp(raw: bytes, *, compress: bool = True) -> str:
    """Encode raw mask bytes per ``dt_exif_xmp_encode``.

    Short blobs are stored as plain hex; longer blobs as
    ``gz<level><base64>``. Mirrors the C function with the
    ``compress_xmp_tags`` config left at "only large entries" default.
    """
    if compress and len(raw) > 100:
        return _encode_blendop_blob(raw)  # same encoding as blendop blobs
    return raw.hex()


def empty_mask_src() -> bytes:
    """8 bytes of zeros — the ``source[2]`` field for non-clone forms."""
    return b"\x00" * 8


# ---------------------------------------------------------------------------
# High-level form builders + masks_history XML generation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DrawnMaskForm:
    """A single drawn-mask form ready to inject into ``masks_history``.

    Carries everything the XMP write side needs in one struct so callers
    don't have to track the per-form state separately.
    """

    mask_id: int
    mask_type: int  # DT_MASKS_GRADIENT / DT_MASKS_ELLIPSE / DT_MASKS_PATH
    mask_version: int
    mask_name: str
    mask_points: bytes  # raw struct bytes
    mask_nb: int  # 1 for single-shape, N for N-corner path
    mask_src: bytes  # 8 zeros for non-clone


def build_gradient_form(
    *,
    mask_id: int,
    anchor_x: float = 0.5,
    anchor_y: float = 0.5,
    rotation: float = 90.0,
    compression: float = 1.0,
    steepness: float = 0.0,
    curvature: float = 0.0,
    state: int = DT_MASKS_GRADIENT_STATE_SIGMOIDAL,
    name: str = "",
) -> DrawnMaskForm:
    """Convenience: build a gradient ``DrawnMaskForm`` in one call."""
    points = encode_gradient_mask_points(
        anchor_x=anchor_x,
        anchor_y=anchor_y,
        rotation=rotation,
        compression=compression,
        steepness=steepness,
        curvature=curvature,
        state=state,
    )
    return DrawnMaskForm(
        mask_id=mask_id,
        mask_type=DT_MASKS_GRADIENT,
        mask_version=DT_MASKS_VERSION,
        mask_name=name,
        mask_points=points,
        mask_nb=1,
        mask_src=empty_mask_src(),
    )


def build_ellipse_form(
    *,
    mask_id: int,
    center_x: float = 0.5,
    center_y: float = 0.5,
    radius_x: float = 0.3,
    radius_y: float = 0.3,
    rotation: float = 0.0,
    border: float = 0.05,
    flags: int = DT_MASKS_ELLIPSE_PROPORTIONAL,
    name: str = "",
) -> DrawnMaskForm:
    """Convenience: build an ellipse ``DrawnMaskForm`` in one call."""
    points = encode_ellipse_mask_points(
        center_x=center_x,
        center_y=center_y,
        radius_x=radius_x,
        radius_y=radius_y,
        rotation=rotation,
        border=border,
        flags=flags,
    )
    return DrawnMaskForm(
        mask_id=mask_id,
        mask_type=DT_MASKS_ELLIPSE,
        mask_version=DT_MASKS_VERSION,
        mask_name=name,
        mask_points=points,
        mask_nb=1,
        mask_src=empty_mask_src(),
    )


def build_rectangle_form(
    *,
    mask_id: int,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    border: float = 0.02,
    name: str = "",
) -> DrawnMaskForm:
    """Convenience: build a 4-corner rectangle path ``DrawnMaskForm``."""
    points = encode_rectangle_path_points(x0=x0, y0=y0, x1=x1, y1=y1, border=border)
    return DrawnMaskForm(
        mask_id=mask_id,
        mask_type=DT_MASKS_PATH,
        mask_version=DT_MASKS_VERSION,
        mask_name=name,
        mask_points=points,
        mask_nb=4,
        mask_src=empty_mask_src(),
    )


def build_path_form(
    *,
    mask_id: int,
    vertices: Sequence[tuple[float, float]],
    border: float = 0.02,
    name: str = "",
) -> DrawnMaskForm:
    """Convenience: build an N-vertex closed-path ``DrawnMaskForm``.

    The general-purpose path-form builder. Use for arbitrary polygon
    outlines — AI-detected subject silhouettes (RFC-026), human-supplied
    polygons, programmatic mask construction. For the 4-vertex
    rectangle special case, prefer :func:`build_rectangle_form` for
    clarity (both produce equivalent forms).

    ``vertices`` are in normalized image-space coordinates ([0, 1] in
    both axes). The path is closed implicitly. ``border`` controls
    feathering, uniform on all sides.
    """
    points = encode_path_form_points(vertices, border=border)
    return DrawnMaskForm(
        mask_id=mask_id,
        mask_type=DT_MASKS_PATH,
        mask_version=DT_MASKS_VERSION,
        mask_name=name,
        mask_points=points,
        mask_nb=len(vertices),
        mask_src=empty_mask_src(),
    )


# darktable XMP namespaces (must match the rest of the chemigram XMP writer)
_NS_RDF: Final = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_NS_DARKTABLE: Final = "http://darktable.sf.net/"


def build_form_from_spec(mask_id: int, spec: dict[str, object]) -> DrawnMaskForm:
    """Build a :class:`DrawnMaskForm` from a vocab entry's ``mask_spec``.

    ``spec`` shape::

        {
          "dt_form": "gradient" | "ellipse" | "rectangle",
          "dt_params": {<form-specific kwargs>}
        }

    The ``dt_params`` are passed verbatim to the matching builder
    (``build_gradient_form`` etc.) along with the allocated ``mask_id``.

    Raises ``ValueError`` if the form name is unknown or required
    params are missing (``TypeError`` from the underlying builder is
    caught and re-raised as ``ValueError`` with the form name).
    """
    form_name_raw = spec.get("dt_form")
    if not isinstance(form_name_raw, str) or not form_name_raw:
        raise ValueError(f"mask_spec missing/invalid 'dt_form': {spec!r}")
    form_name: str = form_name_raw
    params_raw = spec.get("dt_params") or {}
    if not isinstance(params_raw, dict):
        raise ValueError(f"mask_spec 'dt_params' must be a dict, got {type(params_raw)}")
    params: dict[str, object] = params_raw
    if form_name == "gradient":
        return build_gradient_form(mask_id=mask_id, **params)  # type: ignore[arg-type]
    if form_name == "ellipse":
        return build_ellipse_form(mask_id=mask_id, **params)  # type: ignore[arg-type]
    if form_name == "rectangle":
        return build_rectangle_form(mask_id=mask_id, **params)  # type: ignore[arg-type]
    if form_name == "path":
        return build_path_form(mask_id=mask_id, **params)  # type: ignore[arg-type]
    raise ValueError(
        f"unknown mask_spec dt_form {form_name!r}; one of: gradient, ellipse, rectangle, path"
    )


def patch_blendop_params_string(encoded: str, *, mask_id: int, opacity: float = 100.0) -> str:
    """Decode a ``gz<level><base64>`` blendop blob, patch in a drawn-mask
    binding, re-encode. The hex-form (uncompressed) is also accepted.

    Used by the synthesizer-with-mask path when modifying a vocab
    entry's plugin blendop_params before snapshot.
    """
    if encoded.startswith("gz"):
        raw = _decode_default_blendop_blob(encoded)
    else:
        # Plain hex form
        raw = bytes.fromhex(encoded)
    if len(raw) != _BLEND_PARAMS_SIZE:
        raise ValueError(
            f"decoded blendop_params is {len(raw)} bytes, expected {_BLEND_PARAMS_SIZE}; "
            f"likely an older blendop version we don't support yet"
        )
    patched = encode_blendop_with_drawn_mask(mask_id=mask_id, opacity=opacity, base_blendop=raw)
    return _encode_blendop_blob(patched)


def build_masks_history_xml(forms: list[DrawnMaskForm]) -> str:
    """Construct the ``<darktable:masks_history>`` XML element as text.

    Output matches the read side in
    ``src/common/exif.cc:3766+`` (``Xmp.darktable.masks_history[N]/...``).
    Each form becomes one ``<rdf:li>`` with all fields as attributes
    (RDF/XMP compact form). The text is embedded into the parent XMP
    via :class:`Xmp.raw_extra_fields`.
    """
    lines = [
        f'<darktable:masks_history xmlns:darktable="{_NS_DARKTABLE}" xmlns:rdf="{_NS_RDF}">',
        "  <rdf:Seq>",
    ]
    for num, form in enumerate(forms, start=1):
        lines.append(
            f'    <rdf:li darktable:mask_num="{num}" '
            f'darktable:mask_id="{form.mask_id}" '
            f'darktable:mask_type="{form.mask_type}" '
            f'darktable:mask_name="{form.mask_name}" '
            f'darktable:mask_version="{form.mask_version}" '
            f'darktable:mask_points="{encode_mask_blob_for_xmp(form.mask_points)}" '
            f'darktable:mask_nb="{form.mask_nb}" '
            f'darktable:mask_src="{encode_mask_blob_for_xmp(form.mask_src)}"/>'
        )
    lines.append("  </rdf:Seq>")
    lines.append("</darktable:masks_history>")
    return "\n".join(lines)
