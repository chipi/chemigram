"""Lab-grade isolation tests for arbitrary primitives applied through a mask.

The spatial counterpart to ``test_lab_grade_primitives.py``: that file
proves "every primitive does its documented thing globally"; this file
proves "any primitive can be confined to a region of the frame via
:func:`apply_with_drawn_mask`, and the engine actually localizes the
effect" — for a curated representative spread across module categories.

The assertion shape is **paired-render**: each primitive is rendered
globally, then through a centered ellipse mask. The corner patches of
the rendered ColorChecker (0, 5, 18, 23) are inspected. A working mask
must produce a *significant difference* between global and masked
corner chroma — proof the mask actually constrains the primitive's
spatial reach.

We deliberately don't cross-reference a separate baseline render. An
earlier formulation that did (compare masked corners to a fresh
baseline render) was order-dependent and flaky on a shared darktable
configdir: when three renders of the same input file run in close
succession, darktable's library.db caches state across them and the
third render frequently produces visually-incorrect output. Two
renders per test is the working ceiling we found empirically.

Coverage scope:

- :data:`MASK_COVERAGE` lists colorbalancergb saturation primitives.
  Saturation kill produces the largest, most repeatable corner-chroma
  signature on a chart (collapses ~14 chroma units to ~0).
- The unit test :mod:`test_apply_universality` separately proves the
  mechanical apply path completes for every loaded vocab entry across
  every drawn-form spec, so this e2e test doesn't need to enumerate.

Modules deliberately not covered here:

- ``exposure``: corner luma deltas through chart pipeline are sensitive
  to darktable's display-referred clipping behavior; render-to-render
  variance regularly clears the noise floor we'd want for assertion.
  The 4 shipped masked exposure entries (``gradient_*``, ``radial_*``,
  ``rectangle_*``) cover this case in :mod:`test_lab_grade_primitives`.
- ``sigmoid``, ``vignette``, ``bilat``, ``temperature``, ``grain``: see
  ``docs/guides/mask-applicable-controls.md`` for the per-module
  rationale and verification path for each.
"""

from __future__ import annotations

import dataclasses
import os
import sys
from pathlib import Path

import pytest

from chemigram.core.pipeline import render
from chemigram.core.vocab import VocabularyIndex, load_packs
from chemigram.core.xmp import Xmp, parse_xmp, write_xmp

_TESTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_TESTS_ROOT.parent))

from tests.e2e._patch_reader import (  # noqa: E402
    PatchSample,
    chroma_lab,
    read_colorchecker,
)

_REPO = Path(__file__).resolve().parents[2]
_BASELINE_TEMPLATE = _REPO / "src/chemigram/core/_baseline_v1.xmp"
_COLORCHECKER = _REPO / "tests/fixtures/reference-targets/colorchecker_synthetic_srgb.png"

_RENDER_W = 400
_RENDER_H = 400

# Centered ellipse covering the middle 16% of the frame: overlaps the
# 4 center patches (8, 9, 14, 15) and excludes the 4 corner patches
# (0, 5, 18, 23).
_CENTER_MASK_SPEC = {
    "dt_form": "ellipse",
    "dt_params": {
        "center_x": 0.5,
        "center_y": 0.5,
        "radius_x": 0.2,
        "radius_y": 0.2,
        "border": 0.05,
    },
}

_CC_CORNER_4 = [0, 5, 18, 23]


def _corner_chroma(samples: list[PatchSample]) -> float:
    return sum(chroma_lab(samples[i]) for i in _CC_CORNER_4) / 4


# Primitives the e2e tests verify localize through the mask. Each must
# have a clean, large-magnitude corner-chroma signature when applied
# globally so a "masked corners are clearly different from globally-
# affected corners" assertion has enough headroom over render noise.
#
# Each entry: (name, parameter_values). For non-parameterized entries
# parameter_values is an empty dict; for parameterized entries (RFC-021)
# we supply the values that produce the expected signature.
#
# We pick ``saturation_global`` at -1.0 because:
#   - It collapses corner chroma from ~14 to ~0 globally — the largest,
#     most repeatable signature in the vocab.
#   - It exercises colorbalancergb, the most-used module category and
#     the one whose mask binding the unit test cannot verify end-to-end
#     against darktable's renderer.
#   - The unit test :mod:`test_apply_universality` separately proves
#     the apply path completes for every loaded vocab entry across
#     every drawn-form, so we don't need to enumerate at the e2e tier.
#
# Pre-v1.6 this slot was the discrete ``sat_kill`` entry; it was retired
# when ``saturation_global`` shipped (RFC-021) and the parameterized form
# at -1.0 is the direct equivalent.
MASK_COVERAGE: list[tuple[str, dict[str, float]]] = [
    ("saturation_global", {"saturation_global": -1.0}),
]


def _resolve_configdir() -> Path:
    raw = os.environ.get("CHEMIGRAM_DT_CONFIGDIR")
    if raw:
        path = Path(raw).expanduser()
        if path.exists():
            return path
    fallback = Path.home() / "chemigram-phase0" / "dt-config"
    if fallback.exists():
        return fallback
    pytest.skip(
        "CHEMIGRAM_DT_CONFIGDIR not set and ~/chemigram-phase0/dt-config "
        "not found — lab-grade tests need a bootstrapped darktable configdir."
    )


def _empty_baseline() -> Xmp:
    template = parse_xmp(_BASELINE_TEMPLATE)
    return dataclasses.replace(template, history=())


def _render_and_read(
    *,
    applied: Xmp,
    label: str,
    configdir: Path,
    out_dir: Path,
) -> list[PatchSample]:
    xmp_path = out_dir / f"{label}.xmp"
    out_path = out_dir / f"{label}.jpg"
    write_xmp(applied, xmp_path)
    try:
        result = render(
            raw_path=_COLORCHECKER,
            xmp_path=xmp_path,
            output_path=out_path,
            width=_RENDER_W,
            height=_RENDER_H,
            high_quality=False,
            configdir=configdir,
        )
        if not result.success:
            pytest.fail(f"render failed for {label}: {result.error_message}")
        return read_colorchecker(out_path)
    finally:
        xmp_path.unlink(missing_ok=True)


@pytest.fixture(scope="module")
def configdir() -> Path:
    return _resolve_configdir()


@pytest.fixture(scope="module")
def baseline_xmp() -> Xmp:
    return _empty_baseline()


@pytest.fixture(scope="module")
def vocab() -> VocabularyIndex:
    return load_packs(["starter", "expressive-baseline"])


@pytest.mark.parametrize("coverage_entry", MASK_COVERAGE, ids=[name for name, _ in MASK_COVERAGE])
def test_mask_localizes_arbitrary_primitive(
    coverage_entry: tuple[str, dict[str, float]],
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """Render the primitive globally and through a centered mask, then
    assert the corner-chroma divergence between the two. A working
    drawn-mask binding produces dramatically different corner chroma in
    the two renders; a broken binding (no mask, leaked mask, inverted
    mask) produces near-identical corner chroma.

    Specifically, asserts ``|global_corner - masked_corner| > 5.0``
    chroma units. Render-to-render variance on corner chroma sits
    around 0.5 units, so a 5-unit threshold is comfortably above noise
    while still failing fast on a fully-broken mask binding.

    The assertion is **two-render** by design: an earlier triple-render
    formulation that compared each render to a separate baseline render
    was flaky against a shared darktable configdir. Two renders per
    test is the empirical working ceiling.
    """
    _ = darktable_binary
    from chemigram.core.helpers import apply_entry

    primitive_name, parameter_values = coverage_entry

    entry = vocab.lookup_by_name(primitive_name)
    if entry is None:
        pytest.fail(f"primitive {primitive_name!r} not in loaded packs")
    if entry.mask_spec is not None:
        pytest.fail(
            f"primitive {primitive_name!r} already carries a mask_spec — "
            f"this test exercises mask synthesis on global primitives only"
        )

    out_dir = tmp_path_factory.mktemp(f"masked_universality_{primitive_name}")

    global_patches = _render_and_read(
        applied=apply_entry(baseline_xmp, entry, parameter_values=parameter_values or None),
        label="global",
        configdir=configdir,
        out_dir=out_dir,
    )
    masked_patches = _render_and_read(
        applied=apply_entry(
            baseline_xmp,
            entry,
            parameter_values=parameter_values or None,
            mask_spec=_CENTER_MASK_SPEC,
        ),
        label="masked",
        configdir=configdir,
        out_dir=out_dir,
    )

    global_corner = _corner_chroma(global_patches)
    masked_corner = _corner_chroma(masked_patches)
    divergence = abs(global_corner - masked_corner)

    if divergence < 5.0:
        pytest.fail(
            f"primitive {primitive_name!r} masked vs global corners didn't diverge:\n"
            f"  description: {entry.description}\n"
            f"  global_corner_chroma: {global_corner:.3f}\n"
            f"  masked_corner_chroma: {masked_corner:.3f}\n"
            f"  divergence: {divergence:.3f} (expected > 5.0)\n"
            f"\n"
            f"  This means the mask is not constraining the primitive: corners\n"
            f"  receive the same effect whether masked or global, suggesting\n"
            f"  a broken mask binding (mask_id mismatch, opacity 0, inverted\n"
            f"  mask, or pipeline-order issue)."
        )


def test_parameterized_toneequalizer_apply_completes(
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """Toneequalizer is the most complex multi-parameter ship (9 axes).
    We exercise: full curve (all 9 nodes), partial-update (2 nodes), and
    single-node-with-mask. Localization isn't asserted on chart fixtures
    — toneequal x mask works mechanically but the per-band luma deltas
    on flat patches are hard to disentangle from the mask's spatial
    falloff.
    """
    _ = darktable_binary
    from chemigram.core.helpers import apply_entry

    entry = vocab.lookup_by_name("toneequalizer")
    if entry is None:
        pytest.fail("'toneequalizer' parameterized entry not in loaded packs")
    if entry.parameters is None:
        pytest.fail("'toneequalizer' loaded but parameters is None")

    cases = [
        # All 9 axes: synthetic compression curve
        (
            "full_compress",
            {
                "noise": -0.5,
                "ultra_deep_blacks": -0.3,
                "deep_blacks": -0.1,
                "blacks": 0.1,
                "shadows": 0.3,
                "midtones": 0.0,
                "highlights": -0.3,
                "whites": -0.5,
                "speculars": -0.7,
            },
        ),
        # Partial-update: just shadows + highlights
        ("shadows_highlights", {"shadows": 0.7, "highlights": -0.3}),
        # Single-node + mask
        ("midtones_only", {"midtones": 0.5}),
    ]
    out_dir = tmp_path_factory.mktemp("masked_param_toneequalizer")
    for label, values in cases:
        applied = apply_entry(
            baseline_xmp,
            entry,
            parameter_values=values,
            mask_spec=_CENTER_MASK_SPEC,
        )
        _render_and_read(
            applied=applied,
            label=f"toneequalizer_{label}",
            configdir=configdir,
            out_dir=out_dir,
        )


def test_parameterized_colorbalancergb_axes_apply_completes(
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """The 3 colorbalancergb additional axes (vibrance, chroma_global,
    hue_angle) ride the same shared decoder. We verify each parameterized
    + masked apply path runs end-to-end. Localization isn't asserted at
    the e2e tier — saturation_global already proves the colorbalancergb-
    through-mask path in test_mask_localizes_arbitrary_primitive.
    """
    _ = darktable_binary
    from chemigram.core.helpers import apply_entry

    cases = [
        ("vibrance", {"vibrance": 0.5}),
        ("chroma_global", {"chroma_global": 0.5}),
        ("hue_angle", {"hue_angle": 30.0}),
    ]
    out_dir = tmp_path_factory.mktemp("masked_param_colorbalancergb_axes")
    for entry_name, values in cases:
        entry = vocab.lookup_by_name(entry_name)
        if entry is None:
            pytest.fail(f"{entry_name!r} parameterized entry not in loaded packs")
        if entry.parameters is None:
            pytest.fail(f"{entry_name!r} loaded but parameters is None")
        applied = apply_entry(
            baseline_xmp, entry, parameter_values=values, mask_spec=_CENTER_MASK_SPEC
        )
        _render_and_read(
            applied=applied,
            label=f"{entry_name}_masked",
            configdir=configdir,
            out_dir=out_dir,
        )


def test_parameterized_sharpen_apply_completes(
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """Sharpen operates on edges, not flat chart patches — no spatial-
    localization assertion is meaningful on the synthetic fixture. We
    verify the parameterized + masked apply path runs end-to-end at
    multiple amount values.
    """
    _ = darktable_binary
    from chemigram.core.helpers import apply_entry

    entry = vocab.lookup_by_name("sharpen")
    if entry is None:
        pytest.fail("'sharpen' parameterized entry not in loaded packs")
    if entry.parameters is None:
        pytest.fail("'sharpen' loaded but parameters is None")

    out_dir = tmp_path_factory.mktemp("masked_param_sharpen")
    for v in (0.5, 1.0, 1.5):
        applied = apply_entry(
            baseline_xmp,
            entry,
            parameter_values={"amount": v},
            mask_spec=_CENTER_MASK_SPEC,
        )
        _render_and_read(
            applied=applied,
            label=f"sharpen_{v:.1f}",
            configdir=configdir,
            out_dir=out_dir,
        )


def test_parameterized_crop_apply_completes(
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """Crop is a workflow primitive — masking it doesn't make photographic
    sense (you'd just crop differently). We verify the parameterized apply
    + mask path runs end-to-end at multiple crop rectangles to exercise
    the multi-axis ship and confirm crop's mask binding doesn't crash.
    """
    _ = darktable_binary
    from chemigram.core.helpers import apply_entry

    entry = vocab.lookup_by_name("crop")
    if entry is None:
        pytest.fail("'crop' parameterized entry not in loaded packs")
    if entry.parameters is None:
        pytest.fail("'crop' loaded but parameters is None")

    out_dir = tmp_path_factory.mktemp("masked_param_crop")
    cases = [
        ("center_80", {"cx": 0.1, "cy": 0.1, "cw": 0.9, "ch": 0.9}),
        ("partial_left_only", {"cx": 0.05}),  # partial-update — only cx
    ]
    for label, values in cases:
        applied = apply_entry(
            baseline_xmp,
            entry,
            parameter_values=values,
            mask_spec=_CENTER_MASK_SPEC,
        )
        _render_and_read(
            applied=applied,
            label=f"crop_{label}",
            configdir=configdir,
            out_dir=out_dir,
        )


def test_parameterized_temperature_apply_completes(
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """Temperature mask binding is documented as ineffective on most
    pipelines (per mask-applicable-controls.md#temperature) — the module
    runs early in darktable's pipeline so masking has limited photographic
    use. We verify the parameterized + masked apply path runs end-to-end
    at multi-parameter values to exercise the multi-axis ship.
    """
    _ = darktable_binary
    from chemigram.core.helpers import apply_entry

    entry = vocab.lookup_by_name("temperature")
    if entry is None:
        pytest.fail("'temperature' parameterized entry not in loaded packs")
    if entry.parameters is None:
        pytest.fail("'temperature' loaded but parameters is None")

    out_dir = tmp_path_factory.mktemp("masked_param_temperature")
    cases = [
        ("warmer", {"red_coeff": 2.148, "blue_coeff": 1.209}),
        ("cooler", {"red_coeff": 1.209, "blue_coeff": 2.137}),
        ("neutral_partial", {"red_coeff": 1.5}),  # partial-update — only red
    ]
    for label, values in cases:
        applied = apply_entry(
            baseline_xmp,
            entry,
            parameter_values=values,
            mask_spec=_CENTER_MASK_SPEC,
        )
        _render_and_read(
            applied=applied,
            label=f"temperature_{label}",
            configdir=configdir,
            out_dir=out_dir,
        )


def test_parameterized_highlights_clip_threshold_apply_completes(
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """Highlights recovery operates on clipped input data; the synthetic
    chart fixture has no clipping. We verify the parameterized + masked
    apply path runs end-to-end.
    """
    _ = darktable_binary
    from chemigram.core.helpers import apply_entry

    entry = vocab.lookup_by_name("highlights_clip_threshold")
    if entry is None:
        pytest.fail("'highlights_clip_threshold' parameterized entry not in loaded packs")
    if entry.parameters is None:
        pytest.fail("'highlights_clip_threshold' loaded but parameters is None")

    out_dir = tmp_path_factory.mktemp("masked_param_highlights_clip_threshold")
    for v in (0.85, 0.95, 1.0):
        applied = apply_entry(
            baseline_xmp,
            entry,
            parameter_values={"clip_threshold": v},
            mask_spec=_CENTER_MASK_SPEC,
        )
        _render_and_read(
            applied=applied,
            label=f"highlights_clip_threshold_{v:.2f}",
            configdir=configdir,
            out_dir=out_dir,
        )


def test_parameterized_grain_strength_apply_completes(
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """Grain mask binding is mechanically valid but produces a visible
    boundary at the mask edge (per mask-applicable-controls.md#grain).
    We verify the parameterized apply + mask path runs end-to-end.
    """
    _ = darktable_binary
    from chemigram.core.helpers import apply_entry

    entry = vocab.lookup_by_name("grain_strength")
    if entry is None:
        pytest.fail("'grain_strength' parameterized entry not in loaded packs")
    if entry.parameters is None:
        pytest.fail("'grain_strength' loaded but parameters is None")

    out_dir = tmp_path_factory.mktemp("masked_param_grain_strength")
    for v in (8.0, 25.0, 50.0):
        applied = apply_entry(
            baseline_xmp,
            entry,
            parameter_values={"grain_strength": v},
            mask_spec=_CENTER_MASK_SPEC,
        )
        _render_and_read(
            applied=applied,
            label=f"grain_strength_{v:.0f}",
            configdir=configdir,
            out_dir=out_dir,
        )


def test_parameterized_bilat_clarity_strength_apply_completes(
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """Bilat (clarity) operates on edges/details, not flat chart patches —
    no spatial-localization assertion is meaningful on the synthetic
    fixture. We verify the parameterized apply + mask path runs end-to-
    end at multiple strength values.
    """
    _ = darktable_binary
    from chemigram.core.helpers import apply_entry

    entry = vocab.lookup_by_name("bilat_clarity_strength")
    if entry is None:
        pytest.fail("'bilat_clarity_strength' parameterized entry not in loaded packs")
    if entry.parameters is None:
        pytest.fail("'bilat_clarity_strength' loaded but parameters is None")

    out_dir = tmp_path_factory.mktemp("masked_param_bilat_clarity_strength")
    for v in (0.5, 1.5, 2.5):
        applied = apply_entry(
            baseline_xmp,
            entry,
            parameter_values={"clarity_strength": v},
            mask_spec=_CENTER_MASK_SPEC,
        )
        _render_and_read(
            applied=applied,
            label=f"bilat_clarity_strength_{v:.1f}",
            configdir=configdir,
            out_dir=out_dir,
        )


def test_parameterized_sigmoid_contrast_apply_completes(
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """Sigmoid mask binding is mechanically valid but produces visible
    seams between masked and unmasked regions (per
    mask-applicable-controls.md#sigmoid). We don't assert spatial
    localization — just verify the parameterized apply path runs end-to-
    end and produces a valid render at multiple contrast values.
    """
    _ = darktable_binary
    from chemigram.core.helpers import apply_entry

    entry = vocab.lookup_by_name("sigmoid_contrast")
    if entry is None:
        pytest.fail("'sigmoid_contrast' parameterized entry not in loaded packs")
    if entry.parameters is None:
        pytest.fail("'sigmoid_contrast' loaded but parameters is None")

    out_dir = tmp_path_factory.mktemp("masked_param_sigmoid_contrast")
    for v in (1.0, 1.5, 2.5):
        applied = apply_entry(
            baseline_xmp, entry, parameter_values={"contrast": v}, mask_spec=_CENTER_MASK_SPEC
        )
        _render_and_read(
            applied=applied,
            label=f"sigmoid_contrast_{v:.1f}",
            configdir=configdir,
            out_dir=out_dir,
        )


def test_parameterized_vignette_apply_completes(
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """Vignette mask binding doesn't compose photographically (geometric x
    geometric per ADR-076 / mask-applicable-controls.md#vignette), so
    we don't assert spatial localization. We do verify the parameterized
    apply path runs end-to-end and produces a valid render at multiple
    brightness values.
    """
    _ = darktable_binary
    from chemigram.core.helpers import apply_entry

    entry = vocab.lookup_by_name("vignette")
    if entry is None:
        pytest.fail("'vignette' parameterized entry not in loaded packs")
    if entry.parameters is None:
        pytest.fail("'vignette' loaded but parameters is None")

    out_dir = tmp_path_factory.mktemp("masked_param_vignette")
    for v in (-0.8, -0.25, 0.5):
        applied = apply_entry(baseline_xmp, entry, parameter_values={"brightness": v})
        _render_and_read(
            applied=applied,
            label=f"vignette_brightness_{v:+.2f}",
            configdir=configdir,
            out_dir=out_dir,
        )


def test_parameterized_exposure_localizes_through_mask(
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """Closes ADR-080's masked-coverage requirement for parameterized
    exposure: applying ``exposure`` at a non-zero EV through a centered
    ellipse mask must visibly differ from applying it globally — the
    mask actually constrains the parameterized op_params binding.

    Asserts corner-luma divergence between global render at +1 EV and
    masked render at +1 EV; the masked render's corners should be much
    closer to baseline (since the mask excludes them) than the global's.
    """
    _ = darktable_binary
    from chemigram.core.helpers import apply_entry

    entry = vocab.lookup_by_name("exposure")
    if entry is None:
        pytest.fail("'exposure' parameterized entry not in loaded packs")
    if entry.parameters is None:
        pytest.fail("'exposure' loaded but parameters is None — manifest declaration mismatch")

    out_dir = tmp_path_factory.mktemp("masked_param_exposure")
    global_xmp = apply_entry(baseline_xmp, entry, parameter_values={"ev": 1.0})
    masked_xmp = apply_entry(
        baseline_xmp, entry, parameter_values={"ev": 1.0}, mask_spec=_CENTER_MASK_SPEC
    )

    global_patches = _render_and_read(
        applied=global_xmp, label="exposure_param_global", configdir=configdir, out_dir=out_dir
    )
    masked_patches = _render_and_read(
        applied=masked_xmp, label="exposure_param_masked", configdir=configdir, out_dir=out_dir
    )

    # Compare corner luma (Rec. 709 weighted) — global brightens corners,
    # masked leaves them at baseline.
    from tests.e2e._patch_reader import luma_linear

    global_corner_luma = sum(luma_linear(global_patches[i]) for i in _CC_CORNER_4) / 4
    masked_corner_luma = sum(luma_linear(masked_patches[i]) for i in _CC_CORNER_4) / 4
    divergence = abs(global_corner_luma - masked_corner_luma)

    if divergence < 0.05:
        pytest.fail(
            "parameterized exposure at +1 EV: masked vs global corner luma "
            f"didn't diverge:\n"
            f"  global_corner_luma: {global_corner_luma:.4f}\n"
            f"  masked_corner_luma: {masked_corner_luma:.4f}\n"
            f"  divergence: {divergence:.4f} (expected > 0.05)\n"
            "  Mask is not constraining the parameterized op_params binding."
        )


def test_coverage_documents_at_least_colorbalancergb(
    vocab: VocabularyIndex,
) -> None:
    """The MASK_COVERAGE list is small on purpose. This guard ensures every
    primitive named is loaded, is non-mask-bound (we want to test mask
    synthesis on global entries), and at least one represents the
    most-used module category (colorbalancergb)."""
    if not MASK_COVERAGE:
        pytest.fail("MASK_COVERAGE is empty — at least one primitive required")

    touched_modules: set[str] = set()
    for name, _params in MASK_COVERAGE:
        entry = vocab.lookup_by_name(name)
        if entry is None:
            pytest.fail(f"MASK_COVERAGE references unknown primitive: {name}")
        if entry.mask_spec is not None:
            pytest.fail(
                f"MASK_COVERAGE includes already-mask-bound primitive {name!r} — "
                f"the test shape exercises mask synthesis on global primitives only"
            )
        for plug in entry.dtstyle.plugins:
            touched_modules.add(plug.operation)

    if "colorbalancergb" not in touched_modules:
        pytest.fail(
            "MASK_COVERAGE must include at least one colorbalancergb primitive — "
            "this validates mask binding for the most-used module category"
        )
