# ADR-084 — Apply-time mask spec semantics + path shape addition

> Status · Accepted
> Date · 2026-05-08
> TA anchor · /components/masking · /contracts/mcp-tools
> Related RFC · RFC-029 (compositional masks at apply time)

## Context

`apply_primitive` already accepts an inline `mask_spec` argument (`vocab_edit.py:319`) that overrides any manifest mask. `apply_with_drawn_mask` (`helpers.py:355`) hashes the spec into a deterministic `mask_id` so identical specs across separate apply calls bind to the same mask in darktable's `masks_history`. RFC-026's foundation commit (54bdcdd) added `build_path_form` and the `dt_form: "path"` dispatcher branch but did not extend the apply-time schema enum. RFC-029 deliberated whether first-class mask ids (`make_mask` → reusable handle) earn their place on the MCP surface; the answer is no, because deterministic hashing already provides reuse implicitly. Full deliberation in RFC-029.

## Decision

Adopt **inline-only mask construction** as the canonical agent-facing build-by-words surface, with three concrete changes:

1. **Add `"path"` to the apply-time `_MASK_SPEC_SCHEMA["dt_form"]["enum"]`.** `dt_params` for path is `{vertices: [[x, y], ...], border: float}` matching `build_path_form`. The wire was shipped in commit 54bdcdd; this lands the schema gate.

2. **Sharpen the `apply_primitive.mask_spec` tool description** to name the build-by-words workflow explicitly and link to the new docs guide. The capability was always there; this makes it discoverable.

3. **Ship `docs/guides/mask-shapes-from-words.md`** as a stable spatial vocabulary the agent translates from. Examples for top/bottom/left/right halves and thirds, center circles at rule-of-thirds positions, diagonal gradients, plus shape-vs-feathering guidance. A lint test in `tests/unit/docs/` round-trips the guide's example specs through `build_form_from_spec` to prevent rot.

`make_mask` and first-class mask ids are explicitly out of scope. Mask reuse across multiple `apply_primitive` calls works today via deterministic hashing — agent sends the same `mask_spec` dict twice, both apply calls bind to the same `mask_id` in darktable. No new MCP tool needed; ADR-033's narrow-surface principle is preserved.

## Rationale

The sharpest argument for `make_mask` was the same-mask-N-edits Lightroom workflow (mask-as-object, multiple adjustments through it). Reading the existing wire revealed the `mask_id` is already a deterministic blake2b hash of the spec, with the high bit set to avoid colliding with darktable's natural id allocation. Two apply calls with byte-identical `mask_spec` dicts produce byte-identical `mask_id`s and byte-identical `masks_history` form bytes. The deduplication is free; the tool would be solving a non-problem.

The remaining justification — caching expensive AI-mask detection so the agent doesn't re-run inference per apply — is RFC-026's concern. RFC-026's `detect_subjects` provider can cache `(image_id, provider, model, query) → polygon` without surfacing a generic mask registry to chemigram core. Coupling the two RFCs would force RFC-029 to ship registry infrastructure RFC-026 may not actually need (its provider may cache differently).

The `"path"` schema gate is uncontroversial — the encoder shipped, the dispatcher routes it, the integration tests pass; the schema enum was the only thing blocking apply-time use of polygon masks. Adding it is a 1-line change.

The natural-language docs guide is the load-bearing user-value piece. The capability has been live in the tool surface since v1.5.0 and never used in a session because no one (agent or photographer) knew it was there. Documenting "bottom third" → `gradient(anchor_y=0.67, rotation=0)` in a stable place gives the agent grounding so different sessions produce coherent mask choices instead of trial-and-error.

## Alternatives considered

- **First-class mask ids via `make_mask` (RFC-029 Path B).** Rejected — the deterministic-hashing property in `apply_with_drawn_mask` already provides the reuse semantics Path B was justified by.
- **Mask-as-vocabulary-entry (pre-bake `mask_bottom_third`, etc.).** Rejected — vocabulary bloat from mechanical cross-products; doesn't handle AI masks; the next photographer's "bottom 28%" is excluded by any pre-baked set.
- **Defer until RFC-024 / RFC-026 lands.** Rejected — the inline `mask_spec` capability already ships and is invisible. Documenting it now unlocks build-by-words for photographers without waiting on parametric / AI work.
- **Add a `compose` discriminator to `mask_spec` (multi-mask AND/OR/SUBTRACT algebra).** Rejected as scope creep — RFC-024 owns the compositional-mask algebra. RFC-029's schema additions stay forward-compatible: the future `kind` discriminator can layer above the existing `dt_form` field.

## Consequences

Positive:

- **Build-by-words workflow becomes discoverable.** Agent can construct any drawn mask from spatial English without needing a pre-baked vocabulary entry. Closes a v1.5.0 capability that was effectively dead.
- **Path shape unblocked at apply time.** RFC-026's polygon-output integration has a clear schema target; AI subject masks flow through the same surface as drawn masks.
- **MCP surface stays narrow.** No new tool. ADR-033 is preserved.
- **Mask reuse works for free** via deterministic hashing — same spec in N apply calls = same `mask_id` in masks_history.

Negative:

- **Per-apply call carries the full `mask_spec` dict.** Some token overhead in agent conversation for multi-edit-same-mask flows. Acceptable; specs are ~100 bytes.
- **No mask history as a first-class object.** Photographer who wants "the gradient I used three sessions ago" reads it back from the snapshot's `masks_history` XML. Matches the per-image-repo invariant.
- **Documentation can rot.** Mitigated by the lint test that round-trips guide examples through the encoder. If the encoder's parameter names change, the lint fails and forces the doc to update.

## Implementation notes

- `_MASK_SPEC_SCHEMA["dt_form"]["enum"]` extended to `["gradient", "ellipse", "rectangle", "path"]` in `src/chemigram/mcp/tools/vocab_edit.py`.
- `dt_params` description updated to point at `docs/guides/mask-shapes-from-words.md`.
- `apply_primitive` tool description gains a one-line callout: *"For build-by-words mask construction (e.g., 'bottom third'), pass `mask_spec` inline; see `docs/guides/mask-shapes-from-words.md` for the spatial-vocabulary mapping."*
- Docs guide `docs/guides/mask-shapes-from-words.md` created.
- Lint test in `tests/unit/docs/test_mask_shapes_guide.py` parses example specs from the guide and round-trips them through `build_form_from_spec`.
- No changes to `apply_with_drawn_mask` — the deterministic-hashing logic is the load-bearing existing behavior this ADR formalizes.
- No changes to `apply_entry` — its `mask_spec` argument shape is already what the apply-time path needs.

The substrate (path encoder, dispatcher) shipped in commit 54bdcdd. This ADR closes the agent-facing surface.
