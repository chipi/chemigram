# ADR-066 — Reference fixture policy (synthetic-only)

> Status · Accepted
> Date · 2026-05-02
> TA anchor ·/components/eval ·/components/pipeline
> Related RFC · RFC-019 v0.2 (closes here)

## Context

RFC-019 v0.1 proposed a two-tier reference-validation policy: synthetic CC24 + grayscale TIFFs for CI (Tier A) and real-RAW chart photographs for local e2e (Tier B). The project doesn't ship physical chart shoots; CI runs without a Nikon D850 or a controlled lighting setup. RFC-019 v0.2 dropped Tier B and committed to synthetic-only validation for v1.2.0.

This ADR locks the synthetic-only policy in.

## Decision

The reference-fixture set for `chemigram.core.assertions` validation is **synthetic only, generated computationally from published reference values**. Concretely:

- **`tests/fixtures/reference-targets/colorchecker24_lab_d50.json`** — 24-patch X-Rite L\*a\*b\* D50 ground truth (post-Nov 2014 formulation), per the table in `docs/guides/standardized-testing.md`. Includes `neutral_indices` and `out_of_gamut_indices` metadata.
- **`tests/fixtures/reference-targets/colorchecker_synthetic_srgb.png`** — 600×400 px synthetic CC24 with 24 100×100 patches in a 6×4 grid. Generated from the JSON via `chemigram.core.assertions.lab_to_srgb`. PNG (not TIFF) for solid-color compression efficiency — fits well under the 500 KB pre-commit large-file limit at ~1.5 KB.
- **`tests/fixtures/reference-targets/grayscale_synthetic_linear.png`** — 24-step linear sRGB ramp (600×100 px). ~0.4 KB.
- **`tests/fixtures/reference-targets/generate_synthetic.py`** — idempotent regeneration script. The committed fixtures are the canonical output.

The fixture set is **immutable within a version**. Current version: `reference_v1`. Future improvements ship as `reference_v2` — the v1 files stay untouched for reproducibility.

Real-RAW Tier B is deferred. If a community-contributed downloadable RAW pack of standardized chart photographs appears, a follow-on RFC reopens Tier B without breaking this ADR's commitments.

## Rationale

- **CI-friendly.** PNG fixtures committed to the repo, deterministic regeneration, no hardware needed, no per-developer setup. Tier A tests run on every push.
- **Sufficient for the v1.2.0 problem.** RFC-019's primary target is validating the *software pipeline* — sRGB ↔ L\*a\*b\* math, the synthesizer's compose+append behavior, the assertion library's correctness. Synthetic fixtures cover all of that.
- **The darktable-RAW path is covered elsewhere.** Direction-of-change e2e tests against the Phase 0 raw (`tests/e2e/`) cover what darktable does to real photographs. They use heuristic measurements (`highlight_clip_pct`, `corner_vs_center_luma_ratio`, etc.) — sufficient for "did the move go in the right direction" but not for "is the absolute color correct." The latter is what reference targets answer; if that gap matters in practice, follow-on RFC reopens Tier B.
- **PNG, not TIFF.** TIFF was RFC-019 v0.1's choice because the photography industry uses it. For solid-color synthetic patches, PNG compresses ~500× better. The committed file is 1.5 KB vs 700+ KB for TIFF — pre-commit hook compatibility.

## Alternatives considered

- **Real-RAW Tier B in v1.2.0** (RFC-019 v0.1). Rejected per user direction: no chart shoots in scope; CI must run without one.
- **TIFF format** (RFC-019 v0.1). Rejected: file size exceeds pre-commit large-file limit. PNG is the equivalent for synthetic solid-color patches.
- **External reference data downloaded at test time** (Lindbloom, BabelColor TIFFs). Considered. Rejected: introduces a network dependency in CI; goal is to commit deterministic fixtures.
- **No reference fixtures at all; rely on direction-of-change e2e only.** Rejected: misses the methodological gap that RFC-019 identified — direction-of-change can't catch "wrong color, but consistently wrong."

## Consequences

Positive:
- Tier A tests run in CI on every push (no `make test-e2e` gate).
- Reference fixtures are auditable plain text (JSON) + auditable images (PNG).
- The split between absolute-correctness (Tier A) and direction-of-change (e2e) is clean.

Negative:
- Tier A doesn't validate darktable's RAW path (demosaicing, color matrix, lens corrections). The existing e2e tier covers that for direction-of-change but not absolute correctness. Acceptable for v1.2.0; reopen via follow-on RFC if needed.
- Out-of-gamut patches (CC24 #18 Cyan) are clipped during synthesis. Reference JSON's `out_of_gamut_indices` field marks these; assertions exclude them from the strict mean/max Delta E thresholds.

## Implementation notes

- `chemigram.core.assertions.extract_patch_values` reads the synthetic PNG via Pillow.
- `tests/integration/test_reference_synthetic.py` is the Tier A test surface (6 tests today, more under #48).
- The `synthetic_grid` field in `colorchecker24_lab_d50.json` describes the patch layout — 6 cols × 4 rows × 100 px per patch. Index 1 starts at top-left, increases left-to-right then top-to-bottom.
- The grayscale ramp is 24 steps × 25 px wide × 100 px tall; sRGB values evenly spaced across [0, 255].
