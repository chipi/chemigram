# ADR-022 — Mask registry per image with symbolic references

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/synthesizer ·/contracts/per-image-repo
> Related RFC · RFC-003

## Context

Layer 2 of the mask pattern (ADR-021) involves AI-generated raster masks that the agent generates once and references across multiple vocabulary applications. The mechanism for referencing must support: regeneration when the underlying preview changes, reuse across primitives, persistence across sessions, and clean snapshot integration.

A path-based reference (e.g., "use mask `/path/to/mask.png`") would couple vocabulary entries to absolute paths, breaking sharing and snapshot integrity. A symbolic reference resolved at synthesis time avoids that coupling.

## Decision

Each image has a mask registry storing generated masks under symbolic names. Vocabulary entries reference masks symbolically; the engine resolves symbols to actual paths at XMP synthesis time.

Per-image registry layout:

```
<image_id>/
  masks/
    current_subject_mask.png       most recent subject mask (overwritten on regen)
    current_sky_mask.png
    fish_2024_pelagic.png          named persistent mask
    registry.json                  metadata
```

Registry entry shape:

```json
{
  "name": "current_subject_mask",
  "path": "masks/current_subject_mask.png",
  "target": "subject",
  "prompt": null,
  "generator": "sam-mcp",
  "generator_config": { "model": "sam2_hiera_b" },
  "generated_from_render_hash": "a3f291...",
  "created_at": "2026-04-27T15:23:11Z"
}
```

Vocabulary entries with `mask_kind: "raster"` declare `mask_ref: "current_subject_mask"`. The synthesizer looks up the mask by name in the registry and writes the resolved path into the synthesized XMP.

## Rationale

- **Symbolic decoupling.** Vocabulary entries don't embed absolute paths; the same vocabulary works across images with their own subject masks.
- **Reuse across primitives.** The agent generates `current_subject_mask` once; multiple vocabulary applications (`tone_lifted_shadows_subject`, `warm_highlights_subject`, `structure_subject_subtle`) reference it.
- **Lifecycle clarity.** `current_*_mask` is overwritten on regeneration; named persistent masks (custom-named) survive.
- **Auditability.** The registry stores when each mask was generated, which provider produced it, what prompt was used, what render it was generated from. Sessions can be replayed because the masks are versioned alongside snapshots.

## Alternatives considered

- **Embed mask paths directly in vocabulary entries:** rejected — couples entries to specific images, breaks sharing.
- **Database of masks (SQLite):** rejected — same reasons as ADR-018 rejected SQLite for snapshots; PNG-on-disk plus a JSON registry is simpler.
- **No registry; ad-hoc path conventions:** rejected — fragile, no audit trail, no clear regeneration semantics.

## Consequences

Positive:
- Vocabulary entries are portable across images
- Mask reuse is natural (generate once, reference many times)
- Registry serves as audit trail for mask provenance
- Snapshot integration is clean (ADR-018 + RFC-003 detail how masks are versioned with snapshots)

Negative:
- The agent must understand symbolic references (one extra concept beyond raw paths)
- Stale masks (generated from outdated previews) need detection logic — see RFC-003

## Implementation notes

`src/chemigram_core/masking/registry.py` implements the registry. RFC-003 deliberates how masks are stored within snapshots (Option A: content-addressed alongside XMPs vs Option B: per-snapshot subdirectories). RFC-009 specifies the `MaskingProvider` protocol that produces mask PNGs.
