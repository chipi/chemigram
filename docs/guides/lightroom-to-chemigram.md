# Lightroom → chemigram cheat sheet

> "Where do I find X?" mapping for users coming from Lightroom. v1.8.0 ships 51/52 daily-use Lightroom controls (98%); the remaining gap is documented at the end. Each Lightroom control maps to a CLI invocation + MCP tool example, plus notes on what's different.

For the underlying state of what's covered, see [`capability-survey.md`](../capability-survey.md) § 13. This guide is the "I know Lightroom; show me chemigram" view of the same surface.

## Quick orientation

Lightroom's Develop panels map onto chemigram's three-layer vocabulary (per [`docs/concept/03-data-catalog.md`](../concept/03-data-catalog.md)):

- **Lightroom panel sliders** → **L3 primitives** (single-module, parameterized or discrete `.dtstyle` entries)
- **Lightroom presets** → **L2 looks** (multi-module composites)
- **Lightroom workspace settings** (camera profile defaults) → **L1 baselines** (camera-specific templates)

Every Lightroom slider is one CLI invocation. The general shape:

```sh
chemigram apply-primitive <name> --image <id> [--value <V> | --param NAME=V ...]
```

Or via MCP:

```python
apply_primitive(name="<entry_name>", image_id="<id>", value=V, parameters={...})
```

---

## Panel: Light

| Lightroom | chemigram | Notes |
|---|---|---|
| Exposure | `apply-primitive exposure --value V` | Range [-3.0, 3.0] EV. |
| Contrast | `apply-primitive sigmoid_contrast --value V` | Sigmoid-based; range [0.5, 5.0]. 1.5 = no-op. |
| Highlights | `apply-primitive highlights_clip_threshold --value V` | Or `apply-primitive toneequalizer --param highlights=V` for the 9-band approach. |
| Shadows | `apply-primitive toneequalizer --param shadows=V` | Or the mask-bound `gradient_bottom_lift_shadows`. |
| Whites | `apply-primitive toneequalizer --param whites=V` | Or discrete `whites_open`. |
| Blacks | `apply-primitive toneequalizer --param blacks=V` | Or discrete `blacks_lifted` / `blacks_crushed`. |
| **Tone Curve** | ❌ Not yet shipped | Tracked as #94; needs darktable-GUI baseline capture session. |

**Coverage: 6/7.**

### Worked example

> **Lightroom:** "Lift the shadows by +20."
> **chemigram:** `chemigram apply-primitive toneequalizer --param shadows=0.2 --image DSCF1234`

> **Lightroom:** "S-curve the contrast."
> **chemigram:** `chemigram apply-primitive sigmoid_contrast --value 1.8 --image DSCF1234`

---

## Panel: Color

| Lightroom | chemigram | Notes |
|---|---|---|
| WB Temp (Kelvin) | `apply-primitive wb_kelvin_delta --param kelvin_delta=V` | Range [-3000, +3000] K. Positive = warmer. Linear approximation; for raw RGB control use `temperature` directly. |
| WB Tint | `apply-primitive wb_kelvin_delta --param tint_delta=V` | Range [-200, +200]. Positive = magenta. |
| Vibrance | `apply-primitive vibrance --value V` | Range [-1.0, +1.0]. |
| Saturation | `apply-primitive saturation_global --value V` | Range [-1.0, +1.0]. |

**Coverage: 4/4.**

> The raw `temperature` entry is also available for users who want to set red/green/blue coefficients directly: `apply-primitive temperature --param red_coeff=V --param green_coeff=V --param blue_coeff=V`. The `wb_kelvin_delta` entry is the photographic-units wrapper; both ride the same underlying decoder.

---

## Panel: Color Mixer (HSL)

Lightroom's HSL Color Mixer = 24 sliders (Hue / Sat / Luminance × 8 colors). All shipped via [`colorequal`](../adr/ADR-083-hsl-color-mixer-via-colorequal.md) (RFC-023).

| Lightroom | chemigram |
|---|---|
| HSL Hue per color | `apply-primitive hsl_hue --param hue_<color>=V` |
| HSL Saturation per color | `apply-primitive hsl_saturation --param sat_<color>=V` |
| HSL Luminance per color | `apply-primitive hsl_luminance --param bright_<color>=V` |

Colors: `red`, `orange`, `yellow`, `green`, `cyan`, `blue`, `lavender`, `magenta` (Lightroom calls them red / orange / yellow / green / aqua / blue / purple / magenta).

Hue is in degrees [-180, +180]; sat / luminance are normalized [-1.0, +1.0].

**Coverage: 24/24.**

### Worked examples

> **Lightroom:** "Make the sky deeper."
> **chemigram:** `chemigram apply-primitive hsl_luminance --param bright_blue=-0.3 --image DSCF1234`

> **Lightroom:** "Warm up the foliage (shift greens toward yellow)."
> **chemigram:** `chemigram apply-primitive hsl_hue --param hue_green=15.0 --image DSCF1234`

> **Lightroom:** "Mute the orange skin tones slightly."
> **chemigram:** `chemigram apply-primitive hsl_saturation --param sat_orange=-0.1 --image DSCF1234`

---

## Panel: Color Grading

Lightroom's Color Grading panel = per-zone hue / saturation / luminance + global blending + balance.

| Lightroom | chemigram | Notes |
|---|---|---|
| Shadows: hue | `apply-primitive hue_shadows --value V` | [0, 360]°. Or discrete `grade_shadows_warm` / `grade_shadows_cool`. |
| Shadows: saturation | `apply-primitive saturation_shadows --value V` | [-1.0, +1.0] |
| Midtones: hue | `apply-primitive hue_midtones --value V` | Or discrete `grade_midtones_warm` / `grade_midtones_cool`. |
| Midtones: saturation | `apply-primitive saturation_midtones --value V` | |
| Highlights: hue | `apply-primitive hue_highlights --value V` | Or discrete `grade_highlights_warm` / `grade_highlights_cool`. |
| Highlights: saturation | `apply-primitive saturation_highlights --value V` | |
| Global: hue rotation | `apply-primitive hue_angle --value V` | Rotates all pixels uniformly. |
| Per-zone luminance | `apply-primitive brilliance_<zone> --value V` | `brilliance_shadows` / `brilliance_midtones` / `brilliance_highlights` / `brilliance_global`. |
| Blending | `apply-primitive shadows_weight --value V` + `highlights_weight --value V` | Falloff between zones. |
| Balance | `apply-primitive white_fulcrum --value V` | Shifts the shadow/highlight midpoint. |

**Coverage: 7/7 (counting the panel as a whole).**

### Quick split-tone

> **Lightroom:** Apply a teal-orange split toning preset.
> **chemigram:** `chemigram apply-primitive grade_split_warm_cool --image DSCF1234` (a discrete L3 entry combining `grade_shadows_cool` + `grade_highlights_warm` in one move; #110).

For full cinematic looks, see L2 looks below.

---

## Panel: Effects

| Lightroom | chemigram | Notes |
|---|---|---|
| Texture | `apply-primitive texture --param first=V` | Via darktable's `diffuse-or-sharpen`. Negative smooths fine detail; positive enhances. |
| Clarity | `apply-primitive bilat_clarity_strength --value V` | Bilateral local contrast. Range [-1.0, 4.0]. Discrete kinds also: `clarity_painterly`, `clarity_etched`, `clarity_dreamy`. |
| Dehaze | `apply-primitive dehaze --param strength=V` | Range [-1.0, +1.0]. Negative *adds* haze. |
| Vignette | `apply-primitive vignette --value V` | Range [-1.0, +1.0]. Discrete kinds: `vignette_subtle`, `vignette_strong`. |
| Grain | `apply-primitive grain_strength --value V` | Range [0.0, 100.0]. |

**Coverage: 5/5.**

---

## Panel: Transform

Shipped via the `ashift` module (#101).

| Lightroom | chemigram |
|---|---|
| Rotate (degrees) | `apply-primitive transform --param transform_rotation=V` |
| Vertical perspective (keystone) | `apply-primitive transform --param transform_lensshift_v=V` |
| Horizontal perspective | `apply-primitive transform --param transform_lensshift_h=V` |
| Shear | `apply-primitive transform --param transform_shear=V` |
| Aspect adjust | `apply-primitive transform --param transform_aspect=V` |

**Coverage: 5/5.**

> Lightroom's "Auto" transform option (auto-detect verticals / horizontals from image content) is not yet shipped. Manual rotation works fine; auto-detection would need a sibling provider per the BYOA principle.

---

## Panel: Detail

| Lightroom | chemigram | Notes |
|---|---|---|
| Sharpening (Amount) | `apply-primitive sharpen --value V` | Range [0.0, 2.0]. Discrete kinds: `sharpen_edge_only`, `sharpen_overall`. |
| Sharpening (Radius / Detail / Masking) | Not directly exposed | Sharpen module's defaults handle these; if you need custom values, hand-author a discrete entry. |
| Noise Reduction (Luminance) | `apply-primitive denoise --param denoise_strength=V` | NLMEANS mode. Range [0.001, 1000.0]. Wavelet-mode fallback tracked as #100 task C. |
| Noise Reduction (Color) | Implicit in denoise | darktable's denoiseprofile handles luminance + chroma noise together. |

**Coverage: ~2/4.** Lightroom's separate Sharpening Radius / Detail / Masking sliders aren't exposed as parameters; chemigram pins them at darktable defaults. If you need them, hand-author a discrete sharpen variant.

---

## Panel: Lens Corrections

Lens correction shipped via the `lens` module (#95). Photographic effect requires populated lensfun identifier strings — see #100 task B for the EXIF auto-binding follow-up.

| Lightroom | chemigram | Notes |
|---|---|---|
| Profile-based correction | `apply-primitive lens_correction` | Uses lensfun via `camera`/`lens` strings. Currently empty — populated when EXIF auto-binding lands. |
| Distortion (manual) | `apply-primitive lens_correction --param lens_cor_distortion=V` | Range [0.0, 1.0]. |
| Defringe (CA) | `apply-primitive lens_correction --param lens_tca_r=V --param lens_tca_b=V` | Manual TCA shift; 1.0 = no shift. |
| Vignette correction | `apply-primitive lens_correction --param lens_v_strength=V` | Manual override; range [-1.0, 1.0]. |

---

## Panel: Camera Calibration

Mostly handled by darktable's input color profile. Manual primaries-tuning isn't exposed as a chemigram primitive today; if needed, hand-author a discrete `colorin` entry.

---

## Lightroom presets → chemigram L2 looks

Lightroom users typically reach for preset packs (Adobe / VSCO / Mastin Labs / etc.). chemigram ships **13 L2 looks** covering the most common photographic recipes:

**Cinematic / film genre:**
- `look_cinematic_teal_orange` — Hollywood blockbuster
- `look_film_kodachrome` — Saturated reds, warm midtones
- `look_film_portra` — Kodak Portra 400 portrait
- `look_vintage_film` — Faded film aesthetic

**Portrait:**
- `look_portrait` — Gentle skin-protective default
- `look_high_key_portrait` — Bright, soft, lifted
- `look_low_key_portrait` — Dark, dramatic, crushed
- `look_moody_dramatic` — High contrast, desaturated

**Decade:**
- `look_70s_film` — Warm, golden, medium grain
- `look_90s_grain` — Heavy grain, slightly cool
- `look_2000s_digital` — Clean, oversaturated

**Landscape / neutral:**
- `look_landscape` — Vibrant dramatic
- `look_neutral` — Teaching baseline (starter pack)

Apply any of them with:

```sh
chemigram apply-primitive look_<name> --image <id>
```

The visual-proof gallery shows each look applied to the synthetic ColorChecker chart: see [`docs/guides/visual-proofs.md`](visual-proofs.md).

---

## Lightroom features chemigram doesn't yet have

| Lightroom feature | chemigram status | Tracked as |
|---|---|---|
| **Spot removal / heal** | Not shipped | RFC-025 drafted; ADR pending |
| **AI subject mask** | Not shipped (BYOA arc) | RFC-024 (range masks) defers AI to RFC-026 |
| **Range masks** (color-range, luminance-range, depth-range) | Not shipped | RFC-024 drafted |
| **Tone Curve** (parametric / point curve) | Not shipped | #94; needs darktable-GUI baseline session |
| **HSL precision via Range slider** | Not shipped (95% covered via colorequal) | #98 colorzones spline-curve fallback |
| **Profiled lens auto-correction (EXIF-bound)** | Decoder shipped; auto-bind pending | #100 task B |
| **Auto-Tone / Auto-WB** | Not shipped | The BYOA arc — sibling project shape per ADR-007 |
| **Camera Calibration primaries-tuning** | Not exposed as primitive | Hand-author `colorin` discrete entry if needed |

---

## When chemigram differs (and why)

- **WB Kelvin:** chemigram exposes `kelvin_delta` (relative shift) instead of absolute Kelvin. The mapping from absolute Kelvin to RGB coefficients is camera-specific (depends on primaries). Linear approximation is daily-use accurate; perfect chromatic adaptation (CAT02 / Bradford) is out of scope for the UX wrapper.
- **HSL backing module:** chemigram uses darktable's modern `colorequal` mv4, not the older `colorzones`. ADR-083 records the choice. Trade-off: 95% of HSL workflow works perfectly; the remaining 5% (per-zone Range slider falloff curves) is tracked as #98.
- **Vocabulary growth:** Lightroom presets are user-installed. chemigram's vocabulary growth is **use-driven**: the agent logs gaps via `log_vocabulary_gap` when it reaches for a missing primitive; the photographer or maintainer then authors the missing entry. See [`docs/guides/gap-log.md`](gap-log.md) and CLAUDE.md's Phase 2 framing.
- **Agent loop vs. direct manipulation:** chemigram is agent-first. Mode A loops are the canonical interaction. The CLI exposes the same surface for direct invocation, but the design optimizes for agent reasoning (taste / brief / notes / session transcripts) more than slider-by-slider iteration.

---

## See also

- [`capability-survey.md`](../capability-survey.md) — full module-by-module state
- [`docs/concept/00-introduction.md`](../concept/00-introduction.md) — what chemigram is and why
- [`docs/guides/visual-proofs.md`](visual-proofs.md) — every primitive rendered against a reference chart
- [`docs/guides/gap-log.md`](gap-log.md) — Phase 2 use-driven feedback loop
