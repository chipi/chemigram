# API Reference

Auto-generated from the docstrings in `src/chemigram/core/`. Calibrated to **Slice 1** of Phase 1: parser, XMP r/w + synthesizer, render pipeline, EXIF auto-binding. The surface grows with each slice.

## Modules shipped (Slice 1)

| Module | Role | Key public symbols |
|-|-|-|
| [`chemigram.core.dtstyle`](dtstyle.md) | Parse darktable `.dtstyle` style exports | `parse_dtstyle`, `DtstyleEntry`, `PluginEntry`, `DtstyleParseError` |
| [`chemigram.core.xmp`](xmp.md) | Parse, synthesize, and write darktable XMP sidecars | `parse_xmp`, `synthesize_xmp`, `write_xmp`, `Xmp`, `HistoryEntry`, `XmpParseError` |
| [`chemigram.core.pipeline`](pipeline.md) | Render pipeline + `render()` convenience | `Pipeline`, `PipelineStage`, `StageContext`, `StageResult`, `render` |
| [`chemigram.core.stages.darktable_cli`](stages.md) | The v1 render stage that invokes `darktable-cli` | `DarktableCliStage` |
| [`chemigram.core.exif`](exif.md) | EXIF read for L1 vocabulary binding | `read_exif`, `ExifData`, `ExifReadError` |
| [`chemigram.core.binding`](binding.md) | Exact-match L1 vocabulary lookup | `bind_l1`, `VocabularyIndex` |

## Subsequent slices (shipped)

- **Slice 2:** `chemigram.core.versioning` — content-addressed XMP DAG (`canonical`, `repo`, `ops`).
- **Slice 3:** `chemigram.mcp.server` (MCP tool surface), `chemigram.mcp.prompts` (versioned templates).
- **Slice 4 (revised in v1.5.0):** `chemigram.core.masking.dt_serialize` — drawn-form encoders for darktable's `masks_history`. (The earlier `MaskingProvider` Protocol + `CoarseAgentProvider` + PNG mask registry were retired in v1.5.0 per ADR-076 — darktable doesn't read external PNGs for raster masks.)
- **Slice 5:** `chemigram.core.context`, `chemigram.core.session`.

See the [implementation plan](../IMPLEMENTATION.md) for the full slicing.

## Three foundational disciplines

Every module obeys the three disciplines codified in [ADR-003](../adr/ADR-003-three-foundational-disciplines.md):

1. **Agent is the only writer** — these modules never silently mutate state; every change is a tool call.
2. **darktable does the photography, Chemigram does the loop** — no image-processing capabilities live here, only orchestration.
3. **BYOA — Bring Your Own AI** — no AI dependencies in `chemigram.core`'s runtime; AI capabilities arrive via MCP-configured providers.
