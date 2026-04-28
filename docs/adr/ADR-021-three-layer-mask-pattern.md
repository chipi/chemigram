# ADR-021 — Three-layer mask pattern

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/synthesizer ·/components/ai-providers
> Related RFC · RFC-009 (mask provider protocol)

## Context

Local adjustments — restricting an effect to part of the frame — are where Chemigram's value concretizes. Global moves are tractable in any vocabulary system; local moves are where intent ("warm the highlights on the fish") translates to vocabulary plus masking automatically.

darktable supports three kinds of masks: parametric (luminance/hue/chroma ranges), drawn (gradients, circles, ellipses, paths), and raster (external PNG via the raster mask module). Chemigram needs to map vocabulary entries onto these, with AI subject masks fitting in cleanly.

## Decision

Three-layer pattern for handling masks in vocabulary:

**Layer 1 — Pre-baked masks in vocabulary.** Most masked vocabulary. The photographer authored the mask once in darktable's GUI as part of the `.dtstyle`. Frozen at authoring time. Examples: `gradient_top_dampen_highlights`, `vignette_subtle`, `parametric_warm_only_highlights`. The mask data lives in `blendop_params` (gzip+base64 blob); the synthesizer copies it verbatim.

**Layer 2 — AI raster mask + symbolic reference.** Content-aware isolation. The agent calls `generate_mask(image_id, target, prompt?)`; the configured masking provider runs over the current preview, writes a PNG, and registers it under a name (e.g., `current_subject_mask`). Vocabulary entries with `mask_kind: "raster"` declare `mask_ref: "current_subject_mask"` symbolically. The engine resolves the symbol to an actual PNG path at synthesis time.

**Layer 3 — Agent-described composite masks.** *Not in v1.* Compositional mask operations (intersect, dilate, refine via verbal description). Reserved for future work after the three-layer mask pattern is exercised in real sessions.

## Rationale

- **Layer 1 covers the common case** (drawn gradients, parametric warm-only-highlights, etc.) with zero AI dependency. These are authored once and used many times.
- **Layer 2 is where AI buys its keep** — content-aware subject isolation that pre-baked masks can't do. Symbolic references let the same mask be reused across multiple vocabulary applications without regenerating.
- **Layer 3 is deferred deliberately.** Compositional mask operations are speculative; we don't know yet which operations matter most. Defer until session evidence shows the need.
- The pattern aligns with darktable's mask kinds — pre-baked maps to parametric/drawn, AI raster maps to raster, composites would be a Chemigram-level abstraction over the underlying primitives.

## Alternatives considered

- **All-AI masks:** rejected — overkill for global gradients and parametric masks that don't need ML; also adds the cost of regenerating masks every time.
- **Author-everything-in-darktable (no raster path):** rejected — content-aware isolation is exactly what AI is good for and a major project value-add.
- **Composite masks as Layer 3 in v1:** rejected — speculative. We'd be designing operations without knowing which ones photographers actually want.

## Consequences

Positive:
- Most vocabulary works without AI (Layer 1)
- AI adds a clean second layer for content awareness
- Symbolic references enable mask reuse across primitives
- Layer 3 deferral preserves design freedom

Negative:
- The agent must understand which layer a vocabulary entry uses (read from manifest's `mask_kind`)
- AI masks require a configured provider (per ADR-007's BYOA)

## Implementation notes

Vocabulary manifest's `mask_kind` field declares one of `none`, `parametric`, `drawn`, `raster`. For `raster`, `mask_ref` declares the symbolic name. The synthesizer resolves symbolic names to paths via the per-image mask registry (ADR-022). RFC-009 specifies the `MaskingProvider` protocol shape.
