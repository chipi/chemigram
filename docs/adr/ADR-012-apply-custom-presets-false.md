# ADR-012 — `--apply-custom-presets false` always

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/render-pipeline
> Related RFC · None (forced by reproducibility need)

## Context

`darktable-cli` applies custom presets to images by default — including the photographer's auto-applied presets (e.g., "always apply this base curve to Nikon raws"). For Chemigram's render pipeline, this is a contamination source: the same XMP rendered on different machines, or against different photographer configdirs, can produce different output.

## Decision

`darktable-cli` is always invoked with `--apply-custom-presets false`. No exceptions.

## Rationale

- **Reproducibility.** Same XMP + same raw → same output, regardless of which photographer's machine. Critical for snapshot-based versioning, render caching, debugging.
- **Predictability.** What's in the synthesized XMP is what gets applied — no hidden additions from the configdir.
- **Isolation.** Even though Chemigram uses an isolated configdir, that configdir might still have presets imported during vocabulary authoring. `--apply-custom-presets false` makes the isolation complete at render time.

## Alternatives considered

- **Allow the photographer to opt in:** rejected — a config knob for "make my renders inconsistent" is a footgun. If a specific use case requires applied custom presets, that path can be revisited via a superseding ADR.
- **Conditional: false for Chemigram-synthesized XMPs, true for "apply this style" workflows:** moot — ADR-011 rejects the `--style` workflow, so there's no second path to handle.

## Consequences

Positive:
- Renders are reproducible across machines
- Snapshot hashes (ADR-018) are deterministic given the same XMP
- Debugging is straightforward: "what's in the XMP" is "what got rendered"

Negative:
- Photographers who have global presets in their everyday workflow (e.g., a custom base curve) cannot use those globally with Chemigram. They must capture them as L1/L2 vocabulary explicitly, which is the intended behavior anyway.

## Implementation notes

`src/chemigram_core/stages/darktable_cli.py` includes `--apply-custom-presets false` in every `darktable-cli` invocation. Not user-configurable.
