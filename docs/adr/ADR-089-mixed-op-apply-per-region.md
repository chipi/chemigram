# ADR-089 — Mixed-op `apply_per_region` schema extension

> Status · Draft (impl shipped 2026-05-10; flips to Accepted on darkroom validation)
> Date · 2026-05-10
> TA anchor · /contracts/mcp-tools · /components/synthesizer
> Related RFC · RFC-036 (closes; un-defers RFC-031 mixed-op)
> Related ADRs · ADR-051 (same-module collision keyed on `(operation, multi_priority)`)

## Context

RFC-031's `apply_per_region` ships single-primitive batched-region application: one primitive applied to N mask-bound regions atomically. Photographer-survey rounds 1–3 surfaced patterns (eye-detail, dodge-and-burn-with-selective-sharpening, sky-and-foreground twin moves) where regions of one conceptual move want *different* primitives — `+exposure` on the iris, `+sharpen` on the lashes — but the move is conceptually one snapshot. RFC-031 deferred this; RFC-036 un-defers it. Full deliberation in RFC-036.

## Decision

Extend `apply_per_region` to accept a second payload shape: each region carries an `ops` array (`[{entry, parameter_values?}, ...]`) instead of relying on a top-level `entry`. The discriminator is the presence of `ops` on any region — single-primitive shape preserved unchanged for backwards compatibility.

Atomic semantics carry over from RFC-031: every (op × region) combination validates first (parameter range, mask resolution, entry lookup); if any validation fails, the whole batch aborts and no snapshot is taken.

Per-(op, region) `multi_priority` allocation:

> `multi_priority = baseline_max_for_op + per_op_region_counter`

Each op's region instances get their own counter; different ops' regions don't collide because the synthesizer keys SET-replace on `(operation, multi_priority)`.

Cap: `MAX_OP_REGION_PAIRS = 64` total (op × region) pairs per call. Single-primitive shape's existing 32-region cap stays.

## Rationale

- **Composite moves are conceptually one snapshot.** Eye-region work (lift + sharpen on each eye) is one editorial move; forcing the photographer to make two `apply_per_region` calls produces two snapshots and an unclear log entry.
- **Schema extension over new verb.** A new `apply_per_region_mixed` verb explodes the surface for a payload-shape difference. Single discriminator on one verb keeps the API narrow.
- **Per-(op, region) `multi_priority`** keeps stacked instances of the same op coexisting cleanly while preventing cross-op collisions. Aligns with ADR-051's collision-keying.
- **Cap of 64** prevents pathological batches without restricting realistic workflows. Eye-detail (4 regions × 2 ops = 8), dodge-and-burn-with-sharpen (12 regions × 2 ops = 24), face-sculpt-with-clarity (6 regions × 3 ops = 18) all fit comfortably.

## Alternatives considered

- **New verb `apply_per_region_mixed`.** Rejected — explodes the surface; same conceptual operation belongs on one verb with a discriminator.
- **Force every region to use `ops` (no single-primitive shorthand).** Rejected — the dominant pattern (single-primitive dodge-and-burn) is overwhelmingly common; wrapping one op in an array is gratuitous noise.
- **Top-level `ops: [...]` (one ops list applies to all regions).** Considered, deferred — the dominant mixed-op cases have *different* op composition per region. Top-level shorthand is a minor convenience that doesn't justify the schema split.
- **Defer indefinitely (RFC-031's posture).** Rejected — survey evidence across genres shows the patterns recurring, and shipped primitives compose at the cost of N snapshots without this.

## Consequences

Positive:
- One snapshot for composite moves; one `log` entry; one structured op payload covering the move.
- Composes with named masks (RFC-032), parametric range masks (RFC-024), and parametric L2 strength (RFC-035).
- Backwards compatible — single-primitive callers see no change.

Negative:
- +1 schema shape on `apply_per_region`. Validation discriminates cleanly; both shapes have test coverage.
- Op-log entries diverge — single-op records `op: "apply_per_region"`, mixed-op records `op: "apply_per_region_mixed"`. Consumers handle both.
- Failure-mode surface grows. Cross-op parameter validation + per-op mask resolution = more ways a batch fails. Mitigated by atomic-validate-then-apply.
- Visual review pending — the multi_priority-stacking discipline behaves correctly in unit + integration tests; whether the resulting compositions look right against real raws is the darkroom checkpoint.

## Implementation notes

- Extended `src/chemigram/core/batched.py` with `OpSpec`, `MixedRegionSpec` dataclasses + `apply_per_region_mixed()` function.
- `MAX_OP_REGION_PAIRS = 64` constant; `MAX_REGIONS_PER_CALL = 32` preserved for single-op shape.
- CLI: `chemigram apply-per-region` accepts both shapes; presence of `ops` on any region routes to mixed-op path.
- MCP: `apply_per_region` tool same — discriminator-driven dispatch.
- Tests: 12 new in `tests/unit/core/test_batched_mixed.py` covering payload-shape validation, multi_priority allocation, atomic-validate-then-apply, error paths.

## Resolved RFC-036 open questions

1. **Same op twice within one region** — yes, allowed; each op gets its own multi_priority within the per-op counter.
2. **Cap on (op × region) pairs** — 64 total.
3. **Cross-op ordering within a region** — `ops` is a list; order matters; documented in the synthesizer behavior.
4. **Same op declared twice in one region with conflicting parameter values** — hard error (validation rejects) per atomic-discipline.
