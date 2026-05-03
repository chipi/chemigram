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
