# Chemigram capability survey — what a user can actually do today

> Honest, unvarnished snapshot of every photographic move and workflow operation chemigram supports as of **v1.7.0** (released 2026-05-07). Two purposes: (1) baseline for planning what to add next, (2) read-from-cold reference for new contributors / agents asking "is X in scope?"

This document organizes capabilities by **what a photographer wants to do**, not by code structure. Each section lists what's there, what's missing, and where the gap is. Honest about both.

**Inventory (post-v1.7.0):** Vocabulary loaded: `starter` (3 entries) + `expressive-baseline` (39 entries) = **42 vocabulary primitives**. **18 of those are parameterized** (RFC-021 / RFC-022 / ADR-077..081). **12 darktable modules** have at least one shipped entry. MCP tools exposed: **23**. CLI verbs mirror the MCP tool surface verb-for-verb plus a diagnostic `chemigram status` (per RFC-020).

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

- **Manual tone curve** (`tonecurve` module): no per-control-point manual curve. Closest substitute is `toneequalizer`'s 9-band per-zone control, which covers most photographic intents without needing per-curve-point control.
- **Sigmoid `blacks_lifted` / `blacks_crushed` / `whites_open` parameterization** — these still ship as discrete entries. Each represents a *kind* of tonal move (different fields), not a magnitude on the same axis, so they may stay discrete by design (per ADR-081 Tier 0 framing).

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

**Brilliance — per-zone luminance shaping (colorbalancergb — all parameterized; #86)**
- `brilliance_global`, `brilliance_highlights`, `brilliance_midtones`, `brilliance_shadows` (each range [-1.0, +1.0]). Per-zone luminance shaping — global moves all zones; per-zone variants target specific tonal ranges.

**Per-zone chroma**
- `chroma_boost_shadows`, `chroma_boost_midtones`, `chroma_boost_highlights` — boost color intensity in a tonal zone (not selective on hue)

**4-way grade (color tinting per zone)**
- `grade_shadows_warm`, `grade_shadows_cool`, `grade_highlights_warm`, `grade_highlights_cool` — push tint toward orange or blue in the named zone
- *No mid-tone grade entries shipped*

### What's missing (fundamentals)

- **WB tint axis** (magenta ↔ green): the temperature module's mv4 struct stores RGB coefficients, not temp/tint. The 2-axis parameterized `temperature` exposes `red_coeff` + `blue_coeff` — that captures warming / cooling but not the green-magenta axis a photographer thinks in. A separate `tint` parameter with proper coefficient → tint conversion would close this.
- **Selective hue rotation** (HSL-style "shift only greens toward teal"): not present. The Tier 2 `hue_angle` rotates *all* pixels uniformly, not a specific hue band. `colorzones` would unlock this — Tier 3 per ADR-081 (24+ params; surface doesn't reduce cleanly to scalar).
- **Mid-tone grade**: only shadows + highlights have warm/cool entries; midtones don't. Pure authoring work; no architectural blocker.
- **Selective color** (HSL-style "only affect blues"): not present at all. Same `colorzones` Tier-3 framing as above.

---

## 3. Sharpening and detail

### What's there

**Local contrast (bilateral filter)**
- `bilat_clarity_strength` (parameterized; range [-1.0, 4.0]; default 0.0 = no clarity, 1.5 = pronounced). Replaces the v1.5.x discrete `clarity_strong` (the strength axis only). `clarity_painterly` remains discrete — different *kind* of clarity, not strength.
- `clarity_painterly` — softer painterly local contrast

**Edge-aware sharpening (RFC-022 Tier 2)**
- `sharpen` (parameterized; range [0.0, 2.0]; default 0.0 = no sharpen, 0.5 = subtle, 1.0 = strong, 2.0 = aggressive). Unsharp-mask sharpening; radius preserved at darktable default 2.0 px.

### What's missing (fundamentals)

- **Modern darktable sharpening family**: `diffuse-or-sharpen` (reaction-diffusion, darktable's flagship modern sharpener) and `equalizer` (wavelet-based per-frequency contrast control) are unrepresented. The shipped `sharpen` covers the unsharp-mask common case but lacks the more advanced shaping these modules provide.
- **Noise reduction**: no entries for `denoiseprofile`, `nlmeans`, `bilat`-as-denoiser. Users with high-ISO files have no go-to. Tier 3 per ADR-081 (per-camera profiles violate the cost-shape guidance).
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

- **Lens correction** (`lens` module): no entries despite darktable supporting it for thousands of lens profiles. Tier 3 per ADR-081 (lensfun-coupled per-lens-model database lookup; the parameterization shape is "select profile" not "tune scalar value"). A possible non-Path-C path: an L1 binding entry that auto-applies the lens profile based on EXIF (sidesteps Tier 3 framing entirely).
- **Rotation / perspective correction** (`flip`, `ashift`): not in vocabulary. Pure authoring work — both modules are reasonable Tier 2 candidates (small struct; scalar parameters).
- **Distortion correction** (barrel / pincushion): not in vocabulary.
- **Chromatic aberration removal** (`cacorrect`): not in vocabulary.
- **Retouch / spot healing** (`retouch`, `spots`): not in vocabulary at all. This is *the* major portrait gap. The shape is unusual — frequency-separation retouching has stroke-based input that doesn't reduce to a per-image vocabulary entry. Probably needs its own RFC for what shape this would take in chemigram.

---

## 6. Highlights and shadows recovery

### What's there

- `highlights_clip_threshold` (parameterized; range [0.0, 2.0]; default 1.0 = darktable default, 0.95 = subtle, 0.85 = strong). Replaces the v1.5.x `highlights_recovery_subtle / highlights_recovery_strong` ladder.

### What's missing

- **Shadow recovery as an explicit single-named primitive**: the parameterized `toneequalizer --param shadows=+1.0` covers this and more, but a one-liner shorthand (e.g., L2 `recover_shadows` look) doesn't yet exist.
- **HDR-style highlight + shadow combined recovery as a single named move**: again, achievable via `toneequalizer` with shadows up + highlights down, but no L2 composite shipped for this common use case.

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

- `look_neutral` (starter) — `exposure` + `wb_warm_subtle` baseline; the original teaching artifact
- `look_portrait` — gentle skin-protective composition (exposure +0.2 EV + sigmoid_contrast 1.2 + colorbalancergb saturation_global -0.1 + vibrance +0.2)
- `look_landscape` — vibrant dramatic landscape (sigmoid_contrast 2.0 + saturation_global +0.3 + vibrance +0.2 + bilat_clarity_strength 1.0)
- `look_vintage_film` — nostalgia / faded film (sigmoid_contrast 1.2 + saturation_global -0.2 + grain_strength 25 + temperature warm shift)
- B&W trio also serves as look-shaped composition: `bw_convert` (Rec. 709 neutral), `bw_sky_drama` (red-emphasis), `bw_foliage` (green-emphasis)

### What's missing

- **Cinematic genre looks**: no `look_cinematic_teal_orange`, `look_film_kodachrome`, `look_film_portra`, `look_high_key_portrait`, `look_low_key_portrait`, `look_moody_dramatic`, etc. Each is a multi-plugin composite of existing primitives — pure authoring work, no architectural blocker.
- **Decade/era looks** (`look_70s_film`, `look_90s_grain`, `look_2000s_digital`, etc.): same shape — composition of existing primitives.
- **Style transfer**: looks are static composites; the project doesn't currently support "match this reference image" workflows.

The four looks shipped today bring the Looks layer past "essentially nothing" — but it remains the thinnest L2 surface relative to L3. Per the project's "starter is small, Phase 2 grows from session evidence" framing, more looks ship from real session pull rather than upfront authoring.

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
- **Parameterized continuous control** (RFC-021/RFC-022 + ADR-077..083): **38 parameterized entries** across **18 modules** as of v1.8.0+ (every magnitude-ladder Phase 4 module + the original 4 Tier 2 expansions + 4 brilliance axes + 9 colorbalancergb Color Grading axes + dehaze + texture + 3 HSL multi-axis entries via colorequal + filmic + denoise + lens + transform + WB Kelvin UX wrapper). Single-axis, multi-axis (2/3/4 param), 8-axis HSL channels, 9-axis toneequalizer, 10-axis lens, and 24-axis HSL panel cases all proven on the same architecture. Discoverability via MCP `list_vocabulary` + CLI `vocab show` (#89). **Total vocabulary corpus: 78 entries** (38 parameterized + 40 discrete: L1/L2 looks + L3 kinds + mask-bound). Did-you-mean suggestions on unknown entry names (#107).
- **Read-side analytics** (v1.9.0): `chemigram gap-log` sub-app (#106) for `vocabulary_gaps.jsonl` — list / rank / show / clear, supports the Phase 2 use-driven feedback loop. `chemigram session-log` sister sub-app (#109) for session transcripts — list / show / find / replay. Both with full guides under `docs/guides/`.
- **Tone control**: `exposure` (parameterized EV ±3) + `sigmoid_contrast` (parameterized) + `toneequalizer` (9-band parameterized) + `highlights_clip_threshold` (parameterized) + `blacks_lifted/crushed/whites_open` (discrete kinds) + 4 mask-bound exposure entries. The whole tonal surface is photographically operational.
- **Color grading via `colorbalancergb`**: 8 parameterized axes (saturation_global, vibrance, chroma_global, hue_angle, brilliance × 4) plus 7 discrete entries for per-zone chroma + warm/cool grade.
- **B&W conversion**: `bw_convert` / `bw_sky_drama` / `bw_foliage` via channelmixerrgb mv3 — closes #63 and the "channel mixer / B&W" gap from §2.
- **Drawn-mask masking**: works on every primitive (engine-tested), with three drawn-form geometries (gradient / ellipse / rectangle).
- **CI gates**: 5-layer parameterized coverage (ADR-080), manifest-modversion consistency (#85), runtime modversion drift detection (ADR-082) — three separate safety nets against the failure modes parameterization could introduce.

### Where chemigram is thin today (post-v1.9.0 in-progress)

The "thin" list has narrowed dramatically since v1.7.0. v1.8.0 closed the bulk of the Tier 3 module watchlist; the in-progress v1.9.0 cycle has shipped CLI analytics (gap-log + session-log), real-raw fixture path, more vocabulary entries (cinematic L2 looks + L3 discrete kinds), and drafted RFC-024 (range masks) + RFC-025 (spot removal/heal).

**Closed in v1.8.0** (decoder shipped or partial-empirical):
- ✅ **Selective color HSL** — closed via RFC-023 / ADR-083 → `colorequal` mv4 (3 multi-axis entries; 24 axes total).
- ✅ **Noise reduction** — closed via #96 → `denoiseprofile` mv12 (NLMEANS mode; wavelet-curve verification under #100).
- ✅ **Lens correction** — closed via #95 → `lens` mv10 with manual-override strength axes (EXIF auto-binding under #100).
- ✅ **Diffuse-or-sharpen** — closed via #92 → `diffuse` mv2 (texture entry).
- ✅ **Dehaze** — closed via #90 A.2 → `hazeremoval` mv3.
- ✅ **Filmic v6** — closed via #97 → `filmicrgb` mv6 alongside the existing sigmoid.
- ✅ **Rotation / perspective** — closed via #101 → `ashift` mv5 (transform entry).
- ✅ **WB Kelvin UX** — closed via #102 → `wb_kelvin_delta` (UX wrapper on temperature).
- ✅ **Color Grading completion** — closed via #91 + #90 A.4.

**Closed / drafted in v1.9.0 (in-progress)**:
- ✅ **Real-raw visual-proof fixture path** — closed via #103 (commit `830f89f`); script extension supports HSL skip-listed entries against a real raw fixture; awaits the iguana fixture file drop.
- ✅ **Cinematic L2 looks** — closed via #104; 9 named photographic recipes (cinematic / portrait / decade) compose existing primitives.
- ✅ **Gap-log analytics CLI** — closed via #106; Phase 2 use-driven feedback loop now has read-side tooling.
- ✅ **CLI ergonomics polish** — closed via #107; did-you-mean suggestions for unknown vocabulary names; shell-completion guide.
- ✅ **Session-log analytics CLI** — closed via #109; sister to gap-log for session transcripts.
- ✅ **More L3 discrete kinds** — closed via #110; 7 new clarity / sharpen / vignette / split-grade variants.
- ✅ **Lightroom-to-chemigram comparison guide** — closed via #111; onboarding doc for Lightroom users.
- 📝 **Range masks (color-range / luminance-range / depth-range / subject)** — RFC-024 drafted via #105 (Draft v0.1). Hybrid proposal: native parametric for color/luminance ranges + deferred RFC-026 for depth/subject providers.
- ✅ **Spot removal / heal** — closed via RFC-025 / ADR-087. New `apply_spot` MCP tool (sister to `apply_primitive`) with HEAL + CLONE algorithms on CIRCLE geometry. Wire-verified e2e against darktable. AI auto-detection ("find all the spots") deferred to RFC-030.

**Still open** (post-v1.9.0 horizon):
- **Manual tone curve** (`tonecurve`) — the last Lightroom daily-use gap. Decoder is straightforward but the 520-byte spline-curve struct needs an empirical baseline from a darktable-GUI session. Tracked as #94, sequenced under #100.
- **Discrete colorzones HSL precision fallback** — for the 5% HSL workflow that needs Lightroom's per-zone Range slider precision. Discrete-only; tracked as #98, sequenced under #100.
- **AI / content-aware masks + spot detection** — the BYOA arc per ADR-007. Placeholder RFC-026 named in RFC-024 + RFC-025; not yet drafted. Sibling project shape (`chemigram-masker-sam`).
- **Multi-photographer review phase plan** — the deferred work from ADR-081's promotion threshold. Solo build-baseline → community transition. No RFC drafted yet.
- **Pack management / vendor packs / multi-pack composition stress-testing** — the loader supports multi-pack but conflict resolution between packs hasn't been stress-tested. No RFC drafted yet.

**Tier classification post-v1.9.0 in-progress:** ADR-081's Tier 3 examples list is now stale (all of `lens`, `denoiseprofile`, `colorzones`-via-colorequal have been promoted or addressed). ADR-083 records the first formal Tier 3 → Tier 2 promotion (HSL via colorequal). The remaining named Tier 3 items (`tonecurve`, `colorzones`-as-discrete, retouch-via-AI) are blocked on either darktable-session work or RFC-026 / depth-mask provider scaffolding.

### What's been shipped against this survey's vision (v1.6.0 → v1.7.0)

This survey was the source document for **RFC-021** (parameterization architecture) and **RFC-022** (tiered baseline policy). Both closed; their ship landed across v1.6.0 and v1.7.0. The capability surface is materially different from when this doc was first drafted.

**Architecture work completed:**

| RFC / ADR | Decision | Where it shows up |
|---|---|---|
| **RFC-021** → ADR-077..080 | Path C (decode/edit/re-encode op_params) is the default for explicitly-declared parameterizable modules | All 18 parameterized entries below ride this |
| **RFC-022** → ADR-081 | Four-tier classification: Tier 0 immutable / Tier 1 Phase-4 floor / Tier 2 active expansion / Tier 3 default-opaque | This document's "thin today" lists are Tier 3 watchlist |
| **RFC-007** → ADR-082 | Modversion drift: warn-loud at vocab load, hard-fail at apply via `PatchError`, env-var-strict mode | Runtime safety net for the 11 Path C decoders |

**Vocabulary work completed (18 parameterized entries across 11 modules):**

| # | Module | Entries | Tier |
|---|---|---|---|
| 1 | `exposure` | `exposure` (single-axis EV) | 1 (Phase 4 floor) |
| 2 | `vignette` | `vignette` (single-axis brightness) | 1 |
| 3 | `colorbalancergb` | `saturation_global`, `vibrance`, `chroma_global`, `hue_angle`, plus 4 brilliance axes (#86) | 1 + 2 |
| 4 | `sigmoid` | `sigmoid_contrast` (single-axis) | 1 |
| 5 | `bilat` | `bilat_clarity_strength` (single-axis) | 1 |
| 6 | `grain` | `grain_strength` (single-axis) | 1 |
| 7 | `highlights` | `highlights_clip_threshold` (single-axis) | 1 |
| 8 | `temperature` | `temperature` (multi-axis: `red_coeff`, `blue_coeff`) | 1 |
| 9 | `crop` | `crop` (4-axis: cx/cy/cw/ch — first workflow primitive) | 2 |
| 10 | `sharpen` | `sharpen` (single-axis) | 2 |
| 11 | `toneequal` | `toneequalizer` (9-axis: noise..speculars) | 2 |

Plus the **B&W trio** (3 channelmixerrgb mv3 entries, Tier 0 discrete) and the **3 L2 looks** (portrait / landscape / vintage_film).

**Vocabulary delta against this survey's original snapshot:**

| Metric | Survey premise | Post-v1.7.0 | Movement |
|---|---|---|---|
| Total entries | 39 | 42 | +3 net (16 collapsed into parameterized; 19 added) |
| Parameterized entries | 0 | 18 | +18 |
| Modules with at least one entry | 5 | 12 | +7 (added bilat, highlights, temperature, crop, sharpen, toneequal, channelmixerrgb) |
| L2 composite looks | 1 | 4 | +3 |
| Mask-bound entries | 4 | 4 | no change |

### Where this survey was the source of next-batch decisions

The survey's **§12 "biggest user-visible holes"** list (8 items) was the implicit target of RFC-022's Tier 2 ship. Status of each, post-v1.7.0:

| # | Original gap | Status |
|---|---|---|
| 1 | `toneequal` zone-based tone equalizer | ✅ shipped (Tier 2; 9-axis parameterized) |
| 2 | `sharpen` / `diffuse-or-sharpen` / `equalizer` family | ⚠️ partial — `sharpen` shipped; `diffuse-or-sharpen` + `equalizer` still missing |
| 3 | `denoiseprofile` / `nlmeans` denoise | ❌ Tier 3 (per-camera config; ADR-081) |
| 4 | `clipping` / `ashift` / `flip` composition | ⚠️ partial — `crop` (= `clipping` module) shipped; rotation/perspective ❌ |
| 5 | `lens` correction | ❌ Tier 3 (lensfun-coupled; ADR-081) |
| 6 | `retouch` / `spots` portrait healing | ❌ — would need its own RFC for the stroke-based input shape |
| 7 | `colorzones` HSL selective color | ❌ Tier 3 (24+ params; ADR-081) |
| 8 | `tonecurve` manual tone curve | ❌ — natural Tier 2 candidate; same multi-node shape as toneequalizer |

**3 of 8 fully closed; 2 partially; 5 remain (3 of those structurally Tier 3, 2 unblocked Tier 2 candidates).**

### What's next (post-v1.7.0)

Three shapes of work make sense for v1.8.0+:

**Shape A — Tier 2 expansion of unblocked candidates** (judgment-driven feature commits per ADR-081; no per-module ADR overhead):
- `tonecurve` (manual curve) — same shape as `toneequalizer`, ~half a day
- `diffuse-or-sharpen` strength axis — extends the sharpening family
- `flip` / `ashift` — small structs, scalar parameters; closes the rotation/perspective half of #4 above
- More L2 looks (cinematic, film-stock, decade, mood) — pure composition; no Path C

**Shape B — Tier 3 promotion ADRs** (each ships its own ADR per ADR-081; the bar is "real session evidence" + a workable cost-shape argument):
- `denoiseprofile` — possible promotion shape: ship the camera's auto-detected profile baked in, expose only the strength axis
- `lens` — possible promotion shape: L1 binding entry that auto-applies the profile from EXIF, no Path C decoding
- `colorzones` — possible promotion shape: ship "axis-collapsed" entries (only the saturation curve at 4 nodes) rather than the full 24-param spline

**Shape C — Novel-shape RFCs** (architectural questions whose shape isn't yet settled):
- `retouch` / `spots` — stroke-based input doesn't fit the per-image vocabulary entry pattern. RFC needed for what shape this takes.
- AI / content-aware masks — explicitly conditional Phase 4 in IMPLEMENTATION.md; sibling project pattern (`chemigram-masker-sam`); biggest scope jump in the project.

### What "growing it" actually requires

Per the project's Phase 2 framing: *open darktable, capture moves you reach for that don't exist, drop the resulting `.dtstyle` into `~/.chemigram/vocabulary/personal/layers/L3/<module>/`, and add a manifest entry.* The vocabulary-authoring workflow is documented in [`docs/guides/authoring-vocabulary-entries.md`](guides/authoring-vocabulary-entries.md). Building a personal pack to ~30–60 entries over 3 months is the design target.

What changed post-v1.7.0: most "growing it" work for parameterizable modules now ships as Path C decoders programmatically (no GUI seed needed — see `docs/guides/expressive-baseline-authoring.md` for the methodology). Hand-authoring via darktable GUI is reserved for entries whose photographic intent is genuinely discrete (Tier 0) — the 14 plain-discrete entries in expressive-baseline plus the starter-pack teaching artifacts.

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
| `temperature` | White balance (camera-as-shot or user) | ✅ parameterized (Tier 1; multi-axis `red_coeff` + `blue_coeff`). Plus starter `wb_warm_subtle` discrete. Mask binding silently ignored (#80, documented limitation). Tint axis still missing. |
| `highlights` | Highlight reconstruction (clip / LCH / inpaint / segmentation) | ✅ parameterized (Tier 1; `highlights_clip_threshold`). Method enum preserved at default; method-selection variants would be Tier 0 discrete entries if needed. |
| `hotpixels` | Hot-pixel removal | 🚫 out of scope |
| `rawdenoise` | Wavelet denoise on raw mosaic | ❌ not yet |
| `cacorrect` | Chromatic-aberration correction | ❌ not yet |
| `demosaic` | Bayer / X-Trans interpolation | 🚫 out of scope (algorithm choice, not photographic intent) |
| `denoiseprofile` | Profiled (per-camera) denoise | ❌ not yet — high-value gap |

### Scene-referred phase (the modern pipeline middle)

| Module | What it does | Status |
|---|---|---|
| `exposure` | Global EV / black-level / clipping | ✅ parameterized (Tier 1; range [-3.0, +3.0] EV). Plus 4 mask-bound variants (gradient × 2, ellipse, rectangle). |
| `colorin` | Input color profile | 🚫 out of scope (technical) |
| `lens` | Lens correction (vignetting, distortion, CA) | ❌ Tier 3 (lensfun-coupled per-camera config; ADR-081). Possible promotion via L1 EXIF-binding shape. |
| `clipping` | Crop / aspect ratio / rotation | ✅ parameterized as `crop` (Tier 2; 4-axis cx/cy/cw/ch). Aspect ratio constraint preserved at -1/-1 (free). |
| `flip` | Orientation (rotate 90/180/270, flip) | ❌ not yet — Tier 2 candidate (small struct, scalar parameter) |
| `ashift` | Perspective / keystone correction | ❌ not yet — Tier 2 candidate (small struct, scalar params) |
| `liquify` | Local pixel pushing (manual warp) | ❌ not yet — stroke-based input; would need novel RFC shape |
| `retouch` | Frequency-separation retouching | ❌ not yet — *the* major portrait gap; stroke-based input doesn't fit per-image vocabulary entry pattern. Would need its own RFC. |
| `spots` | Spot healing / cloning | ❌ not yet — same shape concern as retouch |
| `censorize` | Pixelation / blur for privacy | ❌ not yet |
| `colorchecker` | Color calibration via reference chart | 🚫 out of scope (technical) |
| `channelmixerrgb` | RGB channel mixer (modern) | ✅ 3 B&W entries (`bw_convert`, `bw_sky_drama`, `bw_foliage`); plus 4 parameterized colorbalancergb axes coexist via the colorbalancergb module — channelmixerrgb's other axes (RGB matrix, illuminant) remain Tier 3 |
| `colorbalancergb` | 4-way grade + saturation + chroma + brilliance | ✅ shipped — 8 parameterized axes (saturation_global, vibrance, chroma_global, hue_angle, brilliance × 4) + 7 discrete (vibrance_+0.3 retired; per-zone chroma_boost × 3; grade × 4) = 15 entries on this module |
| `tonecurve` | Manual RGB / Lab tone curve | ❌ not yet — Tier 2 candidate; same multi-node-curve shape as toneequalizer |
| `toneequal` | Zone-based tone equalizer (darktable's preferred local tone tool) | ✅ shipped (Tier 2) — `toneequalizer` (9-axis: noise / ultra_deep_blacks / deep_blacks / blacks / shadows / midtones / highlights / whites / speculars; each ±2.0 EV) |
| `sigmoid` | Modern tone mapping (filmic replacement) | ✅ shipped — `sigmoid_contrast` (parameterized), plus `blacks_lifted/crushed`, `whites_open` (discrete *kinds* of tonal moves; Tier 0 by design). No `whites_dampen` ladder, no per-channel control. |
| `filmicrgb` | Older tone mapping (still ships) | 🚫 out of scope (sigmoid is preferred) |
| `basicadj` | Combined exposure + contrast + saturation | ❌ not yet (covered by separate primitives) |
| `colorize` | Solid color tint | ❌ not yet |
| `colorbalance` | Older 4-way grade (pre-rgb) | 🚫 out of scope (colorbalancergb is preferred) |
| `colorzones` | Per-hue selective adjustment (HSL) | ❌ Tier 3 (3 splines × 8 nodes = 24+ params; surface doesn't reduce cleanly to scalar `--value V`; ADR-081). Possible promotion shape: axis-collapsed entries (only the saturation curve at 4 nodes). |
| `colorcontrast` | Lab a/b chroma contrast | ❌ not yet |
| `velvia` | Saturation with falloff for skin tones | ❌ not yet |
| `vibrance` | Old vibrance module (newer is in colorbalancergb) | 🚫 out of scope (modern path) |
| `monochrome` | B&W via filter color | ❌ not yet — overlap with channelmixerrgb (B&W trio shipped there) |
| `grain` | Film grain texture | ✅ shipped — `grain_strength` (parameterized, range [0.0, 100.0]; Tier 1) |
| `bilat` (local contrast) | Bilateral local contrast / clarity | ✅ shipped — `bilat_clarity_strength` (parameterized strength axis; Tier 1) + `clarity_painterly` (Tier 0 — different *kind*, not strength) |
| `bloom` | Soft glow / orton-style bloom | ❌ not yet |
| `soften` | Gaussian softening | ❌ not yet |
| `sharpen` | Unsharp mask sharpening | ✅ shipped (Tier 2) — `sharpen` (single-axis amount; range [0.0, 2.0]). Radius + threshold preserved at darktable defaults. |
| `diffuse` (diffuse-or-sharpen) | Reaction-diffusion sharpen / denoise / restore detail | ❌ not yet — modern darktable's flagship sharpening; Tier 2 candidate (extends the sharpen family) |
| `equalizer` (contrast equalizer) | Wavelet-based per-frequency contrast control | ❌ not yet — Tier 2 candidate; per-frequency multi-axis surface |
| `nlmeans` | Non-local-means denoise | ❌ Tier 3 (denoise family; ADR-081) |
| `bilateral` (denoise) | Bilateral denoise | ❌ Tier 3 (denoise family) |
| `defringe` | Color-fringe removal | ❌ not yet |
| `hazeremoval` | Atmospheric haze removal | ❌ not yet |
| `vignette` | Decorative radial darkening | ✅ shipped (Tier 1) — `vignette` (parameterized; range [-1.0, +1.0]; negative darkens, positive lifts) |
| `borders` | Frame border | ❌ not yet (composition / output decoration) |
| `watermark` | Text or image overlay | ❌ not yet |

### Display-referred / output

| Module | What it does | Status |
|---|---|---|
| `colorout` | Output color profile | 🚫 out of scope (technical) |
| `gamma` | Display gamma | 🚫 out of scope |
| `dither` | Output dithering | 🚫 out of scope |
| `finalscale` | Resampling / output size | 🚫 out of scope (handled by `--width`/`--height`) |

### Tally (post-v1.7.0)

- darktable modules total: ~50 photographically-meaningful (excluding 🚫 out-of-scope plumbing)
- chemigram ✅ shipped: **12 modules** (exposure, sigmoid, colorbalancergb, vignette, grain, bilat, highlights, temperature, crop, sharpen, toneequal, channelmixerrgb)
- chemigram ❌ not yet: **~28 modules** — but the framing is sharper now: each unshipped module falls into one of three buckets per ADR-081's tiering policy and the survey's analysis above.

**The remaining gaps, organized by feasibility (post-v1.7.0):**

**Unblocked Tier 2 candidates** — the architecture supports these; they ship as feature commits when authored:

1. **`tonecurve`** — manual tone curve. Same multi-node-curve shape as the already-shipped `toneequalizer`; ~half a day's work.
2. **`diffuse-or-sharpen` / `equalizer`** — modern darktable sharpening family. `sharpen` already covers the unsharp-mask common case; these add reaction-diffusion + per-frequency control.
3. **`flip` / `ashift`** — orientation + perspective correction. Small structs, scalar parameters; closes the rotation/perspective half of the composition gap.
4. **More L2 looks** — cinematic / film-stock / decade / mood. Pure composition of existing primitives; same shape as the 4 looks already shipped.

**Tier 3 candidates** — default-opaque per ADR-081; promotion is evidence-driven and each gets its own ADR:

5. **`denoiseprofile` / `nlmeans` / `bilateral`** — noise reduction family. Per-camera profiles violate Tier 2 cost-shape; possible promotion shape: ship the camera's auto-detected profile baked in via L1 EXIF binding, expose only the strength axis.
6. **`lens`** — lens correction. Lensfun-coupled per-lens database lookup. Possible promotion shape: L1 binding entry that auto-applies the profile from EXIF (sidesteps the parameterized-vocabulary framing entirely).
7. **`colorzones`** — HSL selective color. 3 splines × 8 nodes = 24+ params; doesn't reduce cleanly to `--value V`. Possible promotion shape: axis-collapsed entries (only the saturation curve at 4 nodes).

**Novel-shape gaps** — would need their own RFCs:

8. **`retouch` / `spots`** — frequency-separation retouching + spot healing. *The* major portrait gap. Stroke-based input doesn't fit the per-image vocabulary entry pattern; the right shape isn't yet clear.
9. **AI / content-aware masks** ("the manta's belly") — explicitly conditional Phase 4 in IMPLEMENTATION.md; sibling project (`chemigram-masker-sam`) shape; biggest scope jump in the project.

The gap isn't a single uniform "30 modules to author" anymore — it's three distinct kinds of work each with its own decision shape. Items 1–4 are routine Tier 2 expansion; items 5–7 need policy decisions before authoring; items 8–9 need design RFCs before policy.

---

## 13. Lightroom daily-use panel mapping

> Comparison against the panels a typical Lightroom photographer touches on **every photo** (the user's own daily-use list, captured 2026-05-07). Two purposes: (1) help users coming from Lightroom understand what's available; (2) ground "what's missing" in the most-used controls of the dominant photo editor — a sharper signal than the abstract "modules darktable has" framing in § 12.

The 18 daily-use controls organized by Lightroom panel; mapped to chemigram capability with explicit status flags:

### Light panel (7 controls)

| Lightroom control | chemigram equivalent | Status |
|---|---|---|
| Exposure | `exposure --value V` (range [-3.0, +3.0] EV) | ✅ |
| Contrast | `sigmoid_contrast --value V` (range [0.5, 5.0]; 1.5 = no-op) | ✅ |
| Shadows (zone lift) | `toneequalizer --param shadows=V` + `gradient_bottom_lift_shadows` (mask-bound) | ✅ |
| Blacks (deep-shadow point) | `toneequalizer --param deep_blacks=V` / `--param blacks=V`; plus `blacks_lifted` / `blacks_crushed` (discrete *kinds*) | ✅ |
| Whites (white point) | `toneequalizer --param whites=V`; plus `whites_open` (discrete) | ✅ |
| Highlights (highlight roll-off) | `highlights_clip_threshold --value V` + `toneequalizer --param highlights=V` + `gradient_top_dampen_highlights` (mask-bound) | ✅ |
| **Tone Curve** (parametric / point curve) | — | ❌ — `tonecurve` module unrepresented; tracked as #94 (520-byte spline-curve struct, needs darktable GUI baseline capture). The 9-band `toneequalizer` covers most intents but isn't the same idiom. |

**Light: 6/7 fully covered, 1 missing (#94 tone curve).**

### Color panel (4 controls)

| Lightroom control | chemigram equivalent | Status |
|---|---|---|
| WB Temperature (Kelvin slider) | `wb_kelvin_delta --param kelvin_delta=V` (range [-3000, 3000]; positive = warmer) — shipped via #102 / commit `<TBD>` as a UX wrapper on the existing `temperature` decoder. The raw `temperature --param red_coeff=V --param blue_coeff=V` axes remain available for users who want direct coefficient control. | ✅ |
| WB Tint (green ↔ magenta slider) | `wb_kelvin_delta --param tint_delta=V` (range [-200, 200]) shipped via #102; or `temperature --param green_coeff=V` for direct coefficient control (#90 Bucket A.3 / commit `1a00254`) | ✅ |
| Vibrance | `vibrance --value V` (range [-1.0, +1.0]) | ✅ |
| Saturation | `saturation_global --value V` (range [-1.0, +1.0]) | ✅ |

**Color: 4/4 fully covered.**

### Color Mixer panel — HSL per color band (1 panel = 24 controls)

Lightroom exposes Hue + Saturation + Luminance per 8 color bands (red / orange / yellow / green / aqua / blue / purple / magenta) = 24 sliders. **Shipped via RFC-023 / ADR-083 (commit `1b5db21`)** — backed by darktable's modern `colorequal` module (mv4, 128-byte flat struct), not the older `colorzones` spline-curve module.

| Lightroom control | chemigram equivalent | Status |
|---|---|---|
| HSL Hue per color (8 axes) | `hsl_hue --param hue_<color>=V` (8 axes: hue_red, hue_orange, hue_yellow, hue_green, hue_cyan, hue_blue, hue_lavender, hue_magenta; each [-180, 180] degrees) | ✅ |
| HSL Saturation per color (8 axes) | `hsl_saturation --param sat_<color>=V` (8 axes; each [-1.0, 1.0]) | ✅ |
| HSL Luminance per color (8 axes) | `hsl_luminance --param bright_<color>=V` (8 axes; each [-1.0, 1.0]) | ✅ |

**Color Mixer: 24/24 covered.** Backed by `colorequal` mv4. The 5% spline-curve precision use case (Lightroom's HSL Range slider per-zone falloff) is tracked as #98 — discrete-only `colorzones` fallback if/when needed.

### Color Grading panel (multi-axis)

Lightroom's color grading panel offers per-zone (shadows / midtones / highlights / global) hue + saturation wheels, plus per-zone luminance, plus global blending and balance. **Bucket A.5 (#91 / commit `7eb4aab`) added 9 axes here.**

| Lightroom control | chemigram equivalent | Status |
|---|---|---|
| Shadows: hue + saturation | `hue_shadows` (parameterized [0, 360°]) + `saturation_shadows` (parameterized [-1, 1]) + discrete `grade_shadows_warm` / `grade_shadows_cool` | ✅ |
| Midtones: hue + saturation | `hue_midtones` (parameterized [0, 360°]) + `saturation_midtones` (parameterized [-1, 1]) + discrete `grade_midtones_warm` / `grade_midtones_cool` (#90 Bucket A.4 / commit `72ff3e9`) | ✅ |
| Highlights: hue + saturation | `hue_highlights` (parameterized [0, 360°]) + `saturation_highlights` (parameterized [-1, 1]) + discrete `grade_highlights_warm` / `grade_highlights_cool` | ✅ |
| Global: hue rotation | `hue_angle --value V` (range [-180.0, +180.0] degrees; rotates *all* pixels uniformly) | ✅ |
| Per-zone luminance | `brilliance_shadows`, `brilliance_midtones`, `brilliance_highlights`, `brilliance_global` (all parameterized; range [-1.0, +1.0]) | ✅ |
| Blending (zone falloff) | `shadows_weight`, `highlights_weight` (parameterized [0, 4]) | ✅ |
| Balance (shadow/highlight midpoint) | `white_fulcrum` (parameterized [-2, 2]) | ✅ |

**Color Grading: 7/7 controls fully covered.**

### Effects panel (5 controls)

| Lightroom control | chemigram equivalent | Status |
|---|---|---|
| Texture (mid-frequency detail) | `texture --param first=V --param second=V --param sharpness=V` via `diffuse-or-sharpen` (#92 Bucket A.6 / commit `c9dfe83`). Algorithm match for Lightroom's mid-frequency Texture work; `first` is the primary axis. | ✅ |
| Clarity | `bilat_clarity_strength --value V` (parameterized) + `clarity_painterly` (different *kind* of clarity — softer; Tier 0) | ✅ |
| Dehaze (atmospheric haze removal) | `dehaze --param strength=V --param distance=V` via `hazeremoval` (#90 Bucket A.2 / commit `949516f`; range [-1, 1] for strength, negative *adds* atmospheric fog) | ✅ |
| Vignette | `vignette --value V` (range [-1.0, +1.0]) | ✅ |
| Grain | `grain_strength --value V` (range [0.0, 100.0]) | ✅ |

**Effects: 5/5 covered.**

### Transform panel (5 axes)

Lightroom's Transform panel: rotation, vertical/horizontal perspective, shear, aspect adjust. Architectural / interior / flat-art photographers reach for this every shoot. **Bucket A.7 (#101 / commit `<TBD>`) ships via darktable's `ashift` module.**

| Lightroom control | chemigram equivalent | Status |
|---|---|---|
| Rotate (degrees) | `transform --param transform_rotation=V` (range [-180, 180]°) | ✅ |
| Vertical perspective (keystone) | `transform --param transform_lensshift_v=V` (range [-1, 1]) | ✅ |
| Horizontal perspective | `transform --param transform_lensshift_h=V` (range [-1, 1]) | ✅ |
| Shear | `transform --param transform_shear=V` (range [-1, 1]) | ✅ |
| Aspect adjust | `transform --param transform_aspect=V` (range [0.5, 2.0]; default 1.0) | ✅ |

**Transform: 5/5 covered.**

Lens-tuning fields (focal length, crop factor, ortho-correction) and the user-drawn-lines reference storage are preserved verbatim — those are darktable-GUI-authored when the photographer wants line-based perspective correction; the `transform` entry covers the slider-based daily-use surface.

### Daily-use summary

Aggregating across the 5 panels — Color Mixer's 24 sliders count as 24 controls now that they're individually addressable, Color Grading's per-zone H/S/L axes count individually, and Transform is the final added panel post-#101:

| Panel | Controls | ✅ Full | ⚠️ Partial | ❌ Missing |
|---|---|---|---|---|
| Light | 7 | 6 | 0 | 1 (#94 tone curve) |
| Color | 4 | 4 | 0 | 0 |
| Color Mixer | 24 | 24 | 0 | 0 |
| Color Grading | 7 axes | 7 | 0 | 0 |
| Effects | 5 | 5 | 0 | 0 |
| Transform | 1 panel (5 axes) | 5 | 0 | 0 |
| **Total daily-use surface** | **52 distinct controls** | **51** | **0** | **1** |

**Lightroom daily-use parity: 51/52 fully shipped (98%) + 1 deferred (#94 tone curve, blocked on darktable-GUI baseline session per #100 umbrella).**

### What this implies for next work

Daily-use Lightroom parity is essentially closed. The only remaining gap is **#94 tone curve**, which is blocked on the darktable-session empirical-baseline work tracked under #100. Everything else in the daily-use surface ships.

Post-v1.9.0-in-progress, the next work splits into **darktable-bound** and **keyboard-only** tracks:

**Darktable-bound (the #100 umbrella):**

1. **#94 manual tone curve decoder** — needs darktable-GUI baseline capture
2. **#95 lens EXIF auto-binding** — needs real-raw + lensfun lookup verification
3. **#96 denoise wavelet-curve baseline verification** — confirm or fix the constructed `x[6][7]/y[6][7]` baseline
4. **#98 colorzones spline-curve HSL precision fallback** — discrete-only presets
5. **HSL real-raw visual proofs** — the iguana fixture drop closes the v1.8.0 #103 placeholder rows

**Keyboard-only (no darktable needed):**

1. **RFC-026 — AI-mask + AI-spot-detection provider scaffolding** — placeholder named in RFC-024 + RFC-025; sets up the BYOA-shaped extension at the right architectural level (sibling project shape per ADR-007). High-leverage architectural deliberation; closes the deferred half of both upstream RFCs.
2. **RFC-027 — Multi-photographer review phase plan** — the deferred work from ADR-081's promotion threshold. Solo build-baseline → community transition. The Tier 3 → Tier 2 evidence threshold, gap-log methodology, vocabulary conflict resolution between photographers, the social shape of pack contribution.
3. **RFC-028 — Pack management / multi-pack composition / vendor packs** — the loader supports multi-pack but conflict resolution between packs hasn't been stress-tested. Argues the architectural shape for vendor-distributed packs and pack-versioning.
4. **`chemigram vocab validate <name>` CLI verb** — runs all consistency checks against an entry (modversion drift, manifest correctness, dtstyle file exists + parses, blendop matches, parameters block validation). Useful for vocabulary authors mid-session.
5. **`chemigram cache {list,clear,size}` CLI sub-app** — manage the per-image previews/ render cache (size, listing, opt-in clear).
6. **More mask-bound L2 looks** — `look_subject_lift`, `look_horizon_dampen`, `look_corner_burn` etc. Tests the masked-L2 path explicitly; pure composition.
7. **Recipe book / cookbook** — "100 ways to use chemigram." Worked photographic recipes pulling from the 78-entry vocabulary corpus.
8. **Onboarding guide for new contributors** — what a new contributor reads first (concept → architecture → CLAUDE.md → recipe book).
9. **Architecture diagrams** — visual one-pager(s) of the stack (agent → MCP/CLI → engine → darktable).
10. **Property-based fuzz tests for parameterize decoders** — fuzz the 18 patch() functions to surface byte-correctness regressions. Catches issues the 5-layer manual tests don't.

The `--without-darktable` track is still rich; the `with-darktable` track is bounded by the #100 umbrella. See § 13's "What this implies" for the Lightroom-parity slice specifically.

---

## See also

- [`guides/visual-proofs.md`](guides/visual-proofs.md) — chart-based before/after gallery showing every shipped primitive in action
- [`guides/mask-applicable-controls.md`](guides/mask-applicable-controls.md) — per-module compatibility for masking
- [`guides/vocabulary-patterns.md`](guides/vocabulary-patterns.md) — how to combine shipped primitives
- [`guides/authoring-vocabulary-entries.md`](guides/authoring-vocabulary-entries.md) — author your own primitives via darktable GUI
- [`adr/ADR-008-opaque-blob-carriers.md`](adr/ADR-008-opaque-blob-carriers.md) — the opaque-blob default; ADR-077 supersedes this for explicitly-declared parameterizable modules
- `vocabulary/starter/README.md`, `vocabulary/packs/expressive-baseline/README.md` — pack-level catalogs
