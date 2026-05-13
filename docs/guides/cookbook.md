# Cookbook — recipes for getting things done

> "I want **X** look — what's the chemigram recipe?"
>
> Intent-driven worked examples pulling from the 114-entry vocabulary,
> 9 named maskdefs, the v1.9.0 mask trilogy, and the v1.10.0 workflow
> primitives. Closes [#116](https://github.com/chipi/chemigram/issues/116).

Each recipe has three parts:

- **Intent** — what the photographer wants, in one sentence.
- **Recipe** — numbered CLI / MCP steps.
- **Notes** — why this works, when to reach for an alternative.

Companion docs:
- [`vocabulary-patterns.md`](vocabulary-patterns.md) — primitive composition patterns (intent ↔ composition).
- [`recipes.md`](recipes.md) — verb-level "how do I" (chunked by surface).
- [`visual-proofs.md`](visual-proofs.md) — synthetic-chart renders for every entry.

This cookbook organizes recipes by **photographic intent** rather than by primitive or verb. If you're looking for a specific verb, see `cli-reference.md`; if you're composing primitives at the conceptual level, see `vocabulary-patterns.md`; for "I want a cinematic teal-orange look with the subject lifted out of dark shadows," you're in the right place.

---

## Cinematic / film-look recipes

### "Cinematic teal-and-orange"

Subject color-temperature warm, shadow color-temperature cool — the modern cinematic grade.

```bash
chemigram apply-primitive <id> --entry grade_highlights_warm
chemigram apply-primitive <id> --entry grade_shadows_cool
chemigram apply-primitive <id> --entry saturation_global --value 0.25
```

Or use the pre-baked L2 look:

```bash
chemigram apply-primitive <id> --entry look_cinematic_teal_orange
```

**Notes:** Order matters in the manual version — grade first, sat last, because saturation amplifies whatever color you've put in. The L2 look bakes the order. Dial intensity with `--strength 0.5` for a softer variant (RFC-035 / ADR-088).

### "Cinematic teal-and-orange with subject lifted out of dark shadows"

The cinematic grade + a localized exposure lift on the subject region.

```bash
chemigram apply-primitive <id> --entry look_cinematic_teal_orange
chemigram apply-primitive <id> --entry look_subject_lift_dark_only
```

**Notes:** `look_subject_lift_dark_only` is a compositional-mask L2 (drawn ellipse AND luminance-shadows range_filter) — the lift scopes to dark pixels in the subject region, not the whole subject. Background stays dark; subject's shadows lift.

### "Kodachrome warm-saturated film look"

Pre-baked L2 look pulling from the cinematic decade-grades batch.

```bash
chemigram apply-primitive <id> --entry look_film_kodachrome
```

**Notes:** Soft cap on intensity via `--strength 0.7` if it reads too saturated for the scene.

### "Portra natural-skin film look"

```bash
chemigram apply-primitive <id> --entry look_film_portra
```

### "70s film, faded shadows, warm highlights"

```bash
chemigram apply-primitive <id> --entry look_70s_film
```

### "90s film grain over a contemporary tone"

```bash
chemigram apply-primitive <id> --entry sigmoid_contrast --value 2.5
chemigram apply-primitive <id> --entry look_90s_grain
```

**Notes:** The L2 look ships grain + colorbalancergb; pair with a contemporary contrast curve underneath for a hybrid 90s-feel-modern-tone shape.

---

## Portrait recipes

### "Natural skin in window light"

```bash
chemigram apply-primitive <id> --entry look_portrait_natural_skin
```

**Notes:** Pre-baked L2 composing temperature (warm) + sigmoid + colorbalancergb skin-shift. Survey citation: portrait Round 1, photographers reaching for the LR HSL + Color Mixer combo.

### "Editorial portrait with skin smoothing"

```bash
chemigram apply-primitive <id> --entry look_portrait_editorial
chemigram apply-primitive <id> --entry skin_smooth_painterly --param clarity_strength=-0.5
```

**Notes:** `skin_smooth_painterly` is pre-baked with `mask_skin_region` (RFC-032 named maskdef), so the bilat softening scopes to skin without affecting clothing or background. Approximate frequency-separation — not Photoshop's true band decomposition. For sharper precision, override `--mask-spec` with an LLM-vision-constructed mask (Pattern 7 of `llm-vision-for-masks.md`).

### "Even skin tones — fashion magazine"

```bash
chemigram apply-primitive <id> --entry skin_uniformity --param sat_orange=-0.3
```

**Notes:** RFC-033 Path B — masked colorequal sat_orange reduction on `mask_skin_region`. The negative sat_orange compresses skin-color variance without affecting other reds in the frame.

### "Portrait blemish cleanup pass"

Multi-step manual workflow for visible blemishes.

```bash
# 1. Find each blemish (eyeball or LLM-vision; see llm-vision-for-masks.md)
# 2. Heal each one
chemigram apply-spot <id> --kind heal --x 0.42 --y 0.31 --radius 0.02
chemigram apply-spot <id> --kind heal --x 0.55 --y 0.28 --radius 0.025

# 3. Tone + skin pass
chemigram apply-primitive <id> --entry look_high_key_portrait
chemigram apply-primitive <id> --entry skin_smooth_painterly --param clarity_strength=-0.5
```

**Notes:** v1.9.0 ships single-spot heal/clone via `apply_spot`. AI auto-detection of all spots ("find every blemish") is RFC-030 territory; for now you specify coordinates per spot. The MCP and CLI shapes are identical.

### "Background dim, subject in focus"

```bash
chemigram apply-primitive <id> --entry look_portrait_background_dim
```

**Notes:** L2 composite (vignette + colorbalancergb on the inverse-subject mask). Pre-baked; just apply.

### "Warm skin lift on otherwise-cool image"

```bash
chemigram apply-primitive <id> --entry look_portrait_skin_warm_lift
```

**Notes:** Composes a subtle temperature warm + colorbalancergb shift, masked to `mask_skin_region` so the warm only lands on skin.

### "Moody portrait with split-tone"

```bash
chemigram apply-primitive <id> --entry look_portrait_split_tone_moody
```

**Notes:** Cool shadows + warm highlights split-tone + sigmoid contrast. Survey-cited Adler / Woloszynowicz move.

---

## Landscape recipes

### "Dramatic moody landscape — storm clouds"

```bash
chemigram apply-primitive <id> --entry look_landscape_dramatic_moody
```

**Notes:** Pre-baked sigmoid + colorbalancergb + bilat composition. Survey-cited move for landscape Round 1. Dial back with `--strength 0.6` if too aggressive for the scene.

### "Golden hour warmth + glow"

```bash
chemigram apply-primitive <id> --entry look_landscape_golden_hour
```

### "Blue-hour twilight"

```bash
chemigram apply-primitive <id> --entry look_landscape_blue_hour_cool
```

### "Sky enhancement without touching foreground"

```bash
chemigram apply-primitive <id> --entry look_landscape_sky_enhance
```

**Notes:** Pre-baked with `mask_sky` (RFC-032 named maskdef) — cool-tone shift on the sky region only. For complex skies (sunsets, partial clouds, trees protruding into sky), override mask_spec with a path mask constructed via LLM-vision (`llm-vision-for-masks.md` Pattern 7).

### "Atmospheric haze — milky distant mountains"

```bash
chemigram apply-primitive <id> --entry look_landscape_atmospheric_haze
```

**Notes:** Composes hazeremoval + bilat + colorbalancergb. Negative-direction hazeremoval ADDS haze; the look is calibrated for fog-style distance shaping.

### "Autumn-color pop"

```bash
chemigram apply-primitive <id> --entry look_landscape_autumn_pop
```

**Notes:** Composes temperature shift + colorequal autumn-shift (boost orange/red sat, slight green pull) + bilat. Pair with `vignette_subtle` for an enclosed-glow feel.

### "Long-exposure water silk"

```bash
chemigram apply-primitive <id> --entry look_landscape_water_silk
```

**Notes:** Bilat negative-strength on the (assumed) water region. Works best when water occupies a coherent zone; combine with a path mask for irregular water shapes.

### "Grand vista — wide-scene contrast and color"

```bash
chemigram apply-primitive <id> --entry look_landscape_grand_vista
```

### "Intimate landscape — small scene, quiet tones"

```bash
chemigram apply-primitive <id> --entry look_landscape_intimate_quiet
```

**Notes:** Restrained sigmoid + bilat + colorbalancergb. The discipline opposite of `dramatic_moody` — designed not to push the image.

### "Underwater pelagic blue recovery"

For dive shots where depth has shifted everything to cyan-green.

```bash
chemigram apply-primitive <id> --entry wb_warm_subtle
chemigram apply-primitive <id> --entry chroma_boost_shadows
chemigram apply-primitive <id> --entry grade_shadows_cool
```

**Notes:** WB sets the global tone, chroma boost lets the deep blues survive the contrast, grade-shadows-cool reinforces the cool direction subtly. Order matters.

---

## B&W recipes

### "Adams-school dramatic B&W — red filter sim"

```bash
chemigram apply-primitive <id> --entry look_bw_landscape_dramatic
```

**Notes:** Pre-baked bw_convert v2 with bright_red+0.3 + bright_blue-0.2 + sigmoid 1.6 + bilat 0.5. Storm-cloud drama: red filter lightens land + darkens sky.

### "Classic neutral B&W — Adams baseline"

```bash
chemigram apply-primitive <id> --entry look_bw_classic_neutral
```

### "High-contrast chiaroscuro B&W — Page-style"

```bash
chemigram apply-primitive <id> --entry look_bw_high_contrast_chiaroscuro
```

### "Zone-balanced B&W — Silver Efex style"

```bash
chemigram apply-primitive <id> --entry look_bw_silver_efex_zone_balanced
```

### "Split-tone warm-shadows B&W — selenium print"

```bash
chemigram apply-primitive <id> --entry look_bw_split_tone_warm_shadows
```

### "B&W with custom Adams color-filter sim"

For a specific color-filter effect not covered by the pre-baked looks.

```bash
chemigram apply-primitive <id> --entry bw_convert \
    --param bright_red=+0.3 \
    --param bright_blue=-0.2 \
    --param bright_green=+0.1
```

**Notes:** `bw_convert` v2 exposes 8 `bright_X` axes (red / orange / yellow / green / cyan / blue / lavender / magenta) each `[-1.0, 1.0]`. Positive lightens that hue band's contribution to luminance; negative darkens. The chemigram analog of Photoshop Channel Mixer (Monochrome).

### "B&W via grey-weight (legacy channel-mixer)"

For the v1.4.0-style B&W that uses hard-coded grey weights.

```bash
chemigram apply-primitive <id> --entry bw_sky_drama       # red-emphasis
# or
chemigram apply-primitive <id> --entry bw_foliage          # green-emphasis
```

**Notes:** These ship a single `channelmixerrgb` plugin with fixed grey weights. Use when you want zero-parameter shorthand.

---

## Wildlife recipes

### "Eye-region lift — sharpen the gaze"

```bash
chemigram apply-primitive <id> --entry look_wildlife_eye_lift
```

**Notes:** Pre-baked exposure + sharpen, mask-bound to `mask_eye_region`. The bird's eye gets bright + crisp; everything else stays as is.

### "Subject sharpen, background unchanged"

```bash
chemigram apply-primitive <id> --entry look_wildlife_subject_sharpen
```

**Notes:** Sharpen + bilat scoped to `mask_subject`. Background blur stays soft (no sharpening artifact in the bokeh).

### "Background blur — emphasize subject separation"

```bash
chemigram apply-primitive <id> --entry look_wildlife_background_blur
```

**Notes:** Bilat negative-strength scoped to the inverse-subject mask. Soft falloff at the edges.

### "High-ISO noise recovery"

```bash
chemigram apply-primitive <id> --entry look_wildlife_high_iso_recovery
```

**Notes:** Composes denoiseprofile + sigmoid + bilat. The denoise step uses darktable's NLMEANS algorithm; the bilat compensates for the slight micro-contrast loss denoise introduces.

### "Natural-tone wildlife — warm fur / feathers"

```bash
chemigram apply-primitive <id> --entry look_wildlife_natural_warm
```

---

## Food / product recipes

### "Appetizing warm-tone food"

```bash
chemigram apply-primitive <id> --entry look_food_appetizing_warm
```

**Notes:** Pre-baked temperature warm + sigmoid + colorbalancergb. Food-photography survey citation.

### "Texture-subtle food shot — pizza, bread"

```bash
chemigram apply-primitive <id> --entry look_food_texture_subtle
```

**Notes:** Bilat texture-shaping scoped via a mask. Brings out crumb and grain texture without sharpening artifacts.

### "Green-natural fresh produce"

```bash
chemigram apply-primitive <id> --entry look_food_green_natural
```

### "Orange-pop fruit / juice"

```bash
chemigram apply-primitive <id> --entry look_food_orange_pop
```

### "Clean packshot — commercial product"

```bash
chemigram apply-primitive <id> --entry look_product_packshot_clean
```

**Notes:** Composes sigmoid + colorbalancergb at neutral settings. Assumes gray-card-corrected WB; see "WB from a gray card" below.

---

## Workflow primitives (RFC-035 / 036 / 037)

### "Apply this look at half-strength"

```bash
chemigram apply-primitive <id> --entry look_landscape_dramatic_moody --strength 0.5
```

**Notes:** RFC-035 / ADR-088 Path B. Each parameterized field interpolates from identity to authored: `interpolated = identity + strength * (authored - identity)`. Non-parameterized fields preserve the look's authored values regardless of strength.

### "Dodge-and-burn — face sculpting"

Six lit regions + six shadowed regions in one snapshot.

```bash
chemigram apply-per-region <id> --entry exposure --regions '[
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.4,"center_y":0.35,"radius_x":0.05,"radius_y":0.07,"border":0.03}},"parameter_values":{"ev":0.3}},
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.6,"center_y":0.35,"radius_x":0.05,"radius_y":0.07,"border":0.03}},"parameter_values":{"ev":0.3}},
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.5,"center_y":0.5,"radius_x":0.06,"radius_y":0.04,"border":0.04}},"parameter_values":{"ev":0.2}},
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.5,"center_y":0.7,"radius_x":0.18,"radius_y":0.08,"border":0.05}},"parameter_values":{"ev":-0.3}}
]'
```

**Notes:** RFC-031 single-op shape. All regions validate first; if any fail (out-of-range parameter, unresolved named-mask reference), none apply. Each region gets a unique `multi_priority` so the synthesizer treats them as distinct masked instances.

### "Eye-detail composite — lift iris AND sharpen lashes"

The mixed-op shape (RFC-036 / ADR-089) — different primitives per region, one snapshot.

```bash
chemigram apply-per-region <id> --regions '[
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.45,"center_y":0.4,"radius_x":0.04,"radius_y":0.05,"border":0.02}},
   "ops":[{"primitive_name":"exposure","parameter_values":{"ev":0.3}},
          {"primitive_name":"sharpen","parameter_values":{"amount":0.8}}]},
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.55,"center_y":0.4,"radius_x":0.04,"radius_y":0.05,"border":0.02}},
   "ops":[{"primitive_name":"exposure","parameter_values":{"ev":0.3}},
          {"primitive_name":"sharpen","parameter_values":{"amount":0.8}}]}
]'
```

**Notes:** Drop the top-level `--entry` flag. Per-(op, region) `multi_priority` allocation; cap of 64 (op × region) pairs.

### "Wedding-burst sync — propagate state to N images"

LR-Sync analog. Anchor on the best frame, propagate to the rest.

```bash
chemigram propagate-state <anchor_id> \
    --to <id1> --to <id2> --to <id3> --to <id4> \
    --label "reception-lighting-group-2026-05-14"
```

**Notes:** RFC-037 / ADR-090. Inherit-everything-by-default with framing-bound auto-exclusion (ashift / crop / retouch / lens / drawn-mask-bound). Parametric range masks DO propagate (content-relative). Atomic — every target validates first; any modversion mismatch aborts the batch. Cap 200 targets.

### "WB from a gray card"

```bash
# 1. Render the image at any state to JPEG so we can sample
chemigram render-preview <id>

# 2. Identify the gray card's pixel coordinates (open the JPEG, eyeball or vision)
# Let's say it's at (450, 320) with a 10-pixel sample radius.

# 3. Sample
chemigram wb-from-gray-card ~/Pictures/Chemigram/<id>/previews/preview.jpg \
    --x 450 --y 320 --sample-radius 10
# → red_coeff=1.034, green_coeff=1.000, blue_coeff=0.876

# 4. Apply the coefficients
chemigram apply-primitive <id> --entry temperature \
    --param red_coeff=1.034 \
    --param green_coeff=1.000 \
    --param blue_coeff=0.876
```

**Notes:** Survey Gap #20 closure. Useful for product photography where you control the lighting; less useful for landscape where gray cards aren't typically present.

---

## Mask-driven moves

### "Lift just the dark pixels — global"

Parametric mask only, no spatial shape.

```bash
chemigram apply-primitive <id> --entry look_dark_pixels_global_lift
```

**Notes:** Pre-baked entry — applies an exposure lift through a luminance range_filter for shadows. No drawn mask; the mask is purely parametric.

### "Brighten the brightest 25%"

```bash
chemigram apply-primitive <id> --entry exposure --param ev=0.4 \
    --mask-spec '{"kind":"named","name":"mask_luminosity_brightest_quartile"}'
```

**Notes:** Named maskdef reference (RFC-032). Resolves to a luminance range_filter at the apply-time. Same idea for `mask_luminosity_darkest_quartile` and `mask_luminosity_midtones`.

### "Deepen the sky's blue without affecting foreground"

```bash
chemigram apply-primitive <id> --entry look_sky_blue_deepen
```

**Notes:** Pre-baked compositional mask (drawn gradient on top half AND parametric color_h cyan-blue range_filter). Closes the survey-cited "sky enhancement without affecting clouds" intent.

### "Subject brighten with shadows protection"

```bash
chemigram apply-primitive <id> --entry look_subject_brighten_highlights
```

**Notes:** Compositional mask — drawn ellipse on the subject AND luminance highlights range_filter. The lift only affects bright pixels in the subject region.

### "Horizon warm glow — sunset shading"

```bash
chemigram apply-primitive <id> --entry look_horizon_warm_glow
```

**Notes:** Drawn gradient at horizon line AND warm-hue color_h range_filter. Subtle warm shift on the horizon band only.

### "Build a mask in words"

For when you need a mask that doesn't have a named maskdef.

```bash
# "Apply +0.5 EV to the bottom third of the frame."
chemigram apply-primitive <id> --entry exposure --param ev=0.5 \
    --mask-spec '{"dt_form":"gradient","dt_params":{"anchor_y":0.67,"rotation":180,"compression":0.5}}'
```

**Notes:** See `mask-shapes-from-words.md` for the full phrase → spec mapping (30+ examples: halves, thirds, hard-edged regions, ellipses at rule-of-thirds, diagonals, polygons).

### "LLM-vision precision subject mask"

When the parametric `mask_subject` fallback isn't precise enough.

```
# In your AI client:
# 1. Render preview
# 2. Show preview to the AI; ask "construct mask_spec for the iguana's body, excluding the rock it's sitting on"
# 3. AI returns mask_spec JSON (path or ellipse + range_filter)
# 4. Apply with that mask_spec
```

**Notes:** RFC-026 / ADR-086. The chat-client's vision capability constructs the mask; chemigram applies it. See `llm-vision-for-masks.md` Pattern 7 for the full workflow.

---

## Versioning workflows

### "Compare v1 vs current"

```bash
chemigram tag <id> v1
# ... do more edits ...
chemigram compare <id> v1 main
# → side-by-side JPEG in previews/
```

### "Branch for an exploration"

```bash
chemigram branch <id> exploration_warmer --from main
chemigram checkout <id> exploration_warmer
chemigram apply-primitive <id> --entry temperature --param red_coeff=1.2
# ... explore ...
# Decide it's worth keeping
chemigram tag <id> v2 --hash $(chemigram log <id> --json | jq -r '.[0].hash')
# Or abandon — just checkout back to main; the branch stays inspectable
chemigram checkout <id> main
```

### "Undo the last edit"

```bash
chemigram log <id> --limit 5    # find the previous hash
chemigram checkout <id> <prev_hash>
```

Or to reset to the original ingest baseline:

```bash
chemigram reset <id>
```

---

## Export workflows

### "Export at high quality"

```bash
chemigram export-final <id>
```

**Notes:** Defaults to JPEG, exports current HEAD. Higher quality than `render-preview` (which is preview-sized).

### "Export a specific snapshot"

```bash
chemigram export-final <id> --ref v2
```

### "Batch export across a folder"

```bash
ls ~/Pictures/Chemigram/ | xargs -I {} chemigram export-final {}
```

Or via stdin:

```bash
ls ~/Pictures/Chemigram/ | chemigram export-final - --stdin
```

---

## When to author your own L2 look

If you find yourself running the same 3-5 step recipe across many images:

1. Capture the move in a `.dtstyle` (export from darktable GUI with the moves applied).
2. Add a manifest entry under `~/.chemigram/vocabulary/personal/`.
3. From the next session forward, `chemigram apply-primitive <id> --entry my_signature_look` does the whole thing.

See [`authoring-vocabulary-entries.md`](authoring-vocabulary-entries.md) for the full workflow.

The vocabulary system is designed to grow with you — Phase 2's whole point is that personal-pack growth IS the Phase 2 work. The vocabulary becomes voice not by exhaustive coverage but by accumulating exactly the moves you keep reaching for.

---

## See also

- [`vocabulary-patterns.md`](vocabulary-patterns.md) — primitive composition patterns (the "what" layer below "the look")
- [`recipes.md`](recipes.md) — verb-level reference (snapshot, branch, checkout, etc.)
- [`mask-shapes-from-words.md`](mask-shapes-from-words.md) — phrase → drawn-mask spec
- [`llm-vision-for-masks.md`](llm-vision-for-masks.md) — Pattern 7 — vision-constructed masks
- [`visual-proofs.md`](visual-proofs.md) — synthetic-chart renders for every entry
- [`authoring-vocabulary-entries.md`](authoring-vocabulary-entries.md) — write your own
