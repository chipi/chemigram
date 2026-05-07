# Visual proofs — vocabulary-entry before/after gallery

> Side-by-side renders of the synthetic ColorChecker chart and the synthetic grayscale ramp, before and after each vocabulary entry. For human visual validation: does each primitive *visibly* do what its description claims?

> Renders use an **empty-history baseline** + ``--apply-custom-presets false`` so the chart passes through the darktable pipeline cleanly (input profile → output profile only, no scene-referred tone mapping). Each primitive is then applied in isolation — the only difference between baseline and per-entry renders is *that primitive's effect*. This lets you eyeball each primitive against the reference chart and verify it does what its description claims.

> Production raw renders use the full ``_baseline_v1.xmp`` with sigmoid + colorbalancergb defaults — that path is correct for raws. The empty-baseline trick is specifically for chart-input isolation testing; it would not be appropriate for editing real photographs.

> **Masked columns**: every non-mask-bound primitive renders additionally through a centered ellipse mask (``radius=0.2``, ``border=0.05``) so you can see the spatial shaping in action. The mask covers the middle 16% of the frame; anything outside it should remain at baseline. This visually demonstrates that **any** primitive can be applied through a mask — see [`mask-applicable-controls.md`](mask-applicable-controls.md) for the per-module compatibility matrix.

> **Auto-generated.** Regenerate via ``uv run python scripts/generate-visual-proofs.py`` after vocabulary changes. Commit the regenerated images alongside any vocabulary commit so the gallery and the manifest stay in sync.

> Render size: 400x400, JPEG quality default. Inputs: synthetic targets from [`tests/fixtures/reference-targets/`](https://github.com/chipi/chemigram/blob/main/tests/fixtures/reference-targets/README.md).

---

## Baseline reference

These are the reference targets rendered through the baseline XMP with no primitive applied — the *before* state every row below compares against.

| ColorChecker | Grayscale ramp |
|-|-|
| ![baseline ColorChecker](../visual-proofs/baseline-colorchecker.jpg) | ![baseline grayscale](../visual-proofs/baseline-grayscale.jpg) |

---

## `starter` pack (2 entries)

### `wb_warm_subtle`

_Warm white balance, subtle._

| ColorChecker (global) | Grayscale (global) |
|-|-|
| <img src="../visual-proofs/starter/wb_warm_subtle-colorchecker.jpg" alt="wb_warm_subtle ColorChecker global" width="180"> | <img src="../visual-proofs/starter/wb_warm_subtle-grayscale.jpg" alt="wb_warm_subtle grayscale global" width="180"> |

> 🚫 **Masked variant suppressed**: see [mask-applicable-controls](mask-applicable-controls.md#temperature) for why drawn-mask binding doesn't render usefully for this module.

### `look_neutral`

_Neutral L2 look — exposure + warm-subtle WB baseline._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/starter/look_neutral-colorchecker.jpg" alt="look_neutral ColorChecker global" width="180"> | <img src="../visual-proofs/starter/look_neutral-grayscale.jpg" alt="look_neutral grayscale global" width="180"> | <img src="../visual-proofs/starter/look_neutral-colorchecker-masked.jpg" alt="look_neutral ColorChecker masked" width="180"> | <img src="../visual-proofs/starter/look_neutral-grayscale-masked.jpg" alt="look_neutral grayscale masked" width="180"> |

---

## `expressive-baseline` pack (29 entries)

### `grain_strength`

_Parameterized grain strength (RFC-021). Pass --value V; range [0.0, 100.0]. 8 = grain_fine-equivalent, 25 = grain_medium-equivalent, 50 = grain_heavy-equivalent. Replaces the v1.5.x discrete grain_fine / grain_medium / grain_heavy entries with a single continuous-magnitude primitive._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/grain_strength-colorchecker.jpg" alt="grain_strength ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_strength-grayscale.jpg" alt="grain_strength grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_strength-colorchecker-masked.jpg" alt="grain_strength ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_strength-grayscale-masked.jpg" alt="grain_strength grayscale masked" width="180"> |

_(near-baseline diff in ColorChecker (global): grain texture is hard to see on flat chart patches — see the **clipped-gradient row below** for visible texture, or [mask-applicable-controls](mask-applicable-controls.md#grain))_

_(near-baseline diff in grayscale (global): grain texture is hard to see on flat chart patches — see the **clipped-gradient row below** for visible texture, or [mask-applicable-controls](mask-applicable-controls.md#grain))_

_(near-baseline diff in ColorChecker (masked): grain texture is hard to see on flat chart patches — see the **clipped-gradient row below** for visible texture, or [mask-applicable-controls](mask-applicable-controls.md#grain))_

_(near-baseline diff in grayscale (masked): grain texture is hard to see on flat chart patches — see the **clipped-gradient row below** for visible texture, or [mask-applicable-controls](mask-applicable-controls.md#grain))_

**On the clipped-gradient fixture** (continuous tone + blown highlights — chart designed to show this module's effect; see [`reference-targets/README.md`](https://github.com/chipi/chemigram/blob/main/tests/fixtures/reference-targets/README.md)):

| Clipped gradient (global) | Clipped gradient (centered ellipse mask) |
|-|-|
| <img src="../visual-proofs/expressive-baseline/grain_strength-clipped.jpg" alt="grain_strength clipped-gradient global" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_strength-clipped-masked.jpg" alt="grain_strength clipped-gradient masked" width="180"> |

**Parameter sweep** (`grain_strength`): rendered at multiple values via the parameterized apply path (`--value V` / `--param NAME=V`):

| `0.00` | `+8.00` | `+25.00` | `+50.00` | `+100.00` |
|-|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/grain_strength-sweep-0_00.jpg" alt="grain_strength grain_strength=0.00" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_strength-sweep-p8_00.jpg" alt="grain_strength grain_strength=+8.00" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_strength-sweep-p25_00.jpg" alt="grain_strength grain_strength=+25.00" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_strength-sweep-p50_00.jpg" alt="grain_strength grain_strength=+50.00" width="180"> | <img src="../visual-proofs/expressive-baseline/grain_strength-sweep-p100_00.jpg" alt="grain_strength grain_strength=+100.00" width="180"> |

### `vignette`

_Parameterized vignette (RFC-021). Pass --value V (CLI) or value: V (MCP); range [-1.0, +1.0] (negative darkens corners; positive lifts). Replaces the v1.5.x discrete vignette_subtle / vignette_medium / vignette_heavy entries with a single continuous-magnitude primitive._

| ColorChecker (global) | Grayscale (global) |
|-|-|
| <img src="../visual-proofs/expressive-baseline/vignette-colorchecker.jpg" alt="vignette ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/vignette-grayscale.jpg" alt="vignette grayscale global" width="180"> |

> 🚫 **Masked variant suppressed**: see [mask-applicable-controls](mask-applicable-controls.md#vignette) for why drawn-mask binding doesn't render usefully for this module.

_(near-baseline diff in ColorChecker (global): subtle vignette is small at the modest gallery render size; effect is concentrated at the very corners of the frame)_

_(near-baseline diff in grayscale (global): subtle vignette is small at the modest gallery render size; effect is concentrated at the very corners of the frame)_

**Parameter sweep** (`brightness`): rendered at multiple values via the parameterized apply path (`--value V` / `--param NAME=V`):

| `-0.80` | `-0.50` | `-0.25` | `0.00` |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/vignette-sweep-n0_80.jpg" alt="vignette brightness=-0.80" width="180"> | <img src="../visual-proofs/expressive-baseline/vignette-sweep-n0_50.jpg" alt="vignette brightness=-0.50" width="180"> | <img src="../visual-proofs/expressive-baseline/vignette-sweep-n0_25.jpg" alt="vignette brightness=-0.25" width="180"> | <img src="../visual-proofs/expressive-baseline/vignette-sweep-0_00.jpg" alt="vignette brightness=0.00" width="180"> |

### `highlights_clip_threshold`

_Parameterized highlight-recovery clip threshold (RFC-021). Pass --value V; range [0.0, 2.0]: lower = more aggressive recovery (0.95 = subtle, 0.85 = strong, 0.5 = aggressive). Default 1.0 (darktable default; recovers only above 1.0). Replaces the v1.5.x discrete highlights_recovery_subtle / highlights_recovery_strong entries._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/highlights_clip_threshold-colorchecker.jpg" alt="highlights_clip_threshold ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_clip_threshold-grayscale.jpg" alt="highlights_clip_threshold grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_clip_threshold-colorchecker-masked.jpg" alt="highlights_clip_threshold ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_clip_threshold-grayscale-masked.jpg" alt="highlights_clip_threshold grayscale masked" width="180"> |

_(near-baseline diff in ColorChecker (global): this chart has no blown highlights to recover — see the **clipped-gradient row below** for the visible effect, or [mask-applicable-controls](mask-applicable-controls.md#highlights))_

_(near-baseline diff in grayscale (global): this chart has no blown highlights to recover — see the **clipped-gradient row below** for the visible effect, or [mask-applicable-controls](mask-applicable-controls.md#highlights))_

_(near-baseline diff in ColorChecker (masked): this chart has no blown highlights to recover — see the **clipped-gradient row below** for the visible effect, or [mask-applicable-controls](mask-applicable-controls.md#highlights))_

_(near-baseline diff in grayscale (masked): this chart has no blown highlights to recover — see the **clipped-gradient row below** for the visible effect, or [mask-applicable-controls](mask-applicable-controls.md#highlights))_

**On the clipped-gradient fixture** (continuous tone + blown highlights — chart designed to show this module's effect; see [`reference-targets/README.md`](https://github.com/chipi/chemigram/blob/main/tests/fixtures/reference-targets/README.md)):

| Clipped gradient (global) | Clipped gradient (centered ellipse mask) |
|-|-|
| <img src="../visual-proofs/expressive-baseline/highlights_clip_threshold-clipped.jpg" alt="highlights_clip_threshold clipped-gradient global" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_clip_threshold-clipped-masked.jpg" alt="highlights_clip_threshold clipped-gradient masked" width="180"> |

**Parameter sweep** (`clip_threshold`): rendered at multiple values via the parameterized apply path (`--value V` / `--param NAME=V`):

| `+0.50` | `+0.85` | `+0.95` | `+1.00` | `+1.50` |
|-|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/highlights_clip_threshold-sweep-p0_50.jpg" alt="highlights_clip_threshold clip_threshold=+0.50" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_clip_threshold-sweep-p0_85.jpg" alt="highlights_clip_threshold clip_threshold=+0.85" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_clip_threshold-sweep-p0_95.jpg" alt="highlights_clip_threshold clip_threshold=+0.95" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_clip_threshold-sweep-p1_00.jpg" alt="highlights_clip_threshold clip_threshold=+1.00" width="180"> | <img src="../visual-proofs/expressive-baseline/highlights_clip_threshold-sweep-p1_50.jpg" alt="highlights_clip_threshold clip_threshold=+1.50" width="180"> |

### `sigmoid_contrast`

_Parameterized sigmoid tone-curve contrast (RFC-021). Pass --value V (CLI) or value: V (MCP); range [0.5, 5.0] (1.0 = mild s-curve, 1.5 = darktable default / no curve change, 2.5 = aggressive s-curve). Replaces the v1.5.x discrete contrast_low / contrast_high entries with a single continuous-magnitude primitive._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/sigmoid_contrast-colorchecker.jpg" alt="sigmoid_contrast ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/sigmoid_contrast-grayscale.jpg" alt="sigmoid_contrast grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/sigmoid_contrast-colorchecker-masked.jpg" alt="sigmoid_contrast ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/sigmoid_contrast-grayscale-masked.jpg" alt="sigmoid_contrast grayscale masked" width="180"> |

**Parameter sweep** (`contrast`): rendered at multiple values via the parameterized apply path (`--value V` / `--param NAME=V`):

| `+0.50` | `+1.00` | `+1.50` | `+2.00` | `+2.50` |
|-|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/sigmoid_contrast-sweep-p0_50.jpg" alt="sigmoid_contrast contrast=+0.50" width="180"> | <img src="../visual-proofs/expressive-baseline/sigmoid_contrast-sweep-p1_00.jpg" alt="sigmoid_contrast contrast=+1.00" width="180"> | <img src="../visual-proofs/expressive-baseline/sigmoid_contrast-sweep-p1_50.jpg" alt="sigmoid_contrast contrast=+1.50" width="180"> | <img src="../visual-proofs/expressive-baseline/sigmoid_contrast-sweep-p2_00.jpg" alt="sigmoid_contrast contrast=+2.00" width="180"> | <img src="../visual-proofs/expressive-baseline/sigmoid_contrast-sweep-p2_50.jpg" alt="sigmoid_contrast contrast=+2.50" width="180"> |

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

### `toneequalizer`

_Parameterized 9-band tone equalizer (RFC-022 Tier 2; most complex multi-parameter ship). Pass --param NODE=V for any of: noise, ultra_deep_blacks, deep_blacks, blacks, shadows, midtones, highlights, whites, speculars. Each in [-2.0, +2.0] EV; default 0.0. Algorithm fields preserved at darktable defaults._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/toneequalizer-colorchecker.jpg" alt="toneequalizer ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/toneequalizer-grayscale.jpg" alt="toneequalizer grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/toneequalizer-colorchecker-masked.jpg" alt="toneequalizer ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/toneequalizer-grayscale-masked.jpg" alt="toneequalizer grayscale masked" width="180"> |

_(near-baseline diff in ColorChecker (global): below visible threshold on this chart input)_

_(near-baseline diff in grayscale (global): below visible threshold on this chart input)_

_(near-baseline diff in ColorChecker (masked): below visible threshold on this chart input)_

### `sharpen`

_Parameterized sharpening (RFC-022 Tier 2). Pass --value V; range [0.0, 2.0] (0.0 = no sharpen, 0.5 = subtle, 1.0 = strong, 2.0 = aggressive). Radius preserved at darktable default 2.0 px, threshold at 0.5._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/sharpen-colorchecker.jpg" alt="sharpen ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/sharpen-grayscale.jpg" alt="sharpen grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/sharpen-colorchecker-masked.jpg" alt="sharpen ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/sharpen-grayscale-masked.jpg" alt="sharpen grayscale masked" width="180"> |

_(near-baseline diff in ColorChecker (global): below visible threshold on this chart input)_

_(near-baseline diff in grayscale (global): below visible threshold on this chart input)_

_(near-baseline diff in ColorChecker (masked): below visible threshold on this chart input)_

_(near-baseline diff in grayscale (masked): below visible threshold on this chart input)_

**Parameter sweep** (`amount`): rendered at multiple values via the parameterized apply path (`--value V` / `--param NAME=V`):

| `0.00` | `+0.50` | `+1.00` | `+1.50` | `+2.00` |
|-|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/sharpen-sweep-0_00.jpg" alt="sharpen amount=0.00" width="180"> | <img src="../visual-proofs/expressive-baseline/sharpen-sweep-p0_50.jpg" alt="sharpen amount=+0.50" width="180"> | <img src="../visual-proofs/expressive-baseline/sharpen-sweep-p1_00.jpg" alt="sharpen amount=+1.00" width="180"> | <img src="../visual-proofs/expressive-baseline/sharpen-sweep-p1_50.jpg" alt="sharpen amount=+1.50" width="180"> | <img src="../visual-proofs/expressive-baseline/sharpen-sweep-p2_00.jpg" alt="sharpen amount=+2.00" width="180"> |

### `crop`

_Parameterized crop (RFC-022 Tier 2). Pass --param cx=V cy=V cw=V ch=V — each in [0.0, 1.0]. Default 0,0,1,1 (no crop). cx/cy = top-left margin, cw/ch = bottom-right margin (so crop region is [cx..cw] x [cy..ch] in normalized coords). First workflow-primitive parameterized entry; aspect-ratio constraint preserved at -1/-1 (free)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/crop-colorchecker.jpg" alt="crop ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/crop-grayscale.jpg" alt="crop grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/crop-colorchecker-masked.jpg" alt="crop ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/crop-grayscale-masked.jpg" alt="crop grayscale masked" width="180"> |

_(near-baseline diff in ColorChecker (global): below visible threshold on this chart input)_

_(near-baseline diff in grayscale (global): below visible threshold on this chart input)_

_(near-baseline diff in ColorChecker (masked): below visible threshold on this chart input)_

_(near-baseline diff in grayscale (masked): below visible threshold on this chart input)_

### `bilat_clarity_strength`

_Parameterized clarity strength on bilat / local laplacian (RFC-021). Pass --value V; range [-1.0, 4.0]. 1.5 = clarity_strong-equivalent. clarity_painterly stays as a separate discrete entry — different kind, not strength._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/bilat_clarity_strength-colorchecker.jpg" alt="bilat_clarity_strength ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/bilat_clarity_strength-grayscale.jpg" alt="bilat_clarity_strength grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/bilat_clarity_strength-colorchecker-masked.jpg" alt="bilat_clarity_strength ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/bilat_clarity_strength-grayscale-masked.jpg" alt="bilat_clarity_strength grayscale masked" width="180"> |

_(near-baseline diff in ColorChecker (global): below visible threshold on this chart input)_

_(near-baseline diff in grayscale (global): below visible threshold on this chart input)_

_(near-baseline diff in ColorChecker (masked): below visible threshold on this chart input)_

**Parameter sweep** (`clarity_strength`): rendered at multiple values via the parameterized apply path (`--value V` / `--param NAME=V`):

| `-0.50` | `0.00` | `+0.50` | `+1.50` | `+2.50` |
|-|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/bilat_clarity_strength-sweep-n0_50.jpg" alt="bilat_clarity_strength clarity_strength=-0.50" width="180"> | <img src="../visual-proofs/expressive-baseline/bilat_clarity_strength-sweep-0_00.jpg" alt="bilat_clarity_strength clarity_strength=0.00" width="180"> | <img src="../visual-proofs/expressive-baseline/bilat_clarity_strength-sweep-p0_50.jpg" alt="bilat_clarity_strength clarity_strength=+0.50" width="180"> | <img src="../visual-proofs/expressive-baseline/bilat_clarity_strength-sweep-p1_50.jpg" alt="bilat_clarity_strength clarity_strength=+1.50" width="180"> | <img src="../visual-proofs/expressive-baseline/bilat_clarity_strength-sweep-p2_50.jpg" alt="bilat_clarity_strength clarity_strength=+2.50" width="180"> |

### `clarity_painterly`

_Soft painterly local contrast (detail 0.4)._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/clarity_painterly-colorchecker.jpg" alt="clarity_painterly ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/clarity_painterly-grayscale.jpg" alt="clarity_painterly grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/clarity_painterly-colorchecker-masked.jpg" alt="clarity_painterly ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/clarity_painterly-grayscale-masked.jpg" alt="clarity_painterly grayscale masked" width="180"> |

### `exposure`

_Parameterized exposure compensation (RFC-021). Pass --value V (CLI) or value: V (MCP) in EV stops; range [-3.0, +3.0]. Replaces the v1.5.x discrete expo_+0.3 / expo_+0.5 / expo_-0.3 / expo_-0.5 / shadows_global_+/- entries with a single continuous-magnitude primitive._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/exposure-colorchecker.jpg" alt="exposure ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/exposure-grayscale.jpg" alt="exposure grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/exposure-colorchecker-masked.jpg" alt="exposure ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/exposure-grayscale-masked.jpg" alt="exposure grayscale masked" width="180"> |

_(near-baseline diff in ColorChecker (global): below visible threshold on this chart input)_

_(near-baseline diff in grayscale (global): below visible threshold on this chart input)_

_(near-baseline diff in ColorChecker (masked): below visible threshold on this chart input)_

_(near-baseline diff in grayscale (masked): below visible threshold on this chart input)_

**Parameter sweep** (`ev`): rendered at multiple values via the parameterized apply path (`--value V` / `--param NAME=V`):

| `-1.00` | `-0.50` | `0.00` | `+0.50` | `+1.00` |
|-|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/exposure-sweep-n1_00.jpg" alt="exposure ev=-1.00" width="180"> | <img src="../visual-proofs/expressive-baseline/exposure-sweep-n0_50.jpg" alt="exposure ev=-0.50" width="180"> | <img src="../visual-proofs/expressive-baseline/exposure-sweep-0_00.jpg" alt="exposure ev=0.00" width="180"> | <img src="../visual-proofs/expressive-baseline/exposure-sweep-p0_50.jpg" alt="exposure ev=+0.50" width="180"> | <img src="../visual-proofs/expressive-baseline/exposure-sweep-p1_00.jpg" alt="exposure ev=+1.00" width="180"> |

### `temperature`

_Parameterized white balance (RFC-021; first multi-parameter ship). Two axes: --param red_coeff=V (warmer image: red↑) and --param blue_coeff=V (cooler image: blue↑). Range [0.5, 4.0] each; both default 1.0 (no shift). Replaces the v1.5.x discrete wb_cool_subtle entry. Starter's wb_warm_subtle remains as a discrete teaching artifact; production use of WB shifts should prefer this parameterized entry._

| ColorChecker (global) | Grayscale (global) |
|-|-|
| <img src="../visual-proofs/expressive-baseline/temperature-colorchecker.jpg" alt="temperature ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/temperature-grayscale.jpg" alt="temperature grayscale global" width="180"> |

> 🚫 **Masked variant suppressed**: see [mask-applicable-controls](mask-applicable-controls.md#temperature) for why drawn-mask binding doesn't render usefully for this module.

_(near-baseline diff in ColorChecker (global): below visible threshold on this chart input)_

_(near-baseline diff in grayscale (global): below visible threshold on this chart input)_

### `saturation_global`

_Parameterized global saturation in colorbalancergb (RFC-021). Pass --value V (CLI) or value: V (MCP); range [-1.0, +1.0] (-1.0 = fully desaturated / monochrome; +0.5 = strong boost). Replaces the v1.5.x discrete sat_kill / sat_boost_moderate / sat_boost_strong entries with a single continuous-magnitude primitive._

| ColorChecker (global) | ColorChecker (centered ellipse mask) |
|-|-|
| <img src="../visual-proofs/expressive-baseline/saturation_global-colorchecker.jpg" alt="saturation_global ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/saturation_global-colorchecker-masked.jpg" alt="saturation_global ColorChecker masked" width="180"> |

> **Grayscale column omitted**: this primitive moves chroma only; gray patches have no chroma to affect.

_(near-baseline diff in ColorChecker (global): below visible threshold on this chart input)_

_(near-baseline diff in ColorChecker (masked): below visible threshold on this chart input)_

**Parameter sweep** (`saturation_global`): rendered at multiple values via the parameterized apply path (`--value V` / `--param NAME=V`):

| `-1.00` | `-0.50` | `0.00` | `+0.25` | `+0.50` |
|-|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/saturation_global-sweep-n1_00.jpg" alt="saturation_global saturation_global=-1.00" width="180"> | <img src="../visual-proofs/expressive-baseline/saturation_global-sweep-n0_50.jpg" alt="saturation_global saturation_global=-0.50" width="180"> | <img src="../visual-proofs/expressive-baseline/saturation_global-sweep-0_00.jpg" alt="saturation_global saturation_global=0.00" width="180"> | <img src="../visual-proofs/expressive-baseline/saturation_global-sweep-p0_25.jpg" alt="saturation_global saturation_global=+0.25" width="180"> | <img src="../visual-proofs/expressive-baseline/saturation_global-sweep-p0_50.jpg" alt="saturation_global saturation_global=+0.50" width="180"> |

### `vibrance`

_Parameterized vibrance on colorbalancergb (RFC-022 Tier 2). Pass --value V; range [-1.0, +1.0]. 0.3 = vibrance_+0.3-equivalent. Vibrance protects already-saturated pixels — gentler chroma push than saturation_global. Replaces v1.5.x vibrance_+0.3._

| ColorChecker (global) | ColorChecker (centered ellipse mask) |
|-|-|
| <img src="../visual-proofs/expressive-baseline/vibrance-colorchecker.jpg" alt="vibrance ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/vibrance-colorchecker-masked.jpg" alt="vibrance ColorChecker masked" width="180"> |

> **Grayscale column omitted**: this primitive moves chroma only; gray patches have no chroma to affect.

_(near-baseline diff in ColorChecker (global): below visible threshold on this chart input)_

_(near-baseline diff in ColorChecker (masked): below visible threshold on this chart input)_

**Parameter sweep** (`vibrance`): rendered at multiple values via the parameterized apply path (`--value V` / `--param NAME=V`):

| `-0.50` | `0.00` | `+0.30` | `+0.60` | `+1.00` |
|-|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/vibrance-sweep-n0_50.jpg" alt="vibrance vibrance=-0.50" width="180"> | <img src="../visual-proofs/expressive-baseline/vibrance-sweep-0_00.jpg" alt="vibrance vibrance=0.00" width="180"> | <img src="../visual-proofs/expressive-baseline/vibrance-sweep-p0_30.jpg" alt="vibrance vibrance=+0.30" width="180"> | <img src="../visual-proofs/expressive-baseline/vibrance-sweep-p0_60.jpg" alt="vibrance vibrance=+0.60" width="180"> | <img src="../visual-proofs/expressive-baseline/vibrance-sweep-p1_00.jpg" alt="vibrance vibrance=+1.00" width="180"> |

### `chroma_global`

_Parameterized global chroma on colorbalancergb (RFC-022 Tier 2). Pass --value V; range [-1.0, +1.0]. Less saturated-pixel protection than vibrance, more aggressive than saturation_global at equal magnitudes._

| ColorChecker (global) | ColorChecker (centered ellipse mask) |
|-|-|
| <img src="../visual-proofs/expressive-baseline/chroma_global-colorchecker.jpg" alt="chroma_global ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_global-colorchecker-masked.jpg" alt="chroma_global ColorChecker masked" width="180"> |

> **Grayscale column omitted**: this primitive moves chroma only; gray patches have no chroma to affect.

_(near-baseline diff in ColorChecker (global): below visible threshold on this chart input)_

_(near-baseline diff in ColorChecker (masked): below visible threshold on this chart input)_

**Parameter sweep** (`chroma_global`): rendered at multiple values via the parameterized apply path (`--value V` / `--param NAME=V`):

| `-0.50` | `0.00` | `+0.30` | `+0.60` | `+1.00` |
|-|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/chroma_global-sweep-n0_50.jpg" alt="chroma_global chroma_global=-0.50" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_global-sweep-0_00.jpg" alt="chroma_global chroma_global=0.00" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_global-sweep-p0_30.jpg" alt="chroma_global chroma_global=+0.30" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_global-sweep-p0_60.jpg" alt="chroma_global chroma_global=+0.60" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_global-sweep-p1_00.jpg" alt="chroma_global chroma_global=+1.00" width="180"> |

### `hue_angle`

_Parameterized global hue rotation on colorbalancergb (RFC-022 Tier 2). Pass --value V in degrees; range [-180.0, +180.0]. Rotates every pixel's hue around the color wheel without changing saturation or luminance._

| ColorChecker (global) | Grayscale (global) | ColorChecker (centered ellipse mask) | Grayscale (centered ellipse mask) |
|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/hue_angle-colorchecker.jpg" alt="hue_angle ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/hue_angle-grayscale.jpg" alt="hue_angle grayscale global" width="180"> | <img src="../visual-proofs/expressive-baseline/hue_angle-colorchecker-masked.jpg" alt="hue_angle ColorChecker masked" width="180"> | <img src="../visual-proofs/expressive-baseline/hue_angle-grayscale-masked.jpg" alt="hue_angle grayscale masked" width="180"> |

_(near-baseline diff in ColorChecker (global): below visible threshold on this chart input)_

_(near-baseline diff in grayscale (global): below visible threshold on this chart input)_

_(near-baseline diff in ColorChecker (masked): below visible threshold on this chart input)_

_(near-baseline diff in grayscale (masked): below visible threshold on this chart input)_

**Parameter sweep** (`hue_angle`): rendered at multiple values via the parameterized apply path (`--value V` / `--param NAME=V`):

| `-90.00` | `-30.00` | `0.00` | `+30.00` | `+90.00` |
|-|-|-|-|-|
| <img src="../visual-proofs/expressive-baseline/hue_angle-sweep-n90_00.jpg" alt="hue_angle hue_angle=-90.00" width="180"> | <img src="../visual-proofs/expressive-baseline/hue_angle-sweep-n30_00.jpg" alt="hue_angle hue_angle=-30.00" width="180"> | <img src="../visual-proofs/expressive-baseline/hue_angle-sweep-0_00.jpg" alt="hue_angle hue_angle=0.00" width="180"> | <img src="../visual-proofs/expressive-baseline/hue_angle-sweep-p30_00.jpg" alt="hue_angle hue_angle=+30.00" width="180"> | <img src="../visual-proofs/expressive-baseline/hue_angle-sweep-p90_00.jpg" alt="hue_angle hue_angle=+90.00" width="180"> |

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

| ColorChecker (global) | ColorChecker (centered ellipse mask) |
|-|-|
| <img src="../visual-proofs/expressive-baseline/chroma_boost_shadows-colorchecker.jpg" alt="chroma_boost_shadows ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_boost_shadows-colorchecker-masked.jpg" alt="chroma_boost_shadows ColorChecker masked" width="180"> |

> **Grayscale column omitted**: this primitive moves chroma only; gray patches have no chroma to affect.

### `chroma_boost_midtones`

_Boost mid-tone chroma +0.3._

| ColorChecker (global) | ColorChecker (centered ellipse mask) |
|-|-|
| <img src="../visual-proofs/expressive-baseline/chroma_boost_midtones-colorchecker.jpg" alt="chroma_boost_midtones ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_boost_midtones-colorchecker-masked.jpg" alt="chroma_boost_midtones ColorChecker masked" width="180"> |

> **Grayscale column omitted**: this primitive moves chroma only; gray patches have no chroma to affect.

### `chroma_boost_highlights`

_Boost highlight chroma +0.3._

| ColorChecker (global) | ColorChecker (centered ellipse mask) |
|-|-|
| <img src="../visual-proofs/expressive-baseline/chroma_boost_highlights-colorchecker.jpg" alt="chroma_boost_highlights ColorChecker global" width="180"> | <img src="../visual-proofs/expressive-baseline/chroma_boost_highlights-colorchecker-masked.jpg" alt="chroma_boost_highlights ColorChecker masked" width="180"> |

> **Grayscale column omitted**: this primitive moves chroma only; gray patches have no chroma to affect.

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

- **Inputs are sRGB PNGs**, not raw files. darktable processes them through its non-raw path — input color profile applies, demosaic does not. Some primitives (e.g., raw-aware white-balance moves) behave differently from how they would on a real raw. The gallery is for *visual response validation*, not pipeline calibration; for raw-pipeline direction-of-change validation see the e2e suite in [`tests/e2e/`](https://github.com/chipi/chemigram/blob/main/tests/e2e/).

- **Mask-bound entries** (gradient/ellipse/rectangle, marked 🟦 above) route through the drawn-mask apply path per ADR-076. The mask geometry encodes into the XMP's `masks_history`; you see the spatial shaping in the rendered chart.

- **Out-of-gamut patches** on the ColorChecker (notably patch #18 Cyan) clip to nearest in-gamut sRGB; that clipping is in the input, not the primitive. See [`reference-targets/README.md`](https://github.com/chipi/chemigram/blob/main/tests/fixtures/reference-targets/README.md).
