# Vocabulary patterns

> "For *this* intent, reach for *that* composition."
>
> A practical guide to combining primitives from `starter` + `expressive-baseline` to satisfy common photographer intents. Each pattern is a small recipe — typically 2–4 primitives applied in sequence — that the agent (or you) can lean on.

This guide assumes both packs loaded:

```python
from chemigram.core.vocab import load_packs
vocab = load_packs(["starter", "expressive-baseline"])
```

For the full entry catalog see [`vocabulary/packs/expressive-baseline/README.md`](https://github.com/chipi/chemigram/blob/main/vocabulary/packs/expressive-baseline/README.md). For authoring your own primitives see [`authoring-vocabulary-entries.md`](authoring-vocabulary-entries.md).

---

## The pattern shape

Each pattern is:

- **An intent**, in the photographer's voice
- **A composition** of 2–4 primitives applied in order
- **Notes** on when to reach for it vs. an alternative

Order matters in some compositions but not all. When it matters, it's flagged.

---

## Tone and exposure

### "Bright sky, dim foreground"

A common landscape / underwater problem: top of the frame is hot, bottom is dim, single global exposure can't fix both.

```
gradient_top_dampen_highlights
gradient_bottom_lift_shadows
```

Both are mask-bound (drawn-form gradients). The pair gives compositional depth without darkening the sky-side or burning the foreground. Order doesn't matter; they affect different parts of the frame.

### "Subject is too flat, needs presence"

```
radial_subject_lift              # ellipse mask, +0.6 EV on the subject area
clarity_painterly                # gentle global clarity (or bilat_clarity_strength --value 1.5 if you want crisper)
```

Works when the subject sits roughly center-frame. If the subject is off-center, use a personal variant of the radial with adjusted center coordinates (see authoring guide).

### "Aggressive contemporary contrast"

```
sigmoid_contrast --value 2.5     # aggressive s-curve
blacks_crushed                   # crush the deep shadows
chroma_boost_midtones            # bring the chroma back in the mids (contrast often kills chroma)
```

Optionally cap with `vignette_medium` for a polished feel.

### "Faded film stock"

```
sigmoid_contrast --value 1.0     # mild s-curve
blacks_lifted                    # lift target black
grain_strength --value 25        # visible film-grain texture
```

The combination evokes a faded medium-format aesthetic. Add `grade_shadows_warm` for warm-tone grading on top.

### "Blown highlights, hot afternoon"

```
highlights_clip_threshold --value 0.85   # pull back clipped highlights aggressively
gradient_top_dampen_highlights   # mask-bound, drops top of frame -0.5 EV
```

Apply in order: recovery first (acts on full frame), then the gradient mask localizes any remaining dampening to the actual hot region.

---

## Color

### "Cinematic teal-and-orange"

```
grade_highlights_warm            # +orange in highlights
grade_shadows_cool               # +blue in shadows
saturation_global --value 0.25   # bring saturation up so the grade reads
```

Order: grade first, sat last. Saturation amplifies whatever color you've put in.

### "Underwater pelagic blue"

```
wb_warm_subtle                   # starter — counter the cyan cast of depth
chroma_boost_shadows             # let the deep blues bloom in shadows
grade_shadows_cool               # nudge shadows further toward blue (subtle)
```

The order matters: WB sets the global tone, chroma boost lets the blues survive the contrast, grade shadows reinforces the cool direction.

### "Skin-tone protective contrast"

```
sigmoid_contrast --value 1.0     # avoid aggressive S-curves on skin
chroma_boost_highlights          # let skin highlights bloom slightly
clarity_painterly                # soft local contrast (high clarity strengths damage skin)
```

Stay away from aggressive `sigmoid_contrast` (>2.0), high `bilat_clarity_strength` (>1.0), and `chroma_boost_midtones` for portraiture — all three destroy skin tonality.

### "Monochromatic conversion"

The default B&W move is `bw_convert` — a single colorequal plugin that kills saturation across all 8 hue bands and exposes 8 `bright_X` axes for Adams-school color-filter strength. The 8 axes give photographer-controlled per-color luminance mapping (red filter, green filter, etc.) without leaving the dedicated B&W primitive.

```
chemigram apply-primitive --entry bw_convert \
  --param bright_red=0.3 --param bright_blue=-0.2     # red-filter sim
sigmoid_contrast --value 2.5                            # B&W typically wants extra contrast
```

The 8 `bright_X` axes (`bright_red`, `bright_orange`, `bright_yellow`, `bright_green`, `bright_cyan`, `bright_blue`, `bright_lavender`, `bright_magenta`) range `[-1.0, 1.0]`; default 0 is neutral grayscale. Positive lightens that color band's contribution to luminance; negative darkens. The chemigram analog of Photoshop's Channel Mixer (Monochrome) and Silver Efex's color filters.

For pre-baked B&W *recipes* drawn from the photographer-workflow survey:
- `look_bw_landscape_dramatic` — red-filter sim + sigmoid 1.6 + clarity 0.5; storm-cloud drama
- `look_bw_high_contrast_chiaroscuro` — Page-style chiaroscuro
- `look_bw_classic_neutral` — Adams neutral baseline
- `look_bw_silver_efex_zone_balanced` — Silver-Efex-style zone balance
- `look_bw_split_tone_warm_shadows` — selenium-print warm-shadow split-tone

Pre-v1.10.0 channel-mixer variants `bw_sky_drama` and `bw_foliage` remain available for the channelmixerrgb-mv3 mechanic; both apply hard-coded grey weights without exposing per-band axes.

`saturation_global --value -1.0` is also valid for "drop all color" but does so without channel-aware luminance mapping — different parts of the frame can read at unintuitive luminance values depending on input hue. The dedicated B&W entries are the better default; reach for `saturation_global --value -1.0` only when you want a no-frills desaturation.

---

## Compositional emphasis

### "Pull the eye toward the subject"

```
radial_subject_lift              # +0.6 EV on the subject area (centered ellipse)
vignette_medium                  # darken corners to push attention inward
```

Optionally swap `vignette_medium` for `rectangle_subject_band_dim` if the distraction is on a horizontal band rather than the corners.

### "De-emphasize a distracting horizon"

```
rectangle_subject_band_dim       # -0.3 EV in a horizontal mid-band
```

Single-primitive recipe. The mask-bound rectangle is calibrated for typical horizon-band positions; for off-band horizons, author a personal variant.

### "Push the foreground forward"

```
gradient_bottom_lift_shadows     # mask-bound; +0.4 EV on bottom half
shadows_global_+                 # global shadow lift +0.05 (subtle)
```

The gradient mask localizes the lift to the actual foreground. `shadows_global_+` adds a small global push so even the unmasked region reads slightly brighter.

---

## Texture and finish

### "Film-look polish"

```
sigmoid_contrast --value 1.0     # mild S-curve (avoid digital aggression)
grain_strength --value 25        # visible texture
vignette --value -0.25           # corner softening
```

Optionally finish with `clarity_painterly` for a gentle micro-contrast.

### "Modern HDR-ish (handle carefully)"

```
sigmoid_contrast --value 2.5
bilat_clarity_strength --value 1.5
chroma_boost_midtones
chroma_boost_highlights
```

Reads as commercial / advertising. Easy to overdo. If the result feels harsh, pull back to `clarity_painterly` first, then `sigmoid_contrast --value 1.0`.

### "Soft painterly mood"

```
clarity_painterly                # soft local contrast
sigmoid_contrast --value 1.0
grain_strength --value 8         # subtle texture
grade_highlights_warm            # gentle warmth in highlights
```

Pairs well with low-saturation portraits and quiet landscapes.

---

## Named-mask composition (RFC-032)

Named maskdefs ship as a fourth vocabulary kind — `mask_sky`, `mask_skin_region`, `mask_luminosity_brightest_quartile`, etc. Reference them by name in any `mask_spec` argument:

```
chemigram apply-primitive --entry hsl_saturation \
  --param sat_orange=-0.3 \
  --mask-spec '{"kind":"named","name":"mask_skin_region"}'
```

Or pre-bake the named mask into a manifest entry — `skin_uniformity` and `skin_smooth_painterly` already do this so the photographer doesn't have to remember the binding. List with `chemigram vocab list-masks -p expressive-baseline` and inspect with `chemigram vocab show-mask <name>`.

The maskdefs split into two families:

- **Parametric-only** (`mask_skin_region`, `mask_foliage_green`, `mask_water_blue_cyan`, `mask_luminosity_*`) — the parametric `range_filter` IS the canonical move. Always reach for the named reference.
- **Content-aware** (`mask_sky`, `mask_subject`, `mask_eye_region`) — the parametric fallback is "good enough sometimes." For higher-precision work, escalate to LLM-vision construction per `llm-vision-for-masks.md` Pattern 7. The maskdef's `llm_vision_prompt` field is the canonical prompt for that escalation.

## Batched per-region adjustment (RFC-031)

For "one move with internal structure" — dodge-and-burn, eye-region detail lifts, skin-spot harmonization — `apply-per-region` applies one primitive to N mask-bound regions atomically. Each region is a `mask_spec` + optional `parameter_values` pair; all regions validate first, then apply as one snapshot.

### "Sculpt the face — dodge and burn"

```
chemigram apply-per-region <image_id> --entry exposure --regions '[
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.4,"center_y":0.35,"radius_x":0.05,"radius_y":0.07,"border":0.03}},"parameter_values":{"ev":0.3}},
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.6,"center_y":0.35,"radius_x":0.05,"radius_y":0.07,"border":0.03}},"parameter_values":{"ev":0.3}},
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.5,"center_y":0.5,"radius_x":0.06,"radius_y":0.04,"border":0.04}},"parameter_values":{"ev":0.2}},
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.5,"center_y":0.7,"radius_x":0.18,"radius_y":0.08,"border":0.05}},"parameter_values":{"ev":-0.3}}
]'
```

Six lit regions + six shadowed regions = one snapshot, six `multi_priority`-stacked exposure instances in the synthesized XMP. The agent reasons about it as one move ("sculpt the face"); chemigram tracks it as one log entry.

### "Sky and foreground twin move"

Mix named-mask references with inline drawn forms in a single batch:

```
chemigram apply-per-region <image_id> --entry exposure --regions '[
  {"mask_spec":{"kind":"named","name":"mask_sky"},"parameter_values":{"ev":-0.4}},
  {"mask_spec":{"kind":"named","name":"mask_luminosity_darkest_quartile"},"parameter_values":{"ev":0.3}}
]'
```

Sky cooled and darkened; foreground shadows lifted; one snapshot. The named-mask references resolve at apply time to their parametric specs.

### Mixed-op per-region (RFC-036)

For composite moves like "lighten the iris **and** sharpen the lashes" — primitives differ across regions but the move is conceptually one snapshot — `apply-per-region` accepts an `ops` array per region. Each op names a `primitive_name` with optional `parameter_values`:

```
chemigram apply-per-region <image_id> --regions '[
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.45,"center_y":0.4,"radius_x":0.04,"radius_y":0.05,"border":0.02}},
   "ops":[{"primitive_name":"exposure","parameter_values":{"ev":0.3}},
          {"primitive_name":"sharpen","parameter_values":{"amount":0.8}}]},
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.55,"center_y":0.4,"radius_x":0.04,"radius_y":0.05,"border":0.02}},
   "ops":[{"primitive_name":"exposure","parameter_values":{"ev":0.3}},
          {"primitive_name":"sharpen","parameter_values":{"amount":0.8}}]}
]'
```

Per-(operation, region) `multi_priority` allocation keeps stacked instances of the same op (e.g., exposure on multiple regions) coexisting cleanly. Drop the top-level `--entry` flag when using mixed-op shape; the discriminator is the presence of `ops` on any region.

Use mixed-op when the regions are conceptually one move (eye-region work, dodge-and-burn with selective sharpening); fall back to multiple `apply-per-region` calls when the moves are conceptually separate.

### Strength scaling on L2 looks (RFC-035)

Apply any L2 look at a fraction of its authored intensity with the `--strength` flag (range `[0.0, 1.0]`; default `1.0` = authored values; `0.0` = identity / no-op):

```
chemigram apply-primitive --entry look_landscape_dramatic_moody --strength 0.6
```

Each parameterized field interpolates linearly between the module's identity value and the authored value:

> `interpolated = identity + strength * (authored - identity)`

For `look_landscape_dramatic_moody` at `strength=0.5`, sigmoid contrast of 1.7 becomes `1 + 0.5 * (1.7 - 1) = 1.35`, colorbalancergb saturation_midtones of 0.15 becomes `0 + 0.5 * 0.15 = 0.075`, etc. Non-parameterized fields (sigmoid mode, vignette shape, etc.) preserve the look's authored values regardless of strength — strength only scales what's parameterizable. Modules without a registered parameterize decoder pass through unchanged.

When to reach for `--strength`: dialing back an L2 look that's "almost right but a bit much" is a one-flag adjustment, not a re-author of the look. Authoring full-strength looks and toning them down at apply time is the recommended workflow.

## Anchor-and-sync workflow (RFC-037)

`propagate_state` is the LR-Sync analog: nail the post-processing on one image, then propagate that edit state to a list of related target images. The target images inherit every history entry from the source workspace **except** framing-bound ops that must stay per-image:

```
chemigram propagate-state <anchor_id> \
  --to <id1> --to <id2> --to <id3> \
  --label "wedding-reception-batch-2026-05-08"
```

The source `<anchor_id>` is positional. Each `--to <id>` flag names one target (repeatable; cap 200 per call). Skip extra ops with repeated `--exclude-op <name>`. Use `--include-per-image` to override the framing-bound auto-exclusion (only for tripod-fixed series).

Framing-bound exclusions (auto-applied):
- `ashift` — perspective correction (per-camera-angle)
- `crop` — composition (per-image)
- `retouch` — heal/clone (location-specific)
- `lens` — lens correction (per-camera/lens)
- Any op bound to a drawn mask (gradient, ellipse, rectangle, path) — coordinates are image-specific

What does propagate: white balance, exposure, sigmoid, colorbalancergb, colorequal (HSL), bilat, sharpen, denoiseprofile, grain, hazeremoval, and any op bound to a parametric range mask (color-range / luminance-range — these are content-relative, not coordinate-bound).

Each target gets a single snapshot capturing the full propagated state plus an explicit `label` for the operation log. The agent can later inspect the label to see which images were synced from the same anchor.

When to reach for `propagate-state`:

- **Wedding / event series** — anchor the look on the best frame, propagate to the rest of the burst
- **Product photography** — anchor on the hero shot, propagate to the variants (color-A vs color-B of the same product)
- **Series consistency** — keep a body of work coherent (a magazine spread, a portfolio set)

When NOT to reach for `propagate-state`:

- **Cross-genre images** — propagating a portrait look to a landscape doesn't make sense
- **Different cameras / lenses** — color science differs; framing-bound op exclusion partially handles this but visual review per target is still warranted
- **Masked moves where the mask is drawn** — those are explicitly framing-bound and won't propagate

## When patterns don't fit

Composition is per-image. These are starting points, not prescriptions. The agent's job (and yours) is to judge each move's render against the brief — if a pattern that "should work" doesn't, that's a vocabulary gap or a composition that needs a different recipe.

When you reach for a pattern that doesn't yet exist:

1. The agent will improvise with closest-available primitives and log a `vocabulary_gap`.
2. After the session, read the gap log: `cat ~/Pictures/Chemigram/<id>/vocabulary_gaps.jsonl | jq`.
3. If the gap recurs across images, that's a signal to author a personal vocabulary entry capturing the move. See [`authoring-vocabulary-entries.md`](authoring-vocabulary-entries.md).

The vocabulary becomes voice not by exhaustive coverage but by accumulating exactly the moves you keep reaching for.

---

## See also

- [`vocabulary/packs/expressive-baseline/README.md`](https://github.com/chipi/chemigram/blob/main/vocabulary/packs/expressive-baseline/README.md) — full entry catalog with descriptions, tags, intensity ladders
- [`docs/guides/authoring-vocabulary-entries.md`](authoring-vocabulary-entries.md) — author your own personal-pack entries
- [`docs/getting-started.md`](../getting-started.md#growing-your-vocabulary) — Phase 2 vocabulary-growth workflow
- [`docs/prd/PRD-003-vocabulary-as-voice.md`](../prd/PRD-003-vocabulary-as-voice.md) — the user-value argument for the vocabulary system
