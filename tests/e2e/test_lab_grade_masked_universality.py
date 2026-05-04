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

from chemigram.core.helpers import apply_with_drawn_mask
from chemigram.core.pipeline import render
from chemigram.core.vocab import VocabularyIndex, load_packs
from chemigram.core.xmp import Xmp, parse_xmp, synthesize_xmp, write_xmp

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
# We pick ``sat_kill`` because:
#   - It collapses corner chroma from ~14 to ~0 globally — the largest,
#     most repeatable signature in the vocab.
#   - It exercises colorbalancergb, the most-used module category and
#     the one whose mask binding the unit test cannot verify end-to-end
#     against darktable's renderer.
#   - The unit test :mod:`test_apply_universality` separately proves
#     the apply path completes for every loaded vocab entry across
#     every drawn-form, so we don't need to enumerate at the e2e tier.
MASK_COVERAGE: list[str] = ["sat_kill"]


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


@pytest.mark.parametrize("primitive_name", MASK_COVERAGE, ids=MASK_COVERAGE)
def test_mask_localizes_arbitrary_primitive(
    primitive_name: str,
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
        applied=synthesize_xmp(baseline_xmp, [entry.dtstyle]),
        label="global",
        configdir=configdir,
        out_dir=out_dir,
    )
    masked_patches = _render_and_read(
        applied=apply_with_drawn_mask(baseline_xmp, entry.dtstyle, _CENTER_MASK_SPEC),
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
    for name in MASK_COVERAGE:
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
