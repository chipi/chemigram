# Mode A system_v4 — changelog

## v4 — 2026-05-03 (v1.5.0; mask-path cleanup)

Drops every reference to the removed PNG-mask infrastructure:

- **`generate_mask` / `regenerate_mask` are gone** from the tool surface.
  The bundled `CoarseAgentProvider` produced PNGs that darktable never
  read (verified against darktable 5.4.1 source: `src/develop/blend.c`
  resolves raster masks from in-pipeline pointers, not the filesystem),
  so the entire path was a silent no-op. Removed in the v1.5.0 cleanup.
- **`mask_kind: "raster"` / `mask_ref` removed from the vocabulary
  schema.** Mask-bound entries now declare `mask_spec` only (drawn-form
  geometry: gradient / ellipse / rectangle). `apply_primitive` routes
  through the drawn-mask apply path automatically when `mask_spec` is
  set — no separate masker step.
- **`mask_override` argument dropped from `apply_primitive`.** The
  override existed to let the agent point a raster-mask-bound primitive
  at a different registered PNG; with raster gone, there's nothing to
  override. The mask geometry is fixed in the vocabulary entry.
- **"Local adjustments" section rewritten.** Drops talk of MCP-sampling
  masking, `coarse_agent`, `chemigram-masker-sam`-as-drop-in,
  `regenerate_mask` refinement, and `mask_override` semantics. Adds
  framing around built-in geometric mask types and how to log a
  vocabulary gap when no geometric primitive fits.
- **`masker_available` context key dropped from MANIFEST.toml.** No
  longer meaningful — there is no masker.

Backwards-compat: callers that pass extra context keys are tolerated
(Jinja `UndefinedError` only fires on referenced-but-missing keys).
Required-context-keys updates per ADR-044 in `MANIFEST.toml`.

## v3 — 2026-05-02 (Phase 1.2 / v1.2.0 prep)

(See system_v3.changelog.md.)

## v2 — 2026-04-29 (Phase 1 Slice 6, v1.0.0)

(See system_v2.changelog.md.)

## v1 — pre-v1.0.0

(See system_v1.j2 for the original Mode A prompt — pre-context-layer.)
