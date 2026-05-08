# RFC-024 — Range masks (color-range / luminance-range / depth-range / subject)

> Status · Draft v0.1
> Date · 2026-05-08
> TA anchor ·/components/synthesizer ·/contracts/per-image-repo ·/constraints/opaque-hex-blobs ·/components/masking
> Related · ADR-076 (drawn-mask only architecture; this RFC argues to extend), ADR-007 (BYOA principle), RFC-009 / ADR-057 (historical mask-provider Protocol — closed; this RFC may reintroduce a different shape), capability-survey.md § 7 (local adjustments — range masks are the named gap), #105 (the issue that opened this question)
> Closes into · ADR-NNN (pending — the architectural shape decision); possible MCP-provider scaffolding ADR depending on the chosen path
> Why this is an RFC · ADR-076 settled the v1.5.0 mask architecture as drawn-only after the PNG-mask path was discovered to be a silent no-op. The closing observation was that a future content-aware masker would need to produce drawn-form geometry (or its own equivalent of `masks_history` content), and the schema would extend in place. v1.8.0 closed the bulk of Lightroom-parity work; the largest remaining workflow gap is the *other* masking surface — color-range / luminance-range / depth-range / subject. The "extend in place" claim from ADR-076 needs to be argued now: which extension path, what semantics, what cost. Three viable paths exist with materially different cost/value shapes; an RFC is the right form for the deliberation.

---

## The question

Lightroom's masking has two dimensions chemigram doesn't currently address. ADR-076 ships drawn masks (gradient / ellipse / rectangle), which cover the "I want to affect this region" use case. The other dimension is **content-derived masks**: the photographer says "affect everything that's blue" or "affect just the bright parts" and the engine computes the mask from image content, not user-drawn geometry.

Four named flavors of content-derived mask, in roughly ascending cost order:

1. **Color-range mask.** Pick a hue range; pixels in that range are "in the mask," everything else is "out." Lightroom's HSL Range slider (within the HSL panel) is conceptually adjacent. darktable supports this natively as a parametric mask in `blendop_params`.
2. **Luminance-range mask.** Pick a tonal band (shadows / midtones / highlights); affect only that band. Same darktable parametric-mask path; different field set.
3. **Depth-range mask.** Pick a depth band ("near" / "far"). Requires a depth map per image — either from camera (some cameras emit one) or computed by an ML model. Not natively supported by darktable; would need a depth-aware preprocessor.
4. **Subject mask** (= AI-subject mask in Lightroom). Pick the subject; affect only it. This is the `chemigram-masker-sam` arc per ADR-007 / ADR-076's closing comment.

The genuinely open question: **what's the architectural shape that handles all four?** The answer lands somewhere on a spectrum between "extend `dt_serialize` to emit darktable-native parametric masks" (cheap, but only covers (1) and (2)) and "ship a full MCP-provider scaffolding for ML-derived masks" (covers (3) and (4) but reintroduces a Protocol-shaped surface ADR-076 explicitly rejected).

---

## Use cases

1. **Photographer wants the sky bluer without affecting other blues in the frame.** HSL hue alone affects all blues; a color-range mask isolates the sky's specific blue band. Composition with a drawn-mask gradient at the horizon would then localize further.
2. **Photographer wants to lift just the shadow band of a high-contrast scene.** `toneequalizer --param shadows=...` already partially solves this (per-zone tonal control). Luminance-range mask is the photographer's mental model: "select the dark pixels, then apply X." Same outcome, different framing — but a mask-binding lets the user compose with arbitrary primitives, not just toneequalizer.
3. **Photographer wants to brighten the subject of a portrait without affecting the background.** Today: drawn radial mask (centered ellipse). Future: AI-subject mask gets the subject silhouette exactly. The Lightroom user reaches for the AI-subject mask far more often than the radial.
4. **Photographer wants to dehaze just the distant mountains.** Depth-range mask (far) + dehaze primitive. Depth needs a depth map; provider territory.
5. **Compositional mask: AI-subject AND drawn-radial centered.** Lightroom lets you AND/OR/SUBTRACT range + drawn masks. The compositional surface is real workflow value.

---

## Goals

- **Pick the architectural shape** that handles color-range, luminance-range, depth-range, and subject masks under a coherent vocabulary surface.
- **Honor ADR-076's structural lesson** (don't re-introduce dead Protocol infrastructure for paths that don't connect to pixels). Whatever scaffolding ships needs a real consumer.
- **Stay byte-level-correct.** Like the drawn-mask path, parametric masks should serialize through a `dt_serialize`-equivalent codec that produces darktable-readable bytes. AI-derived raster masks have to land as drawn-form geometry (silhouette polygons) per ADR-076's pixel-truth observation.
- **Preserve composition with drawn masks.** Range + drawn AND/OR/SUBTRACT is the dominant photographer workflow.
- **Bound the modversion-drift surface.** Each parametric-mask field added to the byte serializer adds drift exposure. Same backstop policy as ADR-082 applies.

---

## Constraints

- **ADR-076** (`/components/masking`): the drawn-mask architecture is the current ground truth. This RFC argues an extension; the v1.5.0 surface remains a strict subset of whatever ships.
- **ADR-007** (BYOA): no AI dependencies in `chemigram.core`. AI-subject and depth masks live in sibling projects (`chemigram-masker-sam`, hypothetical depth provider).
- **ADR-008 (amended by ADR-081)**: `blendop_params` is opaque except where parameterization is registered. Parametric masks live inside `blendop_params`; extending the codec amends the opacity boundary for that specific subset.
- **CLAUDE.md three foundational disciplines**: agent-only-writer (mask configuration via tool calls); darktable-does-the-photography (parametric mask math runs in darktable); BYOA (AI providers are sibling projects).
- **TA/components/masking**: `chemigram.core.masking.dt_serialize` already serializes drawn forms; parametric extension goes here.
- **TA/contracts/per-image-repo**: `mask_spec` is the entry-level mask binding shape; range-mask extensions go here too.

---

## Proposed approach

**Hybrid: native parametric for color-range and luminance-range; deferred to a separate provider RFC for depth-range and subject masks.**

Three concrete decisions:

### 1. Native parametric masks for color-range + luminance-range (Tier 2-shaped ship)

Extend `chemigram.core.masking.dt_serialize` with encoders for darktable's parametric-mask `blendop_params` fields. The mask binding extends `mask_spec` with two new shapes:

```python
mask_spec = {
    "kind": "color_range",          # vs. existing "drawn"
    "channel": "h",                 # h / s / l (hue, saturation, lightness)
    "min": 0.5, "max": 0.65,        # range over the channel's [0..1]
    "feather": 0.05,
}
mask_spec = {
    "kind": "luminance_range",
    "min": 0.0, "max": 0.3,         # 0 = blackest pixels, 1 = brightest
    "feather": 0.1,
}
```

The decoder emits the corresponding darktable parametric-mask byte fields inside `blendop_params`; no `masks_history` element is needed (parametric masks are inline, unlike drawn forms). The `apply_with_drawn_mask` helper grows a sibling `apply_with_parametric_mask` (or generalizes — TBD at implementation time).

**Tier classification**: Tier 2 under ADR-081's policy. Flat scalar struct; bytes-level operation; cost matches the magnitude-ladder modules.

### 2. Compositional masks (range + drawn)

`mask_spec` grows a `compose:` field that lists multiple sub-specs with AND/OR/SUBTRACT operators:

```python
mask_spec = {
    "compose": "and",
    "specs": [
        {"kind": "color_range", "channel": "h", "min": 0.5, "max": 0.65},
        {"kind": "drawn", "dt_form": "gradient", "dt_params": {...}},
    ],
}
```

Per darktable's parametric+drawn mask interaction in `blend.c`, the engine composes parametric and drawn masks via the `mask_id` linking + parametric-band fields. The compose syntax serializes to the exact byte combination darktable expects.

### 3. Subject + depth: defer to a follow-up RFC

These need ML models at inference time. The MCP-provider scaffolding shape that lands them is a separate architectural arc — bigger than range masks, and the right shape (raster vs. silhouette polygons) depends on what the provider produces and what darktable accepts. RFC-026 (placeholder) drafts that surface.

The interim story for users who want subject/depth masks: drawn-radial / drawn-rectangle approximations with the existing mask shapes. Lightroom users grumble but ship.

### Vocabulary surface

Range-mask entries land in the existing manifest schema with the new `mask_spec.kind` values. Examples:

- `color_range_blue_sky` — color-range mask isolating the typical sky-blue hue band; bound to an entry that lifts brilliance_highlights and saturation_blue.
- `luminance_range_shadows_lift` — luminance-range mask on the bottom 30% of tones; bound to an exposure +0.5 EV move.

The starter / expressive-baseline packs ship 3-5 range-mask entries to seed the surface; Phase 2 grows from session evidence.

---

## Alternatives considered

### Alt 1: Native parametric for ALL four (color / luminance / depth / subject)

Rejected. Color-range and luminance-range are darktable-native parametric paths — extending `dt_serialize` is bounded and matches Tier 2 cost-shape. Depth-range and subject masks are NOT darktable-native; depth needs an external depth map or ML; subject needs a SAM-class model. Treating them as "just more parametric mask kinds" hides the BYOA architectural shift and produces a misleading Tier 2-shaped issue when they're actually Tier 3-or-bigger.

### Alt 2: MCP-provider scaffolding for ALL four

Rejected. The provider Protocol that ADR-076 retired produced PNG bytes that darktable can't read. Reintroducing a provider Protocol for color-range + luminance-range — when those operate on bytes darktable already knows — re-creates the dead-infrastructure problem. The provider shape is correct for AI / depth (where computation happens outside the engine); it's overkill for color-range / luminance-range (where computation happens inside darktable's parametric mask system).

### Alt 3: AI-subject-only first, color-range / luminance-range later

Rejected. AI-subject is the dominant Lightroom workflow gap, but the architectural surface it needs (provider scaffolding) is materially bigger than what color-range / luminance-range need. Shipping AI first would force every subsequent range-mask decision through the provider lens, which is wrong for the darktable-native cases. Ship the cheap-and-correct path first; the bigger architectural lift earns its own RFC.

### Alt 4: Drawn-mask approximations forever (don't ship parametric at all)

Rejected. Color-range and luminance-range are real photographer workflow today (Lightroom HSL Range, Lightroom Shadow/Highlight masking). The drawn-mask approximations (gradient + ellipse + rectangle) approximate the *region*, not the *content selection*. A blue-sky color-range mask is a fundamentally different operation from a gradient at the horizon — they sometimes overlap photographically but the mental model and the workflow are distinct.

### Alt 5: Defer until v1.10.0+

Rejected. v1.9.0 is the natural slot — Lightroom-parity is the named theme of the post-v1.8.0 horizon (per capability-survey § 13 + § 10). Range masks are the largest remaining named gap. Deferring further pushes against the "Lightroom-parity is the v1.8/v1.9 theme" framing without a corresponding gain.

---

## Trade-offs

- **Compositional surface complexity.** `mask_spec.compose` introduces a small expression language (AND / OR / SUBTRACT over sub-specs). This grows the schema. Mitigated: the compositions darktable's `blend.c` actually supports are limited; the schema mirrors them, doesn't invent new shapes.
- **Two-layer mask-binding code.** `apply_with_drawn_mask` plus `apply_with_parametric_mask` (or a generalized `apply_with_mask` that branches on `kind`). Mitigated: implementation-detail; the user-facing `apply_primitive` just dispatches by the spec's `kind`.
- **Range-mask vocabulary entries are camera-and-image-dependent.** A "blue sky color-range" with hue range [0.55, 0.65] suits one image's sky and not another's. Range entries become more like *templates* than canonical primitives. The starter pack should ship a few representative ones; per-image tuning happens at apply time via `--param`-ish overrides (TBD whether range bounds should be parameterizable).
- **darktable's parametric-mask byte format may evolve.** ADR-082's modversion-drift policy applies; same warn-loud-at-load + hard-fail-at-apply backstop. The parametric encoder pins the supported version per ADR-077.
- **Subject + depth deferred.** Lightroom users reaching for AI-subject masks won't find them in v1.9.0. Mitigated: the gap is named (this RFC explicitly defers it to RFC-026); workaround documented (drawn-radial approximations).

---

## Open questions

- **Parametric mask byte layout.** Need to read darktable 5.4.1 `src/develop/blend.c` end-to-end to map the exact `blendop_params` byte fields for color-range and luminance-range masks. Should be a contained reverse-engineering pass; nothing in the RFC blocks it.
- **mask_spec composition syntax.** Should compose be a list of `(operator, sub-spec)` pairs (sequential application) or a tree (`{op: "and", left: {...}, right: {...}}`)? Tree handles nested compositions cleanly; flat list is simpler. Lean: flat list with operators between, mirroring how Lightroom's UI presents the "added" / "intersected" / "subtracted" mask stack.
- **Range bounds parameterization.** `color_range_blue_sky` could be parameterized over hue min/max so the photographer dials in their image's specific sky. Adds a parameter axis to a non-parameterized-today mask kind. Worth doing? Lean: yes — but defer to the closing ADR; not a blocker.
- **Tier 1 vs Tier 2 classification.** Range masks are Tier 2 expansion (per the cost-shape guidance in ADR-081). The closing ADR should cite that classification explicitly so the work doesn't accidentally cross into Tier 3.
- **Test coverage shape.** 5-layer per ADR-080 covers parameterized vocabulary entries. Range masks aren't parameterized in the same way. Need a parallel coverage rubric (per-kind unit / integration / lab-grade-on-real-raws since the synthetic chart doesn't have hue gradients to mask). Probably worth a short coverage extension ADR alongside the architectural ADR.
- **Real-raw fixture for visual proofs.** The HSL skip-list pattern (#103) — color-range masks need real-raw input for the same reason. The iguana fixture serves both.

---

## How this closes

This RFC closes into:

- **A primary ADR** specifying the hybrid architectural choice — native parametric for color-range / luminance-range, deferred RFC for depth + subject. Records the mask_spec extension, the compose syntax, and the ADR-076 amendment.
- **A possible amendment to ADR-080** clarifying the test-coverage policy for parametric-mask vocabulary entries (the 5-layer gate's "lab-grade global" layer needs a real-raw fixture for content-dependent masks).
- **A placeholder RFC-026** for AI-subject + depth-range provider scaffolding — drafts the BYOA-shaped extension at the right architectural level.

---

## Links

- TA/components/masking — current home of `dt_serialize` (drawn-form encoders)
- TA/contracts/per-image-repo — `mask_spec` schema
- TA/constraints/opaque-hex-blobs — ADR-008's amended boundary
- ADR-007 — BYOA principle (relevant for the deferred AI-subject path)
- ADR-076 — drawn-mask only architecture (this RFC argues to extend)
- ADR-077..080 — parameterization architecture (range masks may inherit pieces)
- ADR-081 — Tier 2 cost-shape guidance
- ADR-082 — modversion-drift handling (backstop for the parametric-mask byte serializer)
- RFC-009 (closed by ADR-057, retired by ADR-076) — historical mask-provider Protocol
- capability-survey.md § 7 — local adjustments / range masks named gap
- Issue #105 — the issue that opened this question
- Future RFC-026 — AI-subject + depth-range provider scaffolding (placeholder)
