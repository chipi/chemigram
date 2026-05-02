# ADR-064 — Vocabulary authoring workflow (post-v0.2)

> Status · Accepted
> Date · 2026-05-02
> TA anchor ·/components/vocabulary
> Related RFC · RFC-018 (closes here)

## Context

RFC-018 v0.1 anticipated a probe-iop-order step in vocabulary authoring (every Path B entry needed a probe run). RFC-018 v0.2 dropped that step (ADR-063): Path A and Path B authoring are now identical. With multi-pack `VocabularyIndex` shipped (#41) and the synthesizer Path B unblocked (#44), the workflow needs documenting cleanly so contributors can author entries without reading three RFCs.

## Decision

The vocabulary authoring procedure is one shape for both Path A and Path B:

1. **Prepare**: open darktable with a clean configdir (per `docs/CONTRIBUTING.md` § "Use an isolated configdir for vocabulary work"). Discard history before each style.
2. **Author**: enable the target module, dial in parameters, export as `.dtstyle`. Uncheck non-target modules in the create-style dialog (the discipline from CONTRIBUTING.md § Authoring procedure step 4 — produces single-module dtstyles).
3. **Place**: drop the file into the right pack and module subdirectory:
   - Starter pack additions go to `vocabulary/starter/layers/L<n>/<subtype>/<name>.dtstyle` (rare; the starter is a minimal teaching artifact)
   - Expressive-baseline additions go to `vocabulary/packs/expressive-baseline/layers/L<n>/<subtype>/<name>.dtstyle`
   - Personal additions go to `~/.chemigram/packs/personal/layers/L<n>/<subtype>/<name>.dtstyle` (gitignored; per-photographer)
4. **Manifest**: append a `manifest.json` entry with `name`, `layer`, `path`, `touches`, `tags`, `description`, `modversions`, `darktable_version`, `source`, `license`. No `iop_order` field — the synthesizer handles Path B without it (ADR-063).
5. **Test**: drop into the `tests/e2e/expressive/` scaffold (or write a similar e2e for personal entries) — the existing test infrastructure auto-discovers entries by name and skips when absent. When the entry is in the pack, the test activates.
6. **Verify**: `make vocab-check` validates the manifest schema and ref-integrity. `make test-e2e` runs the direction-of-change render assertions against the Phase 0 raw.

The CI gate is `make vocab-check` — this checks both shipped packs (`starter` and `expressive-baseline`) on every push.

## Rationale

- **Path A and Path B authoring should look identical to contributors.** The Path A vs Path B distinction is an engine internal (whether the entry's tuple is in the baseline). Authoring procedure shouldn't reflect engine implementation.
- **No probe step keeps the workflow fast.** A vocabulary author can ship 2–3 entries per hour at this discipline. Adding a probe step would have ~doubled per-entry time (run probe, read output, edit JSON).
- **Multi-pack architecture leaves the starter alone.** ADR-024's discipline is preserved: the starter pack stays minimal as a teaching artifact; expansion lives in `expressive-baseline`.
- **Tests auto-activate.** Authoring an entry doesn't require touching `tests/e2e/expressive/` — the scaffolds (commit `145fd2c`) discover entries from the loaded pack by name.

## Alternatives considered

- **Probe-iop-order workflow.** RFC-018 v0.1 proposal. Dropped per ADR-063's empirical evidence.
- **Per-entry assertion spec attached to the .dtstyle.** Each entry would carry `expected_effect: {operation: exposure, direction: +1, magnitude: 0.5}` etc. Considered; rejected as scope creep — the e2e test name (`test_blacks_crushed_increases_shadow_clip_pct`) already encodes the expected effect.
- **Generated manifest entries from .dtstyle metadata.** A script that parses the `.dtstyle` to populate `touches`, `modversions`, etc. automatically. Tempting; rejected because the manifest's editorial fields (`description`, `tags`, `name`) need a human, and a half-automated workflow is more error-prone than a fully manual one.

## Consequences

Positive:
- Authoring takes minutes, not tens of minutes per entry.
- The procedure is the same regardless of whether the underlying engine path is A or B.
- Personal pack growth (Phase 2) reuses the exact same workflow.

Negative:
- Authors must remember the dialog discipline (uncheck non-target modules at create-style time) — not enforced by the tooling; surfaces as a post-load validator failure (`touches` mismatch) if violated.
- No automated check that an entry's effect matches its name/description — the e2e test serves that role, but it's run after authoring not during.

## Implementation notes

- `vocabulary/starter/` (5 entries, unchanged).
- `vocabulary/packs/expressive-baseline/` (scaffold + 0 entries today; populated under #45/#46/#47).
- `~/.chemigram/packs/<name>/` (personal, gitignored).
- `chemigram.core.vocab.load_packs(["starter", "expressive-baseline"])` is the typical multi-pack load (commit `451f8b7`).
- `tests/e2e/expressive/conftest.py` provides `render_with_entry(entry_name, ...)` which auto-skips when the entry isn't in the loaded pack.
- `scripts/verify-vocab.sh` runs per-pack manifest validation; invoked by `make vocab-check`.
- `docs/CONTRIBUTING.md` § Authoring procedure documents the darktable-side discipline; this ADR documents the post-export integration steps.
