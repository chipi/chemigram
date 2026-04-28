# ADR-051 — Same-module collision: SET-replace by `(operation, multi_priority)`, last-writer-wins, Path B deferred

> Status · Accepted
> Date · 2026-04-28
> TA anchor ·/components/synthesizer
> Related RFC · RFC-006 (closes here)
> Related ADR · ADR-002 (SET semantics), ADR-009 (Path A vs Path B), ADR-050 (parser API)

## Context

RFC-006 framed the open question: when synthesis encounters multiple inputs targeting the same `(operation, multi_priority)`, what's the resolution rule? ADR-002 had committed to SET semantics conceptually; RFC-006 enumerated three concrete scenarios (sequential application, composite primitives, cross-pack conflicts) and proposed strict resolution rules including treating in-call collisions as synthesizer errors.

Slice 1 Issue #3 implemented the synthesizer end-to-end against real Phase 0 fixtures. The implementation revealed that "last-writer-wins on input order" is the more useful rule for in-call collisions than "raise on collision" — it lets callers compose primitives naturally, and the snapshot trail (Slice 2) preserves the sequence anyway.

Phase 0 experiment 5 (the originally-deferred validation of darktable's collision behavior) was sidestepped by Slice 1's design choice: the synthesizer never produces a colliding XMP. SET-replace replaces in place at a single index; darktable never sees two `<rdf:li>` entries with the same `(operation, multi_priority)`. The "what does darktable do?" question becomes moot.

## Decision

The synthesizer implements **Path A only** with these rules:

1. **Identity for collision** is the tuple `(operation, multi_priority)`.
2. **In-call collision** (a `<plugin>` matches a baseline `<rdf:li>`): replace the baseline entry **in place at its existing list index**. Preserve `num` and `iop_order` from the baseline slot; take all other fields from the input plugin.
3. **Multiple input plugins targeting the same baseline slot**: last-writer-wins on input order. Each plugin in turn replaces the slot; the final write is the slot's value.
4. **Path B** (input `(operation, multi_priority)` not present in baseline): raise `NotImplementedError` with a message naming the offending tuple. **Not implemented in Slice 1** because darktable 5.4.1 writes no `iop_order` to either `.dtstyle` or XMP, leaving Path B without a source of truth for that field. Reopens when RFC-001's iop_order question is settled.
5. **In-`.dtstyle`-file collision** (two `<plugin>` records with same `(operation, multi_priority)` in one dtstyle): not validated by the parser in Slice 1. Behavior: each plugin in document order is applied to the synthesizer pass, and the last one wins per rule 3. Future parser enhancement may surface this as a schema error per RFC-006's original proposal #1.
6. **Cross-pack conflicts** (same vocabulary primitive name from different packs): not a synthesizer concern. Resolved at vocabulary load time by precedence; out of scope for this ADR.

**Verification:** `tests/unit/core/test_synthesize.py` covers the in-call collision rules including last-writer-wins, num/iop_order preservation, Path B failure, baseline immutability, multi-plugin DtstyleEntry behavior, and top-level metadata preservation. `tests/integration/core/test_synthesis_integration.py` exercises the full path against the Phase 0 v3 reference XMP.

## Rationale

- **In-place index replacement** preserves implicit pipeline ordering. darktable 5.4.1 computes execution order from the parent `iop_order_version` and an internal iop_list, not per-`<rdf:li>` metadata. Keeping the baseline's slot index keeps that ordering intact without the synthesizer needing to compute iop_order.
- **Last-writer-wins (rule 3)** deviates from RFC-006's proposal #2 (raise on in-call collision). The deviation is intentional: callers naturally compose primitives in sequence, and forcing them to deduplicate before the call is ergonomic friction with no architectural payoff. The snapshot trail (Slice 2's versioning) preserves the sequence, so the "lost" intermediate state is recoverable.
- **Path B `NotImplementedError`** is the conservative response to a real ambiguity. Silent wrong-renders (Phase 0 iteration 1's "entry silently dropped" failure mode) would be worse than loud failures.
- **Phase 0 experiment 5 is moot.** The original concern was "what does darktable do with two same-`(op, mp)` entries in one XMP?" — which only matters if our synthesizer can produce such an XMP. SET-replace by design never does.

## Alternatives considered

- **Raise an exception (originally proposed as `SynthesisError`) on in-call collision** (RFC-006 proposal #2): rejected. Real callers naturally compose primitives that may collide; forcing pre-call deduplication is friction without payoff. (The drafted `SynthesisError` class was subsequently removed in the post-Slice-1 cleanup — it was never raised; YAGNI.)
- **Cumulative semantics on collision** (each plugin's effect adds rather than replaces): rejected. Diverges from ADR-002 SET semantics, complicates reasoning, and would require per-field accumulation rules that don't exist for opaque blobs.
- **Implement Path B with a heuristic iop_order** (e.g., baseline.max + 1, or insert-at-end): rejected. Phase 0 iteration 1 demonstrated that wrong iop_order causes darktable to silently drop the entry. A heuristic that "usually works" would surface as a maintenance hazard. Wait for RFC-001's principled resolution.
- **Reject duplicate plugins inside one .dtstyle at parse time** (RFC-006 proposal #1): deferred to a future parser enhancement. Slice 1 doesn't validate this; in practice all Phase 0 fixtures are single-`<plugin>` and the synthesized multi-module fixture has distinct operations, so the collision case is unexercised. Worth adding when contributor packs grow.

## Consequences

Positive:
- Synthesizer is a pure function with simple, predictable rules
- darktable never sees a colliding XMP, sidestepping Phase 0 experiment 5 entirely
- Path B failure is loud (`NotImplementedError`) rather than silent
- Last-writer-wins matches caller intuition

Negative:
- Path B is a real feature gap; primitives that need to add a new module instance to a baseline that doesn't have one fail loudly. Workaround for Slice 1: include the target operation in the baseline before calling synthesize. Real fix tracked in RFC-001.
- In-`.dtstyle`-file collisions aren't validated; misauthored entries get last-wins applied silently. Mitigation: vocabulary review process catches this in PR review (per `docs/CONTRIBUTING.md`).

## Implementation notes

- `src/chemigram/core/xmp.py::synthesize_xmp` — Path A implementation, NotImplementedError for Path B
- `src/chemigram/core/xmp.py::_plugin_to_history` — pure dtstyle-to-XMP shape conversion
- (`SynthesisError` was originally drafted here as a reserved future error class; removed in the post-Slice-1 cleanup since no condition raised it. Re-introduce when needed.)
- Tests: 10 unit cases in `tests/unit/core/test_synthesize.py` exercise every rule; 1 integration case in `tests/integration/core/test_synthesis_integration.py` runs the full path against real fixtures
- RFC-006 status moves to `Decided`; remains as historical record
- Future work: parser-level duplicate detection in dtstyle files (RFC-006 proposal #1, deferred)
