# RFC-034 — `invert` flag on named-mask references

> Status · Draft v0.1
> TA anchor · /components/masking · /contracts/vocabulary-manifest
> Related · RFC-024 (range masks / ADR-085), RFC-029 (compositional masks at apply time / ADR-084), RFC-032 (named-mask vocabulary)
> Closes into · ADR-NNN (pending)
> Why this is an RFC · Tiny surface — three lines of code in the resolver. But the *user-facing semantics* deserve deliberation: should `invert` flip the parametric range_filter's `invert` field, the drawn mask's mask-mode bits, both, or something else? RFC-085 already supports parametric `invert: true`; RFC-029 doesn't have a clean drawn-mask invert. Picking the semantic shape now (instead of "invert means whatever happens to land first") avoids drift.

## The question

The L2 look `look_portrait_background_dim` (shipped this round) requires a caller-supplied mask because chemigram has no shorthand for "invert this named mask." Today the agent has to:

1. Look up the maskdef's `spec` field
2. Manually construct an inverted version of the spec (e.g., `invert: true` on a parametric range_filter)
3. Pass the inverted spec via `--mask-spec`

This is verbose, error-prone (the agent has to know which kind of mask supports `invert` and how), and doesn't compose cleanly with named references in batched calls. The shorthand `{"kind": "named", "name": "mask_subject", "invert": true}` would compress this to one line.

The wire is small. The question is: **what does `invert: true` mean for each mask kind, and is the semantic stable across all five maskdef shapes (parametric, drawn, drawn+parametric, llm-vision, compose)?**

## Use cases

Concretely:

- **`look_portrait_background_dim`** — dim everything *except* the subject. `mask_subject + invert: true`.
- **Inverse-of-sky** — apply to foreground only. `mask_sky + invert: true`.
- **Inverse-of-skin** — apply to non-skin (e.g., background sharpening that protects skin). `mask_skin_region + invert: true`.
- **Inverse luminance bands** — "everything except the brightest 25%" (Page-style inverse-highlight grade). `mask_luminosity_brightest_quartile + invert: true`.

For each of these, the inverted move is a real workflow shape that's currently verbose to express.

## Goals

1. **One-line shorthand** — `{"kind": "named", "name": "mask_X", "invert": true}` resolves correctly.
2. **Stable semantic across mask kinds** — the photographer's mental model ("this maskdef but the inverse region") works the same whether the maskdef is parametric, drawn, or LLM-vision-routed.
3. **No new mask machinery** — RFC-024 / ADR-085 already supports parametric `invert`. The shorthand routes through that wire.
4. **Composable** — mixed batches with `apply_per_region` can have some regions named-and-inverted, others named-and-not, others inline. No special-casing.
5. **Idempotent** — `invert: false` is a no-op (silently); double-inverting via `invert: true` on a maskdef whose spec already has `invert: true` flips back. Less footgun.

## Constraints

- **TA/components/masking** — mask machinery is settled (drawn, parametric, LLM-vision). No new kinds.
- **ADR-085** — parametric range_filter ships with `invert: bool`. The semantic is "the mask is the *complement* of the range".
- **ADR-084** — drawn-mask spec doesn't have an inversion concept at the form level. Inversion is encoded in `masks_history` XML attributes (specifically `inverted="1"`). Possible but not currently exposed in the apply-time spec.
- **ADR-086** — LLM-vision maskdefs ship a parametric fallback (always); the prompt itself is descriptive ("select the sky") and doesn't inherently express "the inverse of the sky" without extra prompt engineering.

## Proposed approach

**Add a single optional `invert: bool` field to the named-mask reference shape, defaulting to false.** The resolver applies inversion at resolution time, not at storage time.

Resolution logic in `chemigram.core.vocab.resolve_named_mask_spec`:

1. If the named-mask reference is `{"kind": "named", "name": "X", "invert": false}` (or no `invert` key) → behave as today: deep-copy and return the maskdef's `spec`.
2. If `{"kind": "named", "name": "X", "invert": true}` → resolve the spec, then **invert the resolved spec in-place** before returning. **v1 scope: parametric inversion only** — toggle `range_filter.invert` (XOR with the existing value).
3. If the maskdef has an `llm_vision_prompt` (content-aware): the parametric fallback inverts as in case 2; the LLM-vision prompt is *not* automatically inverted (would require LLM reasoning at construction time). Document explicitly — the photographer escalating to Pattern 7 of `llm-vision-for-masks.md` constructs the inverse mask by-hand if needed.

**Drawn-only inversion is deferred from v1.** All 9 currently shipped maskdefs carry parametric specs (the LLM-vision-bearing ones have parametric fallbacks; the rest are parametric-only), so v1 covers the entire current catalogue. Drawn-only inversion would require extending `DrawnMaskForm` + `build_masks_history_xml` to flip darktable's `inverted` attribute on each form — modest but real wire work. If a future drawn-only maskdef ships (e.g., `mask_horizon_gradient` graduating from spec to entry), revisit.

**Validation:** the resolver fails loud on drawn-only `invert: true` rather than silently no-op'ing — the user sees the limitation immediately. Drawn + parametric is also v1-rejected for the same reason (would need both halves to invert).

## Alternatives considered

**Inversion at maskdef-author time (separate `mask_subject_inverse` maskdef).** Rejected — doubles the maskdef catalogue (every named mask spawns a `_inverse` variant) and the inverted variant is just `NOT` of the original; no new authoring information. The author-time approach makes sense only when the inverted mask has *different* parametric tuning, which is rare.

**`mask_combine` modifier that takes "and", "or", "not".** A more general operator framing. Rejected for v1 because the dominant case is "just invert this one named mask" — no need for the full algebra surface yet. RFC-029 already supports `compose` operations for multi-mask intersections / unions; extending it to `not` is a separate RFC if demand surfaces.

**Add a CLI flag `--invert-mask` instead of in-spec.** Rejected because it doesn't compose with `apply_per_region` (each region's mask_spec is already a JSON object; an out-of-band CLI flag would have to apply globally or per-region in some other shape — both worse than the inline flag).

**Encode `invert` at the apply-time mask spec level (not the named-reference level).** Already possible for parametric specs (`range_filter.invert: true`). The reason this RFC adds the flag to the *named-reference* shape is so the agent doesn't have to know what kind of mask the named reference resolves to. `mask_sky` may resolve to a parametric or a drawn or both; the agent says "invert this regardless of kind" and the resolver figures out the right wire-level encoding.

## Trade-offs

- **One new wire change in `apply_with_mask`** — drawn-mask inversion (the `invert_drawn` flag). Small surface, contained to the existing `_inject_masks_history_for_drawn` helper. Tests cover.
- **LLM-vision prompts don't auto-invert** — accepted limitation. The construction path through Pattern 7 already has the photographer reasoning about what they want; inverting a constructed mask is the photographer's call. Documented.
- **`invert: true` on a maskdef with already-inverted parametric spec flips back** — XOR semantics. Could surprise an agent that sets `invert: true` thinking "make sure it's inverted" without checking the underlying spec. Mitigated by documentation; matches Boolean convention.

## Open questions

1. **Compose form.** `{"kind": "compose", "operation": "intersect", "operands": [...]}` may contain named references with `invert`. The compose resolver should invoke `resolve_named_mask_spec` on each operand recursively — already implicit but worth documenting in the closing ADR.
2. **Drawn-only `invert_drawn`** — does darktable's `masks_history` `inverted="1"` attribute work on every form (gradient / ellipse / rectangle / path), or only some? Verify before closing the ADR.
3. **Invert-and-named referenced from a different pack.** `mask_sky` from `expressive-baseline` could be inverted in a personal pack's L2 look. The cross-pack resolution rule (load-order wins) should compose naturally — but verify the resolver handles it.

## How this closes

One ADR:

- **ADR-NNN — Inverse-flag shorthand on named-mask references** — formalizes the `invert: true` field on `{"kind": "named", ...}`, the per-kind inversion semantics, the `invert_drawn` wire change in `apply_with_mask`, and the documentation requirement that LLM-vision prompts don't auto-invert.

## Links

- TA/components/masking
- TA/contracts/vocabulary-manifest (named-reference shape extension)
- Related: RFC-032 / pending-ADR (named-mask vocabulary), RFC-024 / ADR-085 (parametric `invert` field), RFC-029 / ADR-084 (compose semantics)
- Consumer: `look_portrait_background_dim` (shipped this round); the missing-mask discipline becomes "use mask_subject + invert: true" once this lands
