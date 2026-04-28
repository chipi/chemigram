# ADR-033 — MCP tool surface (initial)

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/mcp-server ·/contracts/mcp-tools
> Related RFC · RFC-010

## Context

The agent communicates with Chemigram exclusively through MCP tools. The tool surface defines what the agent can do, what parameters it sees, and what it gets back. Too few tools and the agent can't accomplish basic flows; too many and the action space becomes overwhelming.

The concept package (04/10) proposed an initial tool list. This ADR locks that list as the v1 surface.

## Decision

The v1 MCP tool surface, grouped by subsystem:

**Vocabulary and edit operations**
- `list_vocabulary(layer?, tags?)` → entries
- `get_state(image_id)` → entries + head hash
- `apply_primitive(image_id, primitive_name, mask_override?)` → state_after, snapshot_hash
- `remove_module(image_id, module_name)` → state_after, snapshot_hash
- `reset(image_id)` → state_after (resets to baseline_end, not empty)

**Rendering**
- `render_preview(image_id, size=1024, ref_or_hash?)` → jpeg_path
- `compare(image_id, hash_a, hash_b, size=1024)` → jpeg_path
- `export_final(image_id, ref_or_hash?, size=None, format="jpeg")` → output_path

**Versioning**
- `snapshot(image_id, label?)` → hash
- `checkout(image_id, ref_or_hash)` → state
- `branch(image_id, name, from?)` → ref
- `log(image_id, ref?, limit=20)` → entries
- `diff(image_id, hash_a, hash_b)` → primitive diffs
- `tag(image_id, name, hash?)` → ref

**Masking**
- `generate_mask(image_id, target, prompt?, name?)` → mask_id, name
- `list_masks(image_id)` → entries
- `regenerate_mask(image_id, name, target?, prompt?)` → mask_id
- `invalidate_mask(image_id, name)` → ok
- `tag_mask(image_id, source, new_name)` → mask_id

**Ingestion and binding**
- `ingest(raw_path, image_id?)` → image_id, exif_summary, suggested_bindings
- `bind_layers(image_id, l1_template?, l2_template?)` → state_after

**Context**
- `read_context(image_id)` → taste_md + brief_md + notes_md + recent_log
- `propose_taste_update(content, category)` → proposal_id
- `confirm_taste_update(proposal_id)` → ok
- `propose_notes_update(image_id, content)` → proposal_id
- `confirm_notes_update(proposal_id)` → ok
- `log_vocabulary_gap(image_id, description, workaround)` → ok

Total: 30 tools.

## Rationale

- **Covers the conversational loop.** Mode A's natural flow (read context → list vocabulary → apply → preview → snapshot → optionally branch/tag/diff) is fully expressible.
- **Each tool maps to one engine operation.** No "mega-tool" that does many things; the agent's reasoning can chain them clearly.
- **Naming follows convention.** Verbs match concepts: `apply`, `remove`, `snapshot`, `checkout`, `branch`, `tag`. Nothing surprising.
- **Locked surface is intentional.** Adding new tools requires a new ADR (or this one's supersession). Resists scope creep.

## Alternatives considered

- **Fewer tools, with action parameters (e.g., one `versioning_op` tool with a `kind` parameter):** rejected — the agent reasons better with explicit verbs. Generic tools obscure intent in tool-call traces.
- **More tools (e.g., separate tools for parametric vs drawn vs raster mask kinds):** rejected — overwhelms the action space. Mask kind is determined by the vocabulary entry's `mask_kind` field; the agent doesn't choose at tool-call time.
- **Tool returns include rich JSON metadata:** done. Each tool's return shape is specified in RFC-010.

## Consequences

Positive:
- Clear, bounded action space
- Each tool has a single responsibility
- The agent's tool-call traces are inspectable and inform future improvements

Negative:
- 30 tools is non-trivial; new agents must read the manifest carefully (mitigated: tools are organized by group, names are descriptive, parameter shapes are consistent)
- Adding a tool is a real ADR-level change (intentional; resists creep)

## Implementation notes

`src/chemigram_mcp/server.py` registers each tool with the MCP framework. RFC-010 specifies parameter shapes, return schemas, and error contracts. Each tool's implementation delegates to `chemigram_core` (e.g., `apply_primitive` → `xmp.synthesize_xmp` + `versioning.snapshot` + `pipeline.render`).
