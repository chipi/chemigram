# Visual proofs — vocabulary-entry before/after gallery

> Side-by-side renders of the synthetic ColorChecker chart and the synthetic grayscale ramp, before and after each vocabulary entry. For human visual validation: does each primitive *visibly* do what its description claims?

> Renders use an **empty-history baseline** + ``--apply-custom-presets false`` so the chart passes through the darktable pipeline cleanly (input profile → output profile only, no scene-referred tone mapping). Each primitive is then applied in isolation — the only difference between baseline and per-entry renders is *that primitive's effect*. This lets you eyeball each primitive against the reference chart and verify it does what its description claims.

> Production raw renders use the full ``_baseline_v1.xmp`` with sigmoid + colorbalancergb defaults — that path is correct for raws. The empty-baseline trick is specifically for chart-input isolation testing; it would not be appropriate for editing real photographs.

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

| ColorChecker | Grayscale ramp |
|-|-|
| ![expo_+0.5 ColorChecker](../visual-proofs/starter/expo_+0.5-colorchecker.jpg) | ![expo_+0.5 grayscale](../visual-proofs/starter/expo_+0.5-grayscale.jpg) |

### `expo_-0.5`

_Lower exposure -0.5 EV._

| ColorChecker | Grayscale ramp |
|-|-|
| ![expo_-0.5 ColorChecker](../visual-proofs/starter/expo_-0.5-colorchecker.jpg) | ![expo_-0.5 grayscale](../visual-proofs/starter/expo_-0.5-grayscale.jpg) |

### `wb_warm_subtle`

_Warm white balance, subtle._

| ColorChecker | Grayscale ramp |
|-|-|
| ![wb_warm_subtle ColorChecker](../visual-proofs/starter/wb_warm_subtle-colorchecker.jpg) | ![wb_warm_subtle grayscale](../visual-proofs/starter/wb_warm_subtle-grayscale.jpg) |

### `look_neutral`

_Neutral L2 look — exposure + warm-subtle WB baseline._

| ColorChecker | Grayscale ramp |
|-|-|
| ![look_neutral ColorChecker](../visual-proofs/starter/look_neutral-colorchecker.jpg) | ![look_neutral grayscale](../visual-proofs/starter/look_neutral-grayscale.jpg) |

---

## `expressive-baseline` pack (35 entries)

### `grain_fine`

_Subtle film-grain texture; strength 8/100._

| ColorChecker | Grayscale ramp |
|-|-|
| ![grain_fine ColorChecker](../visual-proofs/expressive-baseline/grain_fine-colorchecker.jpg) | ![grain_fine grayscale](../visual-proofs/expressive-baseline/grain_fine-grayscale.jpg) |

### `grain_medium`

_Visible film-grain texture; strength 25/100._

| ColorChecker | Grayscale ramp |
|-|-|
| ![grain_medium ColorChecker](../visual-proofs/expressive-baseline/grain_medium-colorchecker.jpg) | ![grain_medium grayscale](../visual-proofs/expressive-baseline/grain_medium-grayscale.jpg) |

### `grain_heavy`

_Heavy film-grain texture; strength 50/100, coarser scale._

| ColorChecker | Grayscale ramp |
|-|-|
| ![grain_heavy ColorChecker](../visual-proofs/expressive-baseline/grain_heavy-colorchecker.jpg) | ![grain_heavy grayscale](../visual-proofs/expressive-baseline/grain_heavy-grayscale.jpg) |

### `vignette_subtle`

_Subtle corner darkening; brightness -0.25._

| ColorChecker | Grayscale ramp |
|-|-|
| ![vignette_subtle ColorChecker](../visual-proofs/expressive-baseline/vignette_subtle-colorchecker.jpg) | ![vignette_subtle grayscale](../visual-proofs/expressive-baseline/vignette_subtle-grayscale.jpg) |

### `vignette_medium`

_Medium corner darkening; brightness -0.5._

| ColorChecker | Grayscale ramp |
|-|-|
| ![vignette_medium ColorChecker](../visual-proofs/expressive-baseline/vignette_medium-colorchecker.jpg) | ![vignette_medium grayscale](../visual-proofs/expressive-baseline/vignette_medium-grayscale.jpg) |

### `vignette_heavy`

_Strong corner darkening; brightness -0.8._

| ColorChecker | Grayscale ramp |
|-|-|
| ![vignette_heavy ColorChecker](../visual-proofs/expressive-baseline/vignette_heavy-colorchecker.jpg) | ![vignette_heavy grayscale](../visual-proofs/expressive-baseline/vignette_heavy-grayscale.jpg) |

### `highlights_recovery_subtle`

_Subtle highlight reconstruction; clip 0.95._

| ColorChecker | Grayscale ramp |
|-|-|
| ![highlights_recovery_subtle ColorChecker](../visual-proofs/expressive-baseline/highlights_recovery_subtle-colorchecker.jpg) | ![highlights_recovery_subtle grayscale](../visual-proofs/expressive-baseline/highlights_recovery_subtle-grayscale.jpg) |

### `highlights_recovery_strong`

_Strong highlight reconstruction; clip 0.85._

| ColorChecker | Grayscale ramp |
|-|-|
| ![highlights_recovery_strong ColorChecker](../visual-proofs/expressive-baseline/highlights_recovery_strong-colorchecker.jpg) | ![highlights_recovery_strong grayscale](../visual-proofs/expressive-baseline/highlights_recovery_strong-grayscale.jpg) |

### `contrast_low`

_Mild s-curve; sigmoid contrast 1.0._

| ColorChecker | Grayscale ramp |
|-|-|
| ![contrast_low ColorChecker](../visual-proofs/expressive-baseline/contrast_low-colorchecker.jpg) | ![contrast_low grayscale](../visual-proofs/expressive-baseline/contrast_low-grayscale.jpg) |

### `contrast_high`

_Aggressive s-curve; sigmoid contrast 2.5._

| ColorChecker | Grayscale ramp |
|-|-|
| ![contrast_high ColorChecker](../visual-proofs/expressive-baseline/contrast_high-colorchecker.jpg) | ![contrast_high grayscale](../visual-proofs/expressive-baseline/contrast_high-grayscale.jpg) |

### `blacks_lifted`

_Lift target black to 0.5._

| ColorChecker | Grayscale ramp |
|-|-|
| ![blacks_lifted ColorChecker](../visual-proofs/expressive-baseline/blacks_lifted-colorchecker.jpg) | ![blacks_lifted grayscale](../visual-proofs/expressive-baseline/blacks_lifted-grayscale.jpg) |

### `blacks_crushed`

_Crush blacks: target 0.001 + skew -0.3._

| ColorChecker | Grayscale ramp |
|-|-|
| ![blacks_crushed ColorChecker](../visual-proofs/expressive-baseline/blacks_crushed-colorchecker.jpg) | ![blacks_crushed grayscale](../visual-proofs/expressive-baseline/blacks_crushed-grayscale.jpg) |

### `whites_open`

_Open whites: target 300 (3x default)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![whites_open ColorChecker](../visual-proofs/expressive-baseline/whites_open-colorchecker.jpg) | ![whites_open grayscale](../visual-proofs/expressive-baseline/whites_open-grayscale.jpg) |

### `clarity_strong`

_Strong local contrast / clarity (detail 1.5)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![clarity_strong ColorChecker](../visual-proofs/expressive-baseline/clarity_strong-colorchecker.jpg) | ![clarity_strong grayscale](../visual-proofs/expressive-baseline/clarity_strong-grayscale.jpg) |

### `clarity_painterly`

_Soft painterly local contrast (detail 0.4)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![clarity_painterly ColorChecker](../visual-proofs/expressive-baseline/clarity_painterly-colorchecker.jpg) | ![clarity_painterly grayscale](../visual-proofs/expressive-baseline/clarity_painterly-grayscale.jpg) |

### `expo_+0.3`

_Lift exposure +0.3 EV (smaller than starter +0.5)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![expo_+0.3 ColorChecker](../visual-proofs/expressive-baseline/expo_+0.3-colorchecker.jpg) | ![expo_+0.3 grayscale](../visual-proofs/expressive-baseline/expo_+0.3-grayscale.jpg) |

### `expo_-0.3`

_Lower exposure -0.3 EV (smaller than starter -0.5)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![expo_-0.3 ColorChecker](../visual-proofs/expressive-baseline/expo_-0.3-colorchecker.jpg) | ![expo_-0.3 grayscale](../visual-proofs/expressive-baseline/expo_-0.3-grayscale.jpg) |

### `shadows_global_+`

_Lift global black level +0.05._

| ColorChecker | Grayscale ramp |
|-|-|
| ![shadows_global_+ ColorChecker](../visual-proofs/expressive-baseline/shadows_global_+-colorchecker.jpg) | ![shadows_global_+ grayscale](../visual-proofs/expressive-baseline/shadows_global_+-grayscale.jpg) |

### `shadows_global_-`

_Lower global black level -0.05 (deepen shadows)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![shadows_global_- ColorChecker](../visual-proofs/expressive-baseline/shadows_global_--colorchecker.jpg) | ![shadows_global_- grayscale](../visual-proofs/expressive-baseline/shadows_global_--grayscale.jpg) |

### `wb_cool_subtle`

_Cool white balance, subtle (mirror of wb_warm_subtle)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![wb_cool_subtle ColorChecker](../visual-proofs/expressive-baseline/wb_cool_subtle-colorchecker.jpg) | ![wb_cool_subtle grayscale](../visual-proofs/expressive-baseline/wb_cool_subtle-grayscale.jpg) |

### `sat_boost_strong`

_Strong global saturation boost (+0.5)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![sat_boost_strong ColorChecker](../visual-proofs/expressive-baseline/sat_boost_strong-colorchecker.jpg) | ![sat_boost_strong grayscale](../visual-proofs/expressive-baseline/sat_boost_strong-grayscale.jpg) |

### `sat_boost_moderate`

_Moderate global saturation boost (+0.25)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![sat_boost_moderate ColorChecker](../visual-proofs/expressive-baseline/sat_boost_moderate-colorchecker.jpg) | ![sat_boost_moderate grayscale](../visual-proofs/expressive-baseline/sat_boost_moderate-grayscale.jpg) |

### `sat_kill`

_Kill all saturation (global -1.0)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![sat_kill ColorChecker](../visual-proofs/expressive-baseline/sat_kill-colorchecker.jpg) | ![sat_kill grayscale](../visual-proofs/expressive-baseline/sat_kill-grayscale.jpg) |

### `vibrance_+0.3`

_Global vibrance +0.3._

| ColorChecker | Grayscale ramp |
|-|-|
| ![vibrance_+0.3 ColorChecker](../visual-proofs/expressive-baseline/vibrance_+0.3-colorchecker.jpg) | ![vibrance_+0.3 grayscale](../visual-proofs/expressive-baseline/vibrance_+0.3-grayscale.jpg) |

### `grade_shadows_warm`

_Warm shadows (orange tint, hue 30 deg, chroma 0.3)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![grade_shadows_warm ColorChecker](../visual-proofs/expressive-baseline/grade_shadows_warm-colorchecker.jpg) | ![grade_shadows_warm grayscale](../visual-proofs/expressive-baseline/grade_shadows_warm-grayscale.jpg) |

### `grade_shadows_cool`

_Cool shadows (blue tint, hue 210 deg, chroma 0.3)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![grade_shadows_cool ColorChecker](../visual-proofs/expressive-baseline/grade_shadows_cool-colorchecker.jpg) | ![grade_shadows_cool grayscale](../visual-proofs/expressive-baseline/grade_shadows_cool-grayscale.jpg) |

### `grade_highlights_warm`

_Warm highlights (orange tint, hue 45 deg, chroma 0.2)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![grade_highlights_warm ColorChecker](../visual-proofs/expressive-baseline/grade_highlights_warm-colorchecker.jpg) | ![grade_highlights_warm grayscale](../visual-proofs/expressive-baseline/grade_highlights_warm-grayscale.jpg) |

### `grade_highlights_cool`

_Cool highlights (blue tint, hue 200 deg, chroma 0.2)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![grade_highlights_cool ColorChecker](../visual-proofs/expressive-baseline/grade_highlights_cool-colorchecker.jpg) | ![grade_highlights_cool grayscale](../visual-proofs/expressive-baseline/grade_highlights_cool-grayscale.jpg) |

### `chroma_boost_shadows`

_Boost shadow chroma +0.3._

| ColorChecker | Grayscale ramp |
|-|-|
| ![chroma_boost_shadows ColorChecker](../visual-proofs/expressive-baseline/chroma_boost_shadows-colorchecker.jpg) | ![chroma_boost_shadows grayscale](../visual-proofs/expressive-baseline/chroma_boost_shadows-grayscale.jpg) |

### `chroma_boost_midtones`

_Boost mid-tone chroma +0.3._

| ColorChecker | Grayscale ramp |
|-|-|
| ![chroma_boost_midtones ColorChecker](../visual-proofs/expressive-baseline/chroma_boost_midtones-colorchecker.jpg) | ![chroma_boost_midtones grayscale](../visual-proofs/expressive-baseline/chroma_boost_midtones-grayscale.jpg) |

### `chroma_boost_highlights`

_Boost highlight chroma +0.3._

| ColorChecker | Grayscale ramp |
|-|-|
| ![chroma_boost_highlights ColorChecker](../visual-proofs/expressive-baseline/chroma_boost_highlights-colorchecker.jpg) | ![chroma_boost_highlights grayscale](../visual-proofs/expressive-baseline/chroma_boost_highlights-grayscale.jpg) |

### `gradient_top_dampen_highlights` 🟦 mask-bound

_Dampen top-half highlights via -0.5 EV through a top-bright gradient._

| ColorChecker | Grayscale ramp |
|-|-|
| ![gradient_top_dampen_highlights ColorChecker](../visual-proofs/expressive-baseline/gradient_top_dampen_highlights-colorchecker.jpg) | ![gradient_top_dampen_highlights grayscale](../visual-proofs/expressive-baseline/gradient_top_dampen_highlights-grayscale.jpg) |

### `gradient_bottom_lift_shadows` 🟦 mask-bound

_Lift bottom-half shadows via +0.4 EV through a bottom-bright gradient._

| ColorChecker | Grayscale ramp |
|-|-|
| ![gradient_bottom_lift_shadows ColorChecker](../visual-proofs/expressive-baseline/gradient_bottom_lift_shadows-colorchecker.jpg) | ![gradient_bottom_lift_shadows grayscale](../visual-proofs/expressive-baseline/gradient_bottom_lift_shadows-grayscale.jpg) |

### `radial_subject_lift` 🟦 mask-bound

_Lift +0.6 EV in a centered radial mask region (subject emphasis)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![radial_subject_lift ColorChecker](../visual-proofs/expressive-baseline/radial_subject_lift-colorchecker.jpg) | ![radial_subject_lift grayscale](../visual-proofs/expressive-baseline/radial_subject_lift-grayscale.jpg) |

### `rectangle_subject_band_dim` 🟦 mask-bound

_Dim -0.3 EV in a horizontal mid-band rectangle (de-emphasize a horizon line)._

| ColorChecker | Grayscale ramp |
|-|-|
| ![rectangle_subject_band_dim ColorChecker](../visual-proofs/expressive-baseline/rectangle_subject_band_dim-colorchecker.jpg) | ![rectangle_subject_band_dim grayscale](../visual-proofs/expressive-baseline/rectangle_subject_band_dim-grayscale.jpg) |

---

## Notes

- **Inputs are sRGB PNGs**, not raw files. darktable processes them through its non-raw path — input color profile applies, demosaic does not. Some primitives (e.g., raw-aware white-balance moves) behave differently from how they would on a real raw. The gallery is for *visual response validation*, not pipeline calibration; for raw-pipeline direction-of-change validation see the e2e suite in [`tests/e2e/`](../../tests/e2e/).

- **Mask-bound entries** (gradient/ellipse/rectangle, marked 🟦 above) route through the drawn-mask apply path per ADR-076. The mask geometry encodes into the XMP's `masks_history`; you see the spatial shaping in the rendered chart.

- **Out-of-gamut patches** on the ColorChecker (notably patch #18 Cyan) clip to nearest in-gamut sRGB; that clipping is in the input, not the primitive. See [`reference-targets/README.md`](../../tests/fixtures/reference-targets/README.md).
