# chemigram_mcp

The MCP server. Adapts `chemigram_core` subsystems as agent-callable tools.

Thin layer — most of the substance lives in `chemigram_core`. This module is the protocol-shaped boundary between the engine and whatever agent the photographer chooses to drive it.

**Status:** not started. Phase 1 work.

## Tool surface (planned per `docs/architecture.md`)

Grouped by subsystem:

- **Vocabulary and edit operations:** `list_vocabulary`, `get_state`, `apply_primitive`, `remove_module`, `reset`
- **Rendering and comparison:** `render_preview`, `compare`, `export_final`
- **Versioning:** `snapshot`, `checkout`, `branch`, `log`, `diff`, `tag`
- **Local adjustments and AI masks:** `generate_mask`, `list_masks`, `regenerate_mask`, `invalidate_mask`, `tag_mask`
- **Ingestion and binding:** `ingest`, `bind_layers`
- **Context:** `read_context`, `propose_taste_update`, `confirm_taste_update`, `propose_notes_update`, `confirm_notes_update`, `log_vocabulary_gap`

See `docs/architecture.md` § "MCP tool surface" for the full spec.
