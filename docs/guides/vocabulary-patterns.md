# Vocabulary patterns

> "For *this* intent, reach for *that* composition."
>
> A practical guide to combining primitives from `starter` + `expressive-baseline` to satisfy common photographer intents. Each pattern is a small recipe — typically 2–4 primitives applied in sequence — that the agent (or you) can lean on.

This guide assumes both packs loaded:

```python
from chemigram.core.vocab import load_packs
vocab = load_packs(["starter", "expressive-baseline"])
```

For the full entry catalog see [`vocabulary/packs/expressive-baseline/README.md`](../../vocabulary/packs/expressive-baseline/README.md). For authoring your own primitives see [`authoring-vocabulary-entries.md`](authoring-vocabulary-entries.md).

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
clarity_painterly                # gentle global clarity (or clarity_strong if you want crisper)
```

Works when the subject sits roughly center-frame. If the subject is off-center, use a personal variant of the radial with adjusted center coordinates (see authoring guide).

### "Aggressive contemporary contrast"

```
contrast_high                    # sigmoid s-curve, contrast 2.5
blacks_crushed                   # crush the deep shadows
chroma_boost_midtones            # bring the chroma back in the mids (contrast often kills chroma)
```

Optionally cap with `vignette_medium` for a polished feel.

### "Faded film stock"

```
contrast_low                     # mild s-curve
blacks_lifted                    # lift target black
grain_medium                     # visible film-grain texture
```

The combination evokes a faded medium-format aesthetic. Add `grade_shadows_warm` for warm-tone grading on top.

### "Blown highlights, hot afternoon"

```
highlights_recovery_strong       # pull back clipped highlights
gradient_top_dampen_highlights   # mask-bound, drops top of frame -0.5 EV
```

Apply in order: recovery first (acts on full frame), then the gradient mask localizes any remaining dampening to the actual hot region.

---

## Color

### "Cinematic teal-and-orange"

```
grade_highlights_warm            # +orange in highlights
grade_shadows_cool               # +blue in shadows
sat_boost_moderate               # bring saturation up so the grade reads
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
contrast_low                     # avoid aggressive S-curves on skin
chroma_boost_highlights          # let skin highlights bloom slightly
clarity_painterly                # soft local contrast (clarity_strong damages skin)
```

Stay away from `contrast_high`, `clarity_strong`, and `chroma_boost_midtones` for portraiture — all three destroy skin tonality.

### "Monochromatic conversion (placeholder)"

```
sat_kill                         # global saturation -1.0 (drops all color)
contrast_high                    # compensate for the contrast loss B&W typically wants
```

This is the placeholder until the channelmixerrgb B&W trio (`bw_convert`, `bw_sky_drama`, `bw_foliage`) ships in v1.6.0 (#63). `sat_kill` desaturates without channel-aware luminance mapping, which is what the dedicated B&W entries will fix — different parts of the frame will read at different luminance values depending on color, and the dedicated entries will tune that.

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
contrast_low                     # mild S-curve (avoid digital aggression)
grain_medium                     # visible texture
vignette_subtle                  # corner softening
```

Optionally finish with `clarity_painterly` for a gentle micro-contrast.

### "Modern HDR-ish (handle carefully)"

```
contrast_high
clarity_strong
chroma_boost_midtones
chroma_boost_highlights
```

Reads as commercial / advertising. Easy to overdo. If the result feels harsh, pull back to `clarity_painterly` first, then `contrast_low`.

### "Soft painterly mood"

```
clarity_painterly                # soft local contrast
contrast_low
grain_fine                       # subtle texture
grade_highlights_warm            # gentle warmth in highlights
```

Pairs well with low-saturation portraits and quiet landscapes.

---

## When patterns don't fit

Composition is per-image. These are starting points, not prescriptions. The agent's job (and yours) is to judge each move's render against the brief — if a pattern that "should work" doesn't, that's a vocabulary gap or a composition that needs a different recipe.

When you reach for a pattern that doesn't yet exist:

1. The agent will improvise with closest-available primitives and log a `vocabulary_gap`.
2. After the session, read the gap log: `cat ~/Pictures/Chemigram/<id>/vocabulary_gaps.jsonl | jq`.
3. If the gap recurs across images, that's a signal to author a personal vocabulary entry capturing the move. See [`authoring-vocabulary-entries.md`](authoring-vocabulary-entries.md).

The vocabulary becomes voice not by exhaustive coverage but by accumulating exactly the moves you keep reaching for.

---

## See also

- [`vocabulary/packs/expressive-baseline/README.md`](../../vocabulary/packs/expressive-baseline/README.md) — full entry catalog with descriptions, tags, intensity ladders
- [`docs/guides/authoring-vocabulary-entries.md`](authoring-vocabulary-entries.md) — author your own personal-pack entries
- [`docs/getting-started.md`](../getting-started.md#growing-your-vocabulary) — Phase 2 vocabulary-growth workflow
- [`docs/prd/PRD-003-vocabulary-as-voice.md`](../prd/PRD-003-vocabulary-as-voice.md) — the user-value argument for the vocabulary system
