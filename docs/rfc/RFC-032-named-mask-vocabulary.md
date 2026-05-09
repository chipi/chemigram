# RFC-032 — Named-mask vocabulary on v1.9.0 mask primitives

> Status · Draft v0.1
> TA anchor · /components/masking · /contracts/vocabulary-manifest · /contracts/mcp-tools
> Related · RFC-024 (range masks / ADR-085), RFC-026 (LLM-vision masking / ADR-086), RFC-029 (compositional masks at apply time / ADR-084), RFC-018 (vocabulary expansion / ADR-063), `docs/photographer-workflows-survey.md`
> Closes into · ADR-NNN (pending; possibly two — see "How this closes")
> Why this is an RFC · The mask machinery is settled — drawn / parametric / LLM-vision are all shipped (v1.9.0). The genuinely open question is what *vocabulary layer* should sit on top: do masks become a first-class vocabulary kind (alongside L1/L2/L3 entries), or do they remain mask-spec JSON snippets carried inside individual entries' manifests? The first is heavier but composes; the second is lighter but every L2 look that wants "the sky" has to inline the same mask spec. This is a discipline question, not a capability question.

## The question

The photographer-workflows survey surfaced "named-mask vocabulary" as the second-highest-recurrence gap (6/12 across portrait + landscape). The pattern is consistent across genres:

- **Heaton** reaches for "the sky" — LR's adaptive sky mask is a one-click named selection.
- **Page** reaches for "the brightest 25%" — Lumenzia ships luminosity-mask bands as named selections.
- **Adamus** reaches for "the foreground" — luminosity-banded inverse-of-sky, again named.
- **Woloszynowicz / Adler / Nordqvist** reach for "the skin region" — Capture One's Skin Tone tool is a named mask + named adjustment surface.
- **Marino** reaches for "the small-scene subject" — implicit in her composition discipline; a content-aware subject selection.
- **Adler** reaches for "the eye region" — repeatedly, across multiple of her workflow steps.

Each photographer thinks in named regions. Their tools surface those regions as named entities. The agent currently composes masks via the v1.9.0 mask-spec language inline (`{"kind": "parametric", "range": "color_h", "band_low": 200, "band_high": 260}`) — this works, but it's:

1. **Verbose at every call site.** Every L2 look that wants "the sky" inlines the same 4-key spec. Drift across copies is inevitable.
2. **Lossy in agent reasoning.** "Apply warm-shadows to mask_sky" is shorter, more composable, and matches photographer language. "Apply warm-shadows to `{"kind": "parametric", "range": "color_h", ...}`" is longer and reads as implementation, not intent.
3. **Discoverability-poor.** A new agent (or new author of an L2 look) doesn't know the canonical band values for "the sky." They guess. Some get it right; some don't.
4. **Doesn't compose with the existing vocabulary discipline.** Chemigram's foundational rule is "vocabulary, not sliders" (PA / 02-project-concept). The mask-spec inline form is a sliders-equivalent for masks — *parameters*, not *named moves*.

The wire is right (RFC-024/026/029 closures shipped this). What's missing is the **vocabulary layer on top** — named masks as first-class composable entities. The question is what shape that layer takes.

## Use cases

The named masks the survey surfaced, ranked by cross-genre recurrence:

| Mask name (proposed) | Backed by | Photographers |
|-|-|-|
| `mask_sky` | LLM-vision (canonical "select the sky region" prompt) + optional parametric refinement on top luminance + blue hue | Heaton, Page, O'Leary, Adamus, Ramelli — 5/6 landscape |
| `mask_subject` | LLM-vision ("select the main subject") + optional parametric refinement | Adler, Tucker, Nace, Marino — implicit across both genres |
| `mask_luminosity_brightest_quartile` | parametric (`luminance` range, top 25%) | Page, Adamus, Heaton — 3/6 landscape, foundational for luminosity-mask compositing |
| `mask_luminosity_darkest_quartile` | parametric (`luminance` range, bottom 25%) | Page, Adamus, Heaton — same |
| `mask_luminosity_midtones` | parametric (`luminance` range, middle 50%) | Page (selective contrast on midtones) |
| `mask_skin_region` | parametric (`color_h` orange/red band scoped to typical skin hue range) — see also RFC-033 | Woloszynowicz, Adler, Nordqvist — 3/6 portrait |
| `mask_eye_region` | LLM-vision ("select the eye region") | Adler — load-bearing for her workflow; specific enough to be its own primitive |
| `mask_foliage_green` | parametric (`color_h` green band) | Heaton, Adamus, Marino |
| `mask_water_blue_cyan` | parametric (`color_h` blue/cyan band) | Marino (intimate water scenes), Heaton, Page |
| `mask_horizon_gradient` | drawn (linear gradient at detected horizon) | Heaton, Ramelli, O'Leary — substitute for graduated ND |

These should compose: `apply mask_sky` on a sky-blue color grade; `apply mask_skin_region` on a skin-uniformity primitive (RFC-033); `apply mask_horizon_gradient + mask_luminosity_brightest_quartile` (intersected) for Heaton's "intersect with mask" pattern.

## Goals

1. **Named masks as first-class vocabulary** — referenceable by name in L2 look manifests, in CLI calls, and in MCP tool calls.
2. **Composition** — masks compose with each other (intersect, union, exclude) using the existing apply-time mask-spec language (RFC-029 / ADR-084) so the mask vocabulary doesn't fork the spec.
3. **Routing transparency** — calling `mask_sky` should route through the LLM-vision masker without the caller knowing or caring; calling `mask_luminosity_brightest_quartile` should route through parametric mask. The caller sees one named mask; the implementation chooses the right backend.
4. **Discoverability** — `list_masks_vocabulary()` returns the named masks the same way `list_vocabulary()` returns primitives.
5. **No new mask machinery** — purely a vocabulary layer over RFC-024 / RFC-026 / RFC-029 closures. Zero new mask kinds.
6. **Composability with RFC-031** — the proposed `apply_per_region` verb's `mask_spec` field accepts named masks (resolves to spec at call time).
7. **Keep the inline mask-spec form** — named masks don't replace the inline form; they sit alongside it. Inline is for the precise / ad-hoc; named is for the canonical / recurring.

## Constraints

- **TA/components/masking** — drawn / parametric / LLM-vision are the three settled mask kinds. No new kinds (RFC-030 deferred separately).
- **TA/contracts/vocabulary-manifest** — vocabulary entries are JSON manifest files. Named masks must fit this shape (one file per entry, manifest-validated).
- **TA/constraints/byoa** — LLM-vision-backed masks (sky, subject, eye-region) are MCP-provider-mediated; chemigram doesn't bundle the model. The named-mask manifest declares the *intent* and canonical prompt; provider routing happens at apply time per ADR-086.
- **TA/constraints/agent-only-writes** — named masks resolve to a mask spec, which gets stored in the per-image mask repo with the same mutation discipline as today's masks (per-image, per-call).
- **Mask cache semantics (ADR-086)** — LLM-vision-backed masks are cached per-image by content hash. A named mask `mask_sky` for image X resolves to the same cached mask across calls within a session.

## Proposed approach

**Add a fourth vocabulary kind: `mask`. Named masks ship as `.maskdef` JSON files in `vocabulary/packs/<pack>/masks/`, alongside primitives in `layers/L1/`, looks in `layers/L2/`, and L3 in `layers/L3/`.**

A `.maskdef` file declares:

```json
{
  "name": "mask_sky",
  "kind": "mask",
  "description": "The sky region of the image. Routes to LLM-vision with a canonical sky-selection prompt; falls back to parametric (top luminance + blue hue band) if the masker is unconfigured.",
  "tags": ["landscape", "sky", "content-aware"],
  "spec": {
    "primary": {
      "kind": "llm_vision",
      "prompt": "Select the sky region — including clouds, atmosphere, and any visible portions of the upper atmosphere. Exclude horizon-bordering land, mountains, or trees that protrude into the sky."
    },
    "fallback": {
      "kind": "parametric",
      "ranges": [
        {"channel": "luminance", "band_low": 0.6, "band_high": 1.0, "feather": 0.1},
        {"channel": "color_h", "band_low": 180, "band_high": 260, "feather": 15}
      ],
      "combine": "intersect"
    }
  }
}
```

Routing semantics:

- **LLM-vision-backed masks** (sky, subject, eye_region, skin_region for content-aware variant) declare a `primary` of kind `llm_vision` plus a parametric `fallback`. If the LLM-vision masker is configured (per ADR-086), `primary` is used. Otherwise the fallback runs. The fallback is *always* expressible in v1.9.0 primitives — no maskdef can ship that has no parametric fallback (manifest-validated).
- **Parametric-only masks** (luminosity bands, color bands, hue ranges) skip the `primary` field; the spec is just the parametric definition. No fallback needed.
- **Drawn-only masks** (horizon gradient) declare a drawn-mask spec with parametric metadata for placement (e.g., "linear gradient at the detected horizon line, fade 20% above to 80% below"). Horizon-detection itself is a sub-question — see Open questions.

**Composition semantics.** A maskdef can reference other maskdefs via the existing apply-time mask spec language (RFC-029 / ADR-084):

```json
{
  "name": "mask_horizon_intersect_sky",
  "kind": "mask",
  "spec": {
    "kind": "compose",
    "operation": "intersect",
    "operands": ["mask_sky", "mask_horizon_gradient"]
  }
}
```

The compose form resolves recursively at apply time. This means Heaton's "intersect with mask" pattern is one named mask, not a runtime composition every caller has to assemble.

**MCP surface additions.** Two new tools mirror the existing vocabulary verbs:

- `list_masks_vocabulary(tags?) → entries` (vocabulary inspection; sister to `list_vocabulary`)
- (No new apply verb.) Named masks are referenced by name in the existing `mask_spec` arg of `apply_primitive` and `apply_per_region` (RFC-031). The mask-spec parser gains one new shape: `{"kind": "named", "name": "mask_sky"}`.

**Manifest integration.** L2 looks (RFC-018, manifest format) reference named masks in their `mask_spec` field by name. An L2 look like `look_landscape_sky_enhance` carries `"mask_spec": {"kind": "named", "name": "mask_sky"}` instead of inlining the parametric spec. When `mask_sky` evolves (better LLM prompt, refined fallback), every L2 look that uses it gets the improvement automatically.

**Caching.** Resolved mask bytes are cached per-image-per-name following the existing ADR-086 cache discipline. `mask_sky` for image X is computed once per session and reused across all primitives that bind to it within that session. Invalidation follows the existing rules (raw changes → cache invalidates).

## Alternatives considered

**Embed mask specs in L2 look manifests; no separate mask vocabulary kind.** Already supported (the existing manifest accepts inline `mask_spec`). Rejected as the primary path because it produces drift across copies — every L2 look that wants "the sky" inlines a copy of the same spec. When the canonical sky-selection prompt or parametric fallback improves, every copy needs to update. The vocabulary pattern in chemigram is "name it, version it, reference it" — that pattern already applies to dtstyles and L2 looks; extending it to masks is the consistent move.

**Pure documentation — recipe snippets in `vocabulary-patterns.md`, no manifest changes.** Rejected because it leaves the agent reasoning about mask specs as implementation details. Chemigram's vocabulary discipline turns implementation details into named moves; mask specs are the missing piece. Recipe snippets get out of date faster than maintained vocabulary entries.

**Extend the LLM-vision masker (ADR-086) to ship a built-in catalogue of named prompts; no parametric named masks.** Rejected because it splits the named-mask story across two surfaces (LLM-vision-named vs parametric-inline) when photographers don't think in those terms. Photographers think "the sky" — they don't care whether it routes to AI or to a parametric color band. The unified maskdef shape preserves that.

**One maskdef-equivalent per mask kind — split into "prompt vocabulary" for LLM-vision, "parametric vocabulary" for color/luminance bands, "shape vocabulary" for drawn.** Rejected because the natural unit is "the named mask" (sky, subject, foliage), not "the named prompt template" or "the named parametric range." Photographers and L2 look authors compose by mask-name; the storage shape should match the composition shape.

**Make named masks a function of the agent context — taste.md declares "when I say 'the sky', mean X."** Rejected because per-photographer taste customization is a separate concern (and important — see RFC-018), but the *baseline* canonical named masks should be packaged with the vocabulary, not derived from each photographer's taste file. taste.md remains the right place for "I prefer my sky-mask to feather harder than the default" overrides; the named-mask vocabulary is the default everyone customizes from.

## Trade-offs

- **+1 vocabulary kind, +1 file extension (`.maskdef`)** — but it integrates with existing pack / manifest / loader machinery (RFC-018, ADR-063). Cost is real but contained.
- **+1 MCP verb** (`list_masks_vocabulary`) and +1 mask-spec shape (`{"kind": "named", ...}`) — small surface additions.
- **Named-mask catalogue grows over time** — every survey round (genre 3+, future research) surfaces 2-5 new named masks. The catalogue is unbounded in principle. Acceptable; this is the same shape as the dtstyle catalogue and the L2 look catalogue. The vocabulary-not-sliders discipline assumes growth.
- **Fallback-not-equivalent risk** — for LLM-vision-backed masks, the parametric fallback is genuinely worse than the LLM result. A user without an LLM-vision provider gets *some* approximation of "the sky" but it's coarser. This is honest about the BYOA stance (TA/constraints/byoa); document it explicitly so users know what they're getting.
- **Mask-spec parser complexity** — the parser gains the `named` kind and recursive resolution for `compose`-form maskdefs. Worth a careful test layer.

## Open questions

1. **Pack layout.** Do named masks live in `vocabulary/packs/<pack>/masks/` (parallel to `layers/L1/`, `layers/L2/`, `layers/L3/`), or in `vocabulary/packs/<pack>/layers/Lmask/`? Proposal: top-level `masks/` for clarity — masks are not a layer in the L1/L2/L3 sense; they're orthogonal.
2. **Horizon detection for `mask_horizon_gradient`.** No primitive in v1.9.0 detects a horizon line. Two options: (a) ship the horizon line as a parametric metadata field (manually placed at apply time via a "horizon at y=0.55" parameter); (b) route through LLM-vision with a "horizon line" prompt. Proposal: ship (a) for v1.10 (deterministic, agent-controlled); revisit (b) if it's uncomfortable.
3. **Skin-region named mask vs RFC-033 skin-tone uniformity primitive — what's the relationship?** They're different things — `mask_skin_region` is a *region selector*; RFC-033's primitive is a *color operation*. The expected composition is `apply skin_uniformity_primitive with mask_spec=mask_skin_region`. Worth being explicit so neither RFC's scope creeps into the other.
4. **Cross-pack named-mask collision.** What if pack A and pack B both ship a `mask_sky`? Proposal: same rule as primitives (ADR-051 / RFC-006) — pack-load order wins; later pack overrides; collision warning emitted. Same machinery, no new discipline.
5. **Versioned named masks.** When `mask_sky`'s LLM prompt or parametric fallback improves, do we version it (`mask_sky_v2`)? Proposal: same discipline as dtstyles — masks are append-only after ship; meaningful changes ship as `mask_sky_v2` so taste.md references and L2 looks pinning a version don't drift unexpectedly.

## How this closes

Likely **two ADRs** — separate-able, but RFCs sometimes close into multiple:

- **ADR-NNN — Named-mask vocabulary kind + manifest schema** — formalizes the `.maskdef` file format, the four spec shapes (parametric, drawn, llm_vision-with-fallback, compose), the named-mask name resolution rules, the cross-pack collision discipline. Updates `TA/contracts/vocabulary-manifest`.
- **ADR-NNN — `list_masks_vocabulary` verb + `named` mask-spec kind** — formalizes the MCP / CLI surface additions. Updates `TA/contracts/mcp-tools` and `TA/components/mcp-server`.

Splitting is optional; could close as one ADR if scope stays small.

## Links

- TA/components/masking (where the mask machinery lives — unchanged by this RFC)
- TA/contracts/vocabulary-manifest (this is the modification surface — adds a kind)
- TA/contracts/mcp-tools (small additions: one verb, one mask-spec kind)
- Related: RFC-024 / ADR-085 (parametric masks — the substrate), RFC-026 / ADR-086 (LLM-vision masking — the substrate for content-aware masks), RFC-029 / ADR-084 (mask-spec language — the substrate for `compose` forms), RFC-018 / ADR-063 (vocabulary expansion — the substrate for adding a kind), RFC-031 (consumer of named masks via `apply_per_region`)
- Source survey: `docs/photographer-workflows-survey.md` (gap rank #2, 6/12 cross-genre recurrence)
