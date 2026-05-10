# RFC-035 — Parametric L2 strength (opacity-as-amount)

> Status · Decided (Path B; impl shipped 2026-05-10; ADR-088 stays Draft until darkroom validation)
> TA anchor · /components/synthesizer · /contracts/vocabulary-manifest
> Related · RFC-021 (parameterized vocabulary / ADR-077..080), RFC-022 (bulk parameterization / ADR-081), RFC-018 (vocabulary expansion / ADR-063)
> Closes into · ADR-088 (closes; flips to Accepted on darkroom-session sign-off)
> Why this is an RFC · L2 looks today ship as fixed-value composites — `look_landscape_dramatic_moody` has sigmoid contrast 1.7, full saturation grade, full clarity bite, all baked. There's no shorthand for "this look at 50% strength." Three real options: (a) author intensity ladders (`_subtle` / `_medium` / `_strong` per look), (b) parameterize via per-plugin opacity scaling, (c) parameterize via composition-level parameters that scale all touches. Each costs differently in vocabulary surface, authoring effort, and agent reasoning load. The right answer is genuinely not obvious — and depends on what the darkroom-session findings show about whether the fixed-value defaults are *usually right* or *usually need scaling*.

## The question

Across the 17 existing L2 looks plus the 14 survey-derived looks shipped this round, every one is a fixed-value composite. The agent reaches for `look_landscape_dramatic_moody` and gets sigmoid contrast 1.7 + cool-shadow grade + clarity 0.6 — full strength. There's no surface for "this look but more subtle" or "this look but stronger."

Today's workarounds:

1. **Apply the look, then apply a counter-primitive at the right magnitude** — e.g., apply `look_landscape_dramatic_moody`, then apply `sigmoid_contrast` with a value that scales the contrast back. Verbose; doesn't compose cleanly with the look's other plugins.
2. **Author multiple intensity variants** — `look_landscape_dramatic_moody_subtle` / `_medium` / `_strong`. Triples the catalogue size. RFC-021 explicitly collapsed discrete-magnitude entries into parameterized ones for primitives; doing the opposite at the L2 layer would be inconsistent.
3. **Mask the look with a partial-opacity blend** — apply via `apply_with_mask` with a feathered mask covering the whole image at, say, 50% opacity. Works, but conflates "strength" with "spatial coverage" — opacity is also the lever for per-region masks.

The genuinely-open question: **what's the right shape for a parametric strength on an L2 look that doesn't break composition with masks, doesn't multiply the catalogue, and stays consistent with RFC-021's "parameterized magnitudes" discipline?**

## Use cases

- **Subtle vs. strong rendering of a same-named look** — "apply `look_landscape_dramatic_moody` at 50%" produces a softer dramatic mood without authoring a separate variant. The agent can dial.
- **Scene-adaptive composition** — a moody look at full strength on a stormy scene, the same look at 30% strength on a calmer scene. Same vocabulary, agent-controlled magnitude.
- **Apply-and-blend workflows** — the photographer renders both a 100% and a 50% variant, picks their preferred. The look's intent is preserved at any strength; only the magnitude varies.

## Goals

1. **One named L2 look = one entry, with a `strength` parameter** — same shape as RFC-021's parametric primitives.
2. **Strength=1.0 is the current fixed-value behavior** — no behavior change for un-parameterized callers.
3. **Strength scales monotonically** — strength=0.0 is no-op (no plugins touch the image), strength=0.5 is roughly half-effect, strength=1.0 is full effect.
4. **Doesn't break mask composition** — applying a parametric L2 look + named mask still works (the strength scales the *effect*, the mask scopes the *region*).
5. **No surface explosion** — adding a `strength` parameter to all 31 L2 looks must not require re-authoring each one's dtstyle.

## Constraints

- **TA/components/synthesizer** — opacity blend is what darktable provides at the plugin level (`blendop_params`). Strength would route through that mechanism.
- **TA/contracts/vocabulary-manifest** — the `parameters` array is the existing shape for parameterization. L2 looks adding parameters fits the existing schema.
- **ADR-051 (same-module collision)** — same-op stacking is keyed on `(operation, multi_priority)`. Strength scaling per L2 look must not collide with masked instance stacking from `apply_per_region`.
- **darktable plugin opacity is per-plugin, not per-style** — there's no "this entire style at 50% opacity" knob in darktable. We have to scale each plugin's opacity individually.

## Proposed approach (one of three; sketched, not chosen)

### Path A — Per-plugin opacity scaling at synthesis time

Add a single `strength` parameter to L2 look manifests. At apply time, the synthesizer scales each plugin's `blendop_params` opacity field by `strength`. Strength=0.5 → every plugin at opacity 50; strength=1.0 → every plugin at opacity 100 (current behavior); strength=0.0 → every plugin at opacity 0 (effectively no-op since opacity-0 plugins don't render but do appear in history).

**Pros:** No re-authoring of dtstyle files (the strength is applied at synthesis, not stored). Works uniformly across all 31 existing L2 looks once the synthesizer change lands. Composes with masks (strength is the global blend, mask is the spatial scope).

**Cons:** Linear opacity scaling is not always perceptually linear. At strength=0.3, some moves (sigmoid contrast) feel weaker than 30%; others (color grading) feel stronger. The magnitude semantics drift across plugin types.

### Path B — Per-parameter strength scaling at synthesis time

Add `strength` to L2 manifests, but instead of opacity blending, **interpolate every plugin's parameterized field** between baseline and the look's authored value. Sigmoid contrast goes from 1.0 (baseline) → 1.7 (look) at strength=1.0; at strength=0.5 it's 1.35.

**Pros:** Perceptually closer to "this look at half strength" — interpolation in parameter space is more linear than opacity blending. Each plugin's effect is dialed at the right level instead of dimmed wholesale.

**Cons:** Requires every L2 look to know the *baseline* value of each parameter (the no-op identity point). For some plugins this is obvious (sigmoid_contrast=1.0, exposure=0.0); for others it's not (colorbalancergb hue is a 360-degree wheel; "interpolate halfway" requires picking which direction). Heavy authoring burden if the manifest has to declare baselines per parameter per look.

### Path C — Hybrid: per-plugin opacity for non-parameterized plugins, parameter interpolation for parameterized ones

Combine A and B: parameters that have a known identity (per RFC-021/RFC-022's parameterize registry) interpolate from identity; everything else dims via opacity. Single `strength` parameter, mixed routing under the hood.

**Pros:** Best perceptual linearity for parameterized plugins; falls back to opacity for plugins where parameter-space interpolation isn't well-defined.

**Cons:** Most complex of the three. The mixed routing is harder to reason about; the agent's mental model has to know which plugins do which.

## Alternatives considered

**Author intensity ladders (`_subtle` / `_medium` / `_strong` per look) — Path D.** Rejected as the *primary* answer because it triples the catalogue surface. But it's a reasonable *fallback* if Paths A/B/C all fail visual review — discrete intensity variants are coarser but well-understood.

**Apply at full strength then crossfade with the baseline** (render two versions, blend in pixel space). Rejected because it requires post-render pixel manipulation that violates the "darktable does the photography" line. Could be done as a sibling tool / RFC eventually, but not v1 in core.

**Strength via opacity at the apply-time mask level** (apply the entire L2 look through a parametric opacity-blend "mask" at strength%). Possible but conflates strength with masking — the photographer can no longer apply at strength + a real mask without nesting. Rejected.

**Per-look custom `strength` curves** (each L2 look declares how strength maps to per-plugin scaling). Most flexible but also most authoring-heavy — every look becomes a small DSL. Considered as future work if A/B/C prove insufficient.

## Trade-offs

- **Paths A/B/C all require synthesizer changes.** Not just manifest schema. Path A is the smallest synthesizer change (apply opacity multiplier to all plugins); Path B is medium (interpolate parameters); Path C is largest (mixed routing).
- **Cataloguing every L2 look's parameter baseline** (Path B/C requirement) is a one-time cost but a real one. ~31 looks × 2-4 parameters per look = ~60-120 baseline declarations.
- **Visual quality is the open question.** Path A is the "easy 80%" — does opacity scaling produce results photographers find usable? If yes, ship it; iterate to B/C only if needed.

## Open questions

1. **Should `strength` be a single parameter, or multi-axis?** A single `strength` is simpler but a `strength_contrast` / `strength_color` / `strength_clarity` triple lets photographers dial the look's facets independently. RFC-021 went multi-axis for parameterized primitives (`hsl_saturation` exposes per-color sat); the same convention argues for multi-axis here. But the dominant case "this look at 50%" is well-served by a single axis.
2. **Default value.** Strength=1.0 (current behavior preserved) or strength=0.5 (force the agent to opt-in to full strength)? Probably 1.0 for backwards compat, but worth deliberating.
3. **How does this interact with `apply_per_region`?** A batched call applying a parametric L2 look across N regions could supply strength per region. The architecture should support that without further changes.
4. **What happens at strength=0.0?** Each plugin still appears in history with opacity-0 (Path A) or identity-value parameters (Path B). The XMP carries the entries, darktable renders them as no-op, snapshot reflects the structural fact. Acceptable; matches RFC-021 semantics where parameter=identity is structurally present but visually absent.
5. **Should existing fixed-value L2 looks remain available?** Yes — the parametric variant is additive. Adding a strength parameter is opt-in (manifest declares `parameters`); looks without the declaration ship as fixed-value. No breaking change.

## How this closes

One ADR (likely closing into multiple if Path B/C is chosen):

- **ADR-NNN — Parametric L2 strength schema + synthesizer routing** — formalizes which path won (A/B/C/D), the manifest schema for declaring strength on an L2 look, the synthesizer changes, and the visual-quality boundary observed during validation.

**Decision-checkpoint dependency:** this RFC stays Draft until the darkroom-session findings (per `darkroom-session-debt.md` items 1-3) inform whether the *fixed-value* L2 looks are usually right (in which case parametric strength is a v1.11+ refinement) or usually need scaling (in which case Path A is the v1.10 ship target).

## Links

- TA/components/synthesizer
- TA/contracts/vocabulary-manifest
- Related: RFC-021 / ADR-077..080 (parameterized magnitudes for primitives — same shape extended to L2), RFC-031 (apply_per_region — parametric strength composes per-region)
- Source: RFC-031/032/033 post-batch retro item #1 — surfaced after authoring the 14 L2 looks revealed the fixed-value-only constraint as a real limitation
- Blocker: `docs/guides/darkroom-session-debt.md` items 1-3 — the validation pass informs whether this is a near-term need
