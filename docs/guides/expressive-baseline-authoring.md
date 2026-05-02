# Expressive-baseline authoring guide

> How the 35 expressive-baseline vocabulary entries were authored programmatically by reverse-engineering darktable's iop module structs — and how to validate them by re-authoring in darktable's GUI.
> Last updated · 2026-05-02

This guide documents the **Path C technique** (RFC-012) formalized as a vocabulary authoring tool: instead of opening darktable's GUI and saving a style per entry, we read darktable 5.4.1's `src/iop/<module>.c`, identify the `dt_iop_<module>_params_t` struct, map each field to a Python `struct.pack` format, and generate the binary `op_params` blob directly.

The architectural commitment in ADR-001 was that vocabulary growth is *human-author-led so vocabulary reflects taste*. This is unchanged: a programmatic seed entry is a *starting point*, not a final committed entry. The validation step (re-author in darktable's GUI; diff `<op_params>` byte-for-byte) is what closes the loop.

## Status

| Module | RE'd struct | Entries planned | Authored | E2E green |
|-|-|-|-|-|
| `grain` | ✅ v2, 16 bytes | 3 | ✅ 3 | ✅ 2/2 |
| `vignette` | ✅ v4, 44 bytes | 3 | ✅ 3 | ✅ 2/2 |
| `highlights` | ✅ v4, 48 bytes | 2 | ✅ 2 | ✅ 2/2 |
| `sigmoid` | ✅ v3, 56 bytes | 5 | ✅ 5 | ⚠️ 3/4 (1 test-threshold issue) |
| `bilat` (localcontrast) | ✅ v3, 20 bytes | 2 | ✅ 2 | ✅ 2/2 |
| `exposure` | ✅ v7, 28 bytes | 4 | ✅ 4 | (covered indirectly via starter pack tests) |
| `temperature` | ✅ v4, 20 bytes | 1 | ✅ 1 | (covered indirectly via starter pack tests) |
| `colorbalancergb` | ✅ v5, 132 bytes | 11 | ✅ 11 | ✅ 3/3 (sat tests) |
| `channelmixerrgb` | ❌ deferred | 3 (B&W) | 0 | scaffolds skip |
| **`toneequal` (starter bug)** | ❌ deferred | 1 (replace `tone_lifted_shadows_subject`) | 0 | starter bug |
| **Total** | 8 of 9 | 35 | 31 of 35 | 14 of 15 e2e |

## Methodology

For each module:

### 1. Identify the struct

```bash
curl -s https://raw.githubusercontent.com/darktable-org/darktable/release-5.4.1/src/iop/<module>.c \
  | grep -A 40 'typedef struct dt_iop_<module>_params_t'
```

The `DT_MODULE_INTROSPECTION(N, ...)` macro at the top of the file gives the modversion. The struct definition lists each field with its type, default, and (often) `$MIN/$MAX/$DESCRIPTION` annotations.

### 2. Map field types to Python `struct` format

| C type | Python `struct` | Bytes |
|-|-|-|
| `float` | `f` | 4 |
| `int`, `enum`, `gboolean` | `i` (signed) or `I` (unsigned) | 4 |
| `dt_iop_*_mode_t` etc. (enums) | `i` | 4 |

Most darktable params structs are flat float-and-int sequences with no padding (the order in the struct header is the order on disk). `struct.pack('<' + format, *values)` produces the byte-for-byte op_params.

### 3. Calibrate values

Look at the `$DEFAULT:` annotation in the C struct comments for the engine default. For "subtle / medium / heavy" variants, deviate from the default in the direction the entry name implies. Example: `grain_heavy` uses `strength=50.0` (vs default 25.0); `vignette_heavy` uses `brightness=-0.8` (vs default -0.5).

### 4. Wrap in `.dtstyle` XML + manifest entry

Every dtstyle file follows the same shape (see `scripts/author-dtstyle.py` for the template). The single varying piece is the `<op_params>` hex string. The shared `blendop_params` blob is the standard "default blend mode, no mask, fully opaque" gz-compressed value.

### 5. Run the e2e scaffold

The scaffold tests in `tests/e2e/expressive/test_path_*.py` auto-skip when an entry is missing and run when authored. The assertions are direction-of-change pixel statistics (noise variance for grain, corner-vs-center luma ratio for vignette, Laplacian variance for localcontrast, etc.). If the encoded blob is wrong (bad bytes, wrong field order), real darktable typically rejects it loudly or produces a render with no measurable effect.

## How to validate by hand-authoring

1. **Open darktable** → load any image
2. **Enable the module** with the same parameter values listed in this guide's per-module section (see `scripts/author-dtstyle.py` for the canonical defaults)
3. **Save the state as a style:** `right-click on history` → `compress history stack` → `right-click in styles panel` → `save style`
4. **Export the style:** `right-click on style` → `export...` → save somewhere
5. **Diff the `<op_params>` element:**
   ```bash
   diff <(grep -o 'op_params>[^<]*' your_export.dtstyle) \
        <(grep -o 'op_params>[^<]*' vocabulary/packs/expressive-baseline/layers/L3/<module>/<entry>.dtstyle)
   ```

   The two should be byte-identical. If they aren't, possible causes:
   - You set a parameter to a slightly different value (rounding via slider)
   - darktable inserted a field default that this guide didn't account for (rare)
   - The struct has padding or a hidden field (would surface here)

   Differences in the surrounding metadata (timestamps, name, description) are expected and ignored.

## Per-module struct mappings

The canonical encoders are in `scripts/author-dtstyle.py`. Below is the human-readable summary.

### `grain` v2 (16 bytes)

Source: `src/iop/grain.c:62-71`

| Offset | Field | Type | Default | Range |
|-|-|-|-|-|
| 0 | `channel` | enum int | `LIGHTNESS=2` | 0-3 |
| 4 | `scale` | float | `1600/213.2 ≈ 7.504` | 0.094 to 30.02 |
| 8 | `strength` | float | `25.0` | 0-100 |
| 12 | `midtones_bias` | float | `100.0` | 0-100 |

`GRAIN_SCALE_FACTOR = 213.2` (line 44). The UI displays `scale * 213.2` as micrometers.

### `vignette` v4 (44 bytes)

Source: `src/iop/vignette.c:61-73`

11 fields: `scale`, `falloff_scale`, `brightness`, `saturation`, `center.x`, `center.y`, `autoratio` (gboolean = int4), `whratio`, `shape`, `dithering` (enum int), `unbound` (gboolean = int4).

### `highlights` v4 (48 bytes)

Source: `src/iop/highlights.c:104-122`

12 fields: `mode`, `blendL`, `blendC`, `strength`, `clip`, `noise_level`, `iterations` (int), `scales` (enum int), `candidating`, `combine`, `recovery` (enum int), `solid_color`.

`mode` enum: `OPPOSED=5` (default), `LCH=1`, `CLIP=0`, `INPAINT=2`. `recovery` enum: `OFF=0`, `ADAPT=5`, etc.

### `sigmoid` v3 (56 bytes)

Source: `src/iop/sigmoid.c:57-73`

14 fields: `middle_grey_contrast`, `contrast_skewness`, `display_white_target`, `display_black_target`, `color_processing` (enum int: `PER_CHANNEL=0` / `RGB_RATIO=1`), `hue_preservation`, `red_inset`, `red_rotation`, `green_inset`, `green_rotation`, `blue_inset`, `blue_rotation`, `purity`, `base_primaries` (enum int).

### `bilat` / localcontrast v3 (20 bytes)

Source: `src/iop/bilat.c:49-56`

5 fields: `mode` (enum int: `bilateral=0` / `local_laplacian=1`), `sigma_r`, `sigma_s`, `detail`, `midtone`.

### `exposure` v7 (28 bytes)

Source: `src/iop/exposure.c:66-75`

7 fields: `mode` (enum int), `black`, `exposure`, `deflicker_percentile`, `deflicker_target_level`, `compensate_exposure_bias` (gboolean = int4), `compensate_hilite_pres` (gboolean = int4).

The Phase 0 finding (ADR-008): the `exposure` float at offset 8-11 is the EV stop. Hex-edit a starter `expo_+0.5` and replace bytes 8-11 with the IEEE 754 little-endian encoding of the desired EV → produces a valid expo_X.X entry.

### `temperature` v4 (20 bytes)

Source: `src/iop/temperature.c:68-75`

5 fields: `red`, `green`, `blue`, `various`, `preset` (enum int).

The `various` field appears to be set to `+inf` (`0x7f800000`) in saved presets — likely a sentinel for "use computed value." The `preset` enum: `AS_SHOT=0`, `SPOT=1`, `USER=2`, `D65=3`, `D65_LATE=4`. Saved styles use `USER=2`.

### `colorbalancergb` v5 (132 bytes)

Source: `src/iop/colorbalancergb.c:60-106`

33 fields, all floats except the last (enum int):

```
shadows_Y, shadows_C, shadows_H,                 (3 floats)
midtones_Y, midtones_C, midtones_H,              (3 floats)
highlights_Y, highlights_C, highlights_H,        (3 floats)
global_Y, global_C, global_H,                    (3 floats)
shadows_weight, white_fulcrum, highlights_weight,(3 floats)
chroma_shadows, chroma_highlights, chroma_global, chroma_midtones,    (4 floats)
saturation_global, saturation_highlights, saturation_midtones, saturation_shadows,  (4 floats)
hue_angle,                                       (1 float)
brilliance_global, brilliance_highlights, brilliance_midtones, brilliance_shadows,  (4 floats)
mask_grey_fulcrum,                               (1 float)
vibrance, grey_fulcrum, contrast,                (3 floats)
saturation_formula                               (1 enum int: JZAZBZ=0, DTUCS=1)
```

`saturation_formula` defaults to `DTUCS=1` (the modern formula). `grey_fulcrum` and `mask_grey_fulcrum` default to `0.1845`. `shadows_weight` and `highlights_weight` default to `1.0`.

## Deferred to user darktable seeds

Two modules / one bug remain. Both need *one* hand-authored `.dtstyle` from you to unblock me — I can extrapolate the rest from a working seed.

### 1. `channelmixerrgb` v3 (~160 bytes) — 3 B&W entries

Source: `src/iop/channelmixerrgb.c:91-115`

The struct is large and matrix-style: 6 channels × 4-element vectors (`red[]`, `green[]`, `blue[]`, `saturation[]`, `lightness[]`, `grey[]`) plus 6 normalize gbooleans, 4 enum ints (illuminant, illum_fluo, illum_led, adaptation), x/y/temperature/gamut/clip floats, version enum.

Saved styles in the wild use `gz04`-prefixed gz-compressed blobs which adds a layer; uncompressed is also accepted by the parser.

**What I need:** one hand-authored "convert to B&W" style from your darktable session. From there I can vary `grey[]` per the planned variants (`bw_convert` neutral, `bw_sky_drama` blue-emphasis, `bw_foliage` green-emphasis) by editing the 4 floats at the appropriate offset.

### 2. `tone_equalizer` (starter pack bug fix)

The starter `tone_lifted_shadows_subject.dtstyle` currently contains a copy of `expo_+0.5` content (sitting bug). It should be a `tone_equalizer` plugin with raster-mask binding to a registered subject mask.

**What I need:** one hand-authored tone-equalizer + raster-mask save from darktable. The mask binding is encoded in `<blendop_params>`, which is module-specific and harder to reverse-engineer without a working seed.

## How to provide the seeds

For each module:

1. Open any image in darktable
2. Configure ONE example with values close to (`bw_convert` for channelmixerrgb; `tone_lifted_shadows_subject` with a manually-painted subject mask for tone_equalizer)
3. Right-click history → compress
4. Right-click styles panel → create style
5. Right-click that style → export → save anywhere
6. Drop the two `.dtstyle` files in `vocabulary/packs/expressive-baseline/_seeds/` and let me know

I'll do the rest from there.

---

*For the per-module reverse-engineered code, see `scripts/author-dtstyle.py`. For the e2e scaffolds, see `tests/e2e/expressive/`.*
