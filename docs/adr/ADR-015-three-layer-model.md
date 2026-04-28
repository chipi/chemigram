# ADR-015 — Three-layer model (L0/L1/L2/L3)

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/synthesizer
> Related RFC · None (concept-package decision)

## Context

The vocabulary applied to a raw includes everything from "rawprepare and demosaic" (always-on) to "lift the shadows on the iguana" (per-image taste). Without structural separation, the agent's mental model collapses: it sees one undifferentiated stack and can't reason about what's safe to mutate, what's photographer-set, what's it own playground.

The concept-package work proposed a three-layer model that separates *who authors what when*, providing both an agent-cognitive structure and an architectural seam.

## Decision

Edits stack in three explicit layers (with L0 being darktable's always-on internals):

- **L0 — darktable internals.** rawprepare, demosaic, color profiles. Always-on. Not authored by anyone in the Chemigram sense; just present.
- **L1 — Technical correction.** Lens correction, profiled denoise, hot pixel removal. Authored by the photographer per camera+lens binding. Empty by default (opt-in). Pre-baked into baseline.
- **L2 — Look establishment.** Baseline exposure, view transform, color cast recovery, OR a film simulation. Authored by the photographer per image (chosen baseline). Pre-baked into baseline before the agent starts.
- **L3 — Taste.** The vocabulary primitives the agent applies during the session. Mutable in the loop.

The XMP history is partitioned by two integer markers (`technical_end`, `baseline_end`) stored in the per-image metadata. `apply_primitive`, `remove_module`, `reset` only touch the L3 segment. L1 and L2 are read-only mid-session.

## Rationale

- **Clear authorship.** Each layer answers "who set this and when." The photographer never wonders why an L1 lens correction is in their history.
- **Agent-safe action space.** The agent only mutates L3. It can read L1/L2 for context (e.g., "the baseline is filmic; my structure move should preserve that"), but can't accidentally undo a lens correction.
- **`reset()` semantics.** Reset goes to `baseline_end`, not empty history. The agent's "undo everything I did" doesn't blow away the photographer's L1+L2 setup.
- **Aligns with apprentice metaphor.** The apprentice doesn't reach over and re-zero the camera every move; they work within the studio setup the master arranged.

## Alternatives considered

- **Four explicit layers (split L2 into "neutralizing" and "look-committed"):** considered, but the split is a *flavor* of L2 (per ADR-017) rather than a separate layer. They share the "pre-agent baseline" property; differentiating in the layer count adds complexity without commensurate benefit.
- **Two layers (baseline + taste):** rejected — collapses L1/L2 distinction, removes the per-camera+lens binding pattern that makes lens correction work cleanly.
- **No formal layer model:** rejected — without it, the agent has no principled way to know what's mutable, and `reset()` semantics become "to what?"

## Consequences

Positive:
- The agent's action space is clearly bounded (L3 only)
- L1 and L2 are pre-baked once per image, then static for the session
- `reset()` has a well-defined target (baseline_end)
- Vocabulary entries declare which layer they belong to; mis-layered entries are caught by validation

Negative:
- The model adds a concept the photographer must learn (mitigated: starter docs explain it; in practice the agent and tooling handle layer placement)
- L2 boundary is sometimes ambiguous in practice — is "remove blue cast" a neutralizing baseline (L2) or a taste move (L3)? The starter vocabulary documents conventions; ambiguity is acknowledged rather than eliminated.

## Implementation notes

`metadata.json` per image stores `{technical_end, baseline_end}` integers. The synthesizer's `apply_primitive(image_id, primitive_name)` validates the primitive's `layer` against L3 and rejects L1/L2 vocabulary at runtime (those are applied via `bind_layers`, not through the loop).
