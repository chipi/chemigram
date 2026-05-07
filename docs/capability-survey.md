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
- `sigmoid_contrast` (parameterized; range [0.5, 5.0]; 1.0 = mild s-curve, 1.5 = darktable default, 2.5 = aggressive). Replaces the v1.5.x `contrast_low / contrast_high` ladder.
- `blacks_lifted`, `blacks_crushed` — pull or crush deep shadows via sigmoid target
- `whites_open` — extend white target

**9-band tone equalizer (RFC-022 Tier 2)**
- `toneequalizer` (parameterized, 9 axes; each in [-2.0, +2.0] EV, default 0.0). Bands: `noise`, `ultra_deep_blacks`, `deep_blacks`, `blacks`, `shadows`, `midtones`, `highlights`, `whites`, `speculars`. Pass any subset; unspecified bands stay at 0. Closes the "tonal-zone curves" gap previously listed under "What's missing".

**Local tone (drawn-mask exposure)**
- `gradient_top_dampen_highlights` — top-half EV reduction
- `gradient_bottom_lift_shadows` — bottom-half EV lift
- `radial_subject_lift` — center ellipse +0.6 EV
- `rectangle_subject_band_dim` — middle horizontal band -0.3 EV
- **Or any EV through an ad-hoc mask**: `apply-primitive --entry exposure --value 0.7 --mask-spec '<json>'` composes parameter values with drawn-form geometry on a per-photograph basis.

### What's missing (fundamentals)

- **Highlight dampen** as a global move (no inverse of `whites_open` shipped, though sigmoid's white target handles the math).
- **Mid-tone luma**: nothing directly moves midtones globally. Closest is `exposure --value V`, which moves everything proportionally (a true mid-tone-only move would route through `colorbalancergb` mid-zone luma fields).
- **Sigmoid `blacks_lifted` / `blacks_crushed` / `whites_open` parameterization** — these still ship as discrete entries. Each represents a *kind* of tonal move (different fields), not a magnitude on the same axis, so they may stay discrete by design.

---

## 2. Color and white balance

### What's there

**White balance (temperature module)**
- `temperature` (parameterized; multi-axis: `red_coeff`, `blue_coeff` in [0.5, 4.0] each; defaults 1.0). The first multi-parameter parameterized entry. Replaces the v1.5.x `wb_cool_subtle`. `wb_warm_subtle` remains in the starter pack as a discrete teaching artifact.
- ⚠️ does not honor masks (darktable pipeline-position issue, see [`mask-applicable-controls.md`](guides/mask-applicable-controls.md#temperature))

**Saturation / chroma / vibrance (colorbalancergb — all parameterized)**
- `saturation_global` (range [-1.0, +1.0]; -1.0 → monochrome, +0.5 → strong boost). RFC-021; replaces v1.5.x sat_* ladder.
- `vibrance` (range [-1.0, +1.0]). RFC-022 Tier 2; replaces v1.5.x `vibrance_+0.3`. Vibrance protects already-saturated pixels — gentler chroma push than saturation_global.
- `chroma_global` (range [-1.0, +1.0]). RFC-022 Tier 2; less saturated-pixel protection than vibrance, more aggressive than saturation_global at equal magnitudes.
- `hue_angle` (range [-180.0, +180.0] degrees). RFC-022 Tier 2; rotates every pixel's hue around the color wheel.

**Per-zone chroma**
- `chroma_boost_shadows`, `chroma_boost_midtones`, `chroma_boost_highlights` — boost color intensity in a tonal zone (not selective on hue)

**4-way grade (color tinting per zone)**
- `grade_shadows_warm`, `grade_shadows_cool`, `grade_highlights_warm`, `grade_highlights_cool` — push tint toward orange or blue in the named zone
- *No mid-tone grade entries shipped*

### What's missing (fundamentals)

- **WB strength variants**: only `subtle` exists. No `wb_warm_medium`, `wb_warm_heavy`, `wb_cool_medium`, etc.
- **Tint axis** (magenta ↔ green): the temperature module supports it, but no vocabulary primitive touches `tint`. Users who want to push toward magenta or green have no entry.
- **Selective hue rotation** (HSL-style "shift greens toward teal"): not present. The Tier 2 `hue_angle` rotates *all* pixels uniformly, not a specific hue band.
- **Mid-tone grade**: only shadows + highlights have warm/cool entries; midtones don't.
- **Selective color** (HSL-style "only affect blues"): not present at all.
- **Channel mixer / B&W conversion**: `channelmixerrgb` is in the planned-but-not-shipped list (issue #63).

---

## 3. Sharpening and detail

### What's there

**Local contrast (bilateral filter)**
- `bilat_clarity_strength` (parameterized; range [-1.0, 4.0]; default 0.0 = no clarity, 1.5 = pronounced). Replaces the v1.5.x discrete `clarity_strong` (the strength axis only). `clarity_painterly` remains discrete — different *kind* of clarity, not strength.
- `clarity_painterly` — softer painterly local contrast

**Edge-aware sharpening (RFC-022 Tier 2)**
- `sharpen` (parameterized; range [0.0, 2.0]; default 0.0 = no sharpen, 0.5 = subtle, 1.0 = strong, 2.0 = aggressive). Unsharp-mask sharpening; radius preserved at darktable default 2.0 px.

### What's missing (fundamentals)

- **Noise reduction**: no entries for `denoiseprofile`, `nlmeans`, `bilat`-as-denoiser. Users with high-ISO files have no go-to.
- **Luminance vs chrominance noise control**: derivative of the above.
- **Hot-pixel removal, dust spotting**: not in scope (no entries; would need separate vocabulary subtype).

---

## 4. Texture and grain

### What's there

- `grain_strength` (parameterized; range [0.0, 100.0]; 8 = grain_fine-equivalent, 25 = medium, 50 = heavy). Replaces the v1.5.x `grain_fine / grain_medium / grain_heavy` ladder.

### What's missing

- **Negative grain / smoothing** as an opposite move.
- **Grain coloring** (sepia tint within grain) — possible via the module, no entry.

---

## 5. Optical / geometric corrections

### What's there

**Vignette (post-process, decorative)**
- `vignette --value V` — parameterized radial corner darkening (RFC-021); brightness in `[-1.0, +1.0]` (negative darkens corners; positive lifts). Replaces the v1.5.x discrete `vignette_subtle / medium / heavy` ladder.

**Crop (RFC-022 Tier 2)**
- `crop --param cx=V cy=V cw=V ch=V` — parameterized crop rectangle in normalized coordinates [0.0, 1.0]; default cx=cy=0.0, cw=ch=1.0 (no crop). First workflow-primitive parameterized entry; aspect-ratio preserved at -1/-1 (free).

### What's missing entirely

- **Lens correction** (`lens` module) — no entries despite darktable supporting it for thousands of lens profiles
- **Rotation / perspective correction**: not in vocabulary
- **Distortion correction** (barrel / pincushion): not in vocabulary
- **Chromatic aberration removal** (`cacorrect`): not in vocabulary

---

## 6. Highlights and shadows recovery

### What's there

- `highlights_clip_threshold` (parameterized; range [0.0, 2.0]; default 1.0 = darktable default, 0.95 = subtle, 0.85 = strong). Replaces the v1.5.x `highlights_recovery_subtle / highlights_recovery_strong` ladder.

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
- **Parameterized continuous control** (RFC-021/RFC-022 + ADR-077..080): 14 entries across all 8 Phase 4 magnitude-ladder modules + 4 Tier 2 modules (`crop`, `sharpen`, plus `colorbalancergb` extra axes — vibrance / chroma_global / hue_angle — and the 9-band `toneequalizer`). Single-axis, multi-axis (2-param `temperature`, 4-param `crop`), and 9-axis (`toneequalizer`) cases all proven on the same architecture.
- **Color grading via `colorbalancergb`**: 4 parameterized axes (saturation_global, vibrance, chroma_global, hue_angle) plus 7 discrete entries for per-zone chroma + warm/cool grade.
- **Drawn-mask masking**: works on every primitive (engine-tested), with three drawn-form geometries.

### Where chemigram is thin today (post-Tier 2)

- **Noise reduction**: nothing. (`denoiseprofile`, `nlmeans`, `bilat`-as-denoiser unrepresented.)
- **Lens / perspective**: nothing. (`lens` lensfun, `ashift`, `cacorrect` untouched.)
- **Selective color (HSL)**: nothing. (`colorzones` would unlock "shift only blues toward teal" type moves.)
- **Looks / presets**: one entry (`look_neutral`).

### What's done (RFC-021 Phase 4 — in progress)

Phase 4 collapses the remaining magnitude-ladder entries into parameterized form. Per the priority order in RFC-021 and ADR-077:

| # | Module | Status | Replaces |
|---|---|---|---|
| 1 | `exposure` | ✅ shipped (v1.6.0) | `expo_+0.5/-0.5/+0.3/-0.3`, `shadows_global_+/-` |
| 2 | `vignette` | ✅ shipped (v1.6.0) | `vignette_subtle/medium/heavy` |
| 3 | `saturation_global` (colorbalancergb) | ✅ shipped | `sat_boost_strong/moderate`, `sat_kill` |
| 4 | `sigmoid_contrast` | ✅ shipped | `contrast_low/high` |
| 5 | `bilat_clarity_strength` | ✅ shipped | strength axis of `clarity_strong` (clarity_painterly stays — different *kind*, not strength) |
| 6 | `grain_strength` | ✅ shipped | `grain_fine/medium/heavy` |
| 7 | `highlights_clip_threshold` | ✅ shipped | `highlights_recovery_subtle/strong` |
| 8 | `temperature` (multi-axis) | ✅ shipped | `wb_cool_subtle`; first multi-parameter ship. `wb_warm_subtle` retained in starter as discrete teaching artifact |

Each module is a single commit: decoder + manifest entry + 5-layer test coverage + visual-proof sweep + magnitude-ladder cleanup. The CI linter (`tests/unit/core/test_parameterized_module_coverage.py`) enforces ADR-080's coverage policy.

### What's next

**Phase 4 + RFC-022 Tier 2 both closed.** All 8 magnitude-ladder modules + 4 Tier 2 expansion modules ship parameterized: `exposure`, `vignette`, `saturation_global`, `sigmoid_contrast`, `bilat_clarity_strength`, `grain_strength`, `highlights_clip_threshold`, `temperature` (Phase 4); `crop`, `sharpen`, colorbalancergb extras (`vibrance`, `chroma_global`, `hue_angle`), and `toneequalizer` (Tier 2). The architecture is proven across single-axis (sharpen, sigmoid_contrast etc.), 2-axis (temperature), 4-axis (crop), and 9-axis (toneequalizer) cases. The test-coverage CI linter (ADR-080) enforces 5-layer discipline on every parameterized entry.

The remaining gaps in this section ("noise reduction", "lens / perspective", "selective color HSL", "looks") are RFC-022 Tier 3 candidates — default-opaque under ADR-008, evidence-promoted from session gap-log signal as real photographic need surfaces. A "pause and observe" window is the natural next step before deciding which of these (if any) clears the cost/benefit bar.

### What "growing it" actually requires

Per the project's Phase 2 framing: *open darktable, capture moves you reach for that don't exist, drop the resulting `.dtstyle` into `~/.chemigram/vocabulary/personal/layers/L3/<module>/`, and add a manifest entry.* The vocabulary-authoring workflow is documented in [`docs/guides/authoring-vocabulary-entries.md`](guides/authoring-vocabulary-entries.md). Building a personal pack to ~30–60 entries over 3 months is the design target.

The infrastructure to grow vocabulary is in place. What's left is finishing the parameterization rollout, then adding the missing fundamental modules.

---

## 11. The discrete-vocabulary problem (resolved for all 8 magnitude-ladder modules in v1.6.0+)

> **Status update — 2026-05-07:** RFC-021 / ADR-077..080 closed this. All 8 magnitude-ladder modules from the Phase 4 plan are now parameterized: `exposure`, `vignette`, `saturation_global`, `sigmoid_contrast`, `bilat_clarity_strength`, `grain_strength`, `highlights_clip_threshold`, `temperature` (the first multi-parameter ship). The framing below is preserved as historical motivation. Whether to expand the parameterized baseline to net-new modules (sharpen / toneequal / denoise / lens / crop) is the open question in RFC-022.

### The question (historical)

*Why does chemigram ship `expo_+0.3`, `expo_-0.3`, `expo_+0.5`, `expo_-0.5` as four separate vocabulary entries instead of one `exposure(ev: float)` primitive that takes a value at apply time?*

### Honest answer (historical)

The pre-v1.6.0 design was **discrete named primitives** — each entry was a fixed `.dtstyle` file with hardcoded parameter values. To get `+0.7 EV` you couldn't. You could apply `expo_+0.5` and then `expo_+0.3` separately (which worked because exposure stacks linearly), but that was a workaround, not a feature. If you wanted `+1.5 EV`, `+2.0 EV`, `-1.0 EV`, etc., you had nothing.

This was a real limitation. Combinatorially enumerating every plausible exposure value (every 0.1 EV from -3 to +3 = 60 entries) is infeasible. So is shipping only four.

### How it's resolved (v1.6.0 onwards)

Per RFC-021 and the closing ADRs:

- **ADR-077** — Path C (decode/edit/re-encode `op_params`) is the default for explicitly-declared parameterizable modules. `op_params` opacity (ADR-008) still applies to non-parameterized modules.
- **ADR-078** — Vocabulary manifest gains a `parameters` array (multi-parameter from day one). Each parameter declares `name / type / range / default` plus a byte-level `field` location.
- **ADR-079** — `apply_primitive` accepts `--value V` (single-parameter shorthand) and `--param NAME=V` (repeatable, multi-parameter). MCP `value` arg is shape-polymorphic.
- **ADR-080** — Hard CI gate enforces 5-layer test coverage (unit / integration / lab-grade global / lab-grade masked / visual-proof sweep) on every parameterized entry.

The shipped surface today: `chemigram apply-primitive --entry exposure --value 0.7` works. So does `chemigram apply-primitive --entry vignette --value -0.6`. Composes orthogonally with `--mask-spec`.

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
