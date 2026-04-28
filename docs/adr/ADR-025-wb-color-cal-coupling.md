# ADR-025 — WB and color calibration coupling

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/synthesizer ·/contracts/dtstyle-schema
> Related RFC · None (Phase 0 finding 3)

## Context

Phase 0 testing surfaced that darktable's modern scene-referred pipeline couples white balance (`temperature` module) with color calibration (`channelmixerrgb` module). Adjusting WB while color calibration is enabled auto-updates color calibration. This is darktable's intentional behavior — color calibration uses WB as input.

For Chemigram vocabulary, this means a "WB warm subtle" primitive authored with color calibration enabled actually touches both `temperature` AND `channelmixerrgb`. The photographer's intent ("warm the white balance") gets implemented as a coupled two-module move.

## Decision

Vocabulary primitives that touch WB can take either of two forms; both are valid:

**Decoupled WB primitive** — authored with color calibration *disabled* before adjusting WB. The resulting `.dtstyle` touches only `temperature`. Manifest declares `touches: ["temperature"]`.

**Coupled WB primitive** — authored with color calibration *enabled* (darktable's default in scene-referred). The resulting `.dtstyle` touches both `temperature` AND `channelmixerrgb`. Manifest declares `touches: ["temperature", "channelmixerrgb"]`.

The vocabulary entry's manifest is authoritative — the parser uses `touches` to filter `.dtstyle` content; both single-module and multi-module entries work correctly through the synthesizer.

## Rationale

- **Both forms are legitimate.** Some workflows want decoupled control (precise WB without affecting color cal); some want coupled (the modern darktable way, where WB feeds color cal). Forcing one would break the other.
- **The synthesizer handles multi-module entries fine.** `dtstyle.parse_dtstyle()` returns a list of plugin records; SET semantics (ADR-002) applies independently per module.
- **Honest documentation.** Photographers must understand the coupling when authoring; CONTRIBUTING.md documents both forms and lets the contributor choose.

## Alternatives considered

- **Force decoupled (always disable color cal before WB authoring):** rejected — excludes legitimate "modern darktable workflow" vocabulary and forces an extra step that doesn't match how some photographers actually work.
- **Force coupled (always include both):** rejected — excludes legitimate "I want only WB control" vocabulary.
- **Detect coupling automatically and split into two primitives:** rejected — adds parser complexity for a discipline that the photographer can decide directly.

## Consequences

Positive:
- Both common WB workflows are supported
- The manifest's `touches` declaration is the single source of truth
- The synthesizer is simpler — it doesn't need WB-specific logic

Negative:
- Photographers must understand the coupling when authoring (mitigated: documented in CONTRIBUTING.md/Authoring procedure step 3)
- Two photographers' "wb_warm_subtle" entries may not be byte-identical (one decoupled, one coupled), even though both are valid (mitigated: vocabulary names should clarify; e.g., `wb_warm_subtle_decoupled` vs `wb_warm_subtle_modern`)

## Implementation notes

`docs/CONTRIBUTING.md`/Authoring procedure step 3 explains both forms. The vocabulary's starter pack documents which form each WB entry uses. Manifest-schema validation in CI checks that `touches` declarations match the `<operation>` tags actually present in the `.dtstyle`.
