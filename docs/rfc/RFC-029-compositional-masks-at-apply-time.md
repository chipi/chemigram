# RFC-029 — Compositional masks at apply time (build-by-words and reusable mask ids)

> Status · Draft v0.1
> TA anchor · /components/masking · /contracts/mcp-tools · /constraints/agent-only-writer
> Related · ADR-076 (drawn-mask only architecture; this RFC builds on the wire), ADR-033 (narrow MCP tool surface; this RFC argues a small expansion), RFC-021 / ADR-077..080 (parameterized vocabulary; the primitives this RFC composes with masks), RFC-024 (range masks; parametric mask source), RFC-026 (AI mask provider scaffolding; AI mask source), capability-survey.md § 7 (local adjustments)
> Closes into · ADR-NNN (pending — apply-time mask spec semantics + path-shape addition), ADR-NNN (pending — `make_mask` tool surface for reusable mask ids)
> Why this is an RFC · The drawn-mask wire is fully shipped: `apply_primitive` already accepts an inline `mask_spec` (vocab_edit.py:319) that overrides any manifest mask. What's missing is the architectural framing for **how the agent uses it across the full mask-source trilogy** — drawn (today), parametric (RFC-024), AI-derived (RFC-026) — under one compositional surface. The genuine open question: should masks be reusable first-class objects (two-step: build-then-apply, mask_id referenced across primitives) or always inline-with-the-primitive (one-step: every apply call carries its own mask spec)? Lightroom's mask-group model strongly suggests reuse; the simplicity of inline-only is real too. Both have follow-on implications for how AI masks (RFC-026) flow into the apply path. Worth deliberating.

## The question

Today, an agent applying an edit through a mask has two choices:

1. **Pre-baked vocabulary entry.** Pick a manifest entry whose `mask_spec` is already wired (e.g., `gradient_top_dampen_highlights`). 4 such entries ship today.
2. **Inline override on apply.** Call `apply_primitive(name, value, mask_spec={...})` with a constructed mask spec. Wire shipped, but no documented agent-facing pattern, and the schema enum is missing `path`.

Neither pattern handles **mask reuse**. If the agent wants to apply *exposure +0.5* AND *clarity +0.3* through the same gradient covering the bottom third of the photo, it has to construct the same `mask_spec` twice. Lightroom solves this with a "mask" as a first-class object: create a mask, apply N adjustments through it, the mask is one entity in the panel.

The genuinely open question this RFC argues: **what's the right MCP surface for compositional masks?**

Two viable shapes:

- **Inline-only (Path A).** Every `apply_primitive` call carries its own `mask_spec`. Simple, stateless, already shipped. Reuse means duplication.
- **First-class mask ids (Path B).** Add `make_mask(...) → mask_id` and let `apply_primitive(..., mask_id=X)` reference it. Shipped masks become reusable across the session.

Path B subsumes A (you can always inline by skipping `make_mask`). Path A is simpler. The deliberation is whether the reuse story is real enough to justify the extra tool.

A second sub-question: **the natural-language ↔ parameter mapping.** When the user says "mask covering the bottom third," the agent translates to numerics. Today, no doc spells this out for the agent. Should chemigram ship a docs/guides/ page describing the mapping, or rely on the LLM's spatial reasoning from raw parameter names?

## Use cases

1. **"Lift the bottom third by half a stop."** Photographer wants foreground brightening on a landscape. Today: pick `gradient_bottom_lift_shadows` (a pre-baked entry that *might* match) or compose by hand. Future: agent says "exposure +0.5 through a horizontal gradient with anchor at y=0.67, light side down." One call, no vocabulary entry needed.

2. **"Same mask, multiple edits."** Photographer wants the foreground (bottom third) lifted +0.5, AND its shadows opened up, AND its clarity boosted. Three primitives, one mask. Path A: agent constructs the same `mask_spec` three times. Path B: agent calls `make_mask` once, passes the returned `mask_id` to three `apply_primitive` calls.

3. **"Mask the face."** Lightroom-style. With RFC-026, AI provider returns a polygon. The polygon flows into a `mask_id` that the agent then uses to apply N edits (skin tones, exposure, clarity). Path B is the natural fit; Path A would require the polygon to be re-passed to every edit.

4. **"Hand-drawn rectangle, then six tweaks."** Cinematic letterbox effect: rectangle covering the top 10% AND bottom 10%, dim those regions, then a separate global edit. The same mask used across multiple primitives.

5. **Iterative refinement.** Photographer applies an edit through a gradient, dislikes it, wants to nudge the mask slightly (anchor_y from 0.67 → 0.62) without redoing everything. Path B lets the agent edit the mask in place; Path A requires re-issuing every primitive with the new spec.

## Goals

- **Pick the MCP surface for compositional masks** — inline-only vs first-class mask ids, or both.
- **Add `path` to the apply-time schema enum.** RFC-026's foundation commit added `build_path_form` and the dispatcher. The `apply_primitive.mask_spec.dt_form` enum still lists `["gradient", "ellipse", "rectangle"]` only. Trivial fix; this RFC formalizes it.
- **Honor ADR-033 (narrow MCP surface).** Adding `make_mask` is a tool addition; argue it earns its place. If the answer is no, Path A wins by default — the inline path already ships.
- **Compose cleanly with RFC-024 and RFC-026.** Whatever shape lands has to accept parametric mask specs (color-range, luminance-range) and AI-derived polygon specs as first-class operands, not just drawn shapes.
- **Document the natural-language ↔ parameter mapping** so the agent can construct masks from spatial English without trial-and-error.

## Constraints

- **ADR-076** (drawn-mask only architecture): the wire stays drawn-form bytes. Mask specs serialize through `build_form_from_spec`; that's already shipped.
- **ADR-033** (narrow MCP tool surface): tool additions require an ADR. `make_mask` is one tool; RFC-029 must argue it.
- **CLAUDE.md three foundational disciplines**: agent-only-writer (mask construction is a tool call); darktable-does-the-photography (mask math runs in darktable); BYOA (AI sources via MCP providers per RFC-026).
- **Backward compatibility**: existing pre-baked vocabulary entries with manifest `mask_spec` continue to work. Inline `mask_spec` already overrides the manifest one (vocab_edit.py:319, ADR-076). Whatever this RFC adds layers on top, doesn't replace.

## Proposed approach

**Path B (first-class mask ids) as primary; Path A (inline) preserved as syntactic sugar for the one-shot case.** Both already half-shipped via `apply_primitive`'s inline `mask_spec`; this RFC formalizes the dual surface.

### 1. New MCP tool: `make_mask`

```python
@tool
def make_mask(
    image_id: str,
    *,
    spec: dict,           # {dt_form: "gradient" | "ellipse" | "rectangle" | "path", dt_params: {...}}
    name: str = "",       # optional human-readable label
) -> dict:                # {mask_id: int, image_id: str, spec: dict, ...}
    """Construct a drawn mask from a spec; return its id for reuse.

    The mask is registered in the per-image mask registry
    (~/Pictures/Chemigram/<image_id>/masks/registry.json) and
    becomes a first-class object the agent can reference across
    multiple subsequent apply_primitive calls.

    For one-shot apply (no reuse), prefer apply_primitive's inline
    mask_spec — it skips the registry write.
    """
```

`make_mask` writes to the per-image mask registry (the same one already used for the 4 pre-baked mask-bound entries). Mask ids are per-image and stable across the session — the agent can reference `mask_id=7` in 5 apply calls and they all bind to the same mask.

### 2. Add `mask_id` to `apply_primitive`

```python
apply_primitive(
    image_id="DSCF1234",
    primitive_name="exposure",
    value=0.5,
    mask_id=7,             # NEW — reference a mask built via make_mask
)
```

Mutually exclusive with inline `mask_spec`. If both are passed, fail with `INVALID_INPUT`. Exactly one mask source per call.

The dispatch precedence becomes:

1. Caller-supplied `mask_id` (explicit reference; highest priority)
2. Caller-supplied `mask_spec` (explicit inline; per ADR-076's existing override semantics)
3. Entry's manifest `mask_spec` (default; lowest priority)

### 3. Add `path` to the spec enum

The `_MASK_SPEC_SCHEMA` enum gains `"path"`:

```python
"dt_form": {
    "type": "string",
    "enum": ["gradient", "ellipse", "rectangle", "path"],  # +path (RFC-026 substrate)
    ...
}
```

The `dt_params` for path is `{vertices: [[x, y], ...], border: float}` matching `build_path_form`. This unblocks RFC-026's apply-time use of polygon masks.

### 4. Compose with RFC-024 (parametric) and RFC-026 (AI)

When RFC-024 lands parametric mask kinds (`color_range`, `luminance_range`), they slot into the same surface. The `mask_spec` schema gains a `kind` discriminator:

```python
# Drawn (today)
{"kind": "drawn", "dt_form": "gradient", "dt_params": {...}}

# Parametric (RFC-024)
{"kind": "parametric_color_range", "dt_params": {hue_min: 200, hue_max: 240}}

# AI subject (RFC-026)
{"kind": "ai_subject", "query": "person face"}

# Compositional (RFC-024 + RFC-026 + drawn together)
{"kind": "compose", "op": "intersect", "operands": [
    {"kind": "ai_subject", "query": "fish"},
    {"kind": "drawn", "dt_form": "rectangle", "dt_params": {x0: 0.1, y0: 0.3, x1: 0.9, y1: 0.7}}
]}
```

`make_mask` resolves the spec at construction time — calls the AI provider, computes the parametric mask byte representation, etc. — and stores the resolved mask form bytes in the registry. From the apply path's perspective, every mask is a `mask_id` pointing at darktable-readable bytes.

### 5. Natural-language ↔ parameter mapping doc

Ship `docs/guides/mask-shapes-from-words.md` documenting the spatial vocabulary the agent translates from. Examples:

| Phrase | Shape | Parameters |
|-|-|-|
| "Bottom third" | rectangle | `x0=0, y0=0.67, x1=1, y1=1` |
| "Bottom third (smooth)" | gradient | `anchor_y=0.67, rotation=0, state=sigmoidal` |
| "Top half" | rectangle | `x0=0, y0=0, x1=1, y1=0.5` |
| "Center circle, small" | ellipse | `center_x=0.5, center_y=0.5, radius_x=0.15, radius_y=0.15` |
| "Subject in upper-left rule-of-thirds" | ellipse | `center_x=0.33, center_y=0.33, radius_x=0.2, radius_y=0.2` |
| "Diagonal split, top-left dim" | gradient | `anchor_x=0.5, anchor_y=0.5, rotation=135` |

The doc lives in `docs/guides/` so the agent prompt's tool description can reference it for grounding. The LLM does the actual translation; the doc just gives it a standard vocabulary so different sessions produce consistent mask choices.

## Alternatives considered

### Alt 1: Inline-only (Path A); skip `make_mask`

Considered seriously. The wire already supports inline `mask_spec`; ADR-033's narrow-surface principle argues against adding tools when the existing surface suffices. Rejected because:

1. **Mask reuse is a real workflow.** Lightroom's mask-as-object is the dominant mental model among photographers; same-mask-multiple-adjustments is how portrait/landscape edits actually flow.
2. **AI masks (RFC-026) need an id surface.** Re-running `detect_subjects` for every apply call would be expensive (model inference happens twice) and stateless — the agent wants to say "the subject I detected three turns ago, apply this through it."
3. **Iterative refinement.** Path A makes "nudge the mask slightly" hard — every primitive must be re-issued. Path B lets the mask be edited in place.

The narrow-surface budget cost (one extra tool) is justified by the workflow value.

### Alt 2: Mask-as-vocabulary-entry (no new tool; expand the manifest)

Considered. Pre-bake every named mask shape as a manifest entry: `mask_bottom_third`, `mask_top_half`, `mask_center_small`, etc. Maybe 20–30 named shapes plus a recipe DSL for combining them.

Rejected. (1) Vocabulary explosion: we already shipped the lesson that bloating the manifest with mechanical cross-products costs more than it gains. (2) Doesn't handle AI masks (the polygon is per-image, not a vocabulary entry). (3) Doesn't handle iterative refinement — every nudge becomes a new manifest entry.

### Alt 3: Make `mask_spec` always carry an opacity/blend operator

Considered as part of this RFC's scope. Lightroom masks have blend operators (add / subtract / intersect with other masks). Rejected as scope creep — RFC-024 already proposes a `compose` discriminator for this; deferring the multi-mask composition algebra to that RFC keeps RFC-029 focused on the per-mask surface.

### Alt 4: Defer until RFC-026 lands the AI provider

Tempting because (5) compositional with AI is the highest-value use case. Rejected because the inline `mask_spec` wire already ships and is undocumented — leaving it that way risks the agent never discovering it. RFC-029 lands the framing now; RFC-026's AI integration slots in cleanly when it ships.

## Trade-offs

- **One more MCP tool.** ADR-033's narrow-surface principle takes a small hit. Mitigation: `make_mask` is genuinely the only new tool; the rest of this RFC is schema additions and documentation.
- **Mask registry state.** Per-image mask ids persist across the session; the registry has to handle GC (when does an unused mask get removed?), versioning (does mask state snapshot like edit state?), and concurrent access. The existing 4 mask-bound entries already use the registry, so most of the infrastructure is there — but the semantics under heavier reuse need codification.
- **Two paths to do the same thing.** Inline `mask_spec` and `mask_id` are both valid; the agent has to pick. Mitigation: tool description guides — "prefer `mask_id` if you'll reference this mask again; prefer inline for one-shot." Documentation cost is real but bounded.
- **Natural-language doc rots.** The mask-shapes-from-words guide can drift from the actual parameter semantics if the underlying encoder changes. Mitigation: lint script that round-trips example phrases through `build_form_from_spec` to verify the params are valid.

## Open questions

1. **Mask GC policy.** When does an unused `mask_id` get removed from the registry? On session close? On image close? Never (forever-persistent)? The 4 existing entries don't stress this because they're synthesized fresh each apply.
2. **Mask versioning.** Does editing a mask (via a future `update_mask` tool) snapshot the same way edit state does? Or are masks first-class but not history-tracked?
3. **Cross-image mask reuse.** Lightroom doesn't do this (masks are per-image), and ADR-076 is explicit about per-image scope. Confirm: this RFC keeps that constraint.
4. **`mask_id` lifecycle.** If `apply_primitive` is called with `mask_id=99` and 99 doesn't exist (or was GC'd), is the error `INVALID_INPUT` or a softer fallback? Recommendation: hard fail; the agent must construct masks before referencing them.
5. **Compositional schema lock-in.** RFC-029 and RFC-024 both touch the `mask_spec` `kind` discriminator. Coordinate the schema design so they don't diverge — likely RFC-024 gets the first ADR closure and RFC-029 inherits the schema, or vice versa.
6. **Performance of resolved-bytes-in-registry.** For an AI mask with 500 vertices, the resolved bytes are ~18KB. Storing N masks per image at 18KB each is fine; storing 1000 masks per image is not. A registry size cap is probably needed; TBD.

## How this closes

Likely two ADRs:

- **ADR-NNN — Apply-time mask spec semantics + `path` shape addition.** Settles the dispatch precedence (`mask_id` > `mask_spec` > manifest), adds `path` to the apply-time schema enum, codifies that inline and id-referenced masks are mutually exclusive per call. Small ADR; lands first.
- **ADR-NNN — `make_mask` tool surface and per-image mask registry semantics.** Settles the new MCP tool's contract, registry shape, GC policy, lifecycle. Larger ADR; depends on the schema shape from the previous one.

Possibly a third ADR for the natural-language ↔ parameters guide if it grows beyond a docs page into actual schema constraints.

## Links

- TA/components/masking
- TA/contracts/mcp-tools
- TA/constraints/agent-only-writer
- ADR-076 (drawn-mask only architecture; the wire this RFC builds on)
- ADR-033 (narrow MCP tool surface; the constraint this RFC stretches)
- RFC-021 / ADR-077..080 (parameterized vocabulary; the primitives composed with masks)
- RFC-024 (range masks; the parametric mask source that composes here)
- RFC-026 (AI mask provider scaffolding; the AI mask source that composes here)
- capability-survey.md § 7 (local adjustments — Lightroom-mask-parity tracking)
