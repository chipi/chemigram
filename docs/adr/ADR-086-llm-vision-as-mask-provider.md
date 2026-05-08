# ADR-086 — LLM-vision-as-provider for AI-derived masks

> Status · Accepted
> Date · 2026-05-08
> TA anchor · /components/masking · /contracts/mcp-tools · /constraints/byoa
> Related RFC · RFC-026 (LLM-vision-as-provider for AI-derived masks)

## Context

ADR-076 retired the PNG-mask Protocol after discovering darktable-cli does not consume raster mask bytes. ADR-084 / RFC-029 closed the build-by-words spatial mask workflow. ADR-085 / RFC-024 closed the parametric range-filter refinement. The remaining content-derived masking gap — "lift the iguana's face," "deepen the sky," "trace the manta" — needs *vision over the actual photo content*. The naive shape (deploy a SAM-class model) requires every photographer to install something.

Modern chat clients (Claude.ai, ChatGPT, Claude Code) ship vision-capable LLMs in the conversation surface. When the photographer attaches a photo or chemigram surfaces a render via `render_preview`, the LLM sees it and can identify subjects, estimate bounding boxes, trace coarse polygons, and suggest color/luminance ranges. The full deliberation lives in RFC-026; this ADR captures the closing decision.

## Decision

**The LLM in the photographer's chat client is the AI mask provider for v1.9.0.** No engine code changes; no new MCP tools. The integration is documentation + workflow patterns, leveraging:

- `render_preview(image_id)` to surface a current-state JPEG (already shipped).
- The chat client's image rendering (Claude Code via `Read`; Claude Desktop / ChatGPT inline) — surfaces the image to the LLM's vision.
- The `mask_spec` wire (RFC-029 / ADR-084 + RFC-024 / ADR-085) — accepts `dt_form` (rectangle, ellipse, path) and `range_filter` (luminance, color_h/s/l) constructed from the LLM's spatial reasoning.

The closing artifact is `docs/guides/llm-vision-for-masks.md` — a pattern library showing photographer phrase → LLM reasoning → resulting `mask_spec`, covering subject region, sky/foreground split, color-range estimation, and polygon trace.

Precision-tier use cases (pixel-perfect silhouettes, dense spot enumeration, depth maps) where LLM-vision quality is insufficient route to **RFC-030** (deferred), which holds the deployed-sibling-provider scaffolding.

## Rationale

The wire is already there. RFC-029 / ADR-084 ships `dt_form` for spatial shapes including arbitrary N-vertex polygons. RFC-024 / ADR-085 ships `range_filter` for content-derived pixel selection (luminance bands, HSL hue/sat/lightness ranges). Anything the LLM might construct from looking at a photo — a bounding box, a coarse silhouette, a hue range — has a direct mapping into these schemas.

The deployed-provider arc (separate sibling project, model weights, MCP scaffolding) is materially heavier and forces installation friction for *every* photographer who wants content-derived masks. LLM-as-provider unlocks the workflow at zero deployment cost. Quality is bounded — LLMs produce coarse polygons (~8-15 vertices, not pixel-precise) and bounding-box-quality region estimates — but covers ~70% of real workflows: subject regions, sky/foreground splits, color-range estimation, iterative refinement.

The 30% that LLM-vision cannot serve (single-strand hair, hundreds of small spots, per-pixel depth) earns the precision-tier RFC-030 work when photographer evidence demands it. Splitting LLM-vision (now) from deployed-providers (when needed) lets each ship on its own evidence.

## Alternatives considered

- **Skip LLM-as-provider; ship deployed-provider only (the original RFC-026 v0.1 shape).** Rejected — forces every photographer to install a sibling project just to get coarse subject masks. LLM-vision covers ~70% of use cases at zero cost.
- **Skip the deployed path entirely; LLM-vision forever.** Rejected — precision-tier workflows (portrait retouching, wildlife pixel-precision) need it eventually. RFC-030 keeps the path open.
- **Bundle SAM into chemigram core.** Rejected — violates ADR-007.
- **Lightweight Anthropic-API / GPT-4-Vision wrapper as a default sibling.** Considered. Adds API key / billing / rate-limit UX surface that v1.9.0 doesn't need. Reconsider in RFC-030.
- **Single combined RFC-026 covering both LLM-vision and deployed.** Considered, drafted briefly, rejected. Confused the priority signal — shipping LLM-vision MVP is a different decision from designing deployed-provider scaffolding. Splitting (RFC-026 LLM-vision + RFC-030 deployed) lets each close on its own evidence + timeline.

## Consequences

Positive:

- **Content-derived masks ship for every photographer with a vision-capable chat client.** Zero deployment cost, zero infrastructure, zero new core dependencies.
- **MCP surface stays narrow.** No new tools; ADR-033 preserved.
- **BYOA principle taken further.** The "provider" is the chat client the photographer already chose; chemigram never specifies a model.
- **Composes with the existing wire.** LLM-vision constructs flow through the same `mask_spec` apply path as drawn masks (RFC-029) and parametric filters (RFC-024). No fork in the architecture.
- **Workflow patterns are documentable.** A pattern library guide gives the LLM stable grounding so different sessions produce consistent mask designs.

Negative:

- **Precision is bounded.** Coarse bounding boxes and ~12-vertex polygons; not pixel-precise. Single-strand hair, complex silhouettes, fine edges all degrade. Mitigated by RFC-030 as the upgrade path.
- **Workflow is conversation-shaped.** Pure-CLI photographers without an LLM in context can't use this RFC's path. Drawn masks (RFC-029) cover their core needs; RFC-030's deployed providers eventually serve them too.
- **No deterministic reproducibility.** Different LLM responses to the same photo may yield slightly different mask coordinates. Mitigated by chemigram's snapshot history capturing the actual coordinates used.
- **Quality varies by chat-client LLM.** Better LLMs → better masks. Same architectural shape; the photographer's choice of chat client determines vision quality.
- **Image surfacing depends on chat-client capability.** Claude Code's `Read` works today; other MCP clients may need MCP image content blocks. Mitigated by drag-drop / paste workflows and a future enhancement for inline-image MCP support.

## Implementation notes

No engine code changes. The closing artifact is **`docs/guides/llm-vision-for-masks.md`** — pattern library covering:

- **Subject region** (rectangle / ellipse / path from LLM bounding-box-or-polygon estimate).
- **Sky / foreground split** (gradient + color_h refinement).
- **Color-range estimation** (LLM examines image, suggests `range_filter.kind=color_h, min, max`).
- **Polygon trace** (path form from coarse vertex estimate).
- **Iterative refinement** (render preview, LLM re-examines, adjust mask, re-apply — the conversation IS the refinement loop).

Each pattern shows: photographer's phrase → LLM's expected reasoning → resulting `mask_spec` JSON.

### Image surfacing today

`render_preview(image_id)` returns a JPEG path. Claude Code clients use `Read` to surface the image to the conversation. Claude Desktop / ChatGPT users can drag-drop or paste the rendered JPEG. Future enhancement: a sibling tool returning base64-encoded JPEG content as an MCP `image` content block for clients that support it. **Not blocking ADR-086** — the workflow works today via the path-based mechanism.

### What this ADR explicitly does NOT settle

- Deployed-sibling-provider Protocol design (RFC-030).
- AI content-aware spot detection (RFC-025's deferred AI sub-path; routes to RFC-030).
- Depth-mask encoding (RFC-030).
- Cloud-API wrapper as a default provider (RFC-030 open question).

When LLM-vision becomes the bottleneck on real workflows, RFC-030 unfreezes; until then, this ADR is the v1.9.0 ship.
