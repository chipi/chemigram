# Chemigram capability survey — what a user can actually do today

> Honest, unvarnished snapshot of every photographic move and workflow operation chemigram supports as of v1.5.x. Two purposes: (1) baseline for planning what to add next, (2) read-from-cold reference for new contributors / agents asking "is X in scope?"

This document organizes capabilities by **what a photographer wants to do**, not by code structure. Each section lists what's there, what's missing, and where the gap is. Honest about both.

Vocabulary loaded: `starter` (4 entries) + `expressive-baseline` (35 entries) = **39 vocabulary primitives**. MCP tools exposed: **22**. CLI verbs: **22**.

---

## 1. Tone and exposure

### What's there

**Global exposure** (RFC-021 parameterized — v1.6.0)
- `exposure --value V` — continuous EV in `[-3.0, +3.0]`. Replaces the previous discrete `expo_+0.5 / expo_-0.5 / expo_+0.3 / expo_-0.3 / shadows_global_+/-` ladder. Any value the photographer wants.

**Tone curve (sigmoid)**
- `contrast_low`, `contrast_high` — global s-curve strength
- `blacks_lifted`, `blacks_crushed` — pull or crush deep shadows via sigmoid target
- `whites_open` — extend white target

**Local tone (drawn-mask exposure)**
- `gradient_top_dampen_highlights` — top-half EV reduction
- `gradient_bottom_lift_shadows` — bottom-half EV lift
- `radial_subject_lift` — center ellipse +0.6 EV
- `rectangle_subject_band_dim` — middle horizontal band -0.3 EV
- **Or any EV through an ad-hoc mask**: `apply-primitive --entry exposure --value 0.7 --mask-spec '<json>'` composes parameter values with drawn-form geometry on a per-photograph basis.

### What's missing (fundamentals)

- **Highlight dampen** as a global move (no inverse of `whites_open` shipped, though sigmoid's white target handles the math).
- **Mid-tone luma**: nothing directly moves midtones globally. Closest is `exposure --value V`, which moves everything proportionally (a true mid-tone-only move would route through `colorbalancergb` mid-zone luma fields).
- **Tonal-zone curves** like "lift only the bottom 25%" or "compress only the top 10%" — sigmoid only exposes black/white targets, not arbitrary control points. `toneequal` would close this gap (see §12).
- **Sigmoid contrast / blacks / whites parameterization** — these still ship as discrete strengths. Phase 4 (per RFC-021) parameterizes them.

---

## 2. Color and white balance

### What's there

**White balance (temperature module)**
- `wb_warm_subtle`, `wb_cool_subtle` — small temperature shift
- ⚠️ does not honor masks (darktable pipeline-position issue, see [`mask-applicable-controls.md`](guides/mask-applicable-controls.md#temperature))

**Saturation (colorbalancergb)**
- `sat_boost_strong` (+0.5), `sat_boost_moderate` (+0.25), `sat_kill` (-1.0 → monochrome)
- `vibrance_+0.3` — gentle saturation that protects saturated pixels

**Per-zone chroma**
- `chroma_boost_shadows`, `chroma_boost_midtones`, `chroma_boost_highlights` — boost color intensity in a tonal zone (not selective on hue)

**4-way grade (color tinting per zone)**
- `grade_shadows_warm`, `grade_shadows_cool`, `grade_highlights_warm`, `grade_highlights_cool` — push tint toward orange or blue in the named zone
- *No mid-tone grade entries shipped*

### What's missing (fundamentals)

- **WB strength variants**: only `subtle` exists. No `wb_warm_medium`, `wb_warm_heavy`, `wb_cool_medium`, etc.
- **Tint axis** (magenta ↔ green): the temperature module supports it, but no vocabulary primitive touches `tint`. Users who want to push toward magenta or green have no entry.
- **Hue rotation**: the `colorbalancergb` 4-way is fixed at warm/cool axes (orange ↔ blue). No hue-shift primitive that targets, say, "shift greens toward teal" or "shift reds toward orange."
- **Mid-tone grade**: only shadows + highlights have warm/cool entries; midtones don't.
- **Selective color** (HSL-style "only affect blues"): not present at all.
- **Channel mixer / B&W conversion**: `channelmixerrgb` is in the planned-but-not-shipped list (issue #63).

---

## 3. Sharpening and detail

### What's there

**Local contrast (bilateral filter)**
- `clarity_strong` — pronounced local contrast / clarity
- `clarity_painterly` — softer painterly local contrast

### What's missing (fundamentals)

- **Real sharpening**: no entries for darktable's `sharpen` / `diffuse-or-sharpen` modules. The existing `clarity_*` uses bilateral local contrast, which is a different operation from edge-aware sharpening.
- **Noise reduction**: no entries for `denoiseprofile`, `nlmeans`, `bilat`-as-denoiser. Users with high-ISO files have no go-to.
- **Luminance vs chrominance noise control**: derivative of the above.
- **Hot-pixel removal, dust spotting**: not in scope (no entries; would need separate vocabulary subtype).

---

## 4. Texture and grain

### What's there

- `grain_fine`, `grain_medium`, `grain_heavy` — film-grain texture at 8/25/50 strength

### What's missing

- **Negative grain / smoothing** as an opposite move.
- **Grain coloring** (sepia tint within grain) — possible via the module, no entry.

---

## 5. Optical / geometric corrections

### What's there

**Vignette (post-process, decorative)**
- `vignette_subtle`, `vignette_medium`, `vignette_heavy` — radial corner darkening
- Three intensity ladder; no inverted vignette or off-center variant

### What's missing entirely

- **Lens correction** (`lens` module) — no entries despite darktable supporting it for thousands of lens profiles
- **Crop / aspect ratio**: no entries; the `clipping` module is darktable-supported
- **Rotation / perspective correction**: not in vocabulary
- **Distortion correction** (barrel / pincushion): not in vocabulary
- **Chromatic aberration removal** (`cacorrect`): not in vocabulary

This entire category is missing — chemigram doesn't yet have any geometry-touching primitives.

---

## 6. Highlights and shadows recovery

### What's there

- `highlights_recovery_subtle`, `highlights_recovery_strong` — pull back blown highlights via the `highlights` (raw) module

### What's missing

- **Shadow recovery** as an explicit primitive (closest is `shadows_global_+` and `gradient_bottom_lift_shadows`, both small / mask-bound).
- **HDR-style highlight + shadow combined recovery** as a single named move.
- **Tone equalizer / `toneequal` module**: not in vocabulary at all. This is darktable's preferred zone-based tone tool; nothing in chemigram exposes it.

---

## 7. Local adjustments (drawn masks)

### What's there

- 4 mask-bound vocabulary entries (gradient × 2, ellipse, rectangle) — all on the `exposure` module
- **Ad-hoc masking via `--mask-spec`**: any vocabulary primitive can be applied through a drawn mask region at apply time (CLI flag + MCP `mask_spec` arg). Engine-tested for every primitive.
- `gradient`, `ellipse`, `rectangle` drawn-form geometries supported in darktable's wire format

### What's not supported

- **Brush-drawn masks** (`brush` form): no encoder; per ADR-076 deferred.
- **Path / polygon masks** with curves: only sharp-cornered rectangles are encoded (rectangle path with degenerate Bézier control points).
- **Mask combination** (multiple shapes per binding via boolean ops): one form per binding currently.
- **Parametric masks** (mask by luma / chroma / hue range, no drawn shape): the darktable feature exists; chemigram doesn't expose it as vocabulary.
- **Content-aware / AI masks** ("the manta's belly"): Phase 4 work; no provider shipped.

---

## 8. Looks and multi-module presets

### What's there

- `look_neutral` — combines `expo_+0.0` + `wb_warm_subtle` as a "baseline neutral look"

### What's missing

- **Genre-specific looks**: no portrait look, landscape look, B&W look, vintage film emulation, etc.
- **Style transfer / look composition**: no L2 entries beyond `look_neutral`.

This is intentionally thin per design (the project's "starter is small, Phase 2 grows from session evidence" framing) — but it does mean a new user has essentially no "one-click look" available.

---

## 9. Workflow operations (not photographic; pure chemigram)

### Versioning (snapshot / branch / checkout / tag / log / diff / reset)

- `chemigram snapshot <image_id>` — capture current XMP as content-addressed object
- `chemigram branch <image_id> --name <branch>` — create branch at HEAD
- `chemigram checkout <image_id> <ref>` — move HEAD to a ref / hash / branch
- `chemigram tag <image_id> --name <name>` — immutable tag (no overwrite)
- `chemigram log <image_id>` — operation history (newest first)
- `chemigram diff <image_id> <a> <b>` — added / removed / changed primitives between snapshots
- `chemigram reset <image_id>` — rewind to baseline ref (ADR-062)
- `chemigram remove-module <image_id> --operation <name>` — strip all history entries for a darktable module

### Render and export

- `chemigram render-preview <image_id> --size N` — JPEG preview
- `chemigram compare <image_id> <a> <b>` — side-by-side stitched render of two snapshots
- `chemigram export-final <image_id> --format jpeg --size N` — high-quality export

### Vocabulary discovery

- `chemigram vocab list` — all entries (filterable by `--tag`, `--layer`)
- `chemigram vocab show <name>` — full manifest fields for one entry
- `chemigram log-vocabulary-gap <image_id>` — record a missing-primitive observation

### Context (tastes / briefs / notes / sessions)

- `chemigram read-context <image_id>` — agent's first-turn context (tastes + brief + notes + recent log + recent gaps)
- `chemigram apply-taste-update --content <text>` — direct CLI-only taste write
- `chemigram apply-notes-update <image_id> --content <text>` — direct CLI-only per-image note write
- (MCP path: `propose_taste_update` → `confirm_taste_update`, two-step)

### Bindings (L1/L2 templates)

- `chemigram bind-layers <image_id>` — apply camera-specific (L1) and look-baseline (L2) templates onto the current XMP

### Workspace lifecycle

- `chemigram ingest <raw_path>` — bootstrap a per-image workspace
- `chemigram status` — runtime diagnostics

### MCP-only (agent-driven)

The CLI mirrors most MCP tools verb-for-verb. Agent-only tools (no direct CLI):
- `propose_taste_update`, `confirm_taste_update` — the two-step propose/confirm flow
- `propose_notes_update`, `confirm_notes_update` — same shape for per-image notes

---

## 10. Honest assessment of the gap

### Where chemigram is strong today

- **Workflow + versioning**: snapshot/branch/diff/tag/reset is comprehensive and Git-shaped. Cheap, reversible, content-addressed. This part feels finished.
- **Engine architecture**: synthesizer, mask-binding, MCP/CLI parity, taste/brief/notes context, session transcripts — all the *plumbing* is solid.
- **Color grading via `colorbalancergb`**: 11 entries cover saturation, vibrance, per-zone chroma, and warm/cool grade.
- **Drawn-mask masking**: works on every primitive (engine-tested), with three drawn-form geometries.

### Where chemigram is thin today

- **Tone fundamentals**: only ±0.5 EV at the limit. A photographer reaching for "+1 stop" has nothing.
- **WB**: only `subtle` strength; no tint axis at all.
- **Sharpening / noise**: nothing.
- **Geometry / lens / crop**: nothing.
- **Tone equalizer / zone tone**: nothing.
- **Looks / presets**: one entry (`look_neutral`).

### What "growing it" actually requires

Per the project's Phase 2 framing: *open darktable, capture moves you reach for that don't exist, drop the resulting `.dtstyle` into `~/.chemigram/vocabulary/personal/layers/L3/<module>/`, and add a manifest entry.* The vocabulary-authoring workflow is documented in [`docs/guides/authoring-vocabulary-entries.md`](guides/authoring-vocabulary-entries.md). Building a personal pack to ~30–60 entries over 3 months is the design target.

The infrastructure to grow vocabulary is in place. What's missing is the actual primitives.

---

## 11. The discrete-vocabulary problem (the elephant in the room)

### The question

*Why does chemigram ship `expo_+0.3`, `expo_-0.3`, `expo_+0.5`, `expo_-0.5` as four separate vocabulary entries instead of one `exposure(ev: float)` primitive that takes a value at apply time?*

### Honest answer

The current design is **discrete named primitives** — each entry is a fixed `.dtstyle` file with hardcoded parameter values. To get `+0.7 EV` today you cannot. You can apply `expo_+0.5` and then `expo_+0.3` separately (which works because exposure stacks linearly), but that is a workaround, not a feature. If you want `+1.5 EV`, `+2.0 EV`, `-1.0 EV`, etc., you have nothing.

This is a real limitation. Combinatorially enumerating every plausible exposure value (every 0.1 EV from -3 to +3 = 60 entries) is, as you noted, insane. So is shipping only four.

### Why the project chose discrete-vocabulary in the first place

Three reasons, each defensible in isolation but they compound:

1. **Agent-paradigm fit.** LLM agents reason better over named choices ("apply lift_shadows") than over continuous parameter tuning ("set exposure to +0.7"). The vocabulary becomes the *action space*; the agent picks moves the way a photographer does — by name and intent, not by knob position.

2. **`op_params` opacity (ADR-008).** Every darktable module's parameters are stored as an opaque hex/base64 binary blob. To parameterize `exposure(ev=0.7)`, the engine needs to *decode* the blob, edit the EV field, and *re-encode* it — a non-trivial reverse-engineering job per module ("Path C" in the project's terminology). The decision was to keep `op_params` opaque by default and only do Path C for high-value exceptions. Today, `exposure` is technically *in* the Path C exception list (per ADR-008's exception clause), but no parameterized API was ever built.

3. **Magnitude-as-vocabulary framing.** The project's design system (`concept/05-design-system.md`) treats magnitude itself as a photographic decision — "subtle / medium / heavy" is the vocabulary, not a slider. This works for moves with discrete photographic intent ("`vignette_subtle` vs `vignette_heavy`"). It works *less* well for moves where the photographer's mental model is genuinely continuous ("I want +1 stop").

### Where the framing breaks

The discrete-vocabulary framing makes sense for **moves with photographic intent that fold cleanly into named buckets**:

- `clarity_strong` vs `clarity_painterly` — these are different *kinds* of clarity, not the same kind at different strengths. Names carry semantic weight.
- `grade_shadows_warm` vs `grade_highlights_warm` — the *zone* matters; you can't slide between them.
- The 4 mask-bound entries — each is a specific geometric move.

It breaks down for **moves whose only meaningful difference is magnitude**:

- `expo_+0.5` vs `expo_+0.3` — these are not different photographic moves. They are the same move at two strengths. Shipping them as separate entries is a category error.
- `vignette_subtle` vs `vignette_medium` vs `vignette_heavy` — three magnitudes of the same move.
- `wb_warm_subtle` (no medium, no heavy) — the magnitude ladder is incomplete here.

The cleaner shape for this category: **one entry per photographic intent, with a `value` parameter at apply time.**

### What this would look like

A parameterized `apply-primitive` flow:

```bash
chemigram apply-primitive iguana --entry exposure --value +0.7
chemigram apply-primitive iguana --entry vignette --value -0.4
chemigram apply-primitive iguana --entry wb_warmth --value +500   # Kelvin delta
```

The vocabulary entry declares *which field of `op_params` is the magnitude field* and what the valid range is. The engine decodes the blob, edits the field, re-encodes, applies. The agent still reasons in terms of named moves; magnitude becomes a parameter rather than part of the name.

This already has a precedent in darktable — every module's GUI is exactly this: named knob with a continuous value. Chemigram's discrete vocabulary diverges from darktable's underlying model.

### What the migration would cost

Roughly, in scope-of-work terms:

1. **Path C decoders**: per-module hex codecs for the modules where parameterization makes sense (`exposure`, `vignette`, `temperature`, `colorbalancergb` saturation, sigmoid contrast, `grain` strength, `bilat` clarity strength, `highlights` clip threshold). Probably 8–12 modules total. Each is a half-day of struct reverse-engineering against the darktable source. The `_lab_grade_deltas.py` test layer can validate the round-trip.

2. **Manifest schema extension**: vocabulary entries gain an optional `parameter` field declaring the magnitude axis (`{"name": "ev", "field_offset": 0, "type": "float", "range": [-3.0, 3.0], "default": 0.0}`).

3. **CLI / MCP surface**: `apply-primitive` gains a `--value <n>` flag (and MCP `value` arg). Engine routes through the parameterized synthesizer when the entry has a `parameter` field.

4. **Vocabulary cleanup**: the 39 current entries collapse. `expo_±0.3/±0.5/shadows_global_±` become one parameterized `exposure` entry. The three vignette intensities become one. The two WB entries become one (with sign and magnitude as parameter). Net: probably ~20 parameterized entries replace ~30 discrete ones, plus space for ~10 new genuinely-discrete moves.

5. **ADR**: a new ADR documenting the architectural shift. Likely supersedes part of ADR-008's Path A/Path C framing, since Path C becomes the default for parameterizable modules rather than the rare exception.

This is a real piece of architectural work — not a 1-hour ergonomic add. But it's also the right shape for what chemigram is trying to be. The current vocabulary's thinness on fundamentals is a *symptom* of the discrete-vocabulary framing being asked to do work it wasn't designed for.

### Recommendation

Tomorrow's planning conversation should put parameterization on the table as a candidate for the next significant ship. It's the kind of change that unblocks the whole "fundamental controls" gap in section 1, 2, 3, 4, 6 above — without combinatorial vocabulary explosion.

---

## 12. Full darktable module catalog (the universe of what's possible)

What follows is **every photographically-meaningful darktable 5.x module**, organized by pipeline phase. The purpose is to make the gap between "what darktable can do" and "what chemigram exposes" explicit. A primitive is **chemigram-shipped** when there's at least one vocabulary entry touching the module today.

Categories:
- ✅ shipped — chemigram has at least one vocab entry touching this module
- ⚠️ partial — module is touched but coverage is thin (one direction, one magnitude, etc.)
- ❌ not yet — module is not touched by any vocabulary entry
- 🚫 out of scope — generally not exposed via vocabulary (camera/raw plumbing, output)

### RAW phase (pre-demosaic / scene-data)

| Module | What it does | Status |
|---|---|---|
| `rawprepare` | Raw black / white levels, crop edges | 🚫 out of scope (camera-specific) |
| `temperature` | White balance (camera-as-shot or user) | ⚠️ partial — only `wb_warm_subtle`, `wb_cool_subtle`; no medium/heavy, no tint axis. Mask binding silently ignored (#80) |
| `highlights` | Highlight reconstruction (clip / LCH / inpaint / segmentation) | ⚠️ partial — `highlights_recovery_subtle/strong`; no method-selection variants |
| `hotpixels` | Hot-pixel removal | 🚫 out of scope |
| `rawdenoise` | Wavelet denoise on raw mosaic | ❌ not yet |
| `cacorrect` | Chromatic-aberration correction | ❌ not yet |
| `demosaic` | Bayer / X-Trans interpolation | 🚫 out of scope (algorithm choice, not photographic intent) |
| `denoiseprofile` | Profiled (per-camera) denoise | ❌ not yet — high-value gap |

### Scene-referred phase (the modern pipeline middle)

| Module | What it does | Status |
|---|---|---|
| `exposure` | Global EV / black-level / clipping | ⚠️ partial — only ±0.3, ±0.5; black-level via `shadows_global_±` is too small to matter |
| `colorin` | Input color profile | 🚫 out of scope (technical) |
| `lens` | Lens correction (vignetting, distortion, CA) | ❌ not yet — entire module unrepresented |
| `clipping` | Crop / aspect ratio / rotation | ❌ not yet — entire module unrepresented |
| `flip` | Orientation (rotate 90/180/270, flip) | ❌ not yet |
| `ashift` | Perspective / keystone correction | ❌ not yet |
| `liquify` | Local pixel pushing (manual warp) | ❌ not yet |
| `retouch` | Frequency-separation retouching | ❌ not yet — major omission for portrait work |
| `spots` | Spot healing / cloning | ❌ not yet |
| `censorize` | Pixelation / blur for privacy | ❌ not yet |
| `colorchecker` | Color calibration via reference chart | 🚫 out of scope (technical) |
| `channelmixerrgb` | RGB channel mixer (modern) | ❌ planned (#63 — B&W trio) |
| `colorbalancergb` | 4-way grade + saturation + chroma + brilliance | ✅ shipped — 11 entries (saturation, vibrance, chroma, grade) |
| `tonecurve` | Manual RGB / Lab tone curve | ❌ not yet |
| `toneequal` | Zone-based tone equalizer (darktable's preferred local tone tool) | ❌ not yet — major omission |
| `sigmoid` | Modern tone mapping (filmic replacement) | ⚠️ partial — `contrast_low/high`, `blacks_lifted/crushed`, `whites_open`. No `whites_dampen`, no per-channel control |
| `filmicrgb` | Older tone mapping (still ships) | 🚫 out of scope (sigmoid is preferred) |
| `basicadj` | Combined exposure + contrast + saturation | ❌ not yet (covered by separate primitives) |
| `colorize` | Solid color tint | ❌ not yet |
| `colorbalance` | Older 4-way grade (pre-rgb) | 🚫 out of scope (colorbalancergb is preferred) |
| `colorzones` | Per-hue selective adjustment (HSL) | ❌ not yet — no "shift only blues toward teal" capability |
| `colorcontrast` | Lab a/b chroma contrast | ❌ not yet |
| `velvia` | Saturation with falloff for skin tones | ❌ not yet |
| `vibrance` | Old vibrance module (newer is in colorbalancergb) | 🚫 out of scope (modern path) |
| `monochrome` | B&W via filter color | ❌ not yet — overlap with #63 channelmixerrgb |
| `grain` | Film grain texture | ✅ shipped — 3 entries (fine/medium/heavy) |
| `bilat` (local contrast) | Bilateral local contrast / clarity | ⚠️ partial — `clarity_strong`, `clarity_painterly`; no negative/soften variant |
| `bloom` | Soft glow / orton-style bloom | ❌ not yet |
| `soften` | Gaussian softening | ❌ not yet |
| `sharpen` | Unsharp mask sharpening | ❌ not yet — major omission |
| `diffuse` (diffuse-or-sharpen) | Reaction-diffusion sharpen / denoise / restore detail | ❌ not yet — modern darktable's flagship sharpening |
| `equalizer` (contrast equalizer) | Wavelet-based per-frequency contrast control | ❌ not yet — flagship advanced sharpening / clarity |
| `nlmeans` | Non-local-means denoise | ❌ not yet |
| `bilateral` (denoise) | Bilateral denoise | ❌ not yet |
| `defringe` | Color-fringe removal | ❌ not yet |
| `hazeremoval` | Atmospheric haze removal | ❌ not yet |
| `vignette` | Decorative radial darkening | ✅ shipped — 3 entries (subtle/medium/heavy); no inverted variant |
| `borders` | Frame border | ❌ not yet (composition / output decoration) |
| `watermark` | Text or image overlay | ❌ not yet |

### Display-referred / output

| Module | What it does | Status |
|---|---|---|
| `colorout` | Output color profile | 🚫 out of scope (technical) |
| `gamma` | Display gamma | 🚫 out of scope |
| `dither` | Output dithering | 🚫 out of scope |
| `finalscale` | Resampling / output size | 🚫 out of scope (handled by `--width`/`--height`) |

### Tally

- darktable modules total: ~50 photographically-meaningful (excluding 🚫 out-of-scope plumbing)
- chemigram ✅ shipped: **5 modules** (exposure, sigmoid, colorbalancergb, vignette, grain)
- chemigram ⚠️ partial: **5 modules** (temperature/wb, highlights, exposure, sigmoid, bilat)
- chemigram ❌ not yet: **~30 modules**

The gap isn't that the project chose to ship 39 thin entries and ran out of time — it's that ~30 distinct photographic capabilities darktable supports are unrepresented in the vocabulary. The biggest user-visible holes:

1. **`toneequal`** — zone-based tone equalizer; the modern darktable user's primary local-tone tool
2. **`sharpen` / `diffuse-or-sharpen` / `equalizer`** — the entire sharpening family
3. **`denoiseprofile` / `nlmeans`** — denoise; a daily-use need
4. **`clipping` / `ashift` / `flip`** — composition (crop, rotate, perspective)
5. **`lens`** — lens correction (vignetting, distortion, CA)
6. **`retouch` / `spots`** — frequency-sep retouching; portrait essential
7. **`colorzones`** — selective hue/sat/lum (HSL) adjustments
8. **`tonecurve`** — manual tone curve

Closing those gaps is real authoring work (and probably also benefits from the parameterization shift in section 11).

---

## See also

- [`guides/visual-proofs.md`](guides/visual-proofs.md) — chart-based before/after gallery showing every shipped primitive in action
- [`guides/mask-applicable-controls.md`](guides/mask-applicable-controls.md) — per-module compatibility for masking
- [`guides/vocabulary-patterns.md`](guides/vocabulary-patterns.md) — how to combine shipped primitives
- [`guides/authoring-vocabulary-entries.md`](guides/authoring-vocabulary-entries.md) — author your own primitives via darktable GUI
- [`adr/ADR-008-opaque-blob-carriers.md`](adr/ADR-008-opaque-blob-carriers.md) — the opaque-blob default; ADR-077 supersedes this for explicitly-declared parameterizable modules
- `vocabulary/starter/README.md`, `vocabulary/packs/expressive-baseline/README.md` — pack-level catalogs
