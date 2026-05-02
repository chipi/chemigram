# Standardized testing reference guide

> Companion to RFC-019. Industry methodology and resources for
> reference-image validation in Chemigram.

## Why standardized test targets

The photography and imaging industry — Imatest, DxOMark, X-Rite, the
ISO TC-42 and IEEE P1858 committees — converges on a single principle:
**test against inputs with known, published physical properties, then
measure the delta between expected and actual.** Without known ground
truth, any evaluation is subjective opinion.

For Chemigram this means: replace the arbitrary `raw-test.NEF` (which
tells us "did darktable crash?") with standardized chart photographs
(which tell us "did the pipeline produce correct color and tone?").

## The two reference targets

### Calibrite ColorChecker Passport Photo 2

- 24 patches: 18 color + 6 neutral grayscale
- Published CIE L\*a\*b\* D50 reference values from X-Rite
- ~€70 from calibrite.com or Amazon
- Includes free DNG profiling software
- Check manufacturing date (back of chart): formulations changed Nov 2014

**What it tests in Chemigram:**

| Metric | What it catches |
|-|-|
| Per-patch Delta E | Wrong color matrix, WB error, color-grading vocabulary producing unintended shifts |
| Mean/max Delta E | Overall color accuracy regression |
| Grayscale neutrality | Color cast in neutral tones (WB or channel mixer bugs) |
| Patch-to-patch relationships | Relative color accuracy even when absolute is off |

### Calibrite ColorChecker Grayscale

- Neutral step wedge with known optical density values
- ~€40
- Isolates tonal response from color

**What it tests in Chemigram:**

| Metric | What it catches |
|-|-|
| Tonal linearity (R²) | Broken tone curve, sigmoid misconfiguration |
| Gamma fit | Wrong contrast/gamma after vocabulary application |
| Shadow/highlight clipping | Exposure vocabulary pushing values out of range |
| Noise floor | Denoise vocabulary effectiveness |

## Shooting protocol

One afternoon, controlled conditions:

1. Camera: Nikon D850 (same body as existing `CHEMIGRAM_TEST_RAW`)
2. Lens: prime, 50mm or longer, stopped down to f/8 (sharpest aperture)
3. Lighting: overcast daylight OR a 5500K LED panel at 45° angle
4. Chart distance: fill ~1/3 of frame (avoid vignetting)
5. Exposure: white patch of CC24 just below highlight clipping in RAW histogram
6. WB: fixed preset (daylight 5500K), not auto
7. Format: 14-bit lossless compressed NEF
8. Shoot: 3 frames of each chart, pick the sharpest
9. Save: two files, ~50 MB each

Store alongside existing test raw, discovered via:
```bash
export CHEMIGRAM_TEST_CC24=~/chemigram-reference/cc24.NEF
export CHEMIGRAM_TEST_GRAYSCALE=~/chemigram-reference/grayscale.NEF
```

## Reference data sources

### Official L\*a\*b\* values (required)

**X-Rite CGATS files** — the ground truth:
- `ColorChecker24_Before_Nov2014.txt`
- `ColorChecker24_After_Nov2014.txt`
- Download: https://www.xrite.com/service-support/new_color_specifications_for_colorchecker_sg_and_classic_charts

### Community-validated data (supplementary)

**BabelColor** — averaged spectral data from 30 charts, synthetic images, comparison spreadsheets:
- Page 2 (data): https://babelcolor.com/colorchecker-2.htm
- RGB coordinates PDF: https://babelcolor.com/tutorials.htm
- CxF2 format file with both averaged and X-Rite reference data
- Note: BabelColor CT&A and PatchTool are now freeware (since Jan 2025)

**Bruce Lindbloom** — LAB TIFF + comparison spreadsheets:
- https://www.brucelindbloom.com/ColorCheckerRGB.html
- Computer-generated L\*a\*b\* TIFF for synthetic testing

**RIT Munsell Color Science Lab** — independent spectral reflectance measurements:
- https://www.rit.edu/science/munsell-color-science-lab

### Post-Nov 2014 reference L\*a\*b\* D50 (for the JSON fixture)

These are the values that go into `tests/fixtures/reference-targets/colorchecker24_lab_d50.json`:

| # | Patch | L\* | a\* | b\* |
|-|-|-|-|-|
| 1 | Dark Skin | 37.54 | 14.37 | 14.92 |
| 2 | Light Skin | 65.71 | 17.64 | 17.67 |
| 3 | Blue Sky | 49.59 | −3.82 | −22.54 |
| 4 | Foliage | 43.72 | −13.39 | 22.18 |
| 5 | Blue Flower | 55.47 | 9.75 | −24.79 |
| 6 | Bluish Green | 71.77 | −33.13 | 0.68 |
| 7 | Orange | 62.66 | 35.83 | 56.50 |
| 8 | Purplish Blue | 40.56 | 10.09 | −45.17 |
| 9 | Moderate Red | 52.10 | 48.24 | 16.23 |
| 10 | Purple | 30.67 | 21.19 | −20.81 |
| 11 | Yellow Green | 72.53 | −23.71 | 57.26 |
| 12 | Orange Yellow | 71.94 | 19.36 | 67.86 |
| 13 | Blue | 28.78 | 15.42 | −49.80 |
| 14 | Green | 55.26 | −38.34 | 31.37 |
| 15 | Red | 42.43 | 51.05 | 28.62 |
| 16 | Yellow | 82.45 | 2.41 | 80.25 |
| 17 | Magenta | 51.98 | 49.99 | −14.57 |
| 18 | Cyan | 50.98 | −28.78 | −28.35 |
| 19 | White (.05)\* | 96.54 | −0.43 | 1.19 |
| 20 | Neutral 8 (.23)\* | 81.26 | −0.64 | −0.34 |
| 21 | Neutral 6.5 (.44)\* | 66.77 | −0.73 | −0.50 |
| 22 | Neutral 5 (.70)\* | 50.87 | −0.15 | −0.27 |
| 23 | Neutral 3.5 (1.05)\* | 35.66 | −0.42 | −1.23 |
| 24 | Black (1.50)\* | 20.46 | −0.08 | −0.97 |

\* Parenthesized values are approximate optical density.

Source: X-Rite, "After November 2014" CGATS file. Illuminant D50, 2° observer.

## Delta E 2000 — the primary metric

Delta E 2000 (CIE DE2000) is the industry-standard perceptual color difference formula. It accounts for human visual sensitivity: we're more sensitive to hue differences than chroma differences, and more sensitive in low-chroma regions than high-chroma.

**Interpretation:**

| Delta E | Meaning |
|-|-|
| < 1.0 | Not perceptible to the human eye |
| 1.0–2.0 | Perceptible through close observation |
| 2.0–3.5 | Perceptible at a glance |
| 3.5–5.0 | Clear difference |
| > 5.0 | Colors appear noticeably different |

**Python implementation:** the `colour-science` package (`pip install colour-science`) provides `colour.delta_E(lab1, lab2, method='CIE 2000')`.

**For Chemigram assertions:**

```python
import colour
import numpy as np

def compute_delta_e(measured_lab: np.ndarray, reference_lab: np.ndarray) -> np.ndarray:
    """Compute per-patch Delta E 2000."""
    return colour.delta_E(measured_lab, reference_lab, method='CIE 2000')

def assert_color_accuracy(measured, reference, max_mean_de=3.0, max_max_de=6.0):
    de = compute_delta_e(measured, reference)
    mean_de = float(np.mean(de))
    max_de = float(np.max(de))
    passed = mean_de <= max_mean_de and max_de <= max_max_de
    return ColorAccuracyResult(
        passed=passed, mean_de=mean_de, max_de=max_de,
        per_patch=de.tolist()
    )
```

## Vocabulary move assertions — direction and magnitude

Beyond absolute accuracy, each vocabulary entry has an *expected effect* that can be asserted:

| Vocabulary entry | Expected effect | Assertion |
|-|-|-|
| `expo_plus_0p5` | +0.5 EV exposure | Mean L\* of grayscale patches increases by 4–8 units |
| `expo_minus_0p5` | −0.5 EV exposure | Mean L\* decreases by 4–8 units |
| `wb_warm_subtle` | Warm white balance shift | Mean b\* of neutral patches increases (shifts yellow) |
| `wb_cool_subtle` | Cool white balance shift | Mean b\* of neutral patches decreases (shifts blue) |
| `tone_lift_shadows` | Lift dark values | L\* of dark patches (22–24) increases; light patches (19–20) stable |
| `tone_compress_highlights` | Reduce bright values | L\* of bright patches (19–20) decreases; dark patches stable |

These are *relative* assertions: compare "before" vs "after" applying the vocabulary entry to the reference RAW. The direction must be correct; the magnitude should be within a documented range.

**This is the key insight:** each vocabulary `.dtstyle` file should eventually carry a companion assertion spec. When someone contributes a new vocabulary entry, they also specify what effect it should have on the reference targets. This makes vocabulary entries testable, not just parseable.

## Open-source tools

| Tool | Use in Chemigram |
|-|-|
| `colour-science` (Python) | Delta E computation, L\*a\*b\* conversions, chromatic adaptation |
| `Pillow` / `rawpy` | Image loading (TIFF for synthetic, rendered output for real) |
| `numpy` | Patch extraction, histogram stats |
| ArgyllCMS | ICC profile creation, display calibration (if needed) |
| DCamProf | DNG/DCP profile creation from CC24 shots |
| BabelColor CT&A (freeware) | Color measurement and analysis |

## Synthetic fixture generation

For the CI tier, generate synthetic ColorChecker and grayscale TIFFs from the published L\*a\*b\* values:

```python
import colour
import numpy as np
from PIL import Image

# Load reference L*a*b* values
reference_lab = load_json("colorchecker24_lab_d50.json")

# Convert L*a*b* D50 → sRGB
srgb_values = []
for patch in reference_lab:
    lab = np.array([patch["L"], patch["a"], patch["b"]])
    xyz = colour.Lab_to_XYZ(lab, illuminant=colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]["D50"])
    srgb = colour.XYZ_to_sRGB(xyz)
    srgb_clipped = np.clip(srgb, 0, 1)
    srgb_values.append((srgb_clipped * 255).astype(np.uint8))

# Render as 6×4 grid of 100×100 pixel patches
img = np.zeros((400, 600, 3), dtype=np.uint8)
for i, rgb in enumerate(srgb_values):
    row, col = divmod(i, 6)
    img[row*100:(row+1)*100, col*100:(col+1)*100] = rgb

Image.fromarray(img).save("colorchecker_synthetic_srgb.tiff")
```

This synthetic image is the "perfect" digital ColorChecker. Passing it through an identity transform should produce Delta E ≈ 0.0 (limited only by sRGB gamut clipping on out-of-gamut patches like Cyan #18).

## Further reading

- Danny Pascale, "RGB coordinates of the Macbeth ColorChecker" (BabelColor, 2006) — the definitive survey of CC24 color space mathematics
- Imatest Colorcheck documentation — how the industry standard tool analyzes CC24 images
- DxOMark sensor testing protocol — how DxOMark measures noise, dynamic range, and color sensitivity
- ISO 12233:2017 — resolution measurement standard (future expansion if needed)
- ISO 15739 — noise measurement standard
- ISO 17321 — color characterization of digital still cameras
