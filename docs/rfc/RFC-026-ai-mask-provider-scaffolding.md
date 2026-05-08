# RFC-026 — LLM-vision-as-provider for AI-derived masks

> Status · Decided
> TA anchor · /components/masking · /contracts/mcp-tools · /constraints/byoa
> Related · ADR-076 (drawn-mask only architecture; this RFC layers on top), ADR-007 (BYOA principle), ADR-084 / RFC-029 (compositional masks at apply time; the wire AI-derived masks flow through), ADR-085 / RFC-024 (parametric range-mask substrate; subject + depth deferred here for Phase 1, RFC-030 for the precision tier), RFC-025 (spot removal; AI content-aware variants deferred — see "where AI-driven precision goes" below), RFC-009 / ADR-057 (historical mask-provider Protocol — closed), RFC-030 (deployed-sibling-provider scaffolding, deferred; the precision-tier upgrade path)
> Closes into · ADR-086 (LLM-vision-as-provider MVP)
> Why this is an RFC · Photographers reach chemigram through chat clients (Claude.ai, ChatGPT, Claude Code) that already have **vision in the conversation**. When the user attaches a photo, or chemigram surfaces a render via `render_preview`, the LLM sees it. It can identify subjects, estimate bounding boxes, trace coarse polygons, and suggest color/luminance ranges. RFC-024 (color/luminance range masks) and RFC-025 (spot removal) both deferred their AI-derived sub-cases here, and RFC-026 v0.1 imagined a single architectural arc — sibling MCP project with SAM/BiRefNet/onnx, separate process, model weights, polygon output. Re-reading the workflow: the LLM-as-provider already covers the dominant content-derived masking use cases at zero deployment cost; only precision-tier needs (pixel-perfect silhouettes, dense spot enumeration, depth maps) require the deployed scaffolding. The genuine open question argued — and the answer below — is whether to ship the heavy provider scaffolding first or recognize the LLM-as-provider already covers the MVP. Answer: **LLM-vision is RFC-026's scope.** Deployed-sibling-provider scaffolding moves to RFC-030 (deferred) as the precision-tier upgrade path.

---

## The question

There are content-derived mask gaps the engine cannot serve through drawn shapes (RFC-029) or pixel-range filters (RFC-024) alone:

1. **AI-subject masks** — "lift the iguana's face" requires identifying *which region* contains the iguana.
2. **Sky/foreground splits** — "deepen the sky" requires recognizing the sky region.
3. **Color-range estimation from image** — "deepen the warm tones in the sunset" requires looking at the image to pick the right hue band.
4. **Coarse polygon trace of an irregular subject** — "around the manta" needs a rough silhouette outline.

All four need *vision + spatial reasoning over the actual photo content*. The naive shape (deploy a model server) requires every photographer to install something. Modern chat clients (Claude.ai, ChatGPT, Claude Code, Anthropic Console) ship vision-capable LLMs in the conversation surface. When the photographer attaches a photo or chemigram surfaces a render, the LLM sees it and can reason about it.

The genuine open question: **does shipping the deployed-provider scaffolding precede or follow the LLM-as-provider workflow?** Answer: **follow.** RFC-026 ships LLM-as-provider as the MVP; RFC-030 (drafted, deferred) handles the precision-tier sibling-provider scaffolding when LLM-vision becomes the bottleneck.

---

## Use cases (within Phase-1 LLM-vision capability)

1. **Coarse subject region.** Photographer working a portrait, wants to lift the face by +0.3 EV. LLM sees the photo, estimates an ellipse around the face — `center=(0.55, 0.4), radius=(0.15, 0.2)` — and constructs `mask_spec` with `dt_form: ellipse`. Better than a generic centered radial because the LLM picks the right *position* and *size* for the subject.

2. **Subject region in the wild.** Wildlife shot of a manta. LLM identifies "manta is in lower-half, roughly diamond-shaped" and emits `dt_form: path` with 8-12 vertices tracing the rough silhouette. Catches wing tips reasonably; misses fine fin detail.

3. **Sky / foreground split with parametric refinement.** Landscape with sky and mountains. LLM sees the horizon line, suggests a gradient with `anchor_y` near the horizon, plus `range_filter: color_h` covering the cyan-blue band. Composition: drawn gradient + parametric color refinement (RFC-024 wire).

4. **Color-range estimation from image.** Photographer says "deepen the warm tones in the sunset clouds." LLM examines the image, returns `range_filter: color_h, min: 0.05, max: 0.15` (orange/red band). Pure parametric, no `dt_form`.

5. **Subject vs background routing.** Photographer says "brighten the subject, dim the background." LLM identifies subject region, applies the lift through `dt_form: ellipse`, then applies a complementary edit with `range_filter.invert: true` (mask flipped) for the background.

6. **Iterative refinement.** Photographer doesn't like the first mask suggestion. Renders preview, LLM looks at the result, adjusts the mask coordinates, re-applies. The conversation loop *is* the refinement loop.

For use cases beyond LLM-vision precision (single-strand hair, hundreds of small spots, depth maps), see RFC-030 — that's the precision-tier upgrade path.

---

## Goals

- **Ship the LLM-as-provider workflow now.** The wire (RFC-029 / ADR-084 + RFC-024 / ADR-085) is already in place; the gap is purely documentation + workflow patterns.
- **Honor ADR-076's structural lesson.** LLM-estimated polygons land as drawn-form geometry darktable consumes — same `mask_spec` schema as everything else.
- **Honor ADR-007 (BYOA).** No ML in `chemigram.core`. The LLM "provider" lives in the photographer's chat client; chemigram never depends on a specific model.
- **Bound MCP surface growth.** Zero new tools required. `render_preview` (image surfacing) + `apply_primitive` with `mask_spec` (already shipped) is the entire surface.
- **Keep the precision-tier upgrade path open.** RFC-030 covers when LLM-vision quality isn't enough; this RFC explicitly hands off there.

---

## Constraints

- **ADR-076** (drawn-mask only architecture): LLM-estimated mask geometry must land as drawn-form bytes via the existing wire.
- **ADR-007** (BYOA): no ML dependencies in `chemigram.core`; the LLM is in the photographer's chat client, not bundled.
- **ADR-033** (narrow MCP tool surface): RFC-026 adds zero tools.
- **ADR-084** (apply-time mask spec semantics, RFC-029): `mask_spec` is the integration target.
- **ADR-085** (parametric mask encoding, RFC-024): `range_filter` covers content-derived color/luminance refinement; LLM-vision composes with this.
- **CLAUDE.md three foundational disciplines**: agent-only-writer (mask construction via tool calls); darktable-does-the-photography (mask math runs in darktable); BYOA (LLM-as-provider in v1.9.0; deployed siblings via RFC-030 in the future).

---

## Decision

**The LLM in the photographer's chat client is the AI provider.** The integration is documentation + workflow patterns; no engine code changes.

The pattern:

1. Photographer asks for a content-derived mask: "lift the iguana's face."
2. Agent calls `render_preview(image_id)` to surface a current-state JPEG of the image.
3. Chat client surfaces the JPEG — the LLM sees it (Claude Code via `Read`; Claude Desktop / ChatGPT inline via attached/rendered images).
4. LLM reasons spatially: identifies the subject, estimates a bounding box / ellipse / polygon / color range.
5. LLM constructs `mask_spec` (or composite with `range_filter`).
6. LLM calls `apply_primitive(name, value, mask_spec=...)` — the wire shipped in ADR-084 / RFC-029.

The closing artifact is `docs/guides/llm-vision-for-masks.md` — pattern library covering subject region (rectangle/ellipse/path), sky/foreground (gradient + color_h), color-range estimation (range_filter from image inspection), polygon trace (path form from coarse vertex estimate). Each pattern with example dialogue + spec output.

### Implementation note: image surfacing

`render_preview` produces a JPEG path. For chat clients to surface that JPEG inline so the LLM sees it:

- **Claude Code**: `Read` on the JPEG path surfaces image content into the conversation. Already works.
- **Claude Desktop / other MCP clients**: may benefit from MCP `image` content blocks. Future enhancement: a sibling tool returning base64-encoded JPEG content as an MCP image block. **Not blocking RFC-026** — drag-drop / paste workflows in clients without MCP image blocks cover the gap.

### Where AI-driven precision goes

When LLM-vision precision isn't enough — pixel-perfect silhouettes, single-strand hair, hundreds of small spots, depth maps — the workflow degrades to drawn-mask approximations. RFC-030 (deferred) is the deployed-sibling-provider arc that lifts this ceiling: SAM-class subject masks, content-aware spot detectors, depth-aware models. This RFC explicitly hands off there.

---

## Alternatives considered

### Alt 1: Skip LLM-as-provider; ship deployed-provider only

Rejected as MVP. The deployed arc is materially heavier (sibling project, model weights, infrastructure, distribution) and forces every photographer to install something just to get content-derived masks. LLM-vision unlocks the workflow at zero deployment cost and covers ~70% of use cases. Shipping deployed-only means Phase 1 photographers don't get a working content-derived workflow at all until the precision tier ships.

### Alt 2: Skip the deployed path entirely (LLM-as-provider forever)

Rejected. LLM-vision degrades on precision-tier use cases (pixel-perfect silhouettes, dense spot detection, depth maps). The deployed-provider arc earns its place when those bind. RFC-030 keeps the path open.

### Alt 3: Bundle SAM into chemigram core (forget BYOA)

Rejected — violates ADR-007. Bundling torch + SAM checkpoint balloons distribution size, freezes model choice, pulls AI into the core.

### Alt 4: Make Phase 1 include a sibling LLM-vision provider (Python wrapper around Anthropic / GPT-4-Vision API)

Considered. Would let the agent call `detect_subjects` regardless of which chat client the photographer uses. Rejected for v1.9.0 because: (a) the conversation-native workflow is the dominant use case; (b) deploying a wrapper means dealing with API keys, billing, rate limits — non-trivial UX surface; (c) photographers using chemigram CLI without an LLM in context probably don't reach for AI masks anyway. Worth revisiting in RFC-030 as a "lightweight provider" option if evidence suggests demand.

### Alt 5: Single combined RFC-026 covering both LLM-vision and deployed providers

Considered (this was the RFC-026 v0.2 shape briefly). Rejected because it confused the priority signal: shipping LLM-vision MVP is a different decision from designing deployed-provider scaffolding. Splitting into RFC-026 (Decided, ships now) and RFC-030 (Draft, deferred) lets each decision close on its own evidence + timeline.

---

## Trade-offs

- **LLM-vision precision is bounded.** Coarse bounding boxes and ~12-vertex polygons; not pixel-precise. Single-strand hair, complex silhouettes, fine edges all degrade. Mitigation: documented as the trade-off; RFC-030 is the upgrade path.
- **Workflow is conversation-shaped.** Photographer needs to be in a chat client (or any agent context with vision). Pure CLI photographers without an LLM in the loop can't use this RFC's path. Mitigation: drawn masks (RFC-029) cover their core needs; RFC-030's deployed providers eventually serve them too.
- **No deterministic reproducibility.** Different LLM responses to the same photo may produce slightly different mask coordinates. Mitigation: photographers iterate; the snapshot history captures the actual coordinates used.
- **Reliance on chat-client image surfacing.** Claude Code's `Read` surfaces images; other MCP clients may need MCP image content blocks. Mitigation: documented; future enhancement adds explicit inline-image MCP support.
- **Unbundled vision quality.** Whichever LLM the photographer's chat client runs is the vision provider. Quality varies between Claude Sonnet / Opus / GPT-4 / etc. Mitigation: same architectural shape (BYOA principle taken seriously); the better the photographer's LLM choice, the better the masks.

---

## Open questions resolved during deliberation

1. ~~Does the LLM-vision approach cover enough use cases to justify shipping it as MVP?~~ → **Yes**, ~70% of content-derived masking workflows.
2. ~~Workflow pattern documentation shape?~~ → **Pattern library guide** at `docs/guides/llm-vision-for-masks.md`.
3. ~~Image surfacing mechanism?~~ → **`render_preview` + chat-client image rendering** for v1.9.0; future enhancement for MCP image content blocks.
4. ~~Phase 2 (deployed-provider) scope inside this RFC?~~ → **No — moved to RFC-030.** Keeps RFC-026 focused on the MVP that ships now.
5. ~~Should chemigram bundle a "lightweight" Anthropic-API or GPT-API wrapper as a default provider?~~ → **No** for v1.9.0 (API keys / billing / rate limits add UX friction). Reconsider in RFC-030.

---

## How this closes

- **ADR-086 — LLM-vision-as-provider for AI masks.** Lightweight ADR formalizing the workflow pattern. Notes the wire is already shipped; the closing artifact is the workflow guide. Zero engine code changes; zero new tools.

The deployed-provider scaffolding (Phase 2 in earlier drafts) is now RFC-030 — drafted as deferred; ships when LLM-vision becomes the bottleneck.

---

## Links

- TA/components/masking
- TA/contracts/mcp-tools
- TA/constraints/byoa
- ADR-076 (drawn-mask only architecture)
- ADR-007 (BYOA principle)
- ADR-084 / RFC-029 (compositional masks at apply time — the wire)
- ADR-085 / RFC-024 (parametric mask encoding — composes with LLM-vision)
- RFC-025 (spot removal; AI content-aware variants deferred to RFC-030)
- RFC-030 (deployed-sibling-provider scaffolding; the precision-tier upgrade path)
- capability-survey.md § 7
- `src/chemigram/mcp/tools/rendering.py` — `render_preview` (image surfacing)
- `docs/guides/llm-vision-for-masks.md` — workflow pattern library (closing artifact)
