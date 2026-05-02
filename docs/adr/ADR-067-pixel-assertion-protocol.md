# ADR-067 — Pixel-level assertion protocol

> Status · Accepted
> Date · 2026-05-02
> TA anchor ·/components/eval ·/components/pipeline
> Related RFC · RFC-019 v0.2 (closes here)

## Context

RFC-019 proposes a public assertion library for color-accuracy and tonal-response checks against reference targets. The decisions to lock here: which colour-difference metric, which colour-space conversion, what dependencies, what API shape.

## Decision

The assertion library lives at `chemigram.core.assertions` (commit `e2d4725`). Locked decisions:

- **Colour-difference metric**: CIE DE2000 (Sharma/Wu/Dalal 2005). Hand-rolled implementation, validated against the published Sharma reference pair (Lab1=(50, 2.6772, -79.7751), Lab2=(50, 0, -82.7485), expected DE2000=2.0425) within 0.01 tolerance. CIE76 is not implemented in v0.2 — DE2000 is the only metric exposed.
- **Colour-space conversion**: sRGB ↔ CIE L\*a\*b\* D50 via Lindbloom matrices (Bradford D65→D50 chromatic adaptation). Standard ε=216/24389 and κ=24389/27 for the Lab f / f⁻¹ helpers.
- **Dependencies**: hand-rolled in pure Python over Pillow only. No `colour-science`, no numpy. The hot path for v1.2.0 is patch-level math (24 patches × 24 Delta E values per assertion run) — pure Python is fast enough; the dependency surface stays minimal.
- **API shape**: typed dataclasses for results (`ColorAccuracyResult`, `TonalResponseResult`); positional args for the data, keyword-only for thresholds. Skip-list (`skip_indices`) on `assert_color_accuracy` for out-of-gamut patches that synthesizer clips during sRGB rendering.

The complete public API:

| Function / type | Purpose |
|-|-|
| `srgb_to_lab(srgb)` | Convert sRGB triple → CIE L\*a\*b\* D50 |
| `lab_to_srgb(lab)` | Inverse with sRGB gamut clipping |
| `delta_e_2000(lab1, lab2, kL=1, kC=1, kH=1)` | DE2000 perceptual difference |
| `extract_patch_values(image, coords)` | Sample mean Lab per `PatchCoord` |
| `assert_color_accuracy(measured, reference, ...)` | Mean/max DE vs reference |
| `assert_tonal_response(measured_L, reference_L, ...)` | Linear regression R² |
| `assert_exposure_shift(baseline, shifted, direction, min_magnitude)` | Direction-of-change for L\* |
| `assert_wb_shift(baseline, shifted, axis, direction, min_magnitude)` | Direction-of-change for a\*/b\* |
| `PatchCoord(x, y, w, h)` | Rectangular patch sample region |
| `ColorAccuracyResult` / `TonalResponseResult` | Frozen result dataclasses |

Per-file ruff ignores added for `chemigram.core.assertions.py` and its tests (`N802/N803/N806`): CIE notation uses uppercase L/C/T/S/G/R/RT for specific channels and component letters. Renaming would obscure the Sharma algorithm.

## Rationale

- **DE2000 over CIE76**: industry standard for perceptual difference. CIE76 is simpler but doesn't account for hue/chroma sensitivity asymmetry. Implementation cost is ~80 lines either way; the additional complexity of DE2000 is well worth the perceptual fidelity.
- **Hand-rolled, no numpy**: the project's existing pixel work uses Pillow only. `colour-science` brings ~50 MB of transitive deps and numpy. The hot path doesn't need vectorized operations (24 patches per assertion). Hand-rolled DE2000 is ~80 lines, validated against published reference pairs.
- **Pure-Python conversion math**: same reasoning. 30 lines, no surprises.
- **Skip-list API for out-of-gamut**: synthetic CC24 has Cyan #18 outside sRGB gamut; the JSON ground truth's `out_of_gamut_indices` field flags it; the assertion API takes that flag as `skip_indices`. Cleaner than special-casing in the assertion logic.
- **Frozen dataclasses for results**: per the project's style elsewhere (`ToolResult`, `MaskEntry`, etc.).

## Alternatives considered

- **`colour-science` package.** Industry-standard, well-tested, complete. Rejected: dependency surface (numpy + ~50 MB transitive); the project's existing pixel work is Pillow-only; the hot path doesn't need it.
- **CIE76 (simpler Delta E).** Rejected: less perceptually accurate; not used by Imatest, DxOMark, or any modern colour-accuracy workflow.
- **Custom assertion API (separate from ColorAccuracyResult)**. Considered exposing raw Delta E lists. Rejected: the result type carries thresholds + per-patch breakdown, which makes failure messages much better.
- **Migrate the test-tier `pixel_stats` helpers (highlight_clip_pct etc.) into this module.** Considered. Some helpers (saturation_avg, b\*-axis-shift via warmth_ratio) overlap with the new public API. Decision: leave the test-tier helpers in `tests/e2e/conftest.py` for now — they work, and refactoring without active use is risky. Future work can promote them with deprecation aliases.

## Consequences

Positive:
- Public, documented, importable assertion API for any future test or downstream tool.
- 27 unit tests + 6 integration tests provide a working regression surface (commit `e2d4725`).
- The DE2000 implementation is validated against a published reference pair — high confidence in correctness.
- Zero new third-party dependencies.

Negative:
- Hand-rolled colour math is more code to maintain than a `colour-science` import. Mitigated by extensive references in module docstring (Lindbloom, Sharma) and the validation test against the published pair.
- No vectorized path for whole-image comparison. v1.2.0 doesn't need it; future work can wrap the hot loop in numpy or swap in `colour-science` behind the same module's interface.

## Implementation notes

- `src/chemigram/core/assertions.py` — the module (commit `e2d4725`).
- `tests/unit/core/test_assertions.py` — 27 unit tests including the Sharma DE2000 validation pair.
- `tests/integration/test_reference_synthetic.py` — 6 integration tests against the synthetic fixtures.
- Per-file ruff ignores in `pyproject.toml` `[tool.ruff.lint.per-file-ignores]`.
- The `_band_mean` helper duplicates the one in `tests/e2e/conftest.py`. Acceptable: lower coupling between test-tier helpers and the public API; the function is 5 lines.
