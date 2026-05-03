# ADR-076 — Drawn-mask-only mask architecture

> Status · Accepted
> Date · 2026-05-03
> TA anchor · /components/masking, /contracts/vocabulary-manifest
> Supersedes · ADR-021, ADR-022, ADR-055, ADR-057, ADR-058, ADR-074
> Related RFCs · RFC-003 (mask storage), RFC-004 (default masker), RFC-009 (mask provider protocol) — all retroactively closed by this ADR

## Context

Path 4a (drawn-mask XMP serialization) shipped in v1.4.0 and validated end-to-end against real darktable 5.4.1: the encoders write geometric forms directly into `<darktable:masks_history>` and patch each plugin's `blendop_params` to bind the form via `mask_id`. Pixel diffs proved the wire actually wires (B vs B' max=0; B vs C max=38 with std=2.95).

While shipping that, we discovered the previous PNG-based mask path was a silent no-op: `darktable-cli` never reads external PNG files for raster masks. `src/develop/blend.c` resolves raster masks from in-pipeline pointers (`self->raster_mask.sink.source`), not from the filesystem. The whole apply pipeline that wrote PNGs to `<workspace>/masks/<name>.png` and trusted darktable to honor them produced no visible pixel change. The only end-to-end test that purported to validate it (`tests/e2e/test_mask_shaping.py`) passed for the wrong reason — scene asymmetry, not actual masking.

That meant the bundled `MaskingProvider` Protocol, the `CoarseAgentProvider` (MCP-sampling-based default), the geometric providers (gradient/radial/rectangle), the per-image mask registry (`masks/registry.json` + content-addressed PNGs in `objects/`), the `materialize_mask_for_dt` helper, and the CLI/MCP `generate_mask`/`regenerate_mask` verbs were all infrastructure for a path that didn't exist.

## Decision

The mask architecture is drawn-mask only. The vocabulary entry's `mask_spec` field (geometric form + parameters) is the single mask binding. `apply_primitive` routes through `apply_with_drawn_mask` automatically when `mask_spec` is set; there is no provider, no PNG, no registry, no override.

Removed entirely:

- `chemigram.core.masking.MaskingProvider` Protocol + `MaskResult`, `MaskingError`, `MaskGenerationError`, `MaskFormatError`
- `chemigram.core.masking.coarse_agent` (CoarseAgentProvider)
- `chemigram.core.masking.geometric` (Gradient/Radial/RectangleMaskProvider)
- `chemigram.core.versioning.masks` (mask registry, MaskEntry, register_mask, get_mask, list_masks, tag_mask, invalidate_mask, MaskError, MaskNotFoundError, InvalidMaskError)
- `chemigram.core.helpers.materialize_mask_for_dt`, `serialize_mask_entry`, `ensure_preview_render`
- `chemigram.cli.commands.masks` (the `chemigram masks ...` sub-app: list/generate/regenerate/tag/invalidate)
- `chemigram.mcp.tools.masks` (the `generate_mask`/`regenerate_mask`/`list_masks`/`tag_mask`/`invalidate_mask` MCP tools)
- The vocabulary schema fields `mask_kind` and `mask_ref`
- The `mask_override` argument on `apply_primitive` (CLI flag and MCP tool arg)
- The `masker=` parameter on `build_server` and the `masker` field on `ToolContext`
- The per-workspace `masks_dir` property and the `masks/` subdirectory creation in `init_workspace_root`

Retained:

- `chemigram.core.masking.dt_serialize` — drawn-form encoders
- `chemigram.core.helpers.apply_with_drawn_mask` — high-level apply helper
- `mask_spec` on `VocabEntry` — the only mask declaration
- The four mask-bound expressive-baseline entries that ship validated against real darktable

## Rationale

The PNG path produced no pixels; everything that fed it was dead infrastructure. Keeping any of it as "latent infrastructure for a future SAM provider" would have been speculative — even SAM, when it arrives, can't ship PNGs to darktable because darktable doesn't read PNGs for raster masks. A future pixel-precise mask provider has to produce drawn-form geometry (or its own equivalent of `masks_history` content), which makes `MaskingProvider`'s PNG-bytes-out shape wrong for that future too.

The remaining `mask_spec` schema is small enough to evolve in place when content-aware masking does land: extend `dt_form` to whatever shapes darktable adds (path-with-control-points, brushed mask, etc.), or add a top-level `mask_provider` field that names a sibling project producing the geometry. Either way, the v1.5.0 surface is a strict subset of any plausible future surface — no breaking change is forced by ripping the dead path now.

## Alternatives considered

- **Keep `MaskingProvider` Protocol as latent infrastructure.** Rejected: the Protocol's signature (`bytes` return) is wrong for any future masker. Anything that wants drawn-form geometry will need a different shape; keeping the dead Protocol just calcifies the wrong contract.
- **Keep the mask registry but stop using it for apply.** Rejected: the registry's only purpose was apply-time PNG materialization. Without that consumer, list/tag/invalidate manage objects no one reads.
- **Keep `mask_kind`/`mask_ref` as deprecated-but-tolerated schema fields.** Rejected: they pointed at the dead path and would mislead vocabulary contributors. A clean schema with `mask_spec` alone is easier to author against.
- **Bump `apply_primitive` schema to add a `mask_provider` field now.** Rejected: speculative. Add when a real provider lands.

## Consequences

Positive:

- ~2200 lines of dead production + test code removed.
- The vocabulary schema is one-field-cleaner; mask-bound entries declare exactly what they do.
- `apply_primitive`'s tool surface drops a confusing argument that no agent could use correctly anyway.
- The Mode A prompt template (`system_v4.j2`) no longer claims masking capabilities the engine doesn't have.
- The five MCP mask tools and the CLI `masks` sub-app are gone — fewer tool-surface entries to teach the agent.

Negative:

- Mask-bound primitives are limited to gradient, ellipse, and rectangle geometries until a future ADR introduces additional drawn forms or a real content-aware masker. Pixel-precise organic masks (subject silhouettes, eyes, fur edges) are not available in v1.5.0.
- The starter pack's `tone_lifted_shadows_subject` entry, which previously declared `mask_kind: "raster"` + `mask_ref: "current_subject_mask"`, has to be rewritten as a drawn-mask entry (radial/ellipse on subject) or removed pending a real provider.
- The BYOA-masking story (ADR-007 in spirit, ADR-057 in mechanism) collapses for now — there is no plug-in surface for third-party maskers in v1.5.0. When `chemigram-masker-sam` (or equivalent) lands, the new ADR will reintroduce a provider mechanism whose shape matches what darktable can actually consume.

## Implementation notes

This ADR documents a cleanup that is contemporaneous with the v1.5.0 commit. The wire format for drawn-mask serialization is documented at `chemigram/core/masking/dt_serialize.py` with citations into the darktable 5.4.1 source (`src/develop/masks.h`, `src/develop/blend.h`, `src/common/exif.cc`).

The four shipped mask-bound expressive-baseline entries (`gradient_top_dampen_highlights`, `gradient_bottom_lift_shadows`, `radial_subject_lift`, `rectangle_subject_band_dim`) are validated end-to-end and are the canonical examples for new mask-bound vocabulary contributions.
