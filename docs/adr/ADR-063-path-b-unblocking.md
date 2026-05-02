# ADR-063 — Path B unblocking; iop_order resolved as None

> Status · Accepted
> Date · 2026-05-02
> TA anchor ·/components/synthesizer
> Related RFC · RFC-001 (closed by this ADR), RFC-018 (closes here)
> Supersedes · ADR-051's "Path B raises NotImplementedError" stance

## Context

ADR-051 (Phase 1, v0.2.0) deferred Path B (new-instance addition in `synthesize_xmp`) because Phase 0 evidence suggested darktable would silently drop history entries that lacked per-entry `iop_order`. RFC-001 left the iop_order origin question open; ADR-051 made the synthesizer raise `NotImplementedError` until it was resolved. RFC-018 v0.1 inherited that assumption and proposed a "Strategy X" probe-iop-order workflow.

RFC-018 v0.2 ran the empirical experiments (`tests/fixtures/preflight-evidence/`). Result: **darktable 5.4.1 does not require per-entry `iop_order` for Path B.** Five Path B scenarios — vignette + grain (new operations), exposure + temperature + channelmixerrgb at multi_priority=1 (new instances) — all rendered correctly with `iop_order` absent from the per-entry XMP. darktable resolves pipeline order from the description-level `iop_order_version` + its internal iop_list.

## Decision

`synthesize_xmp`'s Path B branch appends a fresh `HistoryEntry` with `iop_order=None`. No probe step, no manifest schema fields, no `colour-science` dependency. Concretely:

- When the input plugin's `(operation, multi_priority)` tuple is **not** in the baseline, append a new `HistoryEntry` at `num = max(existing) + 1` using the existing `_plugin_to_history` helper (which already produces `iop_order=None`).
- Recompute `xmp.history_end = len(history)` after the loop.
- Path A (SET-replace) unchanged.
- Mixed Path A + Path B in one synthesize call works.

The `HistoryEntry.iop_order: float | None` field stays — sidecar XMPs (rendered output) can carry per-entry `iop_order` as a float, and the parser must round-trip those (#42 fix). The synthesizer simply doesn't *require* the field for Path B.

This closes RFC-001's iop_order open question and supersedes ADR-051's NotImplementedError stance.

## Rationale

- **Empirical evidence overrides the theoretical assumption.** Five Path B scenarios across new operations (modules absent from baseline) and new instances (multi_priority>0) confirmed: pipeline order is resolved upstream of the per-entry metadata.
- **Simpler is better.** No probe script, no manifest fields, no `colour-science` dep, no validation rules. The Path B branch is ~10 lines.
- **Reversible if wrong.** If a future darktable version regresses to "drops entries without iop_order," RFC-018 reopens with Strategy X. The empirical reproducer in `tests/fixtures/preflight-evidence/` is the regression detector.

## Alternatives considered

- **Strategy X — XMP probe at authoring time** (RFC-018 v0.1's proposal). Rejected: solves a non-problem in dt 5.4.1; ships infrastructure (probe script, manifest fields, validator rules) for an empirical claim that didn't hold.
- **Strategy Y — static lookup table.** Rejected: couples Chemigram to darktable internals not exposed as a public API.
- **Strategy Z — runtime probe per apply.** Rejected: latency cost on every first apply; requires a raw at apply time.
- **Defer Path B entirely.** Rejected: blocks the v1.2.0 vocabulary expansion that depends on `colorbalancergb`, `localcontrast`, `grain`, `vignette` — none of which are in the baseline XMP.

## Consequences

Positive:
- Path B works without engine ceremony.
- Manifest schema stays minimal.
- Vocabulary authoring is the same workflow for Path A and Path B (no probe step).
- The unblocking is empirically validated end-to-end — `tests/e2e/test_synthesizer_path_b.py` proves the synthesizer's appended entries actually render through real darktable.

Negative:
- The empirical evidence covers five module classes; if a darktable module exists for which Path B silently drops without iop_order, that module's vocabulary entries will fail at authoring time (an e2e render assertion would fail). Not fatal — surfaces as a per-module test failure, recoverable by re-introducing Strategy X for the affected module.
- Concentration risk: all v1.2.0 vocabulary entries depend on dt 5.4.1's permissive Path B behavior. RFC-007 (modversion drift) is the mitigation.

## Implementation notes

- `src/chemigram/core/xmp.py` `synthesize_xmp` — append branch + `history_end` recompute (commit `a35e431`).
- `tests/fixtures/preflight-evidence/` — README + reproducer script (commit `47a7e8e`).
- `tests/unit/core/test_synthesize.py` — 3 new unit tests covering append path.
- `tests/e2e/test_synthesizer_path_b.py` — 1 e2e test through real darktable.
- The `HistoryEntry.iop_order: float | None` type fix lands separately under #42 (commit `9734690`); needed regardless of this ADR because rendered sidecars carry float iop_order values.
