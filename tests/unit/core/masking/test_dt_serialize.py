"""Unit tests for darktable drawn-mask wire-format encoders."""

from __future__ import annotations

import struct

import pytest

from chemigram.core.masking.dt_serialize import (
    _BLEND_PARAMS_SIZE,
    _DEFAULT_BLENDOP_BYTES,
    _OFFSET_MASK_ID,
    _OFFSET_MASK_MODE,
    _OFFSET_OPACITY,
    DEVELOP_MASK_ENABLED,
    DEVELOP_MASK_MASK,
    DT_MASKS_ELLIPSE_PROPORTIONAL,
    DT_MASKS_GRADIENT_STATE_LINEAR,
    DT_MASKS_GRADIENT_STATE_SIGMOIDAL,
    empty_mask_src,
    encode_blendop_with_drawn_mask,
    encode_ellipse_mask_points,
    encode_gradient_mask_points,
    encode_mask_blob_for_xmp,
    encode_path_form_points,
    encode_rectangle_path_points,
)

# ---------------------------------------------------------------------------
# gradient mask encoder
# ---------------------------------------------------------------------------


def test_gradient_default_round_trip() -> None:
    blob = encode_gradient_mask_points(anchor_x=0.5, anchor_y=0.5, rotation=0.0)
    assert len(blob) == 28  # 7 * 4-byte fields
    fields = struct.unpack("<ffffff I", blob)
    assert fields[0] == pytest.approx(0.5)
    assert fields[1] == pytest.approx(0.5)
    assert fields[2] == pytest.approx(0.0)
    assert fields[3] == pytest.approx(1.0)  # default compression
    assert fields[4] == pytest.approx(0.0)  # default steepness
    assert fields[5] == pytest.approx(0.0)  # default curvature
    assert fields[6] == DT_MASKS_GRADIENT_STATE_SIGMOIDAL


def test_gradient_with_state_linear() -> None:
    blob = encode_gradient_mask_points(
        anchor_x=0.0, anchor_y=0.5, rotation=90.0, state=DT_MASKS_GRADIENT_STATE_LINEAR
    )
    fields = struct.unpack("<ffffff I", blob)
    assert fields[6] == DT_MASKS_GRADIENT_STATE_LINEAR


# ---------------------------------------------------------------------------
# ellipse mask encoder
# ---------------------------------------------------------------------------


def test_ellipse_default_round_trip() -> None:
    blob = encode_ellipse_mask_points(center_x=0.5, center_y=0.5, radius_x=0.3, radius_y=0.3)
    assert len(blob) == 28
    fields = struct.unpack("<ffffff I", blob)
    cx, cy, rx, ry, rot, border, flags = fields
    assert (cx, cy) == pytest.approx((0.5, 0.5))
    assert (rx, ry) == pytest.approx((0.3, 0.3))
    assert rot == pytest.approx(0.0)
    assert border == pytest.approx(0.05)
    assert flags == DT_MASKS_ELLIPSE_PROPORTIONAL


def test_ellipse_circle_vs_ellipse_distinguishable() -> None:
    circle = encode_ellipse_mask_points(center_x=0.5, center_y=0.5, radius_x=0.3, radius_y=0.3)
    ellipse = encode_ellipse_mask_points(center_x=0.5, center_y=0.5, radius_x=0.4, radius_y=0.2)
    assert circle != ellipse


# ---------------------------------------------------------------------------
# rectangle path encoder
# ---------------------------------------------------------------------------


def test_rectangle_path_has_four_points() -> None:
    blob = encode_rectangle_path_points(x0=0.1, y0=0.1, x1=0.9, y1=0.9)
    # Each path point: 8 floats + 1 uint32 = 36 bytes
    assert len(blob) == 4 * 36
    # First corner should be (0.1, 0.1)
    fc_x, fc_y = struct.unpack_from("<ff", blob, 0)
    assert (fc_x, fc_y) == pytest.approx((0.1, 0.1))


def test_rectangle_path_corners_in_order() -> None:
    blob = encode_rectangle_path_points(x0=0.0, y0=0.0, x1=1.0, y1=1.0)
    corners = []
    for i in range(4):
        cx, cy = struct.unpack_from("<ff", blob, i * 36)
        corners.append((cx, cy))
    assert corners == [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]


# ---------------------------------------------------------------------------
# generic N-vertex path-form encoder (RFC-026 substrate)
# ---------------------------------------------------------------------------


def test_path_form_encodes_triangle() -> None:
    """3-vertex path: minimum legal polygon."""
    vertices = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)]
    blob = encode_path_form_points(vertices)
    assert len(blob) == 3 * 36


def test_path_form_rejects_under_three_vertices() -> None:
    """A 'closed' polygon needs at least 3 corners."""
    with pytest.raises(ValueError, match="at least 3 vertices"):
        encode_path_form_points([(0.0, 0.0), (1.0, 1.0)])
    with pytest.raises(ValueError, match="at least 3 vertices"):
        encode_path_form_points([])


def test_path_form_round_trips_arbitrary_polygon() -> None:
    """Vertex coords must round-trip through the struct cleanly."""
    vertices = [
        (0.1, 0.2),
        (0.7, 0.15),
        (0.85, 0.5),
        (0.6, 0.9),
        (0.2, 0.85),
        (0.05, 0.55),
    ]
    blob = encode_path_form_points(vertices, border=0.03)
    assert len(blob) == len(vertices) * 36
    decoded_flat = []
    expected_flat = []
    for i, (vx, vy) in enumerate(vertices):
        cx, cy = struct.unpack_from("<ff", blob, i * 36)
        decoded_flat.extend([cx, cy])
        expected_flat.extend([vx, vy])
    assert decoded_flat == pytest.approx(expected_flat)


def test_path_form_uses_degenerate_handles_for_sharp_corners() -> None:
    """ctrl1 = ctrl2 = corner ⇒ sharp corners (no Bézier curvature)."""
    vertices = [(0.2, 0.2), (0.8, 0.3), (0.5, 0.9)]
    blob = encode_path_form_points(vertices)
    for i, (cx, cy) in enumerate(vertices):
        c_x, c_y, h1_x, h1_y, h2_x, h2_y = struct.unpack_from("<ffffff", blob, i * 36)
        assert (c_x, c_y) == pytest.approx((cx, cy))
        assert (h1_x, h1_y) == pytest.approx((cx, cy))  # ctrl1 = corner
        assert (h2_x, h2_y) == pytest.approx((cx, cy))  # ctrl2 = corner


def test_path_form_writes_uniform_per_side_border() -> None:
    """Border parameter applies uniformly to every vertex's per-side floats."""
    vertices = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]
    blob = encode_path_form_points(vertices, border=0.07)
    for i in range(len(vertices)):
        b1, b2 = struct.unpack_from("<ff", blob, i * 36 + 24)
        assert (b1, b2) == pytest.approx((0.07, 0.07))


def test_rectangle_encoder_delegates_to_path_form() -> None:
    """encode_rectangle_path_points and encode_path_form_points produce
    identical bytes for the same 4-corner closed polygon — proves the
    rectangle encoder is now a thin wrapper, no behavior drift."""
    via_rect = encode_rectangle_path_points(x0=0.1, y0=0.2, x1=0.8, y1=0.9, border=0.04)
    via_path = encode_path_form_points(
        [(0.1, 0.2), (0.8, 0.2), (0.8, 0.9), (0.1, 0.9)],
        border=0.04,
    )
    assert via_rect == via_path


# ---------------------------------------------------------------------------
# blendop_params drawn-mask binding
# ---------------------------------------------------------------------------


def test_default_blendop_decodes_to_expected_size() -> None:
    """Sanity: the canonical DEFAULT_BLENDOP decodes to the documented
    420-byte struct size."""
    assert len(_DEFAULT_BLENDOP_BYTES) == _BLEND_PARAMS_SIZE


def test_default_blendop_has_expected_zero_mask_mode() -> None:
    """The canonical default has mask_mode = 0 (DISABLED)."""
    (mask_mode,) = struct.unpack_from("<I", _DEFAULT_BLENDOP_BYTES, _OFFSET_MASK_MODE)
    assert mask_mode == 0


def test_encode_blendop_sets_mask_mode_and_id() -> None:
    out = encode_blendop_with_drawn_mask(mask_id=12345, opacity=80.0)
    assert len(out) == _BLEND_PARAMS_SIZE
    (mask_mode,) = struct.unpack_from("<I", out, _OFFSET_MASK_MODE)
    (mask_id,) = struct.unpack_from("<I", out, _OFFSET_MASK_ID)
    (opacity,) = struct.unpack_from("<f", out, _OFFSET_OPACITY)
    assert mask_mode == (DEVELOP_MASK_ENABLED | DEVELOP_MASK_MASK)  # = 3
    assert mask_id == 12345
    assert opacity == pytest.approx(80.0)


def test_encode_blendop_preserves_other_fields() -> None:
    """Modifying mask_mode / mask_id / opacity must NOT touch the other
    ~400 bytes (blend_cst, blendif_params, raster_mask_source, etc.)."""
    out = encode_blendop_with_drawn_mask(mask_id=7)
    # Compare every byte except the patched fields
    diffs = []
    for i in range(_BLEND_PARAMS_SIZE):
        if i in range(_OFFSET_MASK_MODE, _OFFSET_MASK_MODE + 4):
            continue
        if i in range(_OFFSET_OPACITY, _OFFSET_OPACITY + 4):
            continue
        if i in range(_OFFSET_MASK_ID, _OFFSET_MASK_ID + 4):
            continue
        if out[i] != _DEFAULT_BLENDOP_BYTES[i]:
            diffs.append(i)
    assert not diffs, f"unexpected byte changes at offsets {diffs}"


def test_encode_blendop_rejects_bad_opacity() -> None:
    with pytest.raises(ValueError):
        encode_blendop_with_drawn_mask(mask_id=1, opacity=150.0)


def test_encode_blendop_rejects_wrong_size_template() -> None:
    with pytest.raises(ValueError):
        encode_blendop_with_drawn_mask(mask_id=1, base_blendop=b"\x00" * 100)


# ---------------------------------------------------------------------------
# Parametric (range_filter) mask encoder — RFC-024 / ADR-085
# ---------------------------------------------------------------------------


def test_parametric_luminance_only_sets_mask_mode_5() -> None:
    """Parametric-only (no drawn): mask_mode = ENABLED | CONDITIONAL = 5."""
    from chemigram.core.masking.dt_serialize import (
        DEVELOP_MASK_CONDITIONAL,
        DEVELOP_MASK_ENABLED,
        encode_blendop_with_parametric_mask,
    )

    out = encode_blendop_with_parametric_mask(
        range_kind="luminance",
        range_min=0.0,
        range_max=0.3,
    )
    assert len(out) == _BLEND_PARAMS_SIZE
    (mask_mode,) = struct.unpack_from("<I", out, _OFFSET_MASK_MODE)
    assert mask_mode == (DEVELOP_MASK_ENABLED | DEVELOP_MASK_CONDITIONAL)
    assert mask_mode == 5


def test_parametric_drawn_and_parametric_sets_mask_mode_7() -> None:
    """Drawn + parametric (when mask_id is supplied): mask_mode = 7."""
    from chemigram.core.masking.dt_serialize import (
        DEVELOP_MASK_CONDITIONAL,
        DEVELOP_MASK_ENABLED,
        DEVELOP_MASK_MASK,
        encode_blendop_with_parametric_mask,
    )

    out = encode_blendop_with_parametric_mask(
        range_kind="luminance",
        range_min=0.0,
        range_max=0.3,
        mask_id=12345,
    )
    (mask_mode,) = struct.unpack_from("<I", out, _OFFSET_MASK_MODE)
    expected = DEVELOP_MASK_ENABLED | DEVELOP_MASK_MASK | DEVELOP_MASK_CONDITIONAL
    assert mask_mode == expected
    assert mask_mode == 7
    # mask_id must be set
    from chemigram.core.masking.dt_serialize import _OFFSET_MASK_ID

    (mask_id,) = struct.unpack_from("<I", out, _OFFSET_MASK_ID)
    assert mask_id == 12345


def test_parametric_blendif_sets_correct_channel_bit() -> None:
    """The blendif bitmask must have bit channel_id set; inverted has +16 too."""
    from chemigram.core.masking.dt_serialize import (
        _OFFSET_BLENDIF,
        DEVELOP_BLENDIF_GRAY_in,
        DEVELOP_BLENDIF_H_in,
        encode_blendop_with_parametric_mask,
    )

    # luminance: channel 0
    out = encode_blendop_with_parametric_mask(range_kind="luminance", range_min=0.0, range_max=0.3)
    (blendif,) = struct.unpack_from("<I", out, _OFFSET_BLENDIF)
    assert blendif == (1 << DEVELOP_BLENDIF_GRAY_in)

    # color_h: channel 8
    out = encode_blendop_with_parametric_mask(range_kind="color_h", range_min=0.55, range_max=0.65)
    (blendif,) = struct.unpack_from("<I", out, _OFFSET_BLENDIF)
    assert blendif == (1 << DEVELOP_BLENDIF_H_in)

    # luminance inverted: channels 0 + 16
    out = encode_blendop_with_parametric_mask(
        range_kind="luminance", range_min=0.0, range_max=0.3, invert=True
    )
    (blendif,) = struct.unpack_from("<I", out, _OFFSET_BLENDIF)
    assert blendif == ((1 << DEVELOP_BLENDIF_GRAY_in) | (1 << (DEVELOP_BLENDIF_GRAY_in + 16)))


def test_parametric_control_points_map_min_max_feather_correctly() -> None:
    """{min=0.2, max=0.5, feather=0.05} -> [0.15, 0.20, 0.50, 0.55]."""
    from chemigram.core.masking.dt_serialize import (
        _OFFSET_BLENDIF_PARAMETERS,
        encode_blendop_with_parametric_mask,
    )

    out = encode_blendop_with_parametric_mask(
        range_kind="luminance", range_min=0.2, range_max=0.5, feather=0.05
    )
    # luminance = channel 0, so control points are at offset 68 + 0*16 = 68
    pts = struct.unpack_from("<ffff", out, _OFFSET_BLENDIF_PARAMETERS)
    assert pts == pytest.approx((0.15, 0.20, 0.50, 0.55))


def test_parametric_control_points_clamp_to_zero_one() -> None:
    """Feather extending past [0, 1] must clamp."""
    from chemigram.core.masking.dt_serialize import (
        _OFFSET_BLENDIF_PARAMETERS,
        encode_blendop_with_parametric_mask,
    )

    out = encode_blendop_with_parametric_mask(
        range_kind="luminance", range_min=0.0, range_max=1.0, feather=0.1
    )
    pts = struct.unpack_from("<ffff", out, _OFFSET_BLENDIF_PARAMETERS)
    assert pts == pytest.approx((0.0, 0.0, 1.0, 1.0))  # clamped


def test_parametric_color_h_writes_to_offset_for_channel_8() -> None:
    """color_h is channel 8; control points at offset 68 + 8*16 = 196.
    Channel 0 (luminance) must remain at default [0, 0, 1, 1]."""
    from chemigram.core.masking.dt_serialize import (
        _OFFSET_BLENDIF_PARAMETERS,
        encode_blendop_with_parametric_mask,
    )

    out = encode_blendop_with_parametric_mask(
        range_kind="color_h", range_min=0.55, range_max=0.65, feather=0.05
    )
    # Channel 8 control points
    pts_8 = struct.unpack_from("<ffff", out, _OFFSET_BLENDIF_PARAMETERS + 8 * 16)
    assert pts_8 == pytest.approx((0.50, 0.55, 0.65, 0.70))
    # Channel 0 must still be default [0, 0, 1, 1]
    pts_0 = struct.unpack_from("<ffff", out, _OFFSET_BLENDIF_PARAMETERS)
    assert pts_0 == pytest.approx((0.0, 0.0, 1.0, 1.0))


def test_parametric_color_kind_sets_blend_cst_to_hsl() -> None:
    """color_* kinds must set blend_cst = IOP_CS_HSL = 5; luminance leaves it."""
    from chemigram.core.masking.dt_serialize import (
        _OFFSET_BLEND_CST,
        IOP_CS_HSL,
        encode_blendop_with_parametric_mask,
    )

    # color_h sets blend_cst to HSL
    out = encode_blendop_with_parametric_mask(range_kind="color_h", range_min=0.55, range_max=0.65)
    (blend_cst,) = struct.unpack_from("<i", out, _OFFSET_BLEND_CST)
    assert blend_cst == IOP_CS_HSL

    # luminance leaves blend_cst at base default (4 = Lab in our default blendop)
    out = encode_blendop_with_parametric_mask(range_kind="luminance", range_min=0.0, range_max=0.3)
    (blend_cst,) = struct.unpack_from("<i", out, _OFFSET_BLEND_CST)
    assert blend_cst == 4  # default in _DEFAULT_BLENDOP_BYTES


def test_parametric_mask_combine_hardcoded_to_zero() -> None:
    """ADR-085: mask_combine = 0 (AND/intersect) for v1.9.0."""
    from chemigram.core.masking.dt_serialize import (
        _OFFSET_MASK_COMBINE,
        encode_blendop_with_parametric_mask,
    )

    out = encode_blendop_with_parametric_mask(
        range_kind="luminance", range_min=0.0, range_max=0.3, mask_id=99
    )
    (combine,) = struct.unpack_from("<I", out, _OFFSET_MASK_COMBINE)
    assert combine == 0


def test_parametric_preserves_other_byte_regions() -> None:
    """Encoding a parametric mask must not touch bytes outside the
    explicit set: mask_mode (0..4), opacity (16..20), mask_combine
    (20..24), mask_id (24..28; only when drawn), blendif (28..32),
    blendif_parameters[channel_id] (variable), blend_cst (4..8; only
    for color kinds).

    Everything else stays at the default. This is the discriminator
    for unintended struct churn.
    """
    from chemigram.core.masking.dt_serialize import (
        _OFFSET_BLENDIF,
        _OFFSET_BLENDIF_PARAMETERS,
        _OFFSET_MASK_COMBINE,
        encode_blendop_with_parametric_mask,
    )

    out = encode_blendop_with_parametric_mask(range_kind="luminance", range_min=0.2, range_max=0.5)
    # Build the set of byte indices that ARE allowed to differ
    allowed_diffs: set[int] = set()
    allowed_diffs.update(range(_OFFSET_MASK_MODE, _OFFSET_MASK_MODE + 4))
    allowed_diffs.update(range(_OFFSET_OPACITY, _OFFSET_OPACITY + 4))
    allowed_diffs.update(range(_OFFSET_MASK_COMBINE, _OFFSET_MASK_COMBINE + 4))
    allowed_diffs.update(range(_OFFSET_BLENDIF, _OFFSET_BLENDIF + 4))
    # Channel 0 (luminance) control points: offset 68, 16 bytes
    allowed_diffs.update(range(_OFFSET_BLENDIF_PARAMETERS, _OFFSET_BLENDIF_PARAMETERS + 16))

    diffs = [
        i
        for i in range(_BLEND_PARAMS_SIZE)
        if out[i] != _DEFAULT_BLENDOP_BYTES[i] and i not in allowed_diffs
    ]
    assert not diffs, f"unexpected byte changes at offsets {diffs}"


def test_parametric_rejects_unknown_kind() -> None:
    from chemigram.core.masking.dt_serialize import encode_blendop_with_parametric_mask

    with pytest.raises(ValueError, match="unknown range_kind"):
        encode_blendop_with_parametric_mask(range_kind="bogus", range_min=0.0, range_max=0.5)


def test_parametric_rejects_min_greater_than_max() -> None:
    from chemigram.core.masking.dt_serialize import encode_blendop_with_parametric_mask

    with pytest.raises(ValueError, match=r"range_min.*> range_max"):
        encode_blendop_with_parametric_mask(range_kind="luminance", range_min=0.7, range_max=0.3)


def test_parametric_rejects_out_of_range_bounds() -> None:
    from chemigram.core.masking.dt_serialize import encode_blendop_with_parametric_mask

    with pytest.raises(ValueError, match="range_min must be in"):
        encode_blendop_with_parametric_mask(range_kind="luminance", range_min=-0.1, range_max=0.5)
    with pytest.raises(ValueError, match="range_max must be in"):
        encode_blendop_with_parametric_mask(range_kind="luminance", range_min=0.0, range_max=1.5)


def test_parametric_rejects_excessive_feather() -> None:
    from chemigram.core.masking.dt_serialize import encode_blendop_with_parametric_mask

    with pytest.raises(ValueError, match="feather must be in"):
        encode_blendop_with_parametric_mask(
            range_kind="luminance", range_min=0.0, range_max=0.5, feather=0.7
        )


# ---------------------------------------------------------------------------
# Circle mask form + clone source (RFC-025 / ADR-087)
# ---------------------------------------------------------------------------


def test_circle_mask_points_is_16_bytes() -> None:
    from chemigram.core.masking.dt_serialize import encode_circle_mask_points

    blob = encode_circle_mask_points(center_x=0.5, center_y=0.5, radius=0.05)
    assert len(blob) == 16  # 4 floats


def test_circle_mask_points_round_trips() -> None:
    from chemigram.core.masking.dt_serialize import encode_circle_mask_points

    blob = encode_circle_mask_points(center_x=0.3, center_y=0.7, radius=0.04, border=0.02)
    cx, cy, r, b = struct.unpack("<ffff", blob)
    assert cx == pytest.approx(0.3)
    assert cy == pytest.approx(0.7)
    assert r == pytest.approx(0.04)
    assert b == pytest.approx(0.02)


def test_clone_mask_src_is_8_bytes() -> None:
    from chemigram.core.masking.dt_serialize import encode_clone_mask_src

    blob = encode_clone_mask_src(source_x=0.4, source_y=0.3)
    assert len(blob) == 8


def test_clone_mask_src_round_trips() -> None:
    from chemigram.core.masking.dt_serialize import encode_clone_mask_src

    blob = encode_clone_mask_src(source_x=0.4, source_y=0.3)
    sx, sy = struct.unpack("<ff", blob)
    assert (sx, sy) == pytest.approx((0.4, 0.3))


def test_clone_mask_src_distinguishes_from_empty() -> None:
    """A clone source mask_src is non-zero; empty (heal) is zero."""
    from chemigram.core.masking.dt_serialize import (
        empty_mask_src,
        encode_clone_mask_src,
    )

    clone = encode_clone_mask_src(source_x=0.4, source_y=0.3)
    heal = empty_mask_src()
    assert clone != heal
    assert heal == b"\x00" * 8


# ---------------------------------------------------------------------------
# Retouch encoders (RFC-025 / ADR-087)
# ---------------------------------------------------------------------------


def test_retouch_form_is_44_bytes() -> None:
    from chemigram.core.masking.dt_serialize import (
        DT_IOP_RETOUCH_HEAL,
        encode_retouch_form,
    )

    form = encode_retouch_form(formid=12345, algorithm=DT_IOP_RETOUCH_HEAL)
    assert len(form) == 44


def test_retouch_form_writes_formid_and_algorithm_at_correct_offsets() -> None:
    from chemigram.core.masking.dt_serialize import (
        DT_IOP_RETOUCH_HEAL,
        encode_retouch_form,
    )

    form = encode_retouch_form(formid=99, algorithm=DT_IOP_RETOUCH_HEAL)
    (formid,) = struct.unpack_from("<i", form, 0)
    (scale,) = struct.unpack_from("<i", form, 4)
    (algorithm,) = struct.unpack_from("<i", form, 8)
    assert formid == 99
    assert scale == 0
    assert algorithm == DT_IOP_RETOUCH_HEAL


def test_retouch_form_clone_vs_heal_distinct_bytes() -> None:
    from chemigram.core.masking.dt_serialize import (
        DT_IOP_RETOUCH_CLONE,
        DT_IOP_RETOUCH_HEAL,
        encode_retouch_form,
    )

    heal = encode_retouch_form(formid=1, algorithm=DT_IOP_RETOUCH_HEAL)
    clone = encode_retouch_form(formid=1, algorithm=DT_IOP_RETOUCH_CLONE)
    assert heal != clone


def test_retouch_op_params_total_is_13260_bytes() -> None:
    from chemigram.core.masking.dt_serialize import (
        DT_IOP_RETOUCH_HEAL,
        RETOUCH_PARAMS_SIZE,
        encode_retouch_form,
        encode_retouch_op_params,
    )

    one_form = encode_retouch_form(formid=1, algorithm=DT_IOP_RETOUCH_HEAL)
    blob = encode_retouch_op_params([one_form])
    assert len(blob) == RETOUCH_PARAMS_SIZE
    assert RETOUCH_PARAMS_SIZE == 13260


def test_retouch_op_params_pads_unused_form_slots_with_zeros() -> None:
    """Active forms come first; remaining slots are zero-filled 44-byte blocks."""
    from chemigram.core.masking.dt_serialize import (
        DT_IOP_RETOUCH_HEAL,
        RETOUCH_FORM_SIZE,
        RETOUCH_NO_FORMS,
        encode_retouch_form,
        encode_retouch_op_params,
    )

    one_form = encode_retouch_form(formid=1, algorithm=DT_IOP_RETOUCH_HEAL)
    blob = encode_retouch_op_params([one_form])
    # Slot 0 = the active form
    assert blob[:RETOUCH_FORM_SIZE] == one_form
    # Slots 1..299 must all be zero
    for i in range(1, RETOUCH_NO_FORMS):
        slot = blob[i * RETOUCH_FORM_SIZE : (i + 1) * RETOUCH_FORM_SIZE]
        assert slot == b"\x00" * RETOUCH_FORM_SIZE, f"slot {i} not zero"


def test_retouch_op_params_global_tail_is_zero_by_default() -> None:
    """The 60-byte global tail (algorithm, scales, fill, blur, max_heal_iter)
    is all zeros for the v1.9.0 ship — per-form algorithm is what matters."""
    from chemigram.core.masking.dt_serialize import (
        DT_IOP_RETOUCH_HEAL,
        RETOUCH_FORM_SIZE,
        RETOUCH_NO_FORMS,
        encode_retouch_form,
        encode_retouch_op_params,
    )

    one_form = encode_retouch_form(formid=1, algorithm=DT_IOP_RETOUCH_HEAL)
    blob = encode_retouch_op_params([one_form])
    tail_offset = RETOUCH_NO_FORMS * RETOUCH_FORM_SIZE  # 13200
    tail = blob[tail_offset:]
    assert len(tail) == 60
    assert tail == b"\x00" * 60


def test_retouch_op_params_rejects_too_many_forms() -> None:
    from chemigram.core.masking.dt_serialize import (
        DT_IOP_RETOUCH_HEAL,
        RETOUCH_NO_FORMS,
        encode_retouch_form,
        encode_retouch_op_params,
    )

    too_many = [
        encode_retouch_form(formid=i + 1, algorithm=DT_IOP_RETOUCH_HEAL)
        for i in range(RETOUCH_NO_FORMS + 1)
    ]
    with pytest.raises(ValueError, match="at most 300 forms"):
        encode_retouch_op_params(too_many)


def test_retouch_op_params_rejects_wrong_size_form() -> None:
    from chemigram.core.masking.dt_serialize import encode_retouch_op_params

    with pytest.raises(ValueError, match=r"32 bytes, expected 44"):
        encode_retouch_op_params([b"\x00" * 32])  # wrong size


def test_retouch_op_params_handles_multiple_forms() -> None:
    """v1.9.0 ships single-form per call, but the encoder must handle
    multi-form inputs cleanly (RFC-030 will batch AI-detected spots)."""
    from chemigram.core.masking.dt_serialize import (
        DT_IOP_RETOUCH_CLONE,
        DT_IOP_RETOUCH_HEAL,
        RETOUCH_FORM_SIZE,
        encode_retouch_form,
        encode_retouch_op_params,
    )

    forms = [
        encode_retouch_form(formid=10, algorithm=DT_IOP_RETOUCH_HEAL),
        encode_retouch_form(formid=20, algorithm=DT_IOP_RETOUCH_CLONE),
        encode_retouch_form(formid=30, algorithm=DT_IOP_RETOUCH_HEAL),
    ]
    blob = encode_retouch_op_params(forms)
    # Slots 0-2 are active
    for i in range(3):
        slot = blob[i * RETOUCH_FORM_SIZE : (i + 1) * RETOUCH_FORM_SIZE]
        assert slot == forms[i]
    # Slot 3 should be zero-padded
    slot_3 = blob[3 * RETOUCH_FORM_SIZE : 4 * RETOUCH_FORM_SIZE]
    assert slot_3 == b"\x00" * RETOUCH_FORM_SIZE


# ---------------------------------------------------------------------------
# XMP blob encoding (matches dt_exif_xmp_encode)
# ---------------------------------------------------------------------------


def test_short_blob_encoded_as_hex() -> None:
    """Blobs ≤ 100 bytes are stored as plain lowercase hex."""
    raw = b"\xde\xad\xbe\xef"
    encoded = encode_mask_blob_for_xmp(raw)
    assert encoded == "deadbeef"


def test_long_blob_encoded_as_gz_base64() -> None:
    """Blobs > 100 bytes are gz+base64 encoded with the 'gz<level>' prefix."""
    raw = b"\xab" * 200
    encoded = encode_mask_blob_for_xmp(raw)
    assert encoded.startswith("gz")
    # Round-trip via the decoder used internally
    import base64
    import zlib

    level = int(encoded[2:4])
    assert 1 <= level <= 99
    decompressed = zlib.decompress(base64.b64decode(encoded[4:]))
    assert decompressed == raw


def test_empty_mask_src_is_eight_zeros() -> None:
    assert empty_mask_src() == b"\x00" * 8


# ---------------------------------------------------------------------------
# High-level form builders + masks_history XML
# ---------------------------------------------------------------------------


def test_build_gradient_form_defaults() -> None:
    from chemigram.core.masking.dt_serialize import (
        DT_MASKS_GRADIENT,
        DT_MASKS_VERSION,
        build_gradient_form,
    )

    form = build_gradient_form(mask_id=42)
    assert form.mask_id == 42
    assert form.mask_type == DT_MASKS_GRADIENT
    assert form.mask_version == DT_MASKS_VERSION
    assert form.mask_nb == 1
    assert len(form.mask_points) == 28
    assert form.mask_src == b"\x00" * 8


def test_build_ellipse_form_defaults() -> None:
    from chemigram.core.masking.dt_serialize import DT_MASKS_ELLIPSE, build_ellipse_form

    form = build_ellipse_form(mask_id=7)
    assert form.mask_type == DT_MASKS_ELLIPSE
    assert form.mask_nb == 1
    assert len(form.mask_points) == 28


def test_build_rectangle_form_has_four_path_points() -> None:
    from chemigram.core.masking.dt_serialize import DT_MASKS_PATH, build_rectangle_form

    form = build_rectangle_form(mask_id=99, x0=0.0, y0=0.0, x1=1.0, y1=1.0)
    assert form.mask_type == DT_MASKS_PATH
    assert form.mask_nb == 4
    assert len(form.mask_points) == 4 * 36


def test_build_path_form_with_six_vertex_polygon() -> None:
    """Generic N-vertex path form (RFC-026 substrate)."""
    from chemigram.core.masking.dt_serialize import DT_MASKS_PATH, build_path_form

    vertices = [
        (0.1, 0.2),
        (0.7, 0.15),
        (0.85, 0.5),
        (0.6, 0.9),
        (0.2, 0.85),
        (0.05, 0.55),
    ]
    form = build_path_form(mask_id=42, vertices=vertices, name="hexagon")
    assert form.mask_id == 42
    assert form.mask_type == DT_MASKS_PATH
    assert form.mask_nb == 6
    assert form.mask_name == "hexagon"
    assert len(form.mask_points) == 6 * 36


def test_build_path_form_handles_large_subject_silhouette() -> None:
    """A 500-vertex polygon (typical AI-subject mask after Douglas-Peucker
    simplification) should encode without issue."""
    import math

    from chemigram.core.masking.dt_serialize import build_path_form

    # Synthesize a 500-vertex circle approximation.
    n = 500
    vertices = [
        (0.5 + 0.4 * math.cos(2 * math.pi * i / n), 0.5 + 0.4 * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]
    form = build_path_form(mask_id=1, vertices=vertices)
    assert form.mask_nb == n
    assert len(form.mask_points) == n * 36


def test_build_form_from_spec_dispatches_to_path() -> None:
    """The vocab-spec dispatcher must accept dt_form: 'path' for RFC-026."""
    from chemigram.core.masking.dt_serialize import (
        DT_MASKS_PATH,
        build_form_from_spec,
    )

    spec = {
        "dt_form": "path",
        "dt_params": {
            "vertices": [(0.2, 0.2), (0.8, 0.3), (0.5, 0.9)],
            "border": 0.03,
        },
    }
    form = build_form_from_spec(mask_id=7, spec=spec)
    assert form.mask_type == DT_MASKS_PATH
    assert form.mask_nb == 3


def test_build_form_from_spec_rejects_unknown_form_listing_path() -> None:
    """The error message must list 'path' as a valid form name."""
    from chemigram.core.masking.dt_serialize import build_form_from_spec

    with pytest.raises(ValueError, match="path"):
        build_form_from_spec(mask_id=1, spec={"dt_form": "bogus", "dt_params": {}})


def test_masks_history_xml_round_trip() -> None:
    """The generated XML must parse cleanly and contain one <rdf:li>
    per form with the expected attributes."""
    from defusedxml.ElementTree import fromstring

    from chemigram.core.masking.dt_serialize import (
        build_gradient_form,
        build_masks_history_xml,
    )

    form = build_gradient_form(mask_id=12345, name="sky_grad")
    xml = build_masks_history_xml([form])
    parsed = fromstring(xml)
    # One <rdf:Seq> with one <rdf:li>
    seq = parsed.find("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Seq")
    assert seq is not None
    items = seq.findall("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li")
    assert len(items) == 1
    li = items[0]
    assert li.get("{http://darktable.sf.net/}mask_id") == "12345"
    assert li.get("{http://darktable.sf.net/}mask_name") == "sky_grad"


def test_masks_history_xml_handles_multiple_forms() -> None:
    from defusedxml.ElementTree import fromstring

    from chemigram.core.masking.dt_serialize import (
        build_ellipse_form,
        build_gradient_form,
        build_masks_history_xml,
    )

    forms = [
        build_gradient_form(mask_id=1, name="g"),
        build_ellipse_form(mask_id=2, name="e"),
    ]
    xml = build_masks_history_xml(forms)
    parsed = fromstring(xml)
    items = parsed.findall(".//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li")
    assert len(items) == 2
    assert [i.get("{http://darktable.sf.net/}mask_num") for i in items] == ["1", "2"]
