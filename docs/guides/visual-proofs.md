# Visual proofs — vocabulary-entry before/after gallery

> Side-by-side renders of the synthetic ColorChecker chart and the synthetic grayscale ramp, before and after each vocabulary entry. For human visual validation: does each primitive *visibly* do what its description claims?

> Renders use an **empty-history baseline** + ``--apply-custom-presets false`` so the chart passes through the darktable pipeline cleanly (input profile → output profile only, no scene-referred tone mapping). Each primitive is then applied in isolation — the only difference between baseline and per-entry renders is *that primitive's effect*. This lets you eyeball each primitive against the reference chart and verify it does what its description claims.

> Production raw renders use the full ``_baseline_v1.xmp`` with sigmoid + colorbalancergb defaults — that path is correct for raws. The empty-baseline trick is specifically for chart-input isolation testing; it would not be appropriate for editing real photographs.

> **Masked columns**: every non-mask-bound primitive renders additionally through a centered ellipse mask (``radius=0.2``, ``border=0.05``) so you can see the spatial shaping in action. The mask covers the middle 16% of the frame; anything outside it should remain at baseline. This visually demonstrates that **any** primitive can be applied through a mask — see [`mask-applicable-controls.md`](mask-applicable-controls.md) for the per-module compatibility matrix.

> **Auto-generated.** Regenerate via ``uv run python scripts/generate-visual-proofs.py`` after vocabulary changes. Commit the regenerated images alongside any vocabulary commit so the gallery and the manifest stay in sync.

> Render size: 400x400, JPEG quality default. Inputs: synthetic targets from [`tests/fixtures/reference-targets/`](../../tests/fixtures/reference-targets/README.md).

---

## Baseline reference

These are the reference targets rendered through the baseline XMP with no primitive applied — the *before* state every row below compares against.

| ColorChecker | Grayscale ramp |
|-|-|
| ![baseline ColorChecker](../visual-proofs/baseline-colorchecker.jpg) | ![baseline grayscale](../visual-proofs/baseline-grayscale.jpg) |

---

## `starter` pack (4 entries)

### `expo_+0.5`

_Lift exposure +0.5 EV._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/starter/expo_+0.5-colorchecker.jpg" alt="expo_+0.5 ColorChecker global" width="180"> | <img src="../visual-proofs/starter/expo_+0.5-grayscale.jpg" alt="expo_+0.5 grayscale global" width="180"> | <img src="../visual-proofs/starter/expo_+0.5-colorchecker-masked.jpg" alt="expo_+0.5 ColorChecker masked" width="180"> | <img src="../visual-proofs/starter/expo_+0.5-grayscale-masked.jpg" alt="expo_+0.5 grayscale masked" width="180"> |

### `expo_-0.5`

_Lower exposure -0.5 EV._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/starter/expo_-0.5-colorchecker.jpg" alt="expo_-0.5 ColorChecker global" width="180"> | <img src="../visual-proofs/starter/expo_-0.5-grayscale.jpg" alt="expo_-0.5 grayscale global" width="180"> | <img src="../visual-proofs/starter/expo_-0.5-colorchecker-masked.jpg" alt="expo_-0.5 ColorChecker masked" width="180"> | <img src="../visual-proofs/starter/expo_-0.5-grayscale-masked.jpg" alt="expo_-0.5 grayscale masked" width="180"> |

### `wb_warm_subtle`

_Warm white balance, subtle._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/starter/wb_warm_subtle-colorchecker.jpg" alt="wb_warm_subtle ColorChecker global" width="180"> | <img src="../visual-proofs/starter/wb_warm_subtle-grayscale.jpg" alt="wb_warm_subtle grayscale global" width="180"> | <img src="../visual-proofs/starter/wb_warm_subtle-colorchecker-masked.jpg" alt="wb_warm_subtle ColorChecker masked" width="180"> | <img src="../visual-proofs/starter/wb_warm_subtle-grayscale-masked.jpg" alt="wb_warm_subtle grayscale masked" width="180"> |

### `look_neutral`

_Neutral L2 look — exposure + warm-subtle WB baseline._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/starter/look_neutral-colorchecker.jpg" alt="look_neutral ColorChecker global" width="180"> | <img src="../visual-proofs/starter/look_neutral-grayscale.jpg" alt="look_neutral grayscale global" width="180"> | <img src="../visual-proofs/starter/look_neutral-colorchecker-masked.jpg" alt="look_neutral ColorChecker masked" width="180"> | <img src="../visual-proofs/starter/look_neutral-grayscale-masked.jpg" alt="look_neutral grayscale masked" width="180"> |

---

## `expressive-baseline` pack (35 entries)

### `grain_fine`

_Subtle film-grain texture; strength 8/100._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/grain_fine-colorchecker.jpg" alt="grain_fine ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_fine-grayscale.jpg" alt="grain_fine grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_fine-colorchecker-masked.jpg" alt="grain_fine ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_fine-grayscale-masked.jpg" alt="grain_fine grayscale masked" width="180"> |

### `grain_medium`

_Visible film-grain texture; strength 25/100._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/grain_medium-colorchecker.jpg" alt="grain_medium ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_medium-grayscale.jpg" alt="grain_medium grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_medium-colorchecker-masked.jpg" alt="grain_medium ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_medium-grayscale-masked.jpg" alt="grain_medium grayscale masked" width="180"> |

### `grain_heavy`

_Heavy film-grain texture; strength 50/100, coarser scale._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/grain_heavy-colorchecker.jpg" alt="grain_heavy ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_heavy-grayscale.jpg" alt="grain_heavy grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_heavy-colorchecker-masked.jpg" alt="grain_heavy ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_heavy-grayscale-masked.jpg" alt="grain_heavy grayscale masked" width="180"> |

### `vignette_subtle`

_Subtle corner darkening; brightness -0.25._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/vignette_subtle-colorchecker.jpg" alt="vignette_subtle ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/vignette_subtle-grayscale.jpg" alt="vignette_subtle grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/vignette_subtle-colorchecker-masked.jpg" alt="vignette_subtle ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/vignette_subtle-grayscale-masked.jpg" alt="vignette_subtle grayscale masked" width="180"> |

### `vignette_medium`

_Medium corner darkening; brightness -0.5._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/vignette_medium-colorchecker.jpg" alt="vignette_medium ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/vignette_medium-grayscale.jpg" alt="vignette_medium grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/vignette_medium-colorchecker-masked.jpg" alt="vignette_medium ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/vignette_medium-grayscale-masked.jpg" alt="vignette_medium grayscale masked" width="180"> |

### `vignette_heavy`

_Strong corner darkening; brightness -0.8._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/vignette_heavy-colorchecker.jpg" alt="vignette_heavy ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/vignette_heavy-grayscale.jpg" alt="vignette_heavy grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/vignette_heavy-colorchecker-masked.jpg" alt="vignette_heavy ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/vignette_heavy-grayscale-masked.jpg" alt="vignette_heavy grayscale masked" width="180"> |

### `highlights_recovery_subtle`

_Subtle highlight reconstruction; clip 0.95._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/highlights_recovery_subtle-colorchecker.jpg" alt="highlights_recovery_subtle ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_recovery_subtle-grayscale.jpg" alt="highlights_recovery_subtle grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_recovery_subtle-colorchecker-masked.jpg" alt="highlights_recovery_subtle ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_recovery_subtle-grayscale-masked.jpg" alt="highlights_recovery_subtle grayscale masked" width="180"> |

### `highlights_recovery_strong`

_Strong highlight reconstruction; clip 0.85._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/highlights_recovery_strong-colorchecker.jpg" alt="highlights_recovery_strong ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_recovery_strong-grayscale.jpg" alt="highlights_recovery_strong grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_recovery_strong-colorchecker-masked.jpg" alt="highlights_recovery_strong ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_recovery_strong-grayscale-masked.jpg" alt="highlights_recovery_strong grayscale masked" width="180"> |

### `contrast_low`

_Mild s-curve; sigmoid contrast 1.0._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/contrast_low-colorchecker.jpg" alt="contrast_low ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/contrast_low-grayscale.jpg" alt="contrast_low grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/contrast_low-colorchecker-masked.jpg" alt="contrast_low ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/contrast_low-grayscale-masked.jpg" alt="contrast_low grayscale masked" width="180"> |

### `contrast_high`

_Aggressive s-curve; sigmoid contrast 2.5._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/contrast_high-colorchecker.jpg" alt="contrast_high ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/contrast_high-grayscale.jpg" alt="contrast_high grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/contrast_high-colorchecker-masked.jpg" alt="contrast_high ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/contrast_high-grayscale-masked.jpg" alt="contrast_high grayscale masked" width="180"> |

### `blacks_lifted`

_Lift target black to 0.5._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/blacks_lifted-colorchecker.jpg" alt="blacks_lifted ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/blacks_lifted-grayscale.jpg" alt="blacks_lifted grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/blacks_lifted-colorchecker-masked.jpg" alt="blacks_lifted ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/blacks_lifted-grayscale-masked.jpg" alt="blacks_lifted grayscale masked" width="180"> |

### `blacks_crushed`

_Crush blacks: target 0.001 + skew -0.3._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/blacks_crushed-colorchecker.jpg" alt="blacks_crushed ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/blacks_crushed-grayscale.jpg" alt="blacks_crushed grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/blacks_crushed-colorchecker-masked.jpg" alt="blacks_crushed ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/blacks_crushed-grayscale-masked.jpg" alt="blacks_crushed grayscale masked" width="180"> |

### `whites_open`

_Open whites: target 300 (3x default)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/whites_open-colorchecker.jpg" alt="whites_open ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/whites_open-grayscale.jpg" alt="whites_open grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/whites_open-colorchecker-masked.jpg" alt="whites_open ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/whites_open-grayscale-masked.jpg" alt="whites_open grayscale masked" width="180"> |

### `clarity_strong`

_Strong local contrast / clarity (detail 1.5)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/clarity_strong-colorchecker.jpg" alt="clarity_strong ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/clarity_strong-grayscale.jpg" alt="clarity_strong grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/clarity_strong-colorchecker-masked.jpg" alt="clarity_strong ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/clarity_strong-grayscale-masked.jpg" alt="clarity_strong grayscale masked" width="180"> |

### `clarity_painterly`

_Soft painterly local contrast (detail 0.4)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/clarity_painterly-colorchecker.jpg" alt="clarity_painterly ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/clarity_painterly-grayscale.jpg" alt="clarity_painterly grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/clarity_painterly-colorchecker-masked.jpg" alt="clarity_painterly ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/clarity_painterly-grayscale-masked.jpg" alt="clarity_painterly grayscale masked" width="180"> |

### `expo_+0.3`

_Lift exposure +0.3 EV (smaller than starter +0.5)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/expo_+0.3-colorchecker.jpg" alt="expo_+0.3 ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/expo_+0.3-grayscale.jpg" alt="expo_+0.3 grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/expo_+0.3-colorchecker-masked.jpg" alt="expo_+0.3 ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/expo_+0.3-grayscale-masked.jpg" alt="expo_+0.3 grayscale masked" width="180"> |

### `expo_-0.3`

_Lower exposure -0.3 EV (smaller than starter -0.5)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/expo_-0.3-colorchecker.jpg" alt="expo_-0.3 ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/expo_-0.3-grayscale.jpg" alt="expo_-0.3 grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/expo_-0.3-colorchecker-masked.jpg" alt="expo_-0.3 ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/expo_-0.3-grayscale-masked.jpg" alt="expo_-0.3 grayscale masked" width="180"> |

### `shadows_global_+`

_Lift global black level +0.05._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/shadows_global_+-colorchecker.jpg" alt="shadows_global_+ ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/shadows_global_+-grayscale.jpg" alt="shadows_global_+ grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/shadows_global_+-colorchecker-masked.jpg" alt="shadows_global_+ ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/shadows_global_+-grayscale-masked.jpg" alt="shadows_global_+ grayscale masked" width="180"> |

### `shadows_global_-`

_Lower global black level -0.05 (deepen shadows)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/shadows_global_--colorchecker.jpg" alt="shadows_global_- ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/shadows_global_--grayscale.jpg" alt="shadows_global_- grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/shadows_global_--colorchecker-masked.jpg" alt="shadows_global_- ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/shadows_global_--grayscale-masked.jpg" alt="shadows_global_- grayscale masked" width="180"> |

### `wb_cool_subtle`

_Cool white balance, subtle (mirror of wb_warm_subtle)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/wb_cool_subtle-colorchecker.jpg" alt="wb_cool_subtle ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/wb_cool_subtle-grayscale.jpg" alt="wb_cool_subtle grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/wb_cool_subtle-colorchecker-masked.jpg" alt="wb_cool_subtle ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/wb_cool_subtle-grayscale-masked.jpg" alt="wb_cool_subtle grayscale masked" width="180"> |

### `sat_boost_strong`

_Strong global saturation boost (+0.5)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/sat_boost_strong-colorchecker.jpg" alt="sat_boost_strong ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/sat_boost_strong-grayscale.jpg" alt="sat_boost_strong grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/sat_boost_strong-colorchecker-masked.jpg" alt="sat_boost_strong ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/sat_boost_strong-grayscale-masked.jpg" alt="sat_boost_strong grayscale masked" width="180"> |

### `sat_boost_moderate`

_Moderate global saturation boost (+0.25)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/sat_boost_moderate-colorchecker.jpg" alt="sat_boost_moderate ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/sat_boost_moderate-grayscale.jpg" alt="sat_boost_moderate grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/sat_boost_moderate-colorchecker-masked.jpg" alt="sat_boost_moderate ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/sat_boost_moderate-grayscale-masked.jpg" alt="sat_boost_moderate grayscale masked" width="180"> |

### `sat_kill`

_Kill all saturation (global -1.0)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/sat_kill-colorchecker.jpg" alt="sat_kill ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/sat_kill-grayscale.jpg" alt="sat_kill grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/sat_kill-colorchecker-masked.jpg" alt="sat_kill ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/sat_kill-grayscale-masked.jpg" alt="sat_kill grayscale masked" width="180"> |

### `vibrance_+0.3`

_Global vibrance +0.3._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/vibrance_+0.3-colorchecker.jpg" alt="vibrance_+0.3 ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/vibrance_+0.3-grayscale.jpg" alt="vibrance_+0.3 grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/vibrance_+0.3-colorchecker-masked.jpg" alt="vibrance_+0.3 ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/vibrance_+0.3-grayscale-masked.jpg" alt="vibrance_+0.3 grayscale masked" width="180"> |

### `grade_shadows_warm`

_Warm shadows (orange tint, hue 30 deg, chroma 0.3)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/grade_shadows_warm-colorchecker.jpg" alt="grade_shadows_warm ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/grade_shadows_warm-grayscale.jpg" alt="grade_shadows_warm grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/grade_shadows_warm-colorchecker-masked.jpg" alt="grade_shadows_warm ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/grade_shadows_warm-grayscale-masked.jpg" alt="grade_shadows_warm grayscale masked" width="180"> |

### `grade_shadows_cool`

_Cool shadows (blue tint, hue 210 deg, chroma 0.3)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/grade_shadows_cool-colorchecker.jpg" alt="grade_shadows_cool ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/grade_shadows_cool-grayscale.jpg" alt="grade_shadows_cool grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/grade_shadows_cool-colorchecker-masked.jpg" alt="grade_shadows_cool ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/grade_shadows_cool-grayscale-masked.jpg" alt="grade_shadows_cool grayscale masked" width="180"> |

### `grade_highlights_warm`

_Warm highlights (orange tint, hue 45 deg, chroma 0.2)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/grade_highlights_warm-colorchecker.jpg" alt="grade_highlights_warm ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/grade_highlights_warm-grayscale.jpg" alt="grade_highlights_warm grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/grade_highlights_warm-colorchecker-masked.jpg" alt="grade_highlights_warm ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/grade_highlights_warm-grayscale-masked.jpg" alt="grade_highlights_warm grayscale masked" width="180"> |

### `grade_highlights_cool`

_Cool highlights (blue tint, hue 200 deg, chroma 0.2)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/grade_highlights_cool-colorchecker.jpg" alt="grade_highlights_cool ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/grade_highlights_cool-grayscale.jpg" alt="grade_highlights_cool grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/grade_highlights_cool-colorchecker-masked.jpg" alt="grade_highlights_cool ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/grade_highlights_cool-grayscale-masked.jpg" alt="grade_highlights_cool grayscale masked" width="180"> |

### `chroma_boost_shadows`

_Boost shadow chroma +0.3._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/chroma_boost_shadows-colorchecker.jpg" alt="chroma_boost_shadows ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_boost_shadows-grayscale.jpg" alt="chroma_boost_shadows grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_boost_shadows-colorchecker-masked.jpg" alt="chroma_boost_shadows ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_boost_shadows-grayscale-masked.jpg" alt="chroma_boost_shadows grayscale masked" width="180"> |

### `chroma_boost_midtones`

_Boost mid-tone chroma +0.3._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/chroma_boost_midtones-colorchecker.jpg" alt="chroma_boost_midtones ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_boost_midtones-grayscale.jpg" alt="chroma_boost_midtones grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_boost_midtones-colorchecker-masked.jpg" alt="chroma_boost_midtones ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_boost_midtones-grayscale-masked.jpg" alt="chroma_boost_midtones grayscale masked" width="180"> |

### `chroma_boost_highlights`

_Boost highlight chroma +0.3._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/chroma_boost_highlights-colorchecker.jpg" alt="chroma_boost_highlights ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_boost_highlights-grayscale.jpg" alt="chroma_boost_highlights grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_boost_highlights-colorchecker-masked.jpg" alt="chroma_boost_highlights ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_boost_highlights-grayscale-masked.jpg" alt="chroma_boost_highlights grayscale masked" width="180"> |

### `gradient_top_dampen_highlights` 🟦 mask-bound

_Dampen top-half highlights via -0.5 EV through a top-bright gradient._

| ColorChecker | Grayscale ramp |
|-|-|
| <img src="../visual-proofs/expressive-baseline/gradient_top_dampen_highlights-colorchecker.jpg" alt="gradient_top_dampen_highlights ColorChecker" width="180"> | <img src="../visual-proofs/expressive-baseline/gradient_top_dampen_highlights-grayscale.jpg" alt="gradient_top_dampen_highlights grayscale" width="180"> |

### `gradient_bottom_lift_shadows` 🟦 mask-bound

_Lift bottom-half shadows via +0.4 EV through a bottom-bright gradient._

| ColorChecker | Grayscale ramp |
|-|-|
| <img src="../visual-proofs/expressive-baseline/gradient_bottom_lift_shadows-colorchecker.jpg" alt="gradient_bottom_lift_shadows ColorChecker" width="180"> | <img src="../visual-proofs/expressive-baseline/gradient_bottom_lift_shadows-grayscale.jpg" alt="gradient_bottom_lift_shadows grayscale" width="180"> |

### `radial_subject_lift` 🟦 mask-bound

_Lift +0.6 EV in a centered radial mask region (subject emphasis)._

| ColorChecker | Grayscale ramp |
|-|-|
| <img src="../visual-proofs/expressive-baseline/radial_subject_lift-colorchecker.jpg" alt="radial_subject_lift ColorChecker" width="180"> | <img src="../visual-proofs/expressive-baseline/radial_subject_lift-grayscale.jpg" alt="radial_subject_lift grayscale" width="180"> |

### `rectangle_subject_band_dim` 🟦 mask-bound

_Dim -0.3 EV in a horizontal mid-band rectangle (de-emphasize a horizon line)._

| ColorChecker | Grayscale ramp |
|-|-|
| <img src="../visual-proofs/expressive-baseline/rectangle_subject_band_dim-colorchecker.jpg" alt="rectangle_subject_band_dim ColorChecker" width="180"> | <img src="../visual-proofs/expressive-baseline/rectangle_subject_band_dim-grayscale.jpg" alt="rectangle_subject_band_dim grayscale" width="180"> |

---

## Notes

- **Inputs are sRGB PNGs**, not raw files. darktable processes them through its non-raw path — input color profile applies, demosaic does not. Some primitives (e.g., raw-aware white-balance moves) behave differently from how they would on a real raw. The gallery is for *visual response validation*, not pipeline calibration; for raw-pipeline direction-of-change validation see the e2e suite in [`tests/e2e/`](../../tests/e2e/).

- **Mask-bound entries** (gradient/ellipse/rectangle, marked 🟦 above) route through the drawn-mask apply path per ADR-076. The mask geometry encodes into the XMP's `masks_history`; you see the spatial shaping in the rendered chart.

- **Out-of-gamut patches** on the ColorChecker (notably patch #18 Cyan) clip to nearest in-gamut sRGB; that clipping is in the input, not the primitive. See [`reference-targets/README.md`](../../tests/fixtures/reference-targets/README.md).
