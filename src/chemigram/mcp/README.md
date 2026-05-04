# chemigram.mcp

The MCP server. Adapts `chemigram.core` subsystems as agent-callable tools.

Thin layer — most of the substance lives in `chemigram.core`. This module is the protocol-shaped boundary between the engine and whatever agent the photographer chooses to drive it.

**Status:** Shipped. Slice 3 (v0.3.0) introduced the MCP server + tool surface; v1.5.0 trimmed the surface to 22 tools after retiring the PNG-mask architecture (ADR-076). See `docs/IMPLEMENTATION.md`.

## Tool surface (22 tools, v1.5.0)

Grouped by subsystem:

- **Vocabulary and edit operations:** `list_vocabulary`, `get_state`, `apply_primitive`, `remove_module`, `reset`
- **Rendering and comparison:** `render_preview`, `compare`, `export_final`
- **Versioning:** `snapshot`, `checkout`, `branch`, `log`, `diff`, `tag`
- **Ingestion and binding:** `ingest`, `bind_layers`, `log_vocabulary_gap`
- **Context:** `read_context`, `propose_taste_update`, `confirm_taste_update`, `propose_notes_update`, `confirm_notes_update`

Mask-bound vocabulary entries (those with `mask_spec` set) route through the drawn-mask apply path automatically inside `apply_primitive` per ADR-076 — the previously-separate `generate_mask`, `regenerate_mask`, `list_masks`, `tag_mask`, `invalidate_mask` tools were removed in v1.5.0 (the PNG path they fed turned out to be a silent no-op).

The prompt store at `chemigram/mcp/prompts/` (per RFC-016 / ADR-043) ships `mode_a/system_v4.j2` as the active version.
