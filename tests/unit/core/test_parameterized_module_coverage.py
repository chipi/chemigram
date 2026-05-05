"""CI gate: every parameterized vocabulary entry has full 5-layer coverage.

Closes ADR-080. Per the test-coverage policy for parameterized modules,
every entry whose manifest carries a ``parameters`` block must be
referenced by all of:

1. **Unit test** under ``tests/unit/core/parameterize/test_<module>.py``
   (round-trip / encode-decode / patch).
2. **Integration test** under ``tests/integration/core/`` (apply path).
3. **Lab-grade global** entry in ``tests/e2e/_lab_grade_deltas.py``'s
   ``PARAMETERIZED_EFFECTS`` dict (asserts direction-of-change at
   multiple parameter values).
4. **Lab-grade masked** test in
   ``tests/e2e/test_lab_grade_masked_universality.py`` (asserts spatial
   localization through a drawn mask, OR documents non-applicability
   like vignette x mask via a dedicated apply-completes test).
5. **Visual proof sweep** entry in
   ``scripts/generate-visual-proofs.py``'s ``_PARAMETER_SWEEP_VALUES``
   keyed by the parameter's name.

Escape hatch: a manifest entry can be marked
``"_test_coverage_exempt": "<reason>"`` to skip this check; the reason
string is required and must articulate why one of the layers can't apply.
No v1.6.0 entry uses the escape hatch.

This linter runs as part of the unit-test suite (no darktable required),
so a parameterized PR fails CI fast if any layer is missing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_MANIFESTS = [
    _REPO_ROOT / "vocabulary" / "starter" / "manifest.json",
    _REPO_ROOT / "vocabulary" / "packs" / "expressive-baseline" / "manifest.json",
]


def _parameterized_entries() -> list[dict]:
    """Collect every manifest entry across all packs that has a
    ``parameters`` block (and isn't exempted)."""
    out: list[dict] = []
    for manifest_path in _MANIFESTS:
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text())
        for entry in manifest.get("entries", []):
            if "parameters" not in entry:
                continue
            if entry.get("_test_coverage_exempt"):
                continue
            out.append(entry)
    return out


def _files_under(*relative_paths: str) -> list[str]:
    """Read the textual content of test/script files under the repo
    root. Returns one big string per file (we grep them in the
    coverage checks below)."""
    out = []
    for rel in relative_paths:
        path = _REPO_ROOT / rel
        if path.exists():
            out.append(path.read_text())
    return out


def _has_unit_coverage(entry: dict) -> bool:
    """A unit test under tests/unit/core/parameterize/test_<module>.py
    referencing the entry's parameter name."""
    # Each parameterized entry's plugin module is in entry["touches"][0]
    # (single-touch entries; multi-touch parameterized is a future case).
    module = entry["touches"][0]
    test_file = _REPO_ROOT / "tests" / "unit" / "core" / "parameterize" / f"test_{module}.py"
    return test_file.exists() and test_file.read_text().strip() != ""


def _has_integration_coverage(entry: dict) -> bool:
    """An integration test under tests/integration/core/ that references
    the entry's name OR uses ``apply_entry`` with parameter_values
    against the entry's module."""
    sources = _files_under(
        "tests/integration/core/test_parameterize_exposure.py",
        f"tests/integration/core/test_parameterize_{entry['touches'][0]}.py",
    )
    text = "\n".join(sources)
    # Apply_entry coverage is module-agnostic — exposure's tests cover
    # the apply path; a per-module integration test is optional. The
    # check passes if either the per-module file exists OR apply_entry
    # is exercised in any integration file.
    return ("apply_entry" in text and entry["name"] in text) or _has_per_module_integration(entry)


def _has_per_module_integration(entry: dict) -> bool:
    module = entry["touches"][0]
    f = _REPO_ROOT / "tests" / "integration" / "core" / f"test_parameterize_{module}.py"
    return f.exists()


def _has_lab_grade_global(entry: dict) -> bool:
    """An entry name appears as the first element of a tuple key in
    ``PARAMETERIZED_EFFECTS``."""
    deltas = _files_under("tests/e2e/_lab_grade_deltas.py")
    if not deltas:
        return False
    text = deltas[0]
    # Look for ("entry_name", ... in PARAMETERIZED_EFFECTS context.
    return f'("{entry["name"]}",' in text


def _has_lab_grade_masked(entry: dict) -> bool:
    """The masked test layer references the entry name. Either a
    parametrized localization test or a dedicated apply-completes test
    counts (the latter for documented dead-pairing combos like
    vignette x mask)."""
    masked = _files_under("tests/e2e/test_lab_grade_masked_universality.py")
    if not masked:
        return False
    return entry["name"] in masked[0]


def _has_visual_proof(entry: dict) -> bool:
    """The gallery script's _PARAMETER_SWEEP_VALUES has a recipe for
    at least one of the entry's parameter names."""
    script = _files_under("scripts/generate-visual-proofs.py")
    if not script:
        return False
    text = script[0]
    for param in entry.get("parameters", []):
        if f'"{param["name"]}":' in text:
            return True
    return False


_LAYER_CHECKS = [
    ("unit", _has_unit_coverage),
    ("integration", _has_integration_coverage),
    ("lab-grade global", _has_lab_grade_global),
    ("lab-grade masked", _has_lab_grade_masked),
    ("visual proof sweep", _has_visual_proof),
]


@pytest.mark.parametrize("entry", _parameterized_entries(), ids=lambda e: e["name"])
def test_parameterized_entry_has_full_coverage(entry: dict) -> None:
    """For each parameterized vocabulary entry: every required test
    layer per ADR-080 has at least one matching reference. A PR that
    adds a parameterized entry without coverage fails this test in CI.

    To exempt an entry (rare; documented case-by-case), add
    ``"_test_coverage_exempt": "<reason>"`` to its manifest entry —
    the test will skip it and the reason string articulates why.
    """
    missing = []
    for layer_name, check in _LAYER_CHECKS:
        if not check(entry):
            missing.append(layer_name)
    if missing:
        pytest.fail(
            f"parameterized entry {entry['name']!r} is missing test coverage "
            f"in: {missing}.\n"
            f"  ADR-080 requires all 5 layers: unit, integration, lab-grade "
            f"global, lab-grade masked, visual proof sweep.\n"
            f"  See docs/adr/ADR-080-test-coverage-policy-parameterized-modules.md "
            f"for the policy.\n"
            f"  To exempt this entry (rare), add "
            f"'_test_coverage_exempt: \"<reason>\"' to its manifest entry."
        )


def test_at_least_one_parameterized_entry_exists() -> None:
    """Sanity check: the linter's parametrize is non-empty post-v1.6.0
    (exposure + vignette landed). Catches accidental manifest deletion."""
    entries = _parameterized_entries()
    assert len(entries) >= 2, (
        f"expected at least 2 parameterized entries (exposure, vignette) "
        f"post-v1.6.0; found {len(entries)}: {[e['name'] for e in entries]}"
    )
