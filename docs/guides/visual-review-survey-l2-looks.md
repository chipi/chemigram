# Visual-review checkpoint — survey-derived L2 looks + skin primitives

> Companion to v1.10's photographer-workflows survey work (RFC-031/032/033 + scope-expansion). This is the darktable-session validation pass for entries that ship without lab-grade automated coverage — the natural-skin-vs-painted-skin / dramatic-vs-cartoonish / restrained-vs-flat boundaries are visual judgments, not assertions.
> When · Run before closing RFC-033 into ADR or before any production photographer session that depends on these entries.

## What needs visual sign-off

**Skin primitives (RFC-033 + cheap-#4 scope expansion):**

- `skin_uniformity` — Path B color-band uniformity via colorequal sat_orange shift, masked to mask_skin_region
- `skin_smooth_painterly` — Frequency-separation approximation via masked clarity reduction

**Survey L2 looks (14 new):**

- 5 portrait: `look_portrait_natural_skin`, `look_portrait_editorial`, `look_portrait_skin_warm_lift`, `look_portrait_background_dim`, `look_portrait_split_tone_moody`
- 9 landscape: `look_landscape_grand_vista`, `look_landscape_intimate_quiet`, `look_landscape_golden_hour`, `look_landscape_blue_hour_cool`, `look_landscape_atmospheric_haze`, `look_landscape_dramatic_moody`, `look_landscape_autumn_pop`, `look_landscape_sky_enhance`, `look_landscape_water_silk`

## Required raws

- **3-5 portraits** with varied skin tones (caucasian-through-deep), varied lighting (window light, studio strobe, golden-hour, mixed), and varied makeup load (natural through full editorial). At least one with visibly uneven skin (red patches on forehead, yellow undertones on cheeks).
- **5-7 landscapes** covering: grand-vista wilderness, intimate small-scene (forest interior, abstract detail), golden-hour scene, blue-hour / twilight, hazy / misty / fog, dramatic stormy weather, autumn foliage, water surface (long-exposure or glassy lake).

## Per-entry checklist

For each entry, render (`render_preview` or darktable-cli with the bundled baseline XMP) and visually verify the **intent matches the result**. Score one of:

- ✅ **Matches** — the rendered image reads as the entry's stated intent
- ⚠️ **Approximate** — generally right but parameters need tuning (note suggested adjustment)
- ❌ **Wrong** — fails the intent (note what's wrong; consider re-design or fall-back path)

### Skin primitives

#### `skin_uniformity` at strengths 0.0 / -0.3 / -0.6

| Test image | Strength | Expected | Pass? |
|-|-|-|-|
| Portrait with red forehead patches | -0.3 | Patches noticeably reduced; natural skin still | |
| Portrait with red forehead patches | -0.6 | Strong uniformity; check it doesn't read as "painted" | |
| Portrait with deep skin tones | -0.3 | Uniformity works without lifting tone reading as flat / muddy | |
| Portrait with full lipstick/makeup | -0.5 | Lip color preserved (mask_skin_region's color_h fallback should exclude lips); if lipstick desaturates badly, that's a mask-leakage finding |
| Studio-strobe portrait | -0.5 | Skin reads natural under hard light (the failure mode here is "plastic skin")  | |

**Fail criteria:** if `skin_uniformity` produces "plastic skin" at strength -0.5 on representative portraits, the visual quality bar fails. Fall back to RFC-033 Path A (full Path C decoder of colorequal — substantially heavier work) or document the strength ceiling.

#### `skin_smooth_painterly` at strengths -0.3 / -0.5 / -0.7

| Test image | Strength | Expected | Pass? |
|-|-|-|-|
| Close-up portrait with visible pores | -0.3 | Subtle smoothing; pores still visible | |
| Close-up portrait with visible pores | -0.5 | Noticeable smoothing without crossing into "plastic" | |
| Close-up portrait with visible pores | -0.7 | Strong smoothing; check this is the upper acceptable bound | |
| Editorial / fashion portrait | -0.5 | Composes with skin_uniformity for a complete skin pass | |

**Fail criteria:** if -0.5 already produces over-smoothed / waxy skin, narrow the recommended range to -0.3..-0.5 and update the description's "typical -0.3 to -0.7" guidance.

### Portrait L2 looks

#### `look_portrait_natural_skin`

- [ ] Skin tones unchanged in the warm direction (subtle, not orange)
- [ ] Contrast feels gentle — not flat, not punchy
- [ ] Saturation pulls back without the image looking dull
- [ ] Composes naturally with skin_uniformity / skin_smooth_painterly

#### `look_portrait_editorial`

- [ ] Stronger contrast than natural_skin; visibly punchier
- [ ] Split-tone reads (cool shadows + warm highlights) without skin tones turning unnatural
- [ ] Saturation pull-back doesn't make image look washed out

#### `look_portrait_skin_warm_lift` (masked)

- [ ] mask_skin_region binding scopes the lift to skin only
- [ ] Background / clothing exposure unchanged
- [ ] Skin reads warmer + brighter without the boundary being visible (mask edge feathering OK)
- [ ] If the mask leaks onto orange backgrounds / lipstick, document and consider override-mask recipe

#### `look_portrait_background_dim`

- [ ] Caller-supplied subject mask shape works (no pre-baked mask)
- [ ] Background dims by ~0.4 EV; saturation reduction visible but not aggressive
- [ ] Subject preserved by the inverse mask

#### `look_portrait_split_tone_moody`

- [ ] Stronger split than editorial — cool blue shadows + warm orange highlights
- [ ] Skin tones survive the strong split (the failure mode: skin turns into the highlight color)
- [ ] If skin breaks at the default values, document strength override recipe

### Landscape L2 looks

#### `look_landscape_grand_vista`

- [ ] Sky and foreground both readable; no extreme tone compression
- [ ] Mild clarity bite gives definition without crunch
- [ ] Warm shadows shift visible without being over-warm

#### `look_landscape_intimate_quiet`

- [ ] Reads as **less** processed than the baseline — the explicit Marino-restraint signal
- [ ] Soft clarity (negative bilat) gives painterly feel
- [ ] If image looks just "blurry," not "painterly," recipe needs sharper tuning

#### `look_landscape_golden_hour`

- [ ] Warm shift visible but credible (not orange-sunset cartoon)
- [ ] Highlights amber; shadows warm; image reads as "this captured the warmth I felt"
- [ ] Already-warm scenes don't blow out into pure orange

#### `look_landscape_blue_hour_cool`

- [ ] Cool shift visible but credible
- [ ] Mood reads as twilight / pre-dawn
- [ ] If already-cool scenes go too cyan, consider tempering `temperature` shift

#### `look_landscape_atmospheric_haze`

- [ ] Hazeremoval lifts visibility WITHOUT killing the moody fog
- [ ] Strength 0.5 in the dtstyle is right (not 1.0 or 1.5 — those defeat the intent)
- [ ] Composes with golden_hour for warm-hazy scenes

#### `look_landscape_dramatic_moody`

- [ ] Strong contrast (1.7) reads as dramatic, not crunchy
- [ ] Cool shadows + warm highlights split adds depth without skin-tone-style cartoon
- [ ] Stormy / weather images: mood emerges; calm scenes: image reads over-processed (which is the right failure mode — this look isn't for calm scenes)

#### `look_landscape_autumn_pop`

- [ ] Orange / red foliage visibly lifted without the "Lightroom autumn preset" cartoon look
- [ ] Sky stays natural (the sat_blue compensation working)
- [ ] Non-foliage scenes: applies regardless but reads weird (which is the right failure mode — this look isn't for non-foliage)

#### `look_landscape_sky_enhance` (masked)

- [ ] mask_sky binding scopes the enhancement to sky only
- [ ] Foreground / land unchanged
- [ ] On complex skies (sunsets, partial clouds, trees in sky), parametric fallback may leak — escalate via Pattern 7 of llm-vision-for-masks.md and re-test
- [ ] Composes on top of grand_vista / dramatic_moody for sky-emphasis

#### `look_landscape_water_silk` (masked)

- [ ] mask_water_blue_cyan binding scopes the smoothing to water only
- [ ] Smoothing actually reads as silky water (not "blur applied to a region")
- [ ] Rocks / shore unchanged
- [ ] Cyan-tinted backgrounds may leak — note as a finding

## How to run a render

```bash
# For each test image, ensure a workspace is bootstrapped:
chemigram ingest /path/to/test/raw.NEF --image-id test_portrait_caucasian_window

# Apply the entry under test:
chemigram apply-primitive test_portrait_caucasian_window \
  --entry skin_uniformity \
  --param sat_orange=-0.5 \
  -p expressive-baseline

# Render the preview:
chemigram render-preview test_portrait_caucasian_window
# → outputs JPEG path; open in your viewer of choice

# Visually compare against:
# - the unprocessed baseline render
# - your reference editor (Lightroom / Capture One) doing the equivalent move
```

For the masked entries, also test:
- The pre-baked named mask path (default — apply with no override)
- An LLM-vision-constructed mask via Pattern 7 of `llm-vision-for-masks.md`

## What to record

Per entry, capture:

1. **Pass/fail/approximate** rating
2. **Test images used** (anonymized identifiers)
3. **Specific failure modes observed** (e.g., "lipstick desaturates at strength -0.7 on portrait_caucasian_makeup")
4. **Recommended adjustments** (parameter range narrowing, mask refinement, default value changes)

## Outputs

After the review session:

- Failures → file follow-up issues, mark the entry's manifest description with caveats (or remove and re-author)
- Strength-range tuning → update the manifest's range / default fields, regenerate via `scripts/generate-l2-looks-survey.py`
- Mask-leakage findings → either tighten the maskdef's parametric fallback (RFC-032), document the override-mask recipe in `vocabulary-patterns.md`, or escalate to LLM-vision construction (`llm-vision-for-masks.md` Pattern 7)
- Successes → close the visual-review checkpoint and ship the closing ADR for RFC-033 (currently blocked on this checkpoint)

## See also

- `docs/photographer-workflows-survey.md` — the source survey that informed all 14 looks + 2 skin primitives
- `docs/rfc/RFC-033-skin-tone-uniformity.md` — recommends this checkpoint before ADR closure
- `docs/guides/llm-vision-for-masks.md` — Pattern 7 for content-aware mask escalation
- `docs/guides/vocabulary-patterns.md` — composition recipes referencing these entries
- `docs/guides/visual-proofs.md` — automated visual-proof sweep (different scope: lab-grade vs visual-review)
