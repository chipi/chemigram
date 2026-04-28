# Starter Vocabulary — Specification

> Planning document for the starter vocabulary at `vocabulary/starter/` in the chemigram main repo (per ADR-049).
> Proposed structure for review. Actual `.dtstyle` files captured during Phase 1 Slice 6.
> Status · v0.1 draft

This document proposes the structure and contents of the **starter vocabulary** — the OSS pack that ships with Chemigram and gives a new photographer a working action space on day one. It deliberately stays generic; underwater / wildlife / portrait specializations belong in personal vocabularies.

The starter is a **floor**, not a **ceiling**. After day one, gaps surface in real sessions and the photographer's personal vocabulary grows (Phase 2 of the implementation plan).

---

## Design constraints

- **Generic, not specialized.** No underwater, no wildlife, no specific film looks. Those are personal-vocabulary territory.
- **darktable-native semantics.** Every primitive is captured from real sliders in darktable's GUI per ADR-024 (uncheck non-target modules).
- **Coarse but composable.** Continuous values become discrete steps the agent can pick from. Don't overgranularize — too many entries clutter the action space.
- **Total entry count target: 30–45.** At the lower end of the originally-stated 30–50 range. Skewing small lets gaps surface honestly.
- **Layer assignments per ADR-015 / ADR-017:**
  - L0: raw input (no vocabulary)
  - L1: technical baseline (lens correction, denoise) — empty by default per ADR-016, opt-in per camera+lens
  - L2: look (filmic neutral, balanced color) — neutralizing flavor only in starter
  - L3: creative moves (everything in this list)

---

## Proposed categories

### Exposure (5 entries)

The most common adjustment. Coarse steps cover the usual range.

| Name | Adjustment |
|-|-|
| `expo_-0.5` | -0.5 EV |
| `expo_-0.3` | -0.3 EV |
| `expo_+0.0` | 0.0 EV (true no-op; sets enabled=1 with default params) |
| `expo_+0.3` | +0.3 EV |
| `expo_+0.5` | +0.5 EV |

**Note on `expo_+0.0`:** Authoring a literal-zero exposure entry is fiddly (per Phase 0 finding — darktable's slider granularity is ~0.009 EV). May approximate as +0.009 EV documented as practical neutral, or fall back to the exposure encoder once Path C lands (Phase 5).

### White balance — temperature shifts (4 entries)

Relative shifts from the as-shot WB. Photographers reach for these constantly.

| Name | Adjustment |
|-|-|
| `wb_cooler_subtle` | -200K (relative) |
| `wb_cooler` | -500K (relative) |
| `wb_warmer_subtle` | +200K (relative) |
| `wb_warmer` | +500K (relative) |

**Authoring caveat per ADR-025:** WB lives in `temperature` while modern color happens in `channelmixerrgb` (color calibration). These primitives capture only `temperature`; the `channelmixerrgb` D65 baseline stays in L2.

### Color calibration — recovery and protection (3 entries)

Generic recovery moves; underwater-specific recovery (`colorcal_underwater_*`) is personal-vocabulary.

| Name | Purpose |
|-|-|
| `colorcal_recover_red_subtle` | Lift red channel slightly, useful for shaded subjects |
| `colorcal_recover_blue_subtle` | Lift blue channel slightly, useful for warm-cast scenes |
| `colorcal_neutral_d65` | Reset to D65 baseline (the "undo" for color shifts) |

### Filmic flavors (3 entries)

L2 look-committed primitives. Starter has only neutralizing flavors per ADR-017 (look-committed flavors like Acros are personal vocabulary).

| Name | Purpose |
|-|-|
| `filmic_neutral` | Default scene-referred curve, neutral contrast |
| `filmic_soft` | Lower contrast, lifted shadows, gentler highlights |
| `filmic_punchy` | Higher contrast, deeper shadows, brighter highlights — for flat scenes |

### Tone equalizer (5 entries)

Shadow / midtone / highlight shaping. Common moves only.

| Name | Adjustment |
|-|-|
| `tone_lift_shadows_subtle` | Raise shadow zones gently |
| `tone_lift_shadows` | Raise shadow zones meaningfully |
| `tone_compress_highlights` | Pull down highlight zones |
| `tone_lift_midtones` | Open up midtones (subtle) |
| `tone_balanced` | Neutral curve (true no-op equivalent) |

### Local contrast (2 entries)

| Name | Purpose |
|-|-|
| `contrast_subtle` | Gentle micro-contrast lift |
| `contrast_strong` | Pronounced micro-contrast |

### Denoise — profiled (2 entries)

darktable's profiled denoise per camera. Generic strength levels only.

| Name | Purpose |
|-|-|
| `denoise_standard` | Default profile, standard strength |
| `denoise_high_iso` | Stronger denoise for high-ISO input |

### Sharpen (2 entries)

| Name | Purpose |
|-|-|
| `sharpen_subtle` | Gentle output sharpening |
| `sharpen_standard` | Standard output sharpening |

### Structure / clarity (2 entries)

Diffuse-or-sharpen-style edge enhancement.

| Name | Purpose |
|-|-|
| `structure_subtle` | Gentle structure pass |
| `structure_strong` | Pronounced structure |

### Highlights / shadows specifics (3 entries)

Targeted moves outside the tone equalizer.

| Name | Purpose |
|-|-|
| `highlights_recover` | Reconstruct clipped highlights |
| `shadows_open` | Open up deep shadows separately from midtones |
| `vignette_subtle` | Gentle vignette to settle the frame |

---

## Total

**31 entries** across 10 categories. Roughly the mid-point of the 30–50 range, with room to grow if a category surfaces as too thin in early sessions.

---

## What's NOT in the starter

These belong in personal vocabularies or future packs:

- **Underwater / pelagic moves** — `wb_underwater_*`, `colorcal_underwater_recover_*`, etc. Marko's personal pack.
- **Film simulations** — `fuji_acros`, `fuji_velvia`, `kodak_portra_*`. Look-committed L2 flavors per ADR-017.
- **Subject-masked variants** — `tone_lift_shadows_subject`, `wb_warmer_subject_only`. Phase 1 Slice 4 (mask-bound primitives need the AI masker first).
- **Lens-specific L1 templates** — `nikon_d850_24-70mm_lens_correction`, etc. Per-photographer per ADR-016.
- **High-saturation / vivid moves** — `colorcal_pop`, `velvia_emulation`. Aesthetic, not generic.
- **Genre-specific moves** — wildlife sharpening, portrait skin smoothing, landscape clarity. Personal/community packs.

---

## Open questions for review

1. **Counts per category** — does the proposed distribution feel right? (Heavy on tone, light on structure?)
2. **Naming conventions** — should `subtle` / `standard` / `strong` be the standard intensity ladder, or something else?
3. **The `_+0.0` / `_balanced` no-op entries** — useful or noise? They exist so the agent can explicitly say "neutral, don't touch this module." Worth keeping?
4. **Coverage** — anything obvious missing from a generic-photographer-using-darktable starter?
5. **L2 boundary** — `filmic_neutral` lives in L2 but is in this starter list; should we have a separate starter L2 pack vs starter L3 pack, or one unified starter?

---

## Phase 1 Slice 6 deliverable

Once this spec is accepted, Slice 6 captures these primitives by:

1. Opening a representative raw in an isolated darktable configdir
2. Setting one module to the target value
3. Saving as a style with the proposed name
4. Exporting `.dtstyle` to `vocabulary/starter/` in the main repo (per ADR-049)
5. Adding a manifest entry (layer, subtype, touches, modversions, description)
6. Per-entry CI validation (manifest schema + `.dtstyle` parse + modversion match)

Estimated capture time: ~2–3 hours for all 31 entries (Marko, who knows the moves).

---

*Starter Vocabulary Spec · v0.1 · For review before Slice 6 capture work begins*
