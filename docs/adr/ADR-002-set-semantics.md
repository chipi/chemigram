# ADR-002 — SET semantics: replace by (operation, multi_priority)

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/synthesizer ·/contracts/xmp-darktable-history
> Related RFC · RFC-001

## Context

darktable's XMP history is append-style — each module application adds a new `<rdf:li>` entry. Without a discipline at the synthesizer level, applying `expo_+0.5` after `expo_+0.3` would produce two exposure entries that compose, not replace. This conflicts with the agent's expectation that vocabulary application is idempotent ("apply this primitive" = "make this the current value").

## Decision

The synthesizer treats vocabulary application as SET on the key `(operation, multi_priority)`. When applying a vocabulary entry, the synthesizer looks for any existing entry in the XMP history with matching `operation` and `multi_priority`. If found, the existing entry is replaced. If not found, a new entry is appended.

## Rationale

- Idempotent action space — applying the same primitive twice produces the same state as applying it once.
- Aligns with the agent's mental model: "apply X" means "X is now the active value for this module," not "X is now layered onto existing X."
- Removes the need for the agent to track and explicitly remove prior applications.
- Phase 0 experiment 4 confirmed this approach works end-to-end with darktable's render pipeline.

## Alternatives considered

- **Append semantics (darktable's native behavior):** rejected — non-idempotent, requires the agent to reason about history accumulation, easy to produce unintended layering.
- **Replace by `operation` only (ignore `multi_priority`):** rejected — multi_priority is darktable's mechanism for legitimate multiple-instance modules (e.g., two exposure adjustments at different pipeline positions). Ignoring it would prevent the agent from ever using the multi-instance pattern.
- **Replace by entry name (`darktable:multi_name`):** rejected — `multi_name` is a free-text label, not a reliable key.

## Consequences

Positive:
- Predictable, idempotent vocabulary application
- Synthesizer logic is simple (find-by-key, replace-or-append)
- Same key (`operation, multi_priority`) is what darktable uses internally for module-instance identity

Negative:
- Removes an expressive feature (intentional accumulation) that's now only accessible via Path B (different `multi_priority`)
- The agent must understand that two simultaneous primitives touching the same `(operation, multi_priority)` resolve last-wins, not as accumulation

## Implementation notes

See ADR-009 for the two synthesizer paths (Path A — replace, Path B — add new instance). RFC-001 describes the parser API in full.
