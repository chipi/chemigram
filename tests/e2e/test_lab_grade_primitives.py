"""Lab-grade isolation tests for vocabulary primitives (closes #77).

For each primitive in :data:`EXPECTED_EFFECTS`: render the synthetic
ColorChecker or grayscale ramp through the primitive in isolation
(empty-history baseline + ``--apply-custom-presets false``), read 24
patches from the rendered output, assert the per-patch effect matches
the primitive's documented intent within tolerance.

This is the machine-readable companion to ``docs/guides/visual-proofs.md``
(human eyeballing). Both render through the same empty-baseline pipeline
so a failure here maps directly to the visual change you'd see in the
gallery.

Skipped primitives (texture noise, spatial masks, composites) are
documented in :data:`SKIP_REASONS` and remain covered by the existing
direction-of-change tests in ``tests/e2e/expressive/`` plus visual
inspection in the gallery. Future work: a spatial-aware variant that
samples per-region for mask-bound primitives — tracked in #77's
acceptance notes as out-of-scope for the first ship.

Per ADR-076, mask-bound primitives route through ``apply_with_drawn_mask``
automatically; this test class skips them via :data:`SKIP_REASONS` rather
than failing on the spatial mismatch.
"""

from __future__ import annotations

import dataclasses
import os
import sys
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry, apply_with_drawn_mask
from chemigram.core.pipeline import render
from chemigram.core.vocab import VocabularyIndex, load_packs
from chemigram.core.xmp import Xmp, parse_xmp, synthesize_xmp, write_xmp

# Add tests/ to sys.path so `from tests.e2e._patch_reader import ...` works.
_TESTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_TESTS_ROOT.parent))  # repo root, so `tests.*` resolves

from tests.e2e._lab_grade_deltas import (  # noqa: E402
    EXPECTED_EFFECTS,
    PARAMETERIZED_EFFECTS,
    SKIP_REASONS,
    AssertionResult,
)
from tests.e2e._patch_reader import (  # noqa: E402
    PatchSample,
    read_colorchecker,
    read_grayscale_ramp,
)

_REPO = Path(__file__).resolve().parents[2]
_BASELINE_TEMPLATE = _REPO / "src/chemigram/core/_baseline_v1.xmp"
_COLORCHECKER = _REPO / "tests/fixtures/reference-targets/colorchecker_synthetic_srgb.png"
_GRAYSCALE = _REPO / "tests/fixtures/reference-targets/grayscale_synthetic_linear.png"

_TARGETS = {
    "colorchecker": _COLORCHECKER,
    "grayscale": _GRAYSCALE,
}

_RENDER_W = 400
_RENDER_H = 400


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
    """Empty-history baseline: zero modules. See scripts/generate-visual-proofs.py
    docstring for why this differs from the production baseline.
    """
    template = parse_xmp(_BASELINE_TEMPLATE)
    return dataclasses.replace(template, history=())


def _read_target(target: str, image_path: Path) -> list[PatchSample]:
    if target == "colorchecker":
        return read_colorchecker(image_path)
    if target == "grayscale":
        return read_grayscale_ramp(image_path)
    raise ValueError(f"unknown target {target!r}")


def _render_and_read(
    *,
    baseline: Xmp,
    entry,
    target: str,
    configdir: Path,
    out_dir: Path,
    parameter_values: dict[str, float] | None = None,
    label: str | None = None,
) -> list[PatchSample]:
    """Apply (or skip) the entry to the empty baseline, render, return patches.

    ``parameter_values``: when supplied alongside a parameterized entry,
    routes through :func:`apply_entry` so the entry's op_params is patched
    per RFC-021. ``label`` is used in the rendered filename to keep
    parameterized renders distinguishable across values.
    """
    if entry is None:
        applied = baseline
    elif parameter_values is not None or entry.parameters is not None:
        applied = apply_entry(
            baseline, entry, parameter_values=parameter_values, mask_spec=entry.mask_spec
        )
    elif entry.mask_spec is not None:
        applied = apply_with_drawn_mask(baseline, entry.dtstyle, entry.mask_spec)
    else:
        applied = synthesize_xmp(baseline, [entry.dtstyle])

    name = "baseline" if entry is None else (label or entry.name)
    xmp_path = out_dir / f"{name}-{target}.xmp"
    out_path = out_dir / f"{name}-{target}.jpg"
    write_xmp(applied, xmp_path)
    try:
        result = render(
            raw_path=_TARGETS[target],
            xmp_path=xmp_path,
            output_path=out_path,
            width=_RENDER_W,
            height=_RENDER_H,
            high_quality=False,
            configdir=configdir,
        )
        if not result.success:
            pytest.fail(f"render failed for {name}@{target}: {result.error_message}")
        return _read_target(target, out_path)
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


@pytest.fixture(scope="module")
def baseline_patches(
    baseline_xmp: Xmp,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, list[PatchSample]]:
    """Render the empty baseline once, return patches for both targets."""
    out_dir = tmp_path_factory.mktemp("lab_grade_baseline")
    return {
        target: _render_and_read(
            baseline=baseline_xmp,
            entry=None,
            target=target,
            configdir=configdir,
            out_dir=out_dir,
        )
        for target in _TARGETS
    }


@pytest.mark.parametrize(
    "primitive_name",
    sorted(EXPECTED_EFFECTS.keys()),
    ids=lambda name: name,
)
def test_primitive_isolation_against_chart(
    primitive_name: str,
    baseline_patches: dict[str, list[PatchSample]],
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """For each primitive: render through empty baseline, read 24 patches,
    assert the primitive's effect matches its expected math/direction."""
    _ = darktable_binary  # ensures e2e suite's darktable check has run

    target, check = EXPECTED_EFFECTS[primitive_name]
    entry = vocab.lookup_by_name(primitive_name)
    if entry is None:
        pytest.fail(
            f"primitive {primitive_name!r} not found in loaded packs "
            f"(starter + expressive-baseline) — out-of-sync delta map?"
        )

    out_dir = tmp_path_factory.mktemp(f"lab_grade_{primitive_name}")
    after = _render_and_read(
        baseline=baseline_xmp,
        entry=entry,
        target=target,
        configdir=configdir,
        out_dir=out_dir,
    )
    before = baseline_patches[target]

    result: AssertionResult = check(before, after)
    if not result.passed:
        msg_lines = [
            f"primitive {primitive_name!r} failed lab-grade isolation against {target}:",
            f"  description: {entry.description}",
            "  measurements: "
            + ", ".join(
                f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
                for k, v in result.measurements.items()
            ),
            "  failures:",
        ]
        for f in result.failures:
            msg_lines.append(f"    - {f}")
        pytest.fail("\n".join(msg_lines))


@pytest.mark.parametrize(
    "key",
    sorted(PARAMETERIZED_EFFECTS.keys()),
    ids=lambda k: f"{k[0]}-{k[1]}",
)
def test_parameterized_primitive_isolation_against_chart(
    key: tuple[str, str],
    baseline_patches: dict[str, list[PatchSample]],
    baseline_xmp: Xmp,
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """For each parameterized entry x parameter-value tuple in
    ``PARAMETERIZED_EFFECTS``: apply through the engine's parameterized
    path, render against the synthetic chart, assert direction-of-change
    matches the spec.

    Closes ADR-080's lab-grade-global coverage requirement for
    parameterized modules: every parameter value range bracketed by at
    least one assertion against the live darktable renderer.
    """
    _ = darktable_binary

    entry_name, label = key
    target, check, parameter_values = PARAMETERIZED_EFFECTS[key]
    entry = vocab.lookup_by_name(entry_name)
    if entry is None:
        pytest.fail(
            f"parameterized entry {entry_name!r} not found in loaded packs "
            f"(starter + expressive-baseline) — manifest cleanup left a stale ref?"
        )
    if entry.parameters is None:
        pytest.fail(
            f"entry {entry_name!r} has no 'parameters' declaration but is "
            f"listed in PARAMETERIZED_EFFECTS — vocabulary/test mismatch."
        )

    out_dir = tmp_path_factory.mktemp(f"lab_grade_{entry_name}_{label}")
    after = _render_and_read(
        baseline=baseline_xmp,
        entry=entry,
        target=target,
        configdir=configdir,
        out_dir=out_dir,
        parameter_values=parameter_values,
        label=f"{entry_name}_{label}",
    )
    before = baseline_patches[target]

    result: AssertionResult = check(before, after)
    if not result.passed:
        msg_lines = [
            f"parameterized entry {entry_name!r} at {parameter_values!r} "
            f"failed lab-grade isolation against {target}:",
            f"  description: {entry.description}",
            "  measurements: "
            + ", ".join(
                f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
                for k, v in result.measurements.items()
            ),
            "  failures:",
        ]
        for f in result.failures:
            msg_lines.append(f"    - {f}")
        pytest.fail("\n".join(msg_lines))


def test_skip_reasons_documented_for_remaining_primitives(
    vocab: VocabularyIndex,
) -> None:
    """Every loaded primitive should either be in EXPECTED_EFFECTS (asserted)
    or in SKIP_REASONS (explicitly skipped with a reason). No silent
    coverage gaps."""
    asserted = set(EXPECTED_EFFECTS.keys())
    # Parameterized entries are covered by the parametrized test above;
    # extract just the entry-name half of the (name, label) keys.
    parameterized_names = {k[0] for k in PARAMETERIZED_EFFECTS.keys()}
    skipped = set(SKIP_REASONS.keys())
    all_loaded = {entry.name for entry in vocab.list_all()}

    missing = all_loaded - asserted - parameterized_names - skipped
    # canon_eos_r5_baseline_l1 is an L1 entry (camera-specific binding); not
    # applicable to chart isolation. Skip with implicit reason.
    missing.discard("canon_eos_r5_baseline_l1")

    if missing:
        pytest.fail(
            "Primitives without lab-grade coverage (neither asserted nor "
            f"skipped): {sorted(missing)}. Add to EXPECTED_EFFECTS or "
            "PARAMETERIZED_EFFECTS in tests/e2e/_lab_grade_deltas.py if "
            "asserting, or to SKIP_REASONS with a reason if not."
        )
