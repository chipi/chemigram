# expressive-baseline

The comprehensive baseline vocabulary pack for expressive taste articulation.

35 entries calibrated to darktable 5.4.1, covering the parameter dimensions identified in the taste-library research (Van Gogh, Rembrandt, Picasso, Adams, Capa, Leiter). 31 authored programmatically via Path C struct reverse-engineering (ADR-073) plus 4 drawn-mask-bound entries via path 4a (ADR-076).

## Composition with `starter`

This pack is **opt-in** and complements the minimal `starter` pack rather than replacing it. Photographers typically load both:

```python
from chemigram.core.vocab import load_packs
vocab = load_packs(["starter", "expressive-baseline"])
```

The starter pack stays minimal (4 entries — exposure ±0.5, warm-subtle WB, neutral L2 look) as a teaching artifact. The expressive-baseline pack ships the comprehensive set needed for actual artist-profile work.

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

### sigmoid (5 — tone curve)

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `contrast_low` | sigmoid | tone, contrast, low | Mild s-curve; sigmoid contrast 1.0. |
| `contrast_high` | sigmoid | tone, contrast, high | Aggressive s-curve; sigmoid contrast 2.5. |
| `blacks_lifted` | sigmoid | tone, blacks, lift | Lift target black to 0.5. |
| `blacks_crushed` | sigmoid | tone, blacks, crush | Crush blacks: target 0.001 + skew -0.3. |
| `whites_open` | sigmoid | tone, whites, open | Open whites: target 300 (3x default). |

### highlights (2)

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `highlights_recovery_subtle` | highlights | highlights, subtle | Subtle highlight reconstruction; clip 0.95. |
| `highlights_recovery_strong` | highlights | highlights, strong | Strong highlight reconstruction; clip 0.85. |

### colorbalancergb (11 — color grading)

Saturation:

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `sat_boost_moderate` | colorbalancergb | saturation, boost, moderate | Moderate global saturation boost (+0.25). |
| `sat_boost_strong` | colorbalancergb | saturation, boost, strong | Strong global saturation boost (+0.5). |
| `sat_kill` | colorbalancergb | saturation, kill, monochrome | Kill all saturation (global -1.0). |
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
| `clarity_strong` | localcontrast | clarity, strong | Strong local contrast / clarity (detail 1.5). |
| `clarity_painterly` | localcontrast | clarity, painterly, soft | Soft painterly local contrast (detail 0.4). |

### grain (3 — film-grain texture)

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `grain_fine` | grain | grain, subtle | Subtle film-grain texture; strength 8/100. |
| `grain_medium` | grain | grain, medium | Visible film-grain texture; strength 25/100. |
| `grain_heavy` | grain | grain, heavy | Heavy film-grain texture; strength 50/100, coarser scale. |

### vignette (3 — corner darkening)

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `vignette_subtle` | vignette | vignette, subtle | Subtle corner darkening; brightness -0.25. |
| `vignette_medium` | vignette | vignette, medium | Medium corner darkening; brightness -0.5. |
| `vignette_heavy` | vignette | vignette, heavy | Strong corner darkening; brightness -0.8. |

### wb (1 — white balance)

| Name | Subtype | Tags | Description |
|-|-|-|-|
| `wb_cool_subtle` | wb | wb, cool, subtle | Cool white balance, subtle (mirror of starter's `wb_warm_subtle`). |

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

- **Exposure delta:** `expo_-0.5` (starter) ← `expo_-0.3` ← (no-op) → `expo_+0.3` → `expo_+0.5` (starter)
- **Saturation:** `sat_kill` ← (no-op) → `sat_boost_moderate` → `sat_boost_strong`
- **Contrast:** `contrast_low` → (no-op) → `contrast_high`
- **Blacks (sigmoid):** `blacks_crushed` ← (no-op) → `blacks_lifted` → (no-op) → `whites_open`
- **Highlights recovery:** `highlights_recovery_subtle` → `highlights_recovery_strong`
- **Clarity:** `clarity_painterly` (soft) ← (no-op) → `clarity_strong` (sharp)
- **Grain:** `grain_fine` → `grain_medium` → `grain_heavy`
- **Vignette:** `vignette_subtle` → `vignette_medium` → `vignette_heavy`

Pick the gentlest move that addresses the brief; stack from there.

## By-tag index

Quick lookup by intent:

- **`tone`** — `contrast_low`, `contrast_high`, `blacks_lifted`, `blacks_crushed`, `whites_open`
- **`shadows`** — `shadows_global_+`, `shadows_global_-`, `blacks_lifted`, `blacks_crushed`, `gradient_bottom_lift_shadows`
- **`highlights`** — `highlights_recovery_subtle`, `highlights_recovery_strong`, `whites_open`, `gradient_top_dampen_highlights`, `chroma_boost_highlights`, `grade_highlights_warm`, `grade_highlights_cool`
- **`saturation` / `chroma` / `vibrance`** — `sat_boost_moderate/strong`, `sat_kill`, `vibrance_+0.3`, `chroma_boost_shadows/midtones/highlights`
- **`grade` (split-tone)** — `grade_shadows_warm/cool`, `grade_highlights_warm/cool`
- **`clarity`** — `clarity_strong`, `clarity_painterly`
- **`grain`** — `grain_fine`, `grain_medium`, `grain_heavy`
- **`vignette`** — `vignette_subtle`, `vignette_medium`, `vignette_heavy`
- **`wb`** — `wb_cool_subtle` (this pack), `wb_warm_subtle` (starter)
- **`mask` / `gradient` / `radial` / `rectangle`** — see "Mask-bound entries" above
- **`monochrome`** — `sat_kill` (a channelmixerrgb-based B&W trio is on the v1.6.0 milestone, #63)

For "for X intent, reach for Y composition" patterns, see [`docs/guides/vocabulary-patterns.md`](../../../docs/guides/vocabulary-patterns.md).

---

## Provenance

All entries authored against darktable 5.4.1 by the project maintainers per the discipline in `docs/CONTRIBUTING.md` § Vocabulary contributions. Path C reverse-engineering methodology and per-module struct mappings are documented at [`docs/guides/expressive-baseline-authoring.md`](../../../docs/guides/expressive-baseline-authoring.md).

## Adding to this pack

See `docs/CONTRIBUTING.md` § Vocabulary authoring for the procedure. Path B entries additionally require the probe-iop-order workflow (per ADR-064). For drawn-mask-bound entries, the `mask_spec` schema is documented in [`docs/guides/authoring-vocabulary-entries.md`](../../../docs/guides/authoring-vocabulary-entries.md).
