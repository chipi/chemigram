# RFC-029 — Compositional masks at apply time (build-by-words)

> Status · Decided
> TA anchor · /components/masking · /contracts/mcp-tools · /constraints/agent-only-writer
> Related · ADR-076 (drawn-mask only architecture; this RFC formalizes the apply-time surface), ADR-033 (narrow MCP tool surface; this RFC respects it without expansion), RFC-021 / ADR-077..080 (parameterized vocabulary; the primitives this composes with), RFC-024 (range masks; parametric source — schema integration noted), RFC-026 (AI mask provider scaffolding; AI source — caching responsibility delegated there)
> Closes into · ADR-084 (apply-time mask spec semantics + path-shape addition + natural-language docs)
> Why this is an RFC · The drawn-mask wire is fully shipped: `apply_primitive` already accepts an inline `mask_spec` argument (`vocab_edit.py:319`) that overrides any manifest mask, and `apply_with_drawn_mask` (`helpers.py:355`) hashes the spec into a deterministic `mask_id` that auto-collides for identical specs across calls. The capability is undocumented and undiscoverable, the schema enum still excludes the `path` shape RFC-026's substrate added, and there's no agent-facing vocabulary for "make me a mask covering the bottom third." The genuinely open question this RFC argued was whether **first-class mask ids** (`make_mask` → `mask_id` reused across N edits, Lightroom-style) earn their place on the MCP surface, or whether inline-only is enough. The answer below is **inline-only is enough**, justified by the deterministic-hashing property already in the wire — but reaching that answer required deliberation, hence the RFC.

## The question

Today, an agent applying an edit through a drawn mask has two choices:

1. **Pre-baked vocabulary entry.** Pick a manifest entry whose `mask_spec` is wired into the manifest (e.g., `gradient_top_dampen_highlights`). 4 such entries ship.
2. **Inline override.** Call `apply_primitive(name, value, mask_spec={...})` with a constructed spec. Wire shipped, no agent-facing pattern documented, and the schema enum is missing `path` (RFC-026's substrate).

Neither pattern is well-positioned for the **build-by-words** workflow: photographer says "lift the bottom third," agent translates the spatial English into a `mask_spec` and applies. And neither obviously handles **mask reuse**: same mask, N edits through it.

Two architectural shapes were on the table:

- **Path A — inline-only.** Every `apply_primitive` carries its own `mask_spec`. Reuse means agent re-issues the same dict.
- **Path B — first-class mask ids.** `make_mask(...)` returns a `mask_id`; `apply_primitive(..., mask_id=X)` references it. Lightroom's mask-as-object model.

Path B looked obviously better — until reading the existing code revealed that `mask_id` is already deterministic from the spec (`apply_with_drawn_mask:355`, blake2b hash with high bit set to avoid colliding with darktable's natural id allocation). **Two apply calls with identical specs produce identical mask_ids in darktable's masks_history**, which means same-mask-multiple-edits already works without any new tool. The agent just sends the same dict twice. The "reuse" workflow Path B was built to serve is already free.

That collapses the question. Path A is sufficient. Path B's only remaining justification is AI-mask caching (re-running `detect_subjects` per apply is wasteful), but that's RFC-026's concern — its provider can cache by `(provider, model, query)` without RFC-029 needing a registry.

## Use cases

1. **"Lift the bottom third by half a stop."** Agent translates "bottom third" into `{dt_form: "gradient", dt_params: {anchor_y: 0.67, rotation: 0, state: sigmoidal}}` and calls `apply_primitive("exposure", 0.5, mask_spec={...})`. One call. No vocabulary entry needed.

2. **"Same mask, three edits."** Agent constructs the gradient spec once, passes it to three `apply_primitive` calls (exposure, shadows, clarity). Deterministic hashing means all three bind to the same `mask_id` in darktable's masks_history. No new tool; no agent-side state; the deduplication is free.

3. **"Hand-drawn rectangle, dim the letterbox bands."** Cinematic effect: top 10% + bottom 10% darkened. Two rectangle specs (one per band), two apply calls (or one apply per primitive band). Each band gets its own deterministic mask_id; both coexist in masks_history.

4. **"Polygon from AI subject detection."** Agent calls `detect_subjects` (RFC-026), receives a polygon, packages it as `{dt_form: "path", dt_params: {vertices: [...], border: 0.05}}`, applies primitives through it. RFC-026 owns the caching of the detection result; RFC-029 just needs `path` in the schema enum.

5. **Iterative refinement.** Agent tries `anchor_y=0.67`, photographer says "lower," agent retries with `anchor_y=0.55`. Each retry is a fresh apply_primitive call with the new spec. Snapshots accumulate per ADR-018; the agent can branch off the previous attempt or layer on top.

## Goals

- **Document the inline `mask_spec` path** at the apply surface so the agent can discover it. Today's gap is purely visibility, not capability.
- **Add `"path"` to the apply-time schema enum.** RFC-026's substrate (commit 54bdcdd) shipped `build_path_form` and the dispatcher. The `_MASK_SPEC_SCHEMA` enum still lists `[gradient, ellipse, rectangle]`. Trivial fix.
- **Document the natural-language ↔ parameter mapping.** Ship `docs/guides/mask-shapes-from-words.md` with a stable spatial vocabulary the agent can lean on across sessions.
- **Stay within ADR-033's narrow MCP surface.** No new tools.

## Constraints

- **ADR-076** (drawn-mask only architecture): mask specs serialize through `build_form_from_spec` → bytes darktable consumes. Already shipped.
- **ADR-033** (narrow MCP tool surface): adding tools requires an ADR. RFC-029 deliberately adds none.
- **CLAUDE.md three foundational disciplines**: agent-only-writer (mask construction is a tool call argument); darktable-does-the-photography (mask math runs in darktable); BYOA (AI sources via MCP providers per RFC-026, with caching responsibility there).
- **Backward compatibility**: existing pre-baked vocabulary entries with manifest `mask_spec` continue to work. Inline `mask_spec` already overrides the manifest one. Whatever this RFC formalizes preserves both.

## Decision

**Inline-only (Path A).** No new MCP tool. Three concrete changes:

### 1. Add `"path"` to the apply-time schema enum

`_MASK_SPEC_SCHEMA["dt_form"]["enum"]` gains `"path"`:

```python
"enum": ["gradient", "ellipse", "rectangle", "path"]
```

`dt_params` for path is `{vertices: [[x, y], ...], border: float}` matching `build_path_form`. This unblocks RFC-026's apply-time use of polygon masks and enables programmatic / human-supplied polygons today.

### 2. Sharpen the `apply_primitive.mask_spec` description

The current tool description mentions `mask_spec` overrides the manifest one. It does not say "use this to construct masks at apply time from spatial English" — which is the workflow this RFC is naming. Update the description to reference the new docs guide and call out the build-by-words pattern explicitly.

### 3. Ship `docs/guides/mask-shapes-from-words.md`

A stable spatial vocabulary the agent translates from. Examples table covering top/bottom/left/right halves and thirds, center circles at common rule-of-thirds positions, diagonal gradients, plus shape-vs-feathering ("rectangle for hard edges, gradient for smooth transitions"). The LLM does the translation; the doc gives it consistent grounding so different sessions produce coherent mask choices.

### Why no `make_mask` tool

Path B's rationale was reuse: same mask, N edits. **The deterministic hash in `apply_with_drawn_mask` already provides this.** Two apply calls with identical `mask_spec` dicts produce identical `mask_id`s in darktable's `masks_history`. The "reuse" tool would be solving a problem the wire already solves implicitly. ADR-033's narrow-surface principle wins by default — no tool needed.

The remaining valid case for Path B was AI-mask caching (re-running detection per apply). That's RFC-026's concern; its `detect_subjects` provider can cache `(image_id, provider, model, query) → polygon` without needing a generic mask registry on the chemigram side. RFC-026 will return polygon vertices the agent passes inline; the caching layer lives in the provider or in a thin chemigram-side cache scoped to RFC-026's tools.

## Alternatives considered

### Alt 1: First-class mask ids with `make_mask` (Path B)

Considered seriously, drafted in v0.1 of this RFC. Rejected after reading the existing code:

1. **Reuse already works.** Deterministic hash → same spec → same `mask_id`. No registry needed for the workflow Path B was justified by.
2. **Narrow-surface cost.** ADR-033 makes new tools expensive. The bar is "this can't be expressed without a tool"; Path B fails it.
3. **AI-mask caching is not RFC-029's job.** RFC-026 owns the polygon-cache lifecycle; surfacing a generic mask registry now would couple the two RFCs unnecessarily.
4. **Iterative refinement.** "Nudge the mask" is not actually easier with mask ids than with inline — the photographer is iterating on the spec dict either way; the difference is whether the agent says "update mask 7" or "apply with new spec," and the latter is no harder.

### Alt 2: Mask-as-vocabulary-entry (pre-bake every named shape)

Considered. Add 20–30 manifest entries: `mask_bottom_third`, `mask_top_half`, `mask_center_small`, etc.

Rejected. (1) Manifest bloat — we shipped the lesson with cinematic-look composition that mechanical cross-products cost more than they yield. (2) Doesn't handle AI masks (per-image, not vocabulary). (3) "What about the bottom 28%?" — any pre-baked set excludes the next photographer's intent.

### Alt 3: Defer until RFC-024 or RFC-026 lands

Tempting because the unified compositional surface (drawn + parametric + AI) is the long-term shape. Rejected because the inline `mask_spec` capability already ships and is invisible. Documenting it now lets photographers use the build-by-words workflow today without waiting on RFC-024 / RFC-026 implementation.

### Alt 4: Add a `compose` discriminator to `mask_spec`

Considered. RFC-024's draft proposed a `kind: "compose"` for AND/OR/SUBTRACT of mask operands. RFC-029 considered absorbing it.

Rejected as scope creep. The compositional algebra is genuinely RFC-024's territory (it's where parametric+drawn composition becomes load-bearing). RFC-029 is the per-mask surface; RFC-024 + RFC-026 will codify the multi-mask algebra when they close. Schema additions stay forward-compatible: `dt_form` is one of `[gradient, ellipse, rectangle, path]` today; a future `kind` field can layer above without breaking existing specs.

## Trade-offs

- **Inline-only means the agent re-sends mask specs.** A per-apply call carries the full `mask_spec` dict. For multi-step edits this is some token overhead in the conversation. Mitigation: spec dicts are small (~100 bytes); the deterministic-id property means deduplication happens server-side; the workflow doesn't actually feel different to the photographer.
- **No mask history.** Mask state is per-apply, not snapshotted as a first-class object. If a photographer wants to recover "the gradient I used three sessions ago," they read it back from the snapshot's masks_history XML. Acceptable; matches the per-image-repo invariant.
- **Documentation rot.** The `mask-shapes-from-words.md` guide can drift from the actual parameter semantics if the encoder changes. Mitigation: lint script that round-trips example phrases through `build_form_from_spec` to verify the params parse cleanly. Lands as part of the closing ADR.

## Open questions resolved during deliberation

1. ~~First-class mask ids vs inline-only.~~ → **Inline-only.** Deterministic hashing makes the reuse case free.
2. ~~Mask GC policy.~~ → **N/A.** No registry, no GC. Masks are per-apply.
3. ~~Mask versioning / history-tracking.~~ → **No.** Masks aren't first-class objects; their state lives inside snapshotted XMPs.
4. ~~Cross-image mask reuse.~~ → **Not in scope.** Per-image scope is preserved (consistent with ADR-076).
5. ~~AI-mask caching surface.~~ → **RFC-026's concern**, not RFC-029's. Decoupled cleanly.
6. ~~Compositional mask algebra (AND/OR/SUBTRACT).~~ → **RFC-024's concern.** RFC-029's schema stays forward-compatible.

## How this closes

One ADR closes the work — **ADR-084 — Apply-time mask spec semantics + path shape addition**. Settles:

- The inline-`mask_spec` apply-time path is the canonical agent-facing build-by-words surface.
- The `dt_form` enum adds `"path"`; `dt_params` schema for path is `{vertices, border}`.
- `mask_spec` precedence is unchanged: caller-supplied overrides manifest (per ADR-076).
- `make_mask` and first-class mask ids are explicitly out of scope; reuse is via deterministic hashing.
- A `docs/guides/mask-shapes-from-words.md` ships alongside the code change as the agent's spatial-vocabulary reference.
- Lint script that round-trips guide examples through `build_form_from_spec` ships in `tests/unit/docs/`.

## Links

- TA/components/masking
- TA/contracts/mcp-tools
- TA/constraints/agent-only-writer
- ADR-076 (drawn-mask only architecture)
- ADR-033 (narrow MCP tool surface)
- ADR-077..080 (parameterized vocabulary; primitives composed with masks)
- RFC-024 (range masks; multi-mask compositional algebra owned there)
- RFC-026 (AI mask provider scaffolding; AI-mask caching owned there)
- `src/chemigram/core/masking/dt_serialize.py` (mask wire)
- `src/chemigram/core/helpers.py` (apply_with_drawn_mask, deterministic hashing logic at line 355)
- `src/chemigram/mcp/tools/vocab_edit.py` (apply_primitive surface)
