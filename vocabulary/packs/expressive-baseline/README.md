# expressive-baseline

The comprehensive baseline vocabulary pack for expressive taste articulation.

**81 entries (post-v1.9.0)** calibrated to darktable 5.4.1, covering the parameter dimensions identified in the taste-library research (Van Gogh, Rembrandt, Picasso, Adams, Capa, Leiter) plus the v1.6–v1.9 expansions. Composition:

- **18 parameterized** primitives across 11 modules (Path C; RFC-021 / ADR-077..080) — `exposure`, `vignette`, `colorbalancergb` (saturation_global / vibrance / chroma_global / hue_angle / brilliance × 4), `sigmoid_contrast`, `bilat_clarity_strength`, `grain_strength`, `highlights_clip_threshold`, `temperature`, `crop`, `sharpen`, `toneequalizer`, `dehaze`, plus v1.7+ Bucket A additions and the v1.8 HSL via `colorequal`.
- **L2 looks (13)** — the original `look_neutral`, plus 4 portrait/landscape/vintage looks, plus the **9 cinematic looks** (#104), plus the **5 compositional-mask L2 looks** added in v1.9.0 that exercise drawn + parametric range_filter intersection (`look_subject_lift_dark_only`, `look_sky_blue_deepen`, `look_horizon_warm_glow`, `look_subject_brighten_highlights`, `look_dark_pixels_global_lift`).
- **Mask-bound L3 entries (4)** — `gradient_top_dampen_highlights`, `gradient_bottom_lift_shadows`, `radial_subject_lift`, `rectangle_subject_band_dim`. The new compositional looks above demonstrate the v1.9.0 mask trilogy (RFC-024/025/026/029).
- **L3 discrete kinds** — channelmixerrgb B&W trio + 7 clarity/sharpen/vignette/split-grade variants (#110) + the existing magnitude-ladder discretes preserved as Tier 0 teaching artifacts.

The companion **`apply_spot` MCP tool** (RFC-025 / ADR-087) ships alongside the pack — sister to `apply_primitive` for spot heal/clone retouch (no vocabulary entry required; the tool IS the primitive surface for that class).

## Composition with `starter`

This pack is **opt-in** and complements the minimal `starter` pack rather than replacing it. Photographers typically load both:

```python
from chemigram.core.vocab import load_packs
vocab = load_packs(["starter", "expressive-baseline"])
```

The starter pack stays minimal (2 entries — `wb_warm_subtle` + `look_neutral`) as a teaching artifact post-v1.6.0 (the original discrete `expo_+0.5` / `expo_-0.5` were collapsed into the parameterized `exposure` entry that lives in expressive-baseline). The expressive-baseline pack ships the comprehensive set needed for actual artist-profile work.

## Path A vs Path B authoring

- **Path A** (16 entries) — modules already in the baseline XMP. No engine prerequisites.
  - `highlights`, `sigmoid`, `temperature`, `exposure`
- **Path B** (19 entries) — modules NOT in the baseline; require the synthesizer's Path B (new-instance addition) plus an `iop_order` value populated by `scripts/probe-iop-order.py` per ADR-063.
  - `colorbalancergb`, `localcontrast`, `grain`, `vignette`

Each Path B entry carries `iop_order`, `iop_order_source`, and `iop_order_darktable_version` in the manifest. If darktable bumps a module's modversion or pipeline order, RFC-007's drift detection flags the entry for re-validation.

---

## Catalog

All 35 entries grouped by subtype. The mask-bound entries (drawn-form geometry) are listed separately at the bottom.

### exposure (4 global + 4 mask-bound)

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `expo_+0.3` | exposure | exposure, lift, subtle | Lift exposure +0.3 EV (smaller than starter +0.5). |
| `expo_-0.3` | exposure | exposure, lower, subtle | Lower exposure -0.3 EV (smaller than starter -0.5). |
| `shadows_global_+` | exposure | shadows, lift | Lift global black level +0.05. |
| `shadows_global_-` | exposure | shadows, deepen | Lower global black level -0.05 (deepen shadows). |

(The 4 mask-bound exposure entries — `gradient_top_dampen_highlights`, `gradient_bottom_lift_shadows`, `radial_subject_lift`, `rectangle_subject_band_dim` — are listed under "Mask-bound" below.)

### sigmoid (4 — tone curve)

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `sigmoid_contrast` | sigmoid | tone, contrast, parameterized | Parameterized s-curve contrast; `--value V` in [0.5, 5.0]. 1.0 = mild, 1.5 = darktable default, 2.5 = aggressive. (RFC-021; replaces v1.5.x contrast_low / contrast_high.) |
| `blacks_lifted` | sigmoid | tone, blacks, lift | Lift target black to 0.5. |
| `blacks_crushed` | sigmoid | tone, blacks, crush | Crush blacks: target 0.001 + skew -0.3. |
| `whites_open` | sigmoid | tone, whites, open | Open whites: target 300 (3x default). |

### highlights (1)

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `highlights_clip_threshold` | highlights | highlights, parameterized | Parameterized highlight-recovery clip threshold; `--value V` in [0.0, 2.0]. 0.95 = subtle, 0.85 = strong, 0.5 = aggressive. (RFC-021; replaces v1.5.x highlights_recovery_subtle / highlights_recovery_strong.) |

### colorbalancergb (9 — color grading)

Saturation:

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `saturation_global` | colorbalancergb | saturation, global, parameterized | Parameterized global saturation; `--value V` in [-1.0, +1.0]. -1.0 = monochrome; +0.5 = strong boost. (RFC-021; replaces v1.5.x sat_kill / sat_boost_moderate / sat_boost_strong.) |
| `vibrance_+0.3` | colorbalancergb | vibrance, boost | Global vibrance +0.3. |

Color grading (split-tone style):

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `grade_shadows_warm` | colorbalancergb | grade, shadows, warm | Warm shadows (orange tint, hue 30°, chroma 0.3). |
| `grade_shadows_cool` | colorbalancergb | grade, shadows, cool | Cool shadows (blue tint, hue 210°, chroma 0.3). |
| `grade_highlights_warm` | colorbalancergb | grade, highlights, warm | Warm highlights (orange tint, hue 45°, chroma 0.2). |
| `grade_highlights_cool` | colorbalancergb | grade, highlights, cool | Cool highlights (blue tint, hue 200°, chroma 0.2). |

Per-zone chroma:

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `chroma_boost_shadows` | colorbalancergb | chroma, shadows, boost | Boost shadow chroma +0.3. |
| `chroma_boost_midtones` | colorbalancergb | chroma, midtones, boost | Boost mid-tone chroma +0.3. |
| `chroma_boost_highlights` | colorbalancergb | chroma, highlights, boost | Boost highlight chroma +0.3. |

### localcontrast (2 — clarity)

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `bilat_clarity_strength` | localcontrast | clarity, parameterized | Parameterized clarity strength; `--value V` in [-1.0, 4.0]. 1.5 = clarity_strong-equivalent. (RFC-021; replaces v1.5.x clarity_strong — strength axis only.) |
| `clarity_painterly` | localcontrast | clarity, painterly, soft | Soft painterly local contrast (detail 0.4). Different *kind* of clarity, not a different strength — kept as a discrete entry. |

### grain (1 — film-grain texture)

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `grain_strength` | grain | grain, parameterized | Parameterized grain strength; `--value V` in [0.0, 100.0]. 8 = fine, 25 = medium, 50 = heavy. (RFC-021; replaces v1.5.x grain_fine / grain_medium / grain_heavy.) |

### channelmixerrgb (3 — B&W conversion)

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `bw_convert` | channelmixerrgb | bw, monochrome, fundamental | Neutral B&W conversion via Rec. 709 luminance weights (R 0.2126 / G 0.7152 / B 0.0722). normalize_grey=true. |
| `bw_sky_drama` | channelmixerrgb | bw, sky, drama | B&W with red-emphasis (R 0.5 / G 0.4 / B 0.1) — classic "red filter" landscape look that lightens reds and darkens blues, emphasizing clouds against sky. |
| `bw_foliage` | channelmixerrgb | bw, foliage, green | B&W with green-emphasis (R 0.1 / G 0.7 / B 0.2) — separates foliage from neighboring tones for forest / botanical work. |

### vignette (3 — corner darkening)

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `vignette_subtle` | vignette | vignette, subtle | Subtle corner darkening; brightness -0.25. |
| `vignette_medium` | vignette | vignette, medium | Medium corner darkening; brightness -0.5. |
| `vignette_heavy` | vignette | vignette, heavy | Strong corner darkening; brightness -0.8. |

### wb (1 — white balance, multi-axis parameterized)

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `temperature` | wb | wb, parameterized, multi-axis | Parameterized white balance — first multi-parameter ship. Pass `--param red_coeff=V --param blue_coeff=V`; both range [0.5, 4.0], default 1.0 (no shift). Warmer: red↑; cooler: blue↑. (RFC-021; replaces v1.5.x wb_cool_subtle. Starter's `wb_warm_subtle` remains as a discrete teaching artifact.) |

---

## Mask-bound entries (4)

These four entries declare a `mask_spec` in the manifest. At apply time, the engine encodes the geometry directly into darktable's `<darktable:masks_history>` element and patches each plugin's `blendop_params` to bind it via `mask_id` (per ADR-076). No PNG, no provider, no per-image registry — the mask rides inside the XMP.

| Name | dt_form | Effect | Use case |
|-|-|-|-|
| `gradient_top_dampen_highlights` | gradient | -0.5 EV through a top-bright gradient | Sun glare, blown sky, hot top of frame |
| `gradient_bottom_lift_shadows` | gradient | +0.4 EV through a bottom-bright gradient | Foreground lift, dim ground, dampened lower frame |
| `radial_subject_lift` | ellipse | +0.6 EV in a centered ellipse | Subject emphasis when the subject sits centrally |
| `rectangle_subject_band_dim` | rectangle | -0.3 EV in a horizontal mid-band | De-emphasize a distracting horizon line |

The geometry is darktable-native — open the resulting XMP in darktable's GUI and you'll see the same drawn form you'd get from the masks tool. Edit it manually if you want; the change persists.

For authoring your own drawn-mask-bound vocabulary entries, see [`docs/guides/authoring-vocabulary-entries.md`](../../../docs/guides/authoring-vocabulary-entries.md).

---

## Intensity ladders

For tags that have intensity gradations, the relationships:

All magnitude ladders are now parameterized (RFC-021 / Phase 4 closed v1.6.0+):

- **Exposure:** `exposure --value V` (in [-3.0, +3.0])
- **Saturation:** `saturation_global --value V` (in [-1.0, +1.0])
- **Contrast (sigmoid):** `sigmoid_contrast --value V` (in [0.5, 5.0]; 1.0 = mild, 1.5 = no-op, 2.5 = aggressive)
- **Blacks (sigmoid):** `blacks_crushed` ← (no-op) → `blacks_lifted` → (no-op) → `whites_open` *(remain discrete — different kinds, not strengths on the same axis)*
- **Highlights recovery:** `highlights_clip_threshold --value V` (in [0.0, 2.0]; 0.95 = subtle, 0.85 = strong, 0.5 = aggressive)
- **Clarity:** `bilat_clarity_strength --value V` (in [-1.0, 4.0]; 1.5 = pronounced). `clarity_painterly` remains discrete — different *kind*.
- **Grain:** `grain_strength --value V` (in [0.0, 100.0]; 8 = fine, 25 = medium, 50 = heavy)
- **Vignette:** `vignette --value V` (in [-1.0, +1.0])
- **Temperature (multi-axis):** `temperature --param red_coeff=V --param blue_coeff=V` (each in [0.5, 4.0])

Pick the gentlest move that addresses the brief; stack from there.

## By-tag index

Quick lookup by intent:

- **`tone`** — `contrast_low`, `contrast_high`, `blacks_lifted`, `blacks_crushed`, `whites_open`
- **`shadows`** — `shadows_global_+`, `shadows_global_-`, `blacks_lifted`, `blacks_crushed`, `gradient_bottom_lift_shadows`
- **`highlights`** — `highlights_recovery_subtle`, `highlights_recovery_strong`, `whites_open`, `gradient_top_dampen_highlights`, `chroma_boost_highlights`, `grade_highlights_warm`, `grade_highlights_cool`
- **`saturation` / `chroma` / `vibrance`** — `saturation_global` (parameterized), `vibrance_+0.3`, `chroma_boost_shadows/midtones/highlights`
- **`grade` (split-tone)** — `grade_shadows_warm/cool`, `grade_highlights_warm/cool`
- **`clarity`** — `bilat_clarity_strength` (parameterized), `clarity_painterly` (discrete)
- **`grain`** — `grain_strength` (parameterized)
- **`vignette`** — `vignette` (parameterized)
- **`wb`** — `temperature` (parameterized, multi-axis), `wb_warm_subtle` (starter, discrete)
- **`mask` / `gradient` / `radial` / `rectangle`** — see "Mask-bound entries" above
- **`monochrome`** — `bw_convert` (Rec. 709 neutral), `bw_sky_drama` (red-emphasis), `bw_foliage` (green-emphasis); `saturation_global --value -1.0` is the channel-unaware fallback

For "for X intent, reach for Y composition" patterns, see [`docs/guides/vocabulary-patterns.md`](../../../docs/guides/vocabulary-patterns.md).

---

## Provenance

All entries authored against darktable 5.4.1 by the project maintainers per the discipline in `docs/CONTRIBUTING.md` § Vocabulary contributions. Path C reverse-engineering methodology and per-module struct mappings are documented at [`docs/guides/expressive-baseline-authoring.md`](../../../docs/guides/expressive-baseline-authoring.md).

## Adding to this pack

See `docs/CONTRIBUTING.md` § Vocabulary authoring for the procedure. Path B entries additionally require the probe-iop-order workflow (per ADR-064). For drawn-mask-bound entries, the `mask_spec` schema is documented in [`docs/guides/authoring-vocabulary-entries.md`](../../../docs/guides/authoring-vocabulary-entries.md).
