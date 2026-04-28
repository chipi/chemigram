# ADR-001 — Vocabulary approach (Architecture B)

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/synthesizer ·/constraints/opaque-hex-blobs
> Related RFC · None (foundational decision from concept package)

## Context

darktable's edit state is encoded in XMP sidecars. Module parameters are hex-encoded C structs (`op_params`) and gzip+base64 blend operations (`blendop_params`) — neither is human-editable, both are modversion-pinned to specific darktable releases. The agent needs a way to express edits over this opaque substrate.

Three approaches were considered during the concept-package work: hex param manipulation (decode/encode each module's binary struct), pre-authored vocabulary (`.dtstyle` files captured in darktable's GUI), and a Lua bridge to a running darktable instance.

## Decision

Chemigram uses the vocabulary approach: pre-authored single-module styles captured in darktable's GUI, exported as `.dtstyle` XML files, composed into XMPs by the synthesizer. The agent's action space is a finite, named, photographer-curated set of moves rather than continuous parameter values.

## Rationale

- The agent's action space becomes meaningful and finite (closer to how a human apprentice learns moves, not slider-tweaking).
- Authoring vocabulary is a craft act — it forces the photographer to articulate the moves they reach for, which is part of the project's research thesis.
- Vocabulary is portable, inspectable, versionable, distributable as packs.
- Implementation cost is small: parse `.dtstyle`, copy hex blobs into synthesized XMPs, no struct decoding.
- Phase 0 testing validated end-to-end that this works on darktable 5.4.1.

## Alternatives considered

- **Architecture A — hex param manipulation:** decode/encode each module's binary params struct. Rejected for v1: per-module engineering, modversion drift, complex modules (filmic, color balance rgb) have dozens of fields. Reserved as Path C for high-value modules where continuous control matters (see RFC-012).
- **Architecture C — Lua bridge to running darktable:** the path `darktable-mcp` (w1ne) takes. Rejected: recreates the Lightroom-SDK fragility we picked darktable to escape. App must stay open and focused.
- **Architecture D — write a custom raw processor:** rejected as obviously absurd; darktable is the substrate, not something we'd reimplement.

## Consequences

Positive:
- The vocabulary becomes the project's **voice** — bad vocabulary makes the agent stupid, good vocabulary makes it expressive
- Implementation cost in Phase 1 is bounded (~300 lines for synthesizer + parser)
- Vocabulary itself is a research artifact (a portrait of how a photographer edits)

Negative:
- Coarse rather than continuous parameter control (mitigated by Path C for high-value modules)
- Vocabulary requires authoring work (mitigated by gap-surfacing tooling)
- Photographer must understand darktable's GUI well enough to author primitives correctly

## Implementation notes

`src/chemigram_core/dtstyle.py` parses `.dtstyle` files. `src/chemigram_core/xmp.py` synthesizes XMPs by composing parsed entries. See RFC-001 for the synthesizer architecture and ADR-002 for SET semantics.
