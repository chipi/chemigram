# RFC-024 — Range masks (color-range / luminance-range / depth-range / subject)

> Status · Decided
> Date · 2026-05-08
> TA anchor · /components/masking · /contracts/per-image-repo · /constraints/opaque-hex-blobs
> Related · ADR-076 (drawn-mask only architecture; this RFC formalizes the parametric extension), ADR-007 (BYOA principle), ADR-086 / RFC-026 (LLM-vision-as-provider for AI masks; coarse subject identification routes there), RFC-030 (deployed sibling-provider scaffolding; precision-tier subject + depth masks deferred there), RFC-029 / ADR-084 (compositional masks at apply time; this RFC adds the *refinement* dimension on top of the spatial dimension), capability-survey.md § 7 (local adjustments — range masks are the named gap), #105 (the issue that opened this question)
> Closes into · ADR-085 (parametric mask encoding via blendif; range_filter schema; AND composition with drawn masks)
> Why this is an RFC · ADR-076 settled the v1.5.0 mask architecture as drawn-only and noted that future content-derived masks would need to land as bytes darktable's mask system actually consumes. v1.8.0 closed Lightroom-parity for *spatial* masking; the largest remaining gap is *content-derived* masking — "affect only the dark pixels," "affect only the blue hues" — which Lightroom calls **range masks**. Four flavors (color, luminance, depth, subject) have materially different cost shapes: color and luminance are darktable-native parametric paths (bytes-only extension); depth and subject need ML at inference time (BYOA-shaped). The genuine open question this RFC argued: **what's the architectural shape that handles all four?** The answer below: a **hybrid** — parametric mask encoding for the two darktable-native cases (Tier 2 expansion), with coarse AI subject masks routing to RFC-026 (LLM-vision-as-provider) and the precision tier (depth + pixel-perfect subject silhouettes) deferred to RFC-030 (deployed sibling-provider scaffolding). The byte-level work is bounded; the schema integration with RFC-029's drawn-mask compose path is the load-bearing decision.

---

## The question

Lightroom's masking has two dimensions chemigram doesn't currently address. ADR-076 ships drawn masks (gradient / ellipse / rectangle), and ADR-084 / RFC-029 closed the agent-facing build-by-words spatial workflow. Both cover the "I want to affect this region" case. The other dimension is **content-derived masks**: the photographer says "affect everything that's blue" or "affect just the bright parts" and the engine computes the mask from image content, not user-drawn geometry.

Four named flavors of content-derived mask:

1. **Color-range mask.** Pick a hue range; pixels in that range are "in the mask," everything else is "out." darktable supports this natively as a parametric mask in `blendop_params`.
2. **Luminance-range mask.** Pick a tonal band (shadows / midtones / highlights); affect only that band. Same darktable parametric-mask path; different field set.
3. **Depth-range mask.** Pick a depth band ("near" / "far"). Requires a depth map per image. Not natively supported; needs a depth-aware preprocessor.
4. **Subject mask.** Pick the subject; affect only it. Needs a SAM-class model.

The genuinely open question argued: **what's the architectural shape that handles all four under a coherent vocabulary surface?** The cheap answer (extend `dt_serialize` to emit darktable-native parametric masks) covers (1) and (2) but not (3) and (4). The expensive answer (full MCP-provider scaffolding for ML-derived masks) covers (3) and (4) but reintroduces a Protocol-shaped surface ADR-076 explicitly rejected. Hybrid — parametric for (1) and (2), provider scaffolding for (3) and (4) — is the right shape, but the schema integration with RFC-029's drawn-mask path is the design choice.

---

## Use cases

1. **Photographer wants the sky bluer without affecting other blues in the frame.** HSL hue alone affects all blues. Color-range mask (HSL hue band) isolates the sky's specific blue range. Composition with a drawn-mask gradient at the horizon further localizes — "the blue pixels in the upper third."
2. **Photographer wants to lift just the shadow band of a high-contrast scene.** Luminance-range mask on the bottom 30% of tones; bound to an exposure +0.5 EV move. Lightroom's "Luminance Range" panel does exactly this.
3. **The user's mental model — refine spatial mask with pixel filter.** "Brighten just the *dark* pixels in the bottom third of the photo." Drawn gradient (bottom third) + luminance-range filter (shadows). The drawn mask defines the *region*; the parametric mask refines *which pixels in that region* receive the edit.
4. **Color-range refinement of a drawn ellipse.** "Reduce saturation only in the warm tones around the subject." Drawn ellipse + color-range filter (hue near red/orange).
5. **Subject + depth (coarse via RFC-026 / ADR-086 LLM-vision; precision via RFC-030).** "Brighten just the foreground person." Coarse subject region identification works today through the LLM-vision workflow (chat-client looks at the photo, estimates an ellipse / polygon). Pixel-perfect silhouettes and depth-band masks need deployed sibling providers; that arc is RFC-030 (deferred). Out of scope for this RFC's byte-level work.

---

## Goals

- **Pick the architectural shape** that handles color-range and luminance-range now; coarse subject masks route to RFC-026 (LLM-vision); precision subject + depth land via RFC-030's deployed-provider scaffolding when ready.
- **Honor ADR-076's structural lesson.** Coarse AI cases use LLM-vision (RFC-026, no deployed provider); precision-tier deployed providers land in RFC-030; native byte-encoding for the darktable-native cases (this RFC).
- **Stay byte-level-correct.** Range masks serialize through the same `dt_serialize` codec that handles drawn forms. Same modversion-drift policy (ADR-082) applies.
- **Compose with drawn masks via AND** — that's the dominant photographer workflow ("the dark pixels in this gradient"). Other compose modes (OR / SUBTRACT / invert) deferred until evidence demands them.
- **Bound the modversion-drift surface.** Each field added to the byte serializer adds drift exposure; ADR-082's warn-loud-at-load + hard-fail-at-apply backstop applies to parametric mask fields too.

---

## Constraints

- **ADR-076** (`/components/masking`): drawn-mask architecture is ground truth; this RFC adds parametric as a refinement layer, not a replacement.
- **ADR-007** (BYOA): no AI dependencies in `chemigram.core`. Coarse subject masks via LLM-vision (RFC-026 / ADR-086); precision-tier subject + depth deployed providers live in RFC-030 territory.
- **ADR-008 (amended by ADR-081)**: `blendop_params` is opaque except where parameterization is registered. Parametric masks live inside `blendop_params`; this RFC + ADR-085 register the specific byte regions.
- **ADR-033** (narrow MCP tool surface): no new tools. Extension is purely schema (a new `range_filter` field on `mask_spec`).
- **ADR-084 / RFC-029**: inline `mask_spec` is the canonical apply-time path. The `range_filter` field plugs into the same struct.
- **CLAUDE.md three foundational disciplines**: agent-only-writer (range filter set via tool calls); darktable-does-the-photography (parametric mask math runs in darktable); BYOA (LLM-vision in chat client per RFC-026; deployed AI providers via RFC-030 when needed).

---

## Decision

**Hybrid: parametric mask encoding for color-range + luminance-range; coarse AI subject masks via RFC-026 LLM-vision; precision-tier subject + depth deferred to RFC-030.**

Three concrete pieces:

### 1. Parametric mask byte encoder

Extend `chemigram.core.masking.dt_serialize` with a parametric-mask encoder that writes into `blendop_params`. Verified offsets (against darktable 5.4.1's `dt_develop_blend_params_t`):

```
offset  20: mask_combine          uint32
offset  28: blendif               uint32   (bitmask: which channels active + invert flags)
offset  68: blendif_parameters    float[64]  (4 control points × 16 channels)
offset 324: blendif_boost_factors float[16]
```

Per-channel parameters at offset `68 + channel_id * 16` are 4 floats: `[low_min, low_max, high_min, high_max]` defining a trapezoid mask:

- Below `low_min`: outside (mask=0)
- `low_min → low_max`: ramp up (0 → 1)
- `low_max → high_min`: inside (mask=1)
- `high_min → high_max`: ramp down (1 → 0)
- Above `high_max`: outside (mask=0)

Default per-channel value is `[0, 0, 1, 1]` (= "always pass"). We only modify the channels we filter on; everything else stays default.

### 2. `range_filter` mask_spec field

The `mask_spec` schema gains an optional `range_filter` sibling to `dt_form` / `dt_params`:

```python
mask_spec = {
    # Spatial (RFC-029, optional)
    "dt_form": "gradient",
    "dt_params": {"anchor_x": 0.5, "anchor_y": 0.67, "rotation": 180.0, ...},

    # NEW: pixel-level refinement (this RFC)
    "range_filter": {
        "kind": "luminance",   # or "color_h", "color_s", "color_l"
        "min": 0.0,            # band lower bound, [0..1]
        "max": 0.3,            # band upper bound
        "feather": 0.05,       # ramp width (applied to both edges)
        "invert": false,       # if true, OUTSIDE the range becomes the mask
    },
}
```

Three valid combinations of `dt_form` and `range_filter`:

| dt_form | range_filter | Result |
|-|-|-|
| present | absent | drawn mask only (RFC-029 / ADR-084) |
| absent | present | parametric mask only (e.g., "all dark pixels in the photo") |
| present | present | drawn AND parametric (e.g., "dark pixels in the bottom third") |

The encoder maps `{min, max, feather}` to the 4 control points:

```python
low_min  = max(0.0, min - feather)
low_max  = min
high_min = max
high_max = min(1.0, max + feather)
```

`invert: true` flips the channel's bit at position `+16` in the `blendif` bitmask (darktable's invert convention).

### 3. mask_mode / mask_combine wire-up

Three mask_mode values (all OR'd with `DEVELOP_MASK_ENABLED = 1`):

| Combination | mask_mode | mask_combine |
|-|-|-|
| Drawn only | `1 \| 2 = 3` | unchanged (default 0) |
| Parametric only | `1 \| 4 = 5` | unchanged |
| Drawn + parametric (AND) | `1 \| 2 \| 4 = 7` | `0` (default = AND/intersect) |

Other `mask_combine` values (OR, SUBTRACT, INVERT) are out of scope. Hardcoded to `0` for v1.9.0; future RFC can expose them if photographer evidence demands.

### Color-space handling

Channel IDs in darktable's parametric mask are color-space-dependent. For the four `range_filter.kind` values:

| `kind` | Channel ID | Color space | Notes |
|-|-|-|-|
| `luminance` | 0 | RGB or Lab | aliased: GRAY_in (RGB) = L_in (Lab) = 0 |
| `color_h` | 8 | HSL | requires `blend_cst = HSL` (TBD numeric) |
| `color_s` | 9 | HSL | as above |
| `color_l` | 10 | HSL | as above |

Luminance is universal — channel 0 is always brightness regardless of module color-space. Color-range needs `blend_cst` set to the HSL constant; the encoder picks it based on `kind`.

### Vocabulary surface

Range-mask vocabulary entries land in the existing manifest schema with `range_filter` set in `mask_spec`. Phase 2 grows from session evidence; the v1.9.0 ship may include 2-3 representative entries (e.g., `luminance_range_shadows_lift`, `luminance_range_highlights_dampen`).

---

## Alternatives considered

### Alt 1: Native parametric for ALL four (color / luminance / depth / subject)

Rejected. Color and luminance are darktable-native parametric paths — extending `dt_serialize` is bounded (Tier 2 cost-shape). Depth and subject are NOT darktable-native; depth needs an external depth map or ML; subject needs a SAM-class model. Treating them as "just more parametric mask kinds" hides the BYOA architectural shift and produces a misleading Tier 2-shaped issue when they're actually Tier 3+.

### Alt 2: MCP-provider scaffolding for ALL four

Rejected. The Protocol that ADR-076 retired produced PNG bytes darktable can't read. Reintroducing a provider Protocol for color and luminance ranges — when those operate on bytes darktable already consumes — re-creates the dead-infrastructure problem. The provider shape is correct for AI / depth (computation outside the engine); overkill for parametric masks (computation inside darktable).

### Alt 3: AI-subject-only first; defer color and luminance

Rejected. AI-subject is the dominant Lightroom workflow gap, but the architectural surface it needs (provider scaffolding) is materially bigger. Shipping AI-precision-tier first would force every subsequent range-mask decision through the provider lens, which is wrong for the darktable-native cases. Ship the cheap path first; the bigger lift earns its own RFC (RFC-030, drafted; coarse subject already covered by RFC-026 LLM-vision).

### Alt 4: Drawn-mask approximations forever (don't ship parametric at all)

Rejected. Color-range and luminance-range are real photographer workflow today (Lightroom's HSL Range, Lightroom's Shadow/Highlight masking). The drawn-mask approximations approximate the *region*, not the *content selection*. A "blue-sky" color-range mask is a fundamentally different operation from a gradient at the horizon — they sometimes overlap photographically, but the mental model and workflow are distinct.

### Alt 5: Defer until v1.10.0+

Rejected. v1.9.0 is the natural slot — the spatial side just shipped (RFC-029 / ADR-084). The user's mental model ("further refine selection within a drawn mask") is exactly the workflow this RFC addresses. Deferring would push against the post-v1.8.0 Lightroom-parity theme without corresponding gain.

### Alt 6: Expose mask_combine fully (AND / OR / SUBTRACT / INVERT)

Considered. darktable's `mask_combine` field supports four composition modes. Rejected for v1.9.0 because (a) AND is the dominant photographer workflow (~95% of Lightroom mask compositions per general usage patterns); (b) exposing all four expands the schema in ways that are hard to revert; (c) photographer evidence from real sessions can drive a future RFC if AND-only proves limiting. v1.9.0 hardcodes `mask_combine = 0`; future RFC may revisit.

### Alt 7: Lift range bounds to vocabulary parameters (per RFC-021)

Considered. A `luminance_range_shadows_lift` entry could be parameterized over `min` / `max` / `feather` so the photographer dials in their image's specific shadow band. Plausible, but defers to a future expansion — v1.9.0 ships range-mask entries with hardcoded bounds; if real sessions demand per-image tuning, parameterization can layer on via RFC-021's mechanism.

---

## Trade-offs

- **Schema surface grows.** `mask_spec` gains a `range_filter` field. Mitigated: it's a single optional field with a small dict shape; the schema stays flat and discoverable. Documented in `mask-shapes-from-words.md`.
- **mask_combine hardcoded to AND.** Photographer who wants SUBTRACT ("everywhere EXCEPT the bright pixels") has to express it via the `invert` field on `range_filter` (which inverts the parametric mask, equivalent to drawn AND NOT-parametric). Acceptable; covers ~all real workflows.
- **Color-range needs blend_cst handling.** The encoder must set `blend_cst` to HSL for `color_*` kinds. Adds a small color-space-aware branch. Mitigated: there's only one branch (luminance vs color); the color-space constant is a single value.
- **Range-mask entries are camera/image-dependent.** A "blue-sky" hue range tuned to one image won't match another's sky. Phase 2 evidence will tell us whether to parameterize bounds.
- **modversion drift surface grows.** Each parametric field added is exposure to darktable-version churn. Same backstop policy as ADR-082.
- **Precision-tier AI subject + depth deferred.** Lightroom users reaching for pixel-perfect AI-subject silhouettes won't find them in v1.9.0. Mitigated: coarse subject masks via RFC-026 LLM-vision work today; precision tier lands via RFC-030's deployed-provider scaffolding when it ships.

---

## Open questions resolved during deliberation

1. ~~Native vs provider for which kinds?~~ → **Native for color + luminance (this RFC); LLM-vision for coarse subject (RFC-026 / ADR-086); deployed provider for precision-tier subject + depth (RFC-030, deferred).**
2. ~~Compose syntax (tree vs flat)?~~ → **Neither.** Composition with drawn masks is via the `range_filter` sibling field — the schema is flat, single-level. Future RFC can introduce explicit compose syntax if multi-mask AND/OR demands it.
3. ~~mask_spec schema integration?~~ → **`range_filter` as an optional sibling to `dt_form` / `dt_params`.** Three valid combinations (drawn only, parametric only, both AND-composed). No new top-level schema kinds.
4. ~~mask_combine modes?~~ → **AND only for v1.9.0** (hardcoded `mask_combine = 0`). Other modes deferred until evidence.
5. ~~Tier classification?~~ → **Tier 2.** Bytes-level operation; bounded byte regions; matches the parameterized vocabulary cost-shape.
6. ~~Range bounds parameterization?~~ → **Defer.** v1.9.0 ships hardcoded bounds; revisit per Phase 2 evidence.
7. ~~Test coverage shape?~~ → **5-layer per ADR-080**, with the lab-grade tier using a real-raw fixture (charts have insufficient hue/luminance variation to validate range filtering). Synthetic grayscale ramp suffices for luminance_range; color_range needs a real raw with hue diversity.

---

## How this closes

**ADR-085 — Parametric mask encoding via blendif; range_filter mask_spec field; AND composition with drawn masks.**

Settles:

- Byte offsets for `mask_combine` (20), `blendif` (28), `blendif_parameters` (68), `blendif_boost_factors` (324)
- The `range_filter` schema shape: `{kind, min, max, feather, invert}` with `kind ∈ {luminance, color_h, color_s, color_l}`
- The `{min, max, feather}` → 4-control-point mapping
- mask_mode wiring (drawn-only=3, parametric-only=5, both=7) and mask_combine=0 hardcode
- Color-space handling for color_* kinds (blend_cst = HSL)
- ADR-076 amendment: parametric masks are a registered byte region inside `blendop_params`, complementing (not replacing) the drawn-form mask architecture
- Test-coverage extension: 5-layer per ADR-080 with real-raw fixture for color_range (luminance_range can use synthetic chart)

---

## Links

- TA/components/masking — current home of `dt_serialize`
- TA/contracts/per-image-repo — `mask_spec` schema
- TA/constraints/opaque-hex-blobs — ADR-008's amended boundary
- ADR-007 — BYOA principle (relevant for the deferred AI-subject path)
- ADR-076 — drawn-mask only architecture (this RFC formalizes the parametric extension)
- ADR-077..080 — parameterization architecture
- ADR-081 — Tier 2 cost-shape guidance
- ADR-082 — modversion-drift handling (backstop for parametric mask byte serializer)
- ADR-084 — apply-time mask spec semantics (RFC-029; spatial side; this RFC adds the refinement dimension)
- ADR-086 / RFC-026 — LLM-vision-as-provider for AI masks (coarse subject masks land here)
- RFC-030 — deployed sibling-provider scaffolding (precision-tier subject + depth deferred there)
- capability-survey.md § 7 — local adjustments / range masks named gap
- darktable 5.4.1 `src/develop/blend.h` — `dt_develop_blend_params_t` source struct
- Issue #105 — opened the question
