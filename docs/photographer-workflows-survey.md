# Photographer workflows survey

> Last updated · 2026-05-09 (Portrait + Landscape + Wedding/Event + B&W — rounds 1-2 of 3)
> Status · Research artifact (Tier 3, operational). Companion to `capability-survey.md`. Feeds `vocabulary-patterns.md` and the `expressive-baseline` L2 layer.

This document extracts how working photographers post-process across genres — drawn from public sources (essays, blog posts, course material, interviews, tutorials) — and maps each move to chemigram's existing primitive surface. The output is two things at once: **L2 candidates** (composition recipes that recur across photographers in a genre) and **vocabulary gaps** (moves photographers reach for that chemigram cannot compose because the underlying primitives don't exist yet).

Round 1 covered Portrait + Landscape (maximally different — single-subject skin work vs. wide-scene tonal work). Round 2 covers Wedding/Event + B&W (workflow-pace + skin-under-pressure vs. conversion-discipline + zone-system vocabulary — different axis of contrast, surfacing different gap classes). Nature/Wildlife + Food/Product follow in round 3.

---

## Methodology

**The framing principle — extract intent, not sliders.** Chemigram's foundational discipline is "vocabulary, not sliders" (PA / 02-project-concept). Rooting this research in "what slider does this photographer push" produces a tool-translation table; rooting it in "what *move* is this photographer making, regardless of tool" produces composition recipes that transcend Lightroom-vs-Capture-One-vs-darktable UX differences.

Each extracted move is captured as an **(intent, result, tool surface, ordering note)** tuple:

- **Intent** — what the photographer wants in their own framing ("warm skin tones without affecting the background")
- **Result** — what changes in the image
- **Tool surface** — Lightroom panel / Capture One tool / darktable module / Photoshop technique — noted to verify the move is real and to surface gaps when chemigram can't express it
- **Ordering note** — "always do X before Y because Z" — captured when load-bearing

**Source mix.** Six photographers per genre, drawn from at least three distinct tool ecosystems (Lightroom, Capture One, darktable, plus written-essay sources). This avoids over-indexing on Lightroom's idioms — Capture One's color science is meaningfully different on skin tones, and darktable's modular pipeline produces different ordering disciplines.

**Recurrence threshold.** Moves recurring across **4-6 photographers** in a genre are high-confidence L2 candidates. Moves recurring across **3** are borderline (noted but flagged). Moves recurring across **1-2** are idiosyncratic / signature territory (Phase-2 personal-vocabulary candidates, not L2 ship targets).

**Mapping legend.** For each move:
- ✅ — supported via existing chemigram primitive (named)
- ⚠️ — partially supported (named primitive plus what's missing)
- ❌ — gap; chemigram cannot express this today

---

## Genre — Portrait

### Photographers surveyed (6)

| # | Photographer | Style | Primary tool | Source |
|-|-|-|-|-|
| P1 | **Aaron Nace** (Phlearn) | Editorial portrait, fashion-leaning, structured 6-step workflow | Lightroom + Photoshop | [Phlearn — Professional Retouching Workflow](https://phlearn.com/tutorial/professional-retouching-workflow/) |
| P2 | **Michael Woloszynowicz** | Beauty / commercial, tethered studio | **Capture One** + Photoshop | [Capture One blog — Beauty retouch workflow](https://www.captureone.com/blog/portrait-and-beauty-retouching-workflow) |
| P3 | **Sean Tucker** | Classical, restraint-driven, principle-focused | Lightroom + Photoshop | [Sean Tucker — Photography blog](https://www.seantucker.photography/blog), [Fstoppers — Authentic Portraits](https://fstoppers.com/bts/photographer-sean-tucker-explains-how-capture-authentic-portraits-people-137174) |
| P4 | **Lindsay Adler** | Fashion / editorial, color theory expertise | **Capture One** + Photoshop | [CreativeLive — 3-step retouching process](http://www.creativelive.com/blog/fashion-retouching-tips-technique), [blog.lindsayadlerphotography.com](https://blog.lindsayadlerphotography.com/qa-fashion-fashion-editing-workflow) |
| P5 | **Scott Gilbertson** | General / portrait, open-source focus | **darktable** | [Luxagraf — Developing Photos With Darktable](https://luxagraf.net/essay/craft/darktable-getting-started) |
| P6 | **Jonas Nordqvist** | Beauty / portrait, skin-tone specialist | **Capture One** | [Retouching Academy — Working On Skin Tones In Capture One](https://retouchingacademy.com/working-on-skin-tones-in-capture-one/), [Phase One blog](https://blog.phaseone.com/achieving-perfect-skin-tones-using-capture-one/) |

**Mix:** Lightroom+PS (3) / Capture One+PS (3) / darktable (1). Three ecosystems represented. Tool ecosystems are unevenly distributed in published portrait content — Lightroom is the dominant published-tutorial ecosystem, but commercial / beauty workflows lean Capture One; darktable portrait content is rarer in essay form.

### Common moves (recurrence 3+)

#### Move 1 — White balance / color foundation first
**Recurs across:** P1 (RAW Camera profile), P2 (white balance calibration with gray card), P3 (LR foundation work), P4 (implicit), P5 (Color Calibration module early in workflow), P6 (white balance as first adjustment)

- **Intent:** Establish a neutral color baseline before any contrast / tonal / aesthetic work
- **Result:** Skin tones at their natural color reference; downstream adjustments operate on accurate color
- **Tool surface:** Lightroom Basic panel (Temp/Tint), Capture One White Balance + gray card pick, darktable Color Calibration module
- **Ordering note:** Load-bearing — Woloszynowicz: "perform before contrast adjustments as it affects perception." Gilbertson: "applied early in workflow." Most photographers cite this as Step 1 or Step 2.
- **Mapping:** ✅ supported via `temperature` (parameterized; `red_coeff` + `blue_coeff` + `green_coeff`) and `wb_kelvin_delta` (UX wrapper).

#### Move 2 — Exposure baseline / dynamic range claim
**Recurs across:** P1 (foundational exposure in Camera RAW), P2 (exposure baseline + slight overexposure recovery), P3 (LR exposure + shadow/highlight), P5 (exposure assessment via Shift+E), P6 (exposure as second adjustment)

- **Intent:** Set the working exposure level and recover detail in shadows / highlights before any aesthetic work
- **Result:** Histogram occupies the full tonal range without clipping; foundation for downstream contrast work
- **Tool surface:** Lightroom Basic (Exposure/Highlights/Shadows), Capture One Exposure + HDR tool, darktable Exposure + Tone Equalizer (for shadow recovery)
- **Ordering note:** Always before contrast work. Woloszynowicz uses two phases — tethered (slightly overexpose) and Photoshop-prep (neutral). Multiple photographers note that aggressive exposure recovery in shadows produces noise; address that later.
- **Mapping:** ✅ supported via `exposure` (parameterized EV) + `toneequalizer` (9-axis zone control) + `highlights_clip_threshold`.

#### Move 3 — Skin tone harmonization (specifically)
**Recurs across:** P1 (frequency separation for skin smoothing), P2 (Color Editor > Skin Tone tab with Uniformity sliders), P4 (Photoshop Imagenomic + skin tone tools), P5 (Color Balance RGB), P6 (Skin Tone Color Editor tab — entire workflow centered here)

- **Intent:** Reduce uneven coloration on skin (red patches on forehead/neck, varying saturation across the face) — separate from blemish removal, this is *coloration* uniformity
- **Result:** Skin reads as one continuous tone-space without fighting patches of red/yellow/desaturated regions
- **Tool surface:** Capture One Color Editor → Skin Tone tab (Uniformity Hue/Saturation/Lightness sliders), Lightroom HSL panel + targeted brush (less precise), Photoshop Hue/Saturation with Skin range, darktable Color Balance RGB on shadows/midtones/highlights — *no first-class "skin uniformity" surface in chemigram*
- **Ordering note:** Always after WB but before retouching texture. "Don't push too far" — every photographer reaching for this tool warns against over-using Uniformity sliders (lips and makeup get affected if Uniformity is maxed out).
- **Mapping:** ⚠️ **partially supported.** chemigram has `colorequal` (HSL Color Mixer parity) which can shift hue/sat/luminance per color band, including the orange/red bands skin lives in. But Capture One's "Skin Tone" surface is a *named*, *isolated* set of controls specifically scoped to skin colors, with a Uniformity behavior (compress variance toward selected reference). chemigram's `colorequal` is a more general HSL editor; it can approximate but doesn't expose "uniformity" as a first-class concept. **Gap candidate.**

#### Move 4 — Contrast as second-tier shaping (after WB + exposure)
**Recurs across:** P1 (exposure-balancing layers before frequency work), P2 (contrast foundation via Levels), P3 (contrast in LR foundation), P5 (Sigmoid as part of scene-referred defaults), P6 (post-exposure phase)

- **Intent:** Shape the global tonal response — punch the histogram, set black/white points, add midtone contrast
- **Result:** Image moves from "flat foundation" to "punched but not aggressive" — contrast that supports the subject without overwhelming
- **Tool surface:** Lightroom Tone Curve / Contrast slider, Capture One Levels (drag endpoints inward) + Luma curve, darktable Sigmoid + Tone Curve, Photoshop Curves
- **Ordering note:** Always after WB + exposure foundation; always before color grading. Woloszynowicz: "drive down center point" of curve then pull lower-right histogram handle inward — a specific shaping discipline.
- **Mapping:** ✅ supported via `sigmoid_contrast` (parameterized; range [0.5, 5.0]) for global contrast; `toneequalizer` for zonal control.

#### Move 5 — Blemish / spot removal (textural cleanup)
**Recurs across:** P1 (Step 3: blemish removal before frequency separation), P2 (implicit in PS phase), P4 (Step 1: spot healing brush + patch tool), P5 (Retouch module)

- **Intent:** Remove temporary surface artifacts (pimples, dust spots, flyaways) before texture work
- **Result:** Clean base for downstream skin smoothing / dodge & burn
- **Tool surface:** Photoshop Spot Healing Brush / Patch Tool / Clone Stamp, darktable Retouch module (heal/clone)
- **Ordering note:** **Load-bearing** — Nace: "Remove distractions before frequency separation." Adler same. Doing texture smoothing before blemish removal smooths the blemish into the skin instead of removing it.
- **Mapping:** ✅ supported via `apply_spot` MCP tool (RFC-025 / ADR-087, v1.9.0): heal + clone on circle geometry.

#### Move 6 — Skin smoothing without losing texture
**Recurs across:** P1 (Step 4: frequency separation), P2 (implicit in PS phase), P4 (Step 3: Imagenomic Portraiture with masking), P5 (no direct equivalent — darktable doesn't ship frequency separation natively)

- **Intent:** Smooth skin (reduce micro-noise of pores, even out texture) without producing the "plastic" look of over-smoothing
- **Result:** Magazine-quality skin where the subject still looks like a real person
- **Tool surface:** Photoshop Frequency Separation (low-frequency = color/tone, high-frequency = texture; smooth one without the other), Imagenomic Portraiture plugin with masks, Capture One has no direct frequency separation
- **Ordering note:** Always after blemish removal; always before dodge & burn. Both Nace and Adler explicitly warn against over-smoothing.
- **Mapping:** ❌ **gap.** chemigram has `bilat_clarity_strength` (parameterized local-contrast) but it operates on edges, not on frequency-separated skin texture. Frequency separation is a Photoshop-native technique that doesn't map to a darktable module — would need to be approximated via masked local-contrast reduction + selective blur, or routed to a Photoshop sibling tool. **Gap candidate; high relevance for portrait pack.**

#### Move 7 — Dodge and burn (dimensional sculpting)
**Recurs across:** P1 (Step 5: dodging & burning for depth), P3 (strategic light/shadow manipulation), P4 (implicit in retouching), P5 (no direct module; could approximate via masks)

- **Intent:** Sculpt facial structure — brighten cheekbones / nose bridge / brow, deepen jaw / temple / under-eye recess — without changing color or texture
- **Result:** Three-dimensional rendering of the face; eye is drawn to subject features rather than wandering
- **Tool surface:** Photoshop dodge/burn layers (50% gray + Soft Light blend), Capture One local adjustment with exposure, darktable masked exposure adjustments
- **Ordering note:** After texture work, before sharpening. Sean Tucker: "strategic, not blanket."
- **Mapping:** ⚠️ **partially supported.** chemigram has the wire (drawn ellipse / path masks + parametric range_filter + apply_primitive on `exposure`) so you *can* compose a dodge-and-burn move per region. But the photographer-level workflow is "many small dodges + many small burns across the face," typically 5-15 mask-bound exposure adjustments per portrait. chemigram doesn't yet have a vocabulary surface for *batched local exposure adjustments* — each one becomes a separate `apply_primitive` call with its own mask_spec. Workable but verbose. **Workflow gap, not capability gap.**

#### Move 8 — Color grading (atmosphere / mood)
**Recurs across:** P2 (Color Balance to inject color into shadows/highlights), P3 (subtle shifts maintaining natural skin tones), P4 (color theory for fashion grades), P5 (Color Balance RGB)

- **Intent:** Push the overall image toward a stylistic color palette (warm cinematic, cool editorial, split-tone moody) without breaking skin tone naturalism
- **Result:** Image reads with intentional color mood; skin tones are protected from the grade
- **Tool surface:** Capture One Color Balance (per-zone hue/sat), Lightroom Color Grading panel (4 wheels), Photoshop Selective Color, darktable Color Balance RGB (per-zone H/S)
- **Ordering note:** Always near end of workflow. Tucker: "subtle shifts maintaining natural skin tones." Woloszynowicz: "apply opposing colors between tonal ranges" (shadows cool / highlights warm — split-tone discipline).
- **Mapping:** ✅ supported via the 9 colorbalancergb axes (per-zone hue/sat × shadows/midtones/highlights/global + brilliance + balance/blending) shipped via #91 / Bucket A.5.

#### Move 9 — Sharpening last (output sharpening)
**Recurs across:** P1 (Step 6: sharpening), P2 (subtle clarity in tethered phase), P3 (selective sharpening), P5 (Diffuse or Sharpen)

- **Intent:** Critical-detail sharpening (eyes, lashes, jewelry) at output stage, not as a creative move
- **Result:** Sharp where it matters; soft where it should be
- **Tool surface:** Photoshop multi-pass sharpening Action, Lightroom Detail panel, darktable Diffuse or Sharpen
- **Ordering note:** **Always last.** Nace: "perform last to preserve all prior work."
- **Mapping:** ✅ supported via `sharpen` (parameterized).

#### Move 10 — Vignette as final accent
**Recurs across:** P2 (vignette + clarity polish at end of tethered phase), P4 (no direct mention), P5 (no direct mention — but darktable has `vignette` module)

- **Intent:** Subtle peripheral darkening to draw the eye toward the subject
- **Result:** Frame edges fade slightly; subject pops by contrast
- **Tool surface:** Capture One Vignetting tool, Lightroom Effects panel Vignette, darktable Vignette module
- **Ordering note:** End of workflow.
- **Mapping:** ✅ supported via `vignette` (parameterized brightness).

### Signature / idiosyncratic moves

| Photographer | Signature move | Why it doesn't generalize |
|-|-|-|
| Aaron Nace (P1) | Frequency separation as the centerpiece | Phlearn-specific teaching emphasis; Lindsay Adler explicitly avoids it for finer fashion work |
| Sean Tucker (P3) | "One hour per image" depth + dual color/B&W output | Editorial-gallery approach; commercial photographers cannot afford this time per image |
| Lindsay Adler (P4) | "Lighten" blend mode clone stamp under eyes (preserves texture while filling shadow) | Specific to her under-eye / smile-line discipline; not a universal portrait technique |
| Michael Woloszynowicz (P2) | Tethered-phase pre-Photoshop look-locking | Studio-only workflow; outdoor/event portrait photographers don't tether |
| Scott Gilbertson (P5) | Customizing module visibility (9-15 of 64 visible) | darktable-specific; Lightroom's panel set is fixed |
| Jonas Nordqvist (P6) | Magic Brush mask for skin isolation | Capture One-specific; the Magic Brush is C1's distinctive feature |

### Proposed L2 looks (Portrait)

**High-confidence candidates (recurrence 4+ across photographers):**

| Name | Intent | Composition |
|-|-|-|
| `look_portrait_natural_skin` | Restraint-first portrait foundation: WB neutral, gentle exposure, soft contrast, color tones natural | `temperature` (slight warm shift, +200K equiv) + `exposure` (+0.1 EV) + `sigmoid_contrast` (1.2; soft) + `saturation_global` (-0.05; pull back from punchy) |
| `look_portrait_editorial` | Magazine / fashion punch: punchy contrast, slight warm grade, reduced overall saturation | `sigmoid_contrast` (1.6) + `colorbalancergb` shadows-cool/highlights-warm split + `saturation_global` (-0.1) |
| `look_portrait_high_key_clean` | Brighten overall + lift shadows + reduce contrast (Adler-style high-key) | Already exists as `look_high_key_portrait`; expand description to note Adler attribution |
| `look_portrait_low_key_dramatic` | Crush shadows + warm highlights + tight contrast | Already exists as `look_low_key_portrait`; expand description |
| `look_portrait_skin_warm_lift` | Brighten + warm skin tones in the subject region only | drawn ellipse mask + range_filter (color_h orange/red band) + `exposure` (+0.2) + `temperature` (warm shift) |
| `look_portrait_dodge_burn_eye_lift` | Lift highlights only in subject region — catchlight emphasis | drawn ellipse + range_filter (luminance highlights) + `exposure` (+0.3) — already approximated by `look_subject_brighten_highlights` |

**Borderline candidates (recurrence 3):**

| Name | Intent | Composition | Rationale for borderline |
|-|-|-|-|
| `look_portrait_split_tone_moody` | Cinematic split-tone — cool shadows, warm highlights | `colorbalancergb` shadows hue=210/sat=0.3 + highlights hue=45/sat=0.2 — already exists as `grade_split_warm_cool` | Borderline because some photographers (Adler) consider this "fashion-only," not a general portrait move |

**Existing entries to keep / re-tag:** `look_portrait`, `look_high_key_portrait`, `look_low_key_portrait`, `look_subject_lift_dark_only`, `look_subject_brighten_highlights` already cover several of these intents — refine descriptions but don't duplicate.

### Genre-specific gaps (Portrait)

| Gap | Severity | Photographers reaching for it | RFC / vocabulary candidate |
|-|-|-|-|
| **Skin-tone uniformity tool (named / first-class)** | High | P2 Woloszynowicz, P4 Adler, P6 Nordqvist (3/6) | RFC candidate: a primitive on top of `colorequal` that scopes to skin-color hue range and exposes a "uniformity" (variance-compress) parameter. Capture One ships this; Lightroom has nothing equivalent. |
| **Frequency separation** (texture-vs-color band split) | High | P1 Nace, P4 Adler (2/6 — but central to both their workflows) | Architectural: this is a Photoshop-native technique requiring frequency-band decomposition. darktable doesn't ship this natively. Either approximate via masked local-contrast (`bilat_clarity_strength` with selective masks) or route to a Photoshop sibling tool. **RFC candidate** for v1.10+ if portrait pack work continues. |
| **Batched dodge-and-burn workflow** | Medium | P1 Nace, P3 Tucker, P4 Adler (3/6 — load-bearing for editorial portrait) | Workflow gap, not capability gap — chemigram has the wire. Could ship a meta-tool (`apply_dodge_burn(image_id, regions=[...])`) that takes a list of (region, ev) tuples and applies them as N snapshots. Or document the manual flow more explicitly in `vocabulary-patterns.md`. |
| **Background-only adjustment (separate from subject)** | Medium | P1 Nace (radial filter darkening backgrounds), P2 Woloszynowicz (Color Range Refinement on backgrounds), P4 Adler (implicit) | Already supported via inverted ellipse mask + `exposure` / `saturation_global`, but the workflow surface is verbose. Could ship a pre-baked compositional look — `look_portrait_background_dim` — that takes subject coords as parameters. |
| **Imagenomic Portraiture-style controlled smoothing** | Low | P4 Adler only | Plugin-specific; not a general primitive gap. |

---

## Genre — Landscape

### Photographers surveyed (6)

| # | Photographer | Style | Primary tool | Source |
|-|-|-|-|-|
| L1 | **Sarah Marino** | Intimate / small-scene landscapes, restraint-driven, naturalist | Lightroom + Photoshop | [On Landscape — Featured Photographer](https://www.onlandscape.co.uk/2019/07/sarah-marino/), [CaptureLandscapes — Photographer of the Month](https://www.capturelandscapes.com/photographer-of-the-month-sarah-marino/), [smallscenes.com](https://smallscenes.com/) |
| L2 | **Thomas Heaton** | Grand vista / wilderness, accessible-tutorial style | Lightroom Classic + DxO PureRAW | [Imaging Resource — 5 easy ways to improve landscape photos in Lightroom](https://www.imaging-resource.com/news/2022/06/29/video-5-easy-ways-to-improve-your-landscape-photos-in-adobe-lightroom), [thomasheaton.co.uk](https://thomasheaton.co.uk/) |
| L3 | **Nick Page** | Dramatic atmospheric landscapes, luminosity-mask methodologist | **Photoshop** + Lumenzia | [Nick Page Photography — Mastering Luminosity Masks](https://www.nickpagephotography.com/masteringluminositymasks), [Improve Photography — Advanced Landscape Processing](https://improvephotography.com/44753/learning-advanced-landscape-processing-techniques/) |
| L4 | **Mike O'Leary** | Mixed wilderness, LR-then-PS workflow | Lightroom Classic + Photoshop | [Fstoppers — A Landscape Photographer's Editing Workflow](https://fstoppers.com/landscapes/landscape-photographers-editing-workflow-lightroom-and-photoshop-522537), [mikeoleary.photography](https://www.mikeoleary.photography/) |
| L5 | **Marc Adamus** | American wilderness, exposure-blending / "clone painting" | **Photoshop** (digital darkroom heavy) | [500px — A Day In The Life Of Landscape Photographer Marc Adamus](https://iso.500px.com/a-day-in-the-life-of-landscape-photographer-marc-adamus/), [Photo Cascadia — Lexicon of Post-Processing Terms](https://www.photocascadia.com/a-lexicon-of-post-processing-terms-in-landscape-photography-today/), [marcadamus.com](https://www.marcadamus.com/page/bio/) |
| L6 | **Serge Ramelli** | Cityscape / landscape hybrid, preset-driven dramatic style | Lightroom (preset-heavy) | [Shutterbug — Landscape Shooters: Pro's #1 Lightroom Secret](https://www.shutterbug.com/content/landscape-shooters-learn-pro%E2%80%99s-1-lightroom-secret-and-download-his-presets-free-video), [Lightroom Killer Tips — AI Retouching Presets with Serge Ramelli](https://lightroomkillertips.com/ai-retouching-presets-lightroom-serge-ramelli/), [photoserge.com](https://www.photoserge.com/) |

**Mix:** Lightroom-led (4: L1, L2, L4, L6) / Photoshop-led (2: L3, L5). **One ecosystem represented; this falls short of the methodology's three-ecosystem mix mandate.** Honest finding: published landscape post-processing content skews overwhelmingly Adobe — the Lumenzia-style luminosity-mask discipline is a Photoshop-native idiom, and Capture One's color science (which dominates portrait/beauty content) has much less landscape-specialist representation. No darktable landscape essayist surfaced through the searches conducted; the avidandrew.com scene-referred workflow (cited in cross-genre observations) is the closest analog but isn't authored by a working landscape photographer building a portfolio. **This finding is itself a signal** — the moves that recur across landscape photographers may genuinely *be* Photoshop-native compositing patterns, and chemigram's response is then either to express them via masking primitives or to acknowledge the boundary explicitly.

To partially compensate, Move 9 below cross-references the [avidandrew.com scene-referred landscape workflow](https://avidandrew.com/darktable-scene-referred-workflow.html) for the darktable analog of each common move. This is reference material, not a seventh photographer.

### Common moves (recurrence 3+)

#### Move 1 — Sky-targeted tonal control
**Recurs across:** L2 Heaton (adaptive sky preset, "intersect with mask" combining sky selection + linear gradient), L3 Page (luminosity masks isolating bright sky), L4 O'Leary (sky brightness adjustments), L5 Adamus (multi-exposure blending for sky), L6 Ramelli (dodge/burn imitation of darkroom sky control), L1 Marino (implicit when small scenes include sky elements). **6/6.**

- **Intent:** Tame bright sky / recover sky color and tone separately from foreground; replicate the graduated-ND filter effect digitally
- **Result:** Sky retains color and detail without dragging foreground darker; horizon transition feels natural
- **Tool surface:** Lightroom AI sky mask + intersect-with-linear-gradient (Heaton); Photoshop luminosity masks isolating top-quartile luminance (Page); Photoshop layer masking with painted gradients (Adamus); LR graduated filter (Ramelli, O'Leary); darktable parametric mask on luminance + linear-gradient mask combined (avidandrew reference workflow)
- **Ordering note:** Always done after global exposure baseline — the sky move presumes a calibrated global tone. Heaton: sky mask is "selective from the start." Page: luminosity masks built before any sky-specific contrast.
- **Mapping:** ⚠️ partially supported. chemigram has `parametric mask` (RFC-024 / ADR-085) for luminance-range selection and the `range_filter color_h` family for hue-range selection (sky-blue). Combining the two with a horizontal gradient — to mimic Heaton's intersect-with-linear-gradient — is *expressible* but verbose: requires two mask primitives plus a third gradient mask plus an op. **A pre-baked compositional look would help** (see proposed `look_landscape_sky_enhance`). Sky *detection* (the "AI sky mask" that LR ships) is best served by the **LLM-vision masker** (RFC-026 / ADR-086) given a "select the sky" prompt — that pathway exists in v1.9.0.

#### Move 2 — Foreground brightening / subject lift
**Recurs across:** L2 Heaton (graduated filter for foreground), L3 Page ("dodging dark foregrounds" via luminosity masks, "bringing out dimension and three-dimensionality in dark foregrounds"), L4 O'Leary (dodging in PS), L5 Adamus (luminosity-blended foreground exposure), L6 Ramelli (dodge equivalent in LR). **5/6** — Marino's small-scene work less foreground-vs-sky structured.

- **Intent:** Lift detail and dimension in the foreground (rocks, water, vegetation) that would otherwise sit in shadow relative to the sky
- **Result:** Three-dimensionality in the foreground; viewer's eye drawn into the scene
- **Tool surface:** LR graduated filter (inverted from sky), luminosity masks targeting dark-quartile pixels (Page, Adamus), LR shadow slider + targeted radial filter (Ramelli)
- **Ordering note:** Mid-workflow — after global exposure but before final color grading. Page emphasizes building the dimensionality before any color move.
- **Mapping:** ✅ supported. `parametric mask` over `tone_eq` shadow zones + the parameterized `exposure` + `range_filter` for dark-luminance bands all compose this. Existing entries `look_subject_lift_dark_only` and `look_subject_brighten_highlights` (in the L2 layer) cover the conceptually-cleanest variants. A **landscape-specific** look that combines bottom-half gradient + dark-luminance parametric is worth pre-baking.

#### Move 3 — Dynamic-range compression / tonal claim
**Recurs across:** L2 Heaton (DxO PureRAW + LR Highlights/Shadows), L3 Page (exposure blending difficult scenes), L5 Adamus (signature multi-exposure blending), L1 Marino (exposure adjustments for small-scene contrast), L6 Ramelli (LR Highlights/Shadows). **5/6.**

- **Intent:** Pull the scene's dynamic range into the printable / display gamut without losing extreme highlights or crushing extreme shadows
- **Result:** Sky retains color, deepest shadows retain texture, and the midtone curve has room to shape mood
- **Tool surface:** LR Highlights/Shadows sliders (most), Photoshop multi-exposure blending (Adamus's signature), darktable Filmic RGB scene tab + tone_eq (avidandrew reference). The Adamus pattern is meaningfully different — it presumes multiple raws bracketed at capture, which falls outside chemigram's per-image scope.
- **Ordering note:** Early — directly after exposure baseline. Most published workflows treat this as the "claim the scene" step before any aesthetic work.
- **Mapping:** ✅ supported. `tone_eq` (8-band luminance dodge/burn) handles single-raw DR compression; `highlights_recovery_*` and the parameterized exposure entry handle the compression at filmic. **Multi-raw blending is out of chemigram's scope** — that's an HDR-stack workflow handled at capture or via Hugin/HDRMerge externally; chemigram is per-image-as-edited, not multi-raw fusion.

#### Move 4 — Local contrast / clarity micro-shaping
**Recurs across:** L2 Heaton (LR Clarity / Texture), L3 Page (selective contrast via luminosity masks), L5 Adamus (clone-painted contrast), L6 Ramelli (clarity for drama), L4 O'Leary (PS contrast layering). **5/6** — Marino's restraint aesthetic explicitly minimizes this.

- **Intent:** Shape micro-contrast / mid-frequency definition to add depth and atmosphere without globally crunching the image
- **Result:** Texture in clouds, water, rock; "painterly" quality when used with restraint, "crunchy HDR" when overdone (the failure mode every photographer warns against)
- **Tool surface:** LR Clarity / Texture / Dehaze sliders (most), Photoshop High Pass + Soft Light blend layer (Page, Adamus), darktable Local Contrast / Diffuse-or-Sharpen (avidandrew reference)
- **Ordering note:** Late — after tonal claim and before sharpening. Heaton repeatedly warns against pushing this on global. Marino: *avoids* it as part of restraint discipline.
- **Mapping:** ✅ supported via `bilat_clarity_*` family and `bilat_local_contrast_*`. Selective application via `parametric mask` for "only on midtones" or "only on the foreground" is composable. **Marino's restraint signal is itself a vocabulary insight** — the *absence* of this move in intimate landscapes is a defining stylistic choice (see proposed `look_landscape_intimate_quiet`).

#### Move 5 — Atmospheric color grading
**Recurs across:** L2 Heaton (Calibration panel for color shift), L3 Page (color contrast in shadows / highlights), L5 Adamus (color tonality in digital darkroom), L6 Ramelli (golden-hour warming), L1 Marino (signature soft palette), L4 O'Leary (creative color in PS). **6/6.**

- **Intent:** Push image color away from neutral toward an atmospheric / emotional register — golden warmth, blue-hour cool, autumn saturation, intimate-soft pastel
- **Result:** Image carries genre-mood signature recognizable independent of subject
- **Tool surface:** LR Calibration panel + Color Grading wheels (Lightroom-side photographers), Photoshop color-balance adjustment layers + selective color (Page, Adamus, O'Leary), darktable Color Balance RGB shadows/midtones/highlights wheels (avidandrew reference)
- **Ordering note:** Late — after tonal work is settled. Several photographers emphasize this is the last "creative" step before sharpening. Ramelli's preset workflow is essentially a packaged version of this move.
- **Mapping:** ✅ supported via `colorbalance_*` family (parameterized in v1.6.0 — RFC-021/ADR-077..080) plus the `color_grade_*` looks. Existing `look_warm_shadows`, `look_split_tone_*` entries cover several variants. **Genre-specific landscape grades** (golden-hour, blue-hour, autumn-saturated, blue-hour-cool) are clear L2 candidates.

#### Move 6 — Selective saturation / vibrance enhancement
**Recurs across:** L2 Heaton (HSL adjustments for skies, foliage), L3 Page (color contrast layering), L4 O'Leary (PS selective color), L5 Adamus (color tonality), L6 Ramelli (saturation for drama). **5/6** — Marino explicitly restrained.

- **Intent:** Lift specific color ranges (sky-blue, foliage-green, water-cyan, autumn-orange) without globally over-saturating
- **Result:** Subject colors sing without the cartoonish over-saturation that flags amateur work
- **Tool surface:** LR HSL panel (per-color sat/lum/hue), Capture One Advanced Color Editor (rare in landscape but Adamus/Page have used it), Photoshop selective color, darktable Color Equalizer
- **Ordering note:** Mid-late — after tonal compression. Heaton: HSL is a nudge, not a wholesale move. Marino: explicitly minimal use as part of authenticity discipline.
- **Mapping:** ✅ supported via the `colorequal` family and `range_filter color_h` parametric masks. `look_sat_kill_blues_global`, `look_sat_lift_oranges_global` and similar entries exist. Worth ensuring **at least one entry per major landscape color band** — sky-blue, foliage-green, foliage-orange (autumn), water-cyan.

#### Move 7 — Targeted dodge and burn
**Recurs across:** L3 Page ("controlled dodging and burning using luminosity masks" — a tutorial cornerstone), L5 Adamus ("clone painting" — his signature variant), L6 Ramelli (LR dodge/burn imitating darkroom techniques — explicit in his teaching), L4 O'Leary (PS dodge/burn workflow). **4/6.**

- **Intent:** Sculpt light selectively — brighten where the eye should land, darken where it should rest — to direct compositional attention
- **Result:** Image carries internal "pull" toward the subject; depth and dimensionality emerge from light-shaping rather than slider-pushing
- **Tool surface:** Photoshop dodge/burn tool on a 50%-gray Soft Light layer (most), LR Adjustment Brush with positive/negative exposure (Ramelli), luminosity-masked exposure layers (Page, Adamus)
- **Ordering note:** Late — generally last creative move before sharpening. Page emphasizes this is the discipline that separates pro from amateur landscape work.
- **Mapping:** ⚠️ partial — same gap as Portrait. chemigram has the wire (`drawn mask` from RFC-029/ADR-084 + parameterized `exposure`), but the **batched-region workflow** (specify N regions with N exposure deltas, apply as a single move) is verbose. **Same RFC candidate as in Portrait genre** — `apply_dodge_burn(image_id, regions=[...])` meta-tool. Consolidates into a single cross-genre RFC.

#### Move 8 — Sharpening last
**Recurs across:** L2 Heaton (DxO PureRAW pre-sharp + LR sharpening), L3 Page (sharpening last in luminosity-mask workflow), L5 Adamus (final sharpening pass), L6 Ramelli (LR sharpening as final step), L4 O'Leary (PS Smart Sharpen). **5/6.**

- **Intent:** Apply input sharpening (sensor recovery) and output sharpening (display medium) without amplifying noise or compressed-tone artifacts
- **Result:** Detail crispness without halos or noise lift
- **Tool surface:** LR Detail panel + masking slider, Photoshop Smart Sharpen / High Pass, DxO PureRAW (Heaton's pre-sharp), darktable Diffuse or Sharpen scene-referred preset (avidandrew reference)
- **Ordering note:** Universally last (after color grading, before export). One of the few near-universal ordering disciplines across all six photographers.
- **Mapping:** ✅ supported via `sharpen_subtle_punch` / `sharpen_aggressive` / Diffuse-or-Sharpen-based primitives. Output sharpening (per-medium) is a separate concern handled at export rather than vocabulary, and chemigram doesn't currently address that — out of scope for L2.

#### Move 9 — Crop / composition refinement
**Recurs across:** L1 Marino (extensive — "something as small as an errant stick or tiny patch of bare ground can sometimes ruin a composition"), L2 Heaton (crop early), L3 Page (composition refinement), L5 Adamus (precision composition), L6 Ramelli (crop for drama), L4 O'Leary (crop in LR). **6/6.**

- **Intent:** Eliminate distractions; refine composition to its strongest internal geometry
- **Result:** Cleaner read of the intended subject and structure
- **Tool surface:** LR Crop tool, PS Crop/Healing Brush for distractions, darktable Crop/Rotate (avidandrew reference). Adamus and Marino both emphasize that distraction-removal is part of composition, not a separate "retouch" step.
- **Ordering note:** Variable — some photographers crop first (claim the frame), others crop last (after seeing how tone shapes the image). Both are defensible.
- **Mapping:** ✅ supported via `crop_*` and `retouch` primitives (RFC-025/ADR-087). The **distraction-removal** flavor of crop (Marino's "errant stick" — small content-aware removal) routes through `retouch heal/clone` (v1.9.0). Already well-served.

#### Move 10 — Vignette / edge framing
**Recurs across:** L2 Heaton (post-crop vignette), L3 Page (selective edge darkening via luminosity), L6 Ramelli (vignette as preset component), L4 O'Leary (PS vignette layer). **4/6** — Marino and Adamus generally avoid as too-aesthetic.

- **Intent:** Subtle radial darkening (or rare brightening) at frame edges to direct eye toward center
- **Result:** Internal "pull" toward the central subject; cinematic feel when restrained
- **Tool surface:** LR Effects panel Vignette, PS radial gradient mask, darktable Vignette module (avidandrew reference)
- **Ordering note:** Late — after composition is settled.
- **Mapping:** ✅ supported via the parameterized `vignette` entry (RFC-021 / ADR-077..080).

### Signature / idiosyncratic moves (recurrence 1-2)

| Photographer | Signature move | Why not L2 |
|-|-|-|
| L1 Marino | **Restraint discipline** — explicit minimization of clarity, saturation, contrast as authenticity stance | An *aesthetic posture*, not a technical move. Better expressed as a "restraint mode" `look_landscape_intimate_quiet` that *applies less* — proposed below. |
| L3 Page | **Pure luminosity-mask compositing** — entire workflow built around mask creation with Lumenzia | Tool-specific (Photoshop + Lumenzia); the *underlying intent* (luminance-banded selective adjustment) is captured in Move 1, 2, 7. |
| L5 Adamus | **"Clone painting"** — synchronizing multiple image files with the clone stamp / history brush as a multi-exposure blend | Out of chemigram's per-image scope; this is multi-raw fusion. Workflow gap, not L2 candidate. |
| L5 Adamus | **Multi-exposure bracketing as default** | Capture-side discipline, not post-process vocabulary. |
| L6 Ramelli | **Preset stack as workflow** — applying preset + nudging | Aesthetically a chemigram anti-pattern (vocabulary, not sliders, not preset-bundles). However, the *bundles* he ships effectively *are* L2 looks expressed as LR XMP — instructive as composition examples. |

### Proposed L2 looks

| Look name | Composition | When to reach for it |
|-|-|-|
| `look_landscape_grand_vista` | sky-targeted parametric (`range_filter color_h` blue + `parametric mask` luminance top quartile) → mild `tone_eq` shadow lift on lower half (gradient mask) → `bilat_clarity_subtle` global → `colorbalance_warm_shadows` | Wide-scene work where sky and foreground are competing for attention; the LR Heaton/PureRAW workflow rendered in chemigram primitives. |
| `look_landscape_intimate_quiet` | neutral `temperature` + clarity *reduction* (`bilat_clarity_painterly`) + restrained saturation (`colorequal_sat_pull_back`) + soft `colorbalance_neutral_lift` | Marino-style intimate / small-scene work: forest interiors, abstract details, anything where drama would betray the subject. The *restraint* look — applies less than baseline does, deliberately. |
| `look_landscape_golden_hour` | warm `temperature` shift (+200K) + `colorbalance_warm_shadows_amber_highlights` + `tone_eq` mild contrast bump in midtones + `colorequal_lift_oranges` | Sunset / sunrise mood; pushes the warmth that golden-hour light *almost* has and amplifies it without breaking color credibility. |
| `look_landscape_blue_hour_cool` | cool `temperature` shift (-200K) + `colorbalance_cool_shadows_neutral_highlights` + lift the blue range via `colorequal_lift_blues` + slight desaturation of warm bands | Twilight / pre-dawn / night-edge work; opposite mood from golden hour, equally valid genre signature. |
| `look_landscape_atmospheric_haze` | `hazeremoval_strong` + `tone_eq` lift on highlights + `bilat_local_contrast_subtle` + warm `colorbalance` | Misty / hazy conditions where the *atmosphere* is the subject; lifts visibility while preserving the moody fog. |
| `look_landscape_dramatic_moody` | deep `tone_eq` shadow crush (-1.5 EV in lowest 2 bands) + `colorbalance_cool_shadows_warm_highlights` + `bilat_clarity_subtle` + sky parametric darken (-0.5 EV on top luminance band) | Page/Adamus-style moody atmospheric — for stormy skies, rugged terrain, weather drama. The dramatic counterpart to `intimate_quiet`. |
| `look_landscape_autumn_pop` | warm `temperature` (+150K) + `colorequal_lift_oranges` + `colorequal_pull_blues` (compensating shift to keep skies natural) + restrained `bilat_clarity_subtle` | Autumn foliage, fall color season; lifts orange/red while preventing over-blueing of skies. |
| `look_landscape_sky_enhance` | sky parametric (`parametric mask` top luminance + `range_filter color_h` blue range) → `colorbalance_cool` + `tone_eq` -0.5 highlight on the masked region | A focused move (not a full grade) — applies only to sky region. Stack with any other landscape look for "use this base + enhance sky." |
| `look_landscape_water_silk` | `range_filter color_h` cyan/blue + `bilat_clarity_painterly` *reduction* on masked water + slight `colorbalance_cool_lift` | Water surfaces — silky water in long-exposure work, glassy lakes; reduces clarity selectively to enhance the smoothness photographers spent shutter-time creating. |

**Existing entries to keep / re-tag:** `look_dramatic_landscape`, `look_warm_shadows`, `look_split_tone_warm_highlights_cool_shadows` already cover several adjacent intents in the existing L2 layer — refine descriptions but don't duplicate. Several of the proposed looks above (`golden_hour`, `blue_hour_cool`, `autumn_pop`) are explicitly genre-time-of-day variants that don't yet have first-class entries.

### Genre-specific gaps (Landscape)

| Gap | Severity | Photographers reaching for it | RFC / vocabulary candidate |
|-|-|-|-|
| **First-class luminosity-band selection ("brightest 25%")** | High | L3 Page (cornerstone technique), L5 Adamus (signature blends), L2 Heaton (intersect-with-mask combines this with gradient) — 3/6 but central to landscape compositing | The `parametric mask` primitive (RFC-024 / ADR-085) supports this in principle (luminance range slider). What's missing is **named bands** — `mask_luminosity_brightest_quartile`, `mask_luminosity_darkest_quartile`, `mask_luminosity_midtones`. RFC candidate to layer pre-named masks on top of `parametric mask`. Aligns with "vocabulary not sliders" discipline. |
| **Multi-exposure / bracket blending** | High (for Adamus-class workflow) | L5 Adamus (signature), L3 Page (exposure-blending workshops) — 2/6 but defining for one whole school | **Architectural / out of scope.** chemigram is per-image-as-edited; multi-raw HDR fusion is a Hugin / HDRMerge / Photomatix workflow at capture-time. Acknowledge as a deliberate boundary: chemigram does single-raw landscape work. Multi-exposure shooters bring their fused TIFF in as the "raw." Document this in `vocabulary-patterns.md`. |
| **Sky-detection as a single op** | Medium | L2 Heaton (LR adaptive sky preset is his Step 1) — 1/6 explicit, but implicitly underpins much of the sky work in L3, L4, L5, L6 | **Already addressed by LLM-vision masker** (RFC-026 / ADR-086 in v1.9.0) — instruct the masker to "select the sky region" via natural language. The gap is **discoverability / wrapping** — most photographers won't think to invoke an LLM-masker for a "sky" mask. RFC candidate for a `mask_sky` shorthand that auto-routes to LLM-vision with a canonical sky prompt. Light architectural lift; meaningful UX win. |
| **Batched dodge-and-burn** (cross-genre with Portrait) | Medium | L3 Page, L5 Adamus, L6 Ramelli, L4 O'Leary — 4/6 in landscape; 3/6 in portrait. Cross-genre confirms RFC priority. | **Cross-genre RFC consolidation** — same entry as in Portrait gaps. `apply_dodge_burn(image_id, regions=[(x,y,r,ev), ...])` meta-tool. The cross-genre recurrence (4 landscape + 3 portrait = 7 photographers) makes this the single highest-priority workflow gap surfaced by this survey. |
| **"Output sharpening" per medium** | Low | L2 Heaton, L6 Ramelli (implicit: sharpening for screen vs. print) — 2/6 | Out of L2 scope; this is an export-time concern, not a compositional vocabulary. Note in TODO for export-pipeline future work. |
| **Preset-stack / preset-pipeline as workflow** | Low | L6 Ramelli only | Anti-pattern from chemigram's POV (vocabulary, not preset-bundles). Acknowledge but explicitly do not address. |

---

## Genre — Wedding / Event

### Photographers surveyed (6)

| # | Photographer | Style | Primary tool | Source |
|-|-|-|-|-|
| W1 | **Susan Stripling** | New York editorial wedding, "clean-yet-gritty," DVLOP-preset-driven | Lightroom + DVLOP presets | [Susan Stripling — Lightroom presets for wedding photographers](https://susanstripling.com/blog/lightroom-presets-wedding-photographers/), [CreativeLive 30 Days bootcamp](https://www.creativelive.com/class/30-days-wedding-photography-susan-stripling) |
| W2 | **Alexander Flemming** (Capture One) | Session-based virtual albums, structured Capture-One workflow | **Capture One** | [Capture One Blog — Smart wedding photography workflow](https://www.captureone.com/blog/capture-one-wedding-photography-workflow) |
| W3 | **Eric Ronald** | Speed-edit Capture One workflow, keyboard-shortcut discipline | **Capture One** | [Capture One Blog — How to edit wedding photos faster](https://www.captureone.com/blog/how-to-edit-wedding-photos-faster) |
| W4 | **Hunter & Sarah Photography** | High-volume LR workflow, lens × lighting preset matrix | Lightroom Classic | [Hunter and Sarah — Post Production Secrets Step 5](https://hunterandsarah.com/post-production-secrets-5/) |
| W5 | **Mark Davidson** | Mixed-light reception specialist, anchor-image discipline | Lightroom | [mark-davidson.com — How to edit wedding photos](https://www.mark-davidson.com/blog/how-to-edit-wedding-photos) |
| W6 | **SLR Lounge / Pye Jirsa** (Lin & Jirsa) | Studio-pace LR workflow, sync + clipboard mastery | Lightroom | [SLR Lounge — Lightroom workflow tips](https://www.slrlounge.com/lightroom-workflow-tips/) |

**Mix:** Lightroom (4: W1, W4, W5, W6) / Capture One (2: W2, W3). **Two ecosystems represented; falls short of the three-ecosystem mandate** — same finding as Landscape. Wedding-photography published-process content skews overwhelmingly Adobe and Capture One; no darktable wedding-photographer essayist surfaced in searches. The finding is itself a signal: open-source raw-developer adoption among working wedding photographers is rare, likely because the volume + time-pressure workflow patterns require the batch-sync + Smart-Adjustments-class tooling that only Adobe and Capture One ship at the integration depth wedding work demands.

### Common moves (recurrence 3+)

#### Move 1 — Anchor-image + sync workflow
**Recurs across:** W2 Flemming (edit first image, copy settings via Clipboard), W4 Hunter & Sarah (Shift/Ctrl select all images in a lighting group, sync), W5 Davidson (anchor per lighting situation, then sync), W6 SLR Lounge (Sync + Auto-Sync). **4/6.**

- **Intent:** One image edited per lighting situation; that edit propagates across all images in the same lighting group as a single move
- **Result:** ~50-200 similar-light images receive identical baseline edits in seconds, rather than hours of per-image work
- **Tool surface:** Lightroom Sync button + Auto-Sync toggle, Capture One Clipboard with selectable tool subset, both with metadata-filtered selection (lens, ISO, time bucket)
- **Ordering note:** **Foundational to wedding-pace workflow.** Every photographer ships an anchor-and-sync discipline; no exceptions. The variants differ in how groups are formed (by lighting / by lens / by time / by smart-album) but the core "edit one, propagate to many" move is universal.
- **Mapping:** ❌ **gap.** chemigram's `apply_primitive` is per-image. There's no "apply this primitive to N images at once" surface. The closest existing wire is `--stdin` batch mode (apply same primitive to a list of images), which works for primitive-level apply but not for "edit this image, sync the resulting *state* to N others." **High-priority RFC candidate.**

#### Move 2 — Mixed-lighting white-balance reconciliation
**Recurs across:** W2 Flemming (Color Balance for cohesive look), W4 Hunter & Sarah (per-light presets: tungsten/window/gel/flash), W5 Davidson (scene-by-scene WB + HSL orange/red), W3 Ronald (luma range masking for selective tonal work). **4/6.**

- **Intent:** Resolve color-cast conflicts when a single scene contains tungsten + LED + window + flash — none of which agree on neutral
- **Result:** Skin tones read consistent across the scene; the wedding venue's mixed lighting doesn't show as ugly color stripes
- **Tool surface:** LR Temperature/Tint + HSL panel + selective masking, Capture One White Balance + Skin Color tab + local adjustment layers, **gradient masking with WB shift** for fading between two light sources within a wide-angle frame
- **Ordering note:** Davidson explicitly: *"Correct white balance scene by scene"* precedes HSL refinement, which precedes selective masking. Most photographers identify the dominant light source and let the others read as accent.
- **Mapping:** ⚠️ **partial.** chemigram has `temperature` (parameterized) + `colorequal` for HSL refinement + `parametric mask` for color-band scoping + drawn gradient masks. Composition is expressible but verbose — needs a "WB-correction-with-gradient-fade" L2 look or an `apply_per_region` recipe. The cross-region WB-anchor pattern (one corner of the frame at 3200K, the other at 5500K) is a real gap — drawn-gradient masks scope spatially but the parameter (WB temperature) can't gradient-interpolate within the same primitive instance.

#### Move 3 — Preset-driven first pass
**Recurs across:** W1 Stripling (5 DVLOP presets — All We See Is Sky as 99% baseline), W4 Hunter & Sarah (30+ presets per lens × lighting), W6 SLR Lounge (anchor-image becomes preset). **3/6** (and load-bearing for the wedding workflow more generally — most published wedding tutorials assume a preset-driven base).

- **Intent:** Apply a personal-style baseline as Step 1, before any image-specific work
- **Result:** Image already 90% finished; per-image work is just exposure / WB / minor tweaks
- **Tool surface:** Lightroom Develop Presets (saved Develop settings), Capture One Styles (.costyle files), **explicitly named** in the photographer's mental model: "All We See Is Sky," "Curious Cat," "Overcast – 85mm"
- **Ordering note:** Always Step 1 after import. The agent's reasoning starts FROM the preset, not from a neutral baseline.
- **Mapping:** ⚠️ **partial.** chemigram has L2 looks (the `look_*` family — 31 entries post-v1.10) which are functionally equivalent to LR/C1 presets. The gap is *naming convention* and *batch application* — wedding photographers think in "this is my Stripling preset for tungsten light"; chemigram thinks in "look_landscape_golden_hour at full strength." For the Phase 2 personal-vocabulary path, the photographer authors their own L2 looks named after their style — not a primitive gap, a UX/discoverability gap. **Workflow gap.**

#### Move 4 — Skin-tone uniformity (Capture One signature)
**Recurs across:** W2 Flemming (Skin Smoothing + Skin Color combination), W3 Ronald (Smart Adjustments — face-aware AI batch). **2/6 explicit but central to commercial wedding work** — every Capture-One-using wedding photographer reaches for this; the Adobe-using ones approximate via HSL.

- **Intent:** Bride's / groom's skin reads consistent across portraits despite mixed lighting and strong gel-flash interactions
- **Result:** Skin variance compressed; the slight orange under tungsten + slight blue from window doesn't fight
- **Tool surface:** Capture One **Skin Color tab** with Hue / Saturation / Lightness Uniformity sliders + Skin Smoothing + Smart Adjustments (face-aware)
- **Ordering note:** After WB foundation, before color grading. Shadow / highlight / midtone color shifts should NOT compete with skin uniformity work.
- **Mapping:** ✅ **shipped (RFC-033).** `skin_uniformity` parameterized entry with `mask_skin_region` pre-baked. Wedding genre confirms the cross-genre relevance: 3/6 portrait + 2/6 wedding = 5/12 across two genres. **Visual-review checkpoint findings particularly relevant for wedding scenes** (mixed-light skin retouching is a harder visual quality bar than portrait studio work).

#### Move 5 — Backlit subject recovery
**Recurs across:** W4 Hunter & Sarah (per-lighting "backlight" preset), W5 Davidson (highlight recovery + shadow lift), W6 SLR Lounge (Highlights/Shadows in Basic panel). **3/6** — the canonical "shooting toward sun, against bright window" wedding scene.

- **Intent:** Recover detail in a subject silhouetted against bright window/sun; the photographer wants the subject readable, not a black cutout
- **Result:** Subject lifted ~1-2 stops in shadow region; background rolloff preserved (don't crush the bright halo around the subject — that's the look)
- **Tool surface:** LR Shadows slider + radial filter, Capture One HDR tool + local adjustment, Photoshop Camera Raw Shadows
- **Ordering note:** After WB; before color grading.
- **Mapping:** ✅ supported via `tone_eq` (parameterized; 8-band luminance dodge/burn) + `mask_subject` (RFC-032) for region scoping, OR drawn radial mask + parameterized `exposure`. `look_subject_lift_dark_only` (existing L2) approximates this for portrait; could ship a wedding-tuned variant as L2 candidate.

#### Move 6 — B&W alternates as parallel deliverable
**Recurs across:** W1 Stripling (Dead Girl Walking preset), W2 Flemming (Clone Variants + Black & White tool), W6 SLR Lounge (Smart Collections for B&W subset). **3/6** — wedding photographers commonly deliver both color + B&W versions of select images.

- **Intent:** From one color edit, produce a B&W variant that complements without simply being a desaturated version of the color
- **Result:** Two cohesive renders; the B&W has its own tonal punch / structure / mood, not a monochrome copy
- **Tool surface:** LR Variant + Black & White panel, Capture One Clone Variants + B&W tool with Color Sensitivity + Split Tones tabs, Photoshop Layer Comp
- **Ordering note:** After color edit complete (ratings, sync, individual tweaks). The B&W variant is a separate creative output, not just an export option.
- **Mapping:** ⚠️ **partial — gap on the B&W primitive itself.** chemigram has `colorequal` and `channelmixerrgb` decoders that COULD compose a B&W conversion, but no named "B&W conversion" primitive in the vocabulary. The B&W genre below confirms this gap with much higher recurrence. **High-priority L2 candidate.**

#### Move 7 — Speed-edit / keyboard-shortcut discipline
**Recurs across:** W3 Ronald (custom Capture-One shortcuts; map Speed Edit keys to identical letters; tap-vs-hold for minor-vs-major), W4 Hunter & Sarah (filmstrip Shift+Ctrl multi-select), W6 SLR Lounge (Caps Lock auto-advance, P/X flag system). **3/6.**

- **Intent:** Eliminate cursor-and-click friction on the tens of thousands of slider adjustments per wedding
- **Result:** ~3-5x speedup per image; days saved per wedding
- **Tool surface:** Capture One Edit Keyboard Shortcuts + Speed Edit, LR Library/Develop module shortcuts, Caps Lock auto-advance behavior
- **Mapping:** ❌ **out of scope.** chemigram is agent-driven (ADR-006 / ADR-033) — no keyboard-shortcut surface beyond the standard CLI. Workflow-philosophy difference, not a gap to address. The agent loop is the chemigram-equivalent of the speed-edit pattern: photographer says "match all reception shots to this anchor's WB," agent batches.

#### Move 8 — Reception low-light / high-ISO recovery
**Recurs across:** W1 Stripling ("I Believe" preset for flash/artificial), W4 Hunter & Sarah (per-lighting noise-reduction sync per ISO), W6 SLR Lounge (sort by ISO + sync NR per group). **3/6.**

- **Intent:** Recover detail in dance-floor / candlelit ceremony images where ISO is 6400+ and noise dominates
- **Result:** Subject readable; noise softened without smearing detail
- **Tool surface:** LR Detail panel (Luminance + Color noise reduction), Capture One Noise Reduction tool, sometimes routed through DxO PureRAW (Heaton-style pre-sharp pipeline)
- **Ordering note:** Before sharpening. Aggressive NR before clarity / structure work; conservative NR after.
- **Mapping:** ✅ supported via `denoiseprofile` decoder; could ship an L2 look for "high-ISO reception lift" as a wedding-pack candidate.

#### Move 9 — Rating + culling first
**Recurs across:** W2 Flemming (5-star Smart Album rating pass), W6 SLR Lounge (P/X flag binary keep/reject), W3 Ronald (selection accelerated via shortcuts). **3/6.**

- **Intent:** Cull ~3000 frames from a wedding to ~300 deliverables before any editing
- **Result:** Editing time spent only on keepers
- **Tool surface:** LR Library module flag/rating + Smart Collections, Capture One ratings + filter
- **Ordering note:** Always Step 1 — before WB / preset / batch sync
- **Mapping:** Out of chemigram's vocabulary scope (this is an asset-management discipline, not an edit primitive). Documented because the *absence* of culling is a wedding-genre signal — chemigram's per-image workspace model assumes the culling already happened (the `image_id` is a survivor of selection).

#### Move 10 — Export recipe / dual-format delivery
**Recurs across:** W2 Flemming ("Wedding Print" + "Wedding Resized" recipes), W3 Ronald (Export Recipes with subfolder tokens), W6 SLR Lounge (full-size + web-size exports). **3/6.**

- **Intent:** Single-action export to multiple output formats / sizes / sharpening profiles per photo
- **Result:** Couple's preview gallery (web-size) + delivery folder (full-size, print-sharpened) + B&W variant — all from one button
- **Tool surface:** Capture One Process Recipes with token-based folder structure, LR Export Presets
- **Mapping:** Out of vocabulary scope (export-pipeline concern, not edit primitive). Tracked alongside output sharpening (Landscape Gap #10) as a future export-pipeline RFC.

### Signature / idiosyncratic moves

| Photographer | Signature move | Why it doesn't generalize |
|-|-|-|
| W1 Stripling | DVLOP-preset-stack workflow with named modifier presets | Preset-stack is ecosystem-specific; chemigram's vocabulary discipline serves the same intent differently |
| W2 Flemming | Session-based virtual album discipline (Preparations / Ceremony / Reception) | Capture One's session feature; LR users use Collections to similar effect; chemigram has per-image workspaces, not multi-image sessions yet |
| W3 Ronald | Tap-vs-hold Speed Edit keyboard mapping | Speed-edit is a slider-driven UX, doesn't translate to chemigram's vocabulary surface |
| W4 Hunter & Sarah | 30+-preset matrix (per lens × per lighting) | Volume of presets is wedding-specific; corresponds in chemigram to a personal-pack of L2 looks (Phase 2) |
| W5 Davidson | Last-resort B&W fallback when mixed-light WB is unrecoverable | An aesthetic fallback, not a technique — interesting framing of "B&W as recovery move" |
| W6 SLR Lounge | RAW → JPG conversion of rejected files for storage compression | Asset-management discipline, out of edit-vocabulary scope |

### Proposed L2 looks (Wedding/Event)

| Name | Intent | Composition |
|-|-|-|
| `look_wedding_natural_warm` | Stripling/Hunter-Sarah-style clean-warm wedding default | `temperature` (warm shift +0.04) + `exposure` (+0.15) + `sigmoid_contrast` (1.25) + `colorbalancergb` warm-shadow mild |
| `look_wedding_reception_high_iso` | High-ISO dance-floor recovery | `denoiseprofile` (medium) + `bilat_clarity_strength` (mild) + warm-shadow + slight saturation pull |
| `look_wedding_backlight_lift` | Subject-lifted under bright backlight | `tone_eq` shadow lift (zones 1-3 +0.4) + `mask_subject` from RFC-032 + `exposure` (+0.2 in subject region) |
| `look_wedding_mixed_light_warm_dominant` | Tungsten-dominant reception with subject window-light | warm `temperature` baseline + parametric mask cool-correction on top-luminance band |
| `look_wedding_bw_alternate` | B&W alternate from a color edit | (depends on B&W primitive — see Gap below) |

**Note:** four out of five proposed looks are essentially adaptations of existing primitives composed into wedding-specific recipes — no new primitive authoring needed beyond the L2 entries themselves. The fifth (`look_wedding_bw_alternate`) blocks on the B&W gap surfaced below.

### Genre-specific gaps (Wedding/Event)

| Gap | Severity | Photographers reaching for it | RFC / vocabulary candidate |
|-|-|-|-|
| **Batch-sync workflow / "edit one image, propagate to N"** | **High** (4/6 — load-bearing for the genre) | W2 Flemming, W4 Hunter & Sarah, W5 Davidson, W6 SLR Lounge | **RFC candidate (high priority).** chemigram's `apply_primitive` is per-image; `--stdin` works for "apply the same primitive to N image_ids" but not for "edit this image, replicate the resulting STATE to N images." A `propagate_state(source_image, target_image_ids, scope)` MCP verb would close this gap. Affects MCP tool surface; extension to RFC-031's atomic-batch shape. |
| **Within-image WB gradient (one corner tungsten, other corner window)** | Medium | W5 Davidson (gradient-tool with WB shift), W2 Flemming (Color Balance) | **RFC candidate.** Drawn-gradient masks scope spatially but parameter (`temperature` red/blue/green coeffs) can't gradient-interpolate within the same primitive instance. Either (a) extend `temperature` to support gradient-aware values, or (b) compose two `temperature` instances at different multi_priorities each masked to half the frame with a gradient feather. (b) is expressible today but verbose. |
| **Smart-Adjustments-class AI batch consistency** | Medium | W3 Ronald (C1 Smart Adjustments — face-aware), W4 Hunter & Sarah (preset matrix is the manual analog) | **Out of scope (deliberate boundary).** Per ADR-007 chemigram doesn't bundle AI; the BYOA framing is right here. The closest chemigram-analog: agent applies `look_*` looks across a batch via `--stdin`, scoping per metadata. Document as workflow pattern. |
| **Preset-stack as intentional workflow** | Low | W1 Stripling, W4 Hunter & Sarah | Already addressed by the L2 looks layer + the Phase 2 personal-vocabulary path. Photographers author their own preset-equivalents as L2 looks. Not a gap; a workflow-philosophy note. |
| **Asset management (rating, culling, smart collections, sessions)** | Out of scope | All wedding photographers | chemigram operates on `image_id` post-culling; asset management is a sibling concern. Document the boundary; no RFC. |
| **Export recipes / dual-format delivery** | Low | W2 Flemming, W3 Ronald, W6 SLR Lounge | Same boundary as Landscape Gap #10 — export-pipeline concern, not vocabulary. Tracked for future export-pipeline RFC. |

---

## Genre — B&W (black-and-white)

### Photographers surveyed (6)

| # | Photographer | Style | Primary tool | Source |
|-|-|-|-|-|
| BW1 | **Sean Tucker** | Chiaroscuro street / portrait, ~1hr-per-image discipline | Lightroom + Photoshop | [Sean Tucker — Photography blog](https://www.seantucker.photography/blog), [PetaPixel — Dramatic B&W with curves and HSL](https://petapixel.com/2017/08/09/edit-dramatic-bw-photos-mobile-curves-hsl-sliders/) |
| BW2 | **Joel Tjintjelaar** | Long-exposure architectural fine-art B&W; iSGM workflow | **Photoshop** + custom panels | [BWVision](https://bwvision.com/), [ProImageEditors — B&W Fine Art Masking](https://www.proimageeditors.eu/workflow/black-white-fine-art-masking-service-designed-by-joel-tjintjelaar/) |
| BW3 | **Cole Thompson** | High-contrast / mid-tone-removal B&W; "I see in B&W" philosophy | **Photoshop** (channel mixer, dodge/burn 1-3% per layer) | [Cole Thompson Photography](https://colethompsonphotography.com/), [Cole Thompson — Secret to B&W Conversion](https://colethompsonphotography.com/2009/05/23/secret-bw-conversion/) |
| BW4 | **Robin Whalley** (Lenscraft) | Silver Efex Pro methodologist; zone-system-aware | **Silver Efex Pro / Nik Collection** | [Lenscraft — Two Powerful Silver Efex Adjustments](https://lenscraft.co.uk/photo-editing-tutorials/two-powerful-adjustments-in-nik-silver-efex-pro/) |
| BW5 | **Richard Boutwell** | Capture One Pro B&W workflow; print-medium thinking | **Capture One** | [Capture One Blog — Master your B&W with Luma Curves](https://www.captureone.com/blog/master-your-bw-conversion-with-the-new-luma-curves), [B&W Mastery — C1 Pro 8 Workflows](https://www.bwmastery.com/blog/2015/black-and-white-with-capture-one-pro-8-part-2-workflows) |
| BW6 | **Stefano** (Mela365) | darktable B&W workflow; Color Zones-driven | **darktable** | [mel365.com — darktable black and white tutorial](https://mel365.com/darktable-black-and-white/) |

**Mix:** Photoshop (3: Tjintjelaar, Thompson, Tucker — though Tucker composes with LR) / Silver Efex Pro / Capture One / darktable. **Four ecosystems represented; mandate met cleanly.** B&W is a specialist genre with strong tooling diversity — Silver Efex Pro is genre-defining, Capture One has dedicated B&W tabs, darktable's `monochrome` and `channelmixerrgb` modules are well-supported. Notably stronger ecosystem mix than wedding/event.

### Common moves (recurrence 3+)

#### Move 1 — Color filter / channel-mixed conversion (the foundational B&W move)
**Recurs across:** **All 6 photographers.** BW3 Thompson (channel mixer source channels), BW4 Whalley (Color Filters first — red darkens skies, green enhances foliage), BW5 Boutwell (Color Editor B&W mode), BW6 Stefano (Color Zones black-and-white preset), BW1 Tucker (HSL color limit), BW2 Tjintjelaar (color-targeted iSGM masking).

- **Intent:** Each color in the original image maps to a tonal value in the B&W rendition; the mapping itself IS the creative move. Red sky → dark vs. light depending on photographer's intent.
- **Result:** B&W image with deliberate tonal separation rather than uniform desaturation; "this is how the original colors should render as tones"
- **Tool surface:** Photoshop Channel Mixer (Monochrome checkbox + RGB sliders), Silver Efex Color Filters + Color Response, LR HSL B&W tab, Capture One B&W Color Sensitivity tab + Luma Curve, darktable Color Zones / Channel Mixer RGB / Monochrome module
- **Ordering note:** **Universal Step 1 of any B&W workflow.** Before contrast, before tonal sculpting, before everything. The decision "how should reds render in this image" precedes all other B&W decisions.
- **Mapping:** ❌ **gap.** chemigram has `colorequal` (HSL band shifts) and `channelmixerrgb` (decoder shipped, sat-kill capable) — both could compose this — but no named "B&W conversion" primitive in the vocabulary. **Highest-priority L2 candidate; possibly a parameterized primitive.** The discipline is "vocabulary, not sliders" — B&W conversion needs a named move, not a chain of slider-equivalents.

#### Move 2 — Tonal sculpting via dodge & burn
**Recurs across:** BW3 Thompson (Photoshop dodge/burn at 1-3% per layer over weeks), BW2 Tjintjelaar (multi-section masking with iSGM), BW4 Whalley (Silver Efex Control Points — "intelligent dodge/burn"), BW6 Stefano (darktable dodge/burn presets with feathered masks). **4-5/6.**

- **Intent:** Sculpt LIGHT in the B&W image — brighten the eye, deepen the shadow under the chin, lighten the cloud, darken the corner. The traditional darkroom discipline transposed to digital.
- **Result:** B&W image that "reads like a print" — directional lighting independent of the actual scene lighting
- **Tool surface:** Photoshop dodge/burn on 50%-gray Soft Light layer (Thompson — "1, 2, and 3 percent very gradually"), Silver Efex Control Points (region-clipped local contrast/brightness), darktable masked exposure, Capture One Local Adjustment
- **Ordering note:** Late in the workflow; after conversion + global tonal foundation. The "fine sculpting" pass.
- **Mapping:** ⚠️ **partial** — same gap as Portrait + Landscape. RFC-031's `apply_per_region` ships the wire (atomic N-region exposure adjustment), but the B&W discipline is *especially* about precision dodge/burn. Thompson does 1-3% per layer over weeks — chemigram's `apply_per_region` is fine for the architectural shape but the per-region magnitude granularity matters more here. **Visual-review checkpoint relevant for B&W workflows specifically.**

#### Move 3 — Contrast shaping (separate from conversion)
**Recurs across:** BW4 Whalley (Soft Contrast slider + Dynamic Brightness — distinct from conversion), BW5 Boutwell (HDR setting + Clarity 24-36 + Structure low), BW6 Stefano (final RGB curve), BW1 Tucker (curves on mobile + desktop), BW2 Tjintjelaar (multi-layer contrast). **5/6.**

- **Intent:** After B&W conversion, shape the global tonal response — punch the histogram, set black/white points
- **Result:** Image moves from "converted but flat" to "converted with intentional tonal architecture"
- **Tool surface:** LR/Photoshop Curves + Tone Curve, Silver Efex Soft Contrast + Dynamic Brightness, Capture One Levels + Luma Curve (B&W mode), darktable RGB Curve / Sigmoid
- **Ordering note:** After conversion (Move 1), before sculpting (Move 2)
- **Mapping:** ✅ supported via `sigmoid_contrast` (parameterized) + `tone_eq` (8-band luminance control). The B&W-specific variant: contrast applied AFTER `colorequal` saturation-kill produces correct B&W contrast. Could ship `look_bw_contrast_shape` as L2 candidate.

#### Move 4 — Local contrast / structure / clarity
**Recurs across:** BW5 Boutwell (Clarity 24-36 + Structure low), BW4 Whalley (Silver Efex Structure slider), BW6 Stefano (Local Contrast module), BW1 Tucker (LR Clarity), BW2 Tjintjelaar (selective structure via masks). **5/6.**

- **Intent:** Mid-frequency definition / micro-contrast — the texture in skin, fabric, stone, water
- **Result:** B&W image carries dimensional depth without crunchy HDR feel
- **Tool surface:** LR Clarity + Texture, Silver Efex Structure (with shadow/midtone/highlight independence), Capture One Clarity + Structure, darktable Local Contrast / Diffuse-or-Sharpen
- **Ordering note:** Mid-workflow; after contrast (Move 3), before sharpening
- **Mapping:** ✅ supported via `bilat_clarity_strength` (parameterized) + `bilat_local_contrast_*`. The Silver Efex tri-axis structure (shadows/midtones/highlights) is a notable surface that chemigram's `bilat` doesn't expose — that's a sub-gap (chemigram has zone-by-zone via `tone_eq` but not "structure per zone").

#### Move 5 — Underexpose-then-recover (Adams's "expose for shadows, develop for highlights")
**Recurs across:** BW3 Thompson (underexpose by ~1 stop, then dodge highlights to taste), BW5 Boutwell (HDR setting 10-50+ for shadow/highlight recovery). **2/6 explicit, but the foundational philosophy underlying all 6 photographers.**

- **Intent:** Capture more shadow detail (underexposed image preserves it), then push light back into the image during processing
- **Result:** Preserved shadow detail + photographer-controlled highlight allocation
- **Tool surface:** Capture-time decision (underexpose) + LR Shadows slider / Capture One HDR Shadows / darktable `tone_eq`
- **Ordering note:** Capture-time discipline; processing-time recovery follows
- **Mapping:** ✅ supported via `tone_eq` shadow-zone lift (parameterized) + `highlights_recovery_*`. The Adams discipline is partly a vocabulary observation — there's no "Adams expose-for-shadows recovery" primitive, but the building blocks exist.

#### Move 6 — Vignetting / edge framing
**Recurs across:** BW6 Stefano (vignetting module), BW4 Whalley (Silver Efex Finishing Effects vignette), BW2 Tjintjelaar (subtle vignette in iSGM finishing). **3/6.**

- **Intent:** Subtle peripheral darkening in B&W; pulls the eye toward the central subject, mimics print-paper falloff
- **Result:** Image carries internal "pull" toward the subject; cinematic feel when restrained
- **Tool surface:** LR Effects panel Vignette, Silver Efex Vignette, darktable Vignette, Capture One Vignetting
- **Ordering note:** Late — finishing pass.
- **Mapping:** ✅ supported via parameterized `vignette` entry. `look_landscape_intimate_quiet` and similar restraint-discipline looks already compose vignette; could ship a B&W-specific variant (`look_bw_print_vignette`).

#### Move 7 — Split toning (subtle warm/cool tints in B&W)
**Recurs across:** BW4 Whalley (Silver Efex Toning), BW5 Boutwell (Color Editor for tone), BW1 Tucker (subtle warm/cool tints in finishing). **3/6.**

- **Intent:** Subtle tinted B&W — warm shadows + cool highlights (or vice versa) to evoke selenium / sepia / cyanotype print traditions
- **Result:** B&W image carries subtle warmth or coolness; reads as "toned print" rather than pure neutral
- **Tool surface:** Silver Efex Toning tab, Capture One B&W Split Tones tab, LR Color Grading panel (4 wheels, applied to a desaturated image)
- **Ordering note:** Last creative step before sharpening
- **Mapping:** ✅ supported via the `colorbalancergb` parameterized axes. The B&W-specific application is "use shadows hue + highlights hue at low saturation on a desaturated image" — composable. Could ship `look_bw_split_tone_warm_shadows` etc. as L2 candidates.

#### Move 8 — Iterative refinement over time
**Recurs across:** BW3 Thompson ("let it sit for a few days, look again, repeat — sometimes a month"), BW1 Tucker (~1hr per image with multiple software passes). **2/6 explicit; the time-honored craft posture underlying B&W work.**

- **Intent:** B&W work isn't fast — multiple passes with rest periods between them surface flaws the photographer didn't see fresh
- **Result:** Image converges on the photographer's intent over days/weeks rather than minutes
- **Tool surface:** Workflow discipline (not a tool) — save state, return later, edit again
- **Mapping:** ✅ supported via chemigram's snapshot history + branch model (ADR-018). Photographer can `chemigram snapshot --label "first pass"`, return later, render preview, `chemigram apply-primitive` further. Already there; UX/discoverability question for the agent prompt template ("when working on B&W, propose a rest period before the closing pass").

#### Move 9 — Multi-section workflow (Tjintjelaar's iSGM)
**Recurs across:** BW2 Tjintjelaar (signature; divides the image into N sections, edits each separately, saves intermediate files). **1/6 — signature move, but a high-impact one.**

- **Intent:** Acknowledge that B&W tonal allocation is region-specific (sky needs different tonal logic from foreground), explicitly partition the image
- **Result:** Each region carries its own tonal architecture; the assembled image has internal coherence
- **Tool surface:** Photoshop layers + masks; a custom workflow shape rather than a single tool
- **Mapping:** ⚠️ partial — RFC-031's `apply_per_region` is the architectural primitive for this. The Tjintjelaar workflow IS a per-region adjustment workflow, just at coarser regions than dodge-and-burn. Composable today; verify in visual review.

#### Move 10 — Long-exposure rendering (signature, capture-time)
**Recurs across:** BW2 Tjintjelaar (signature). **1/6 — capture-time discipline, not edit-time.**

- **Intent:** 10-stop ND filter + 30-second exposure smooths water and clouds into ethereal forms
- **Result:** Architectural / fine-art B&W with smooth water + streak clouds — Tjintjelaar's signature aesthetic
- **Tool surface:** Capture-time (lens filter + tripod + long shutter), edit-time is Just B&W conversion + tonal sculpting on the smoothed input
- **Mapping:** Out of chemigram's edit-time scope. Documented because it's the genre's most-recognizable signature; the edit-time component is just standard B&W.

### Signature / idiosyncratic moves

| Photographer | Signature move | Why it doesn't generalize |
|-|-|-|
| BW1 Tucker | One-hour-per-image discipline + 4-program pipeline | Process discipline, not technique; chemigram's snapshot model supports it |
| BW2 Tjintjelaar | iSGM (intelligent Selective Gradient Masking) — multi-section workflow with intermediate saves | Capturable in chemigram via `apply_per_region` + branch / snapshot per section |
| BW3 Thompson | Dodge/burn at 1-3% over weeks of iteration | Time discipline + sub-percent precision; the agent-loop equivalent is many small `apply_per_region` calls with low-magnitude exposure deltas |
| BW4 Whalley | Silver Efex Pro Soft Contrast + Dynamic Brightness as the two foundation sliders | Silver-Efex-specific; the underlying intent (separate midtone control from extremes) is captured by chemigram's `tone_eq` zonal control |
| BW5 Boutwell | Luma Curve (Capture One) for tonal punch without saturation drift | C1-specific tool; chemigram's curves apply post-conversion in the same way (saturation already killed) |
| BW6 Stefano | Color Zones-driven darktable B&W preset | A specific darktable composition pattern; replicable in chemigram via `colorequal` |

### Proposed L2 looks (B&W)

| Name | Intent | Composition |
|-|-|-|
| `look_bw_classic_neutral` | Default B&W conversion — neutral channel weighting, mid contrast, mild structure | New B&W primitive (see Gap below) + `sigmoid_contrast` (1.3) + `bilat_clarity_strength` (0.3) |
| `look_bw_high_contrast_chiaroscuro` | Tucker/Thompson-style chiaroscuro — strong contrast, deep shadows, lifted highlights | New B&W primitive + `sigmoid_contrast` (1.7) + `tone_eq` shadow crush (zones 0-2) + `tone_eq` highlight lift (zones 8-10) |
| `look_bw_long_exposure_fineart` | Tjintjelaar-style long-exposure architectural B&W — smooth, structured | New B&W primitive + `bilat_clarity_strength` (-0.2; soften texture) + `tone_eq` shadow lift (zones 0-3) + `vignette` (subtle) |
| `look_bw_silver_efex_zone_balanced` | Whalley/Boutwell zone-system-aware balanced B&W | New B&W primitive + `tone_eq` per-zone allocation (zones balanced) + structure subtle |
| `look_bw_split_tone_warm_shadows` | Subtle warm-shadows toned B&W (sepia/selenium evocation) | New B&W primitive + `colorbalancergb` shadows hue=30, sat=0.05 + highlights hue=200, sat=0.03 |
| `look_bw_split_tone_cool_highlights` | Cyanotype evocation — cool highlights, warm shadows minor | Inverse split-tone composition |
| `look_bw_landscape_dramatic` | Page/Adamus B&W landscape (storm clouds, deep shadows) | New B&W primitive + `sigmoid_contrast` (1.6) + `bilat_clarity_strength` (0.5) + sky-specific contrast via `mask_sky` |
| `look_bw_portrait_chiaroscuro` | Tucker portrait B&W — directional light, deep shadows | New B&W primitive + masked contrast lift via `mask_subject` + `tone_eq` chin-shadow deepen |

**Existing entry to keep:** `look_neutral` is mostly color-neutral and unrelated. The shipped vocabulary has no B&W-specific composite looks pre-v1.10 — this is genuinely a new category in the L2 layer.

### Genre-specific gaps (B&W)

| Gap | Severity | Photographers reaching for it | RFC / vocabulary candidate |
|-|-|-|-|
| **Named B&W conversion primitive** | **Highest** (6/6 — universal foundational move) | All BW1-BW6 | **L2 / parameterized primitive candidate (top priority).** chemigram's `colorequal` can saturation-kill globally; `channelmixerrgb` decoder can express channel-mixed conversion. Neither is named "B&W conversion." **Ship as `bw_convert` parameterized entry** with parameters for red/green/blue channel weights (matching the channel-mixer mental model) and a `preset` parameter (red-filter / green-filter / orange-filter / blue-filter / luminosity / saturation-kill). High-impact, low-cost ship. |
| **Zone System surface** | Medium (2/6 explicit, but underlies all 6) | BW4 Whalley (Silver Efex zone display), BW5 Boutwell (zone-allocated thinking) | Documentation / agent-prompt-template change. chemigram's `tone_eq` IS a zone-aligned 8-band tool; what's missing is the AGENT'S ability to reason about it as zones. Update the agent prompt template to surface "tone_eq zones map to Adams zones" when working on B&W. Lightweight; no new vocabulary. |
| **Per-zone structure (Silver Efex tri-axis structure)** | Low | BW4 Whalley | Not currently expressible via single `bilat` instance; would need three `bilat` instances at different luminance bands via `apply_per_region` + `mask_luminosity_*`. Composable today; document as workflow pattern, no RFC needed. |
| **Multi-section iSGM workflow** | Low (1/6 signature, but referenced as a methodology) | BW2 Tjintjelaar | RFC-031 / `apply_per_region` is the architectural primitive. Document the iSGM pattern in `vocabulary-patterns.md` as a B&W workflow recipe; no new capability needed. |
| **Long-exposure rendering** | Out of scope | BW2 Tjintjelaar | Capture-time concern. |
| **Split-toning of B&W (sepia / selenium / cyanotype evocation)** | Medium (3/6) | BW1 Tucker, BW4 Whalley, BW5 Boutwell | Composable today via `colorbalancergb` on a desaturated image; ship as L2 looks (`look_bw_split_tone_*` proposed above). No RFC. |
| **"Iterative over weeks" workflow** | Low (workflow philosophy, not capability) | BW1 Tucker, BW3 Thompson | Already supported by snapshot history + branches. Documentation / agent-prompt-template surface for "propose a rest period before the closing pass" — could ship as a `vocabulary-patterns.md` recipe. |

---

## Cross-genre observations

Patterns that hold across the four genres surveyed (Portrait + Landscape + Wedding/Event + B&W) — and what they imply for chemigram's vocabulary direction. Now updated for round 2; new patterns surfaced specifically by Wedding and B&W are flagged as **(R2-new)**.

### Pattern 1 — White balance is universally Step 1

Every one of the **24 photographers across all four genres** establishes white balance / color foundation before any other tonal or aesthetic move. **All four ecosystems represented.** The "WB first" discipline is the closest thing to a universally-shared ordering rule across the entire survey, with one B&W-specific caveat: the WB step in B&W workflows is a *conversion-step input* — wrong WB still produces wrong tonal mapping in the channel-mixed output.

**Implication for chemigram.** The parameterized `temperature` entry (RFC-021 / ADR-077..080 in v1.6.0) is correctly positioned as a foundational primitive. Documentation in `vocabulary-patterns.md` should make explicit that **any L2 look not built on a settled WB is fragile** — a `look_portrait_natural_skin` applied to an image with broken WB will fail to read as natural skin. The composition order in L2 entries should list `temperature` (or accept-existing-WB) as Step 1 unless deliberately stylized.

### Pattern 2 — Sharpening is universally last

22/24 photographers (Marino is the only consistent abstainer; one wedding photographer surveyed defers all sharpening to export-recipe-time which is functionally the same outcome) treat sharpening as the *final* creative step before export. This is the one piece of ordering discipline shared across all four tool ecosystems unmodified — LR, Capture One, darktable, and Silver Efex / Photoshop all sharpen last. **(R2 confirms.)**

**Implication for chemigram.** The agent loop's "compose vocabulary in any order" flexibility should be tempered with a **soft ordering convention** in `vocabulary-patterns.md`: sharpening primitives are tagged as terminal, and L2 looks that include sharpening should be applied last in any sequence. Worth a note in the agent's prompt template (`MANIFEST.toml` per ADR-044) that sharpening is the closing move, not a midstream one.

### Pattern 3 — "Selective beats global" — masking is the discriminator between amateur and pro work

Every pro across all four genres reaches for masking — luminosity masks (Page, Adamus, Whalley, Boutwell), parametric color masks (Woloszynowicz, Nordqvist, Heaton, Stripling), gradient masks (Heaton, Ramelli, O'Leary, Davidson), drawn masks (Adler, Adamus, Thompson 1-3% dodge/burn layers, Tjintjelaar iSGM sections). The amateur pattern that gets explicitly warned-against — by Heaton, Tucker, Marino, Boutwell — is "global slider over-application." **The pro discipline is: identify the region, scope the move.** **(R2 strongly confirms; B&W is especially mask-heavy.)**

**Implication for chemigram.** The masking trilogy shipped in v1.9.0 + RFC-032 named-masks (shipped this round) directly addresses this. The 9 canonical maskdefs cover the parametric variants; RFC-031's `apply_per_region` covers the batched dodge/burn shape; RFC-034's invert flag handles the inverted-subject case. The remaining mask-side gap is **the LLM-vision routing maturity** — Pattern 7 of `llm-vision-for-masks.md` documents the workflow, but the named-mask references for content-aware masks (sky/subject/eye_region) still default to parametric fallback. R2 strongly reinforces that this is the highest-leverage capability work going forward.

### Pattern 4 — "Restraint" recurs as an explicit aesthetic stance

Sean Tucker (Portrait + B&W), Sarah Marino (Landscape), and to a lesser extent Heaton, Gilbertson, Boutwell, Whalley all explicitly *theorize restraint as a discipline* — not just under-applying, but treating the *absence* of an aesthetic move as a stylistic choice. This is rarer in commercial / fashion / dramatic-landscape content (Adler, Page, Adamus, Ramelli, Woloszynowicz, Stripling all push harder). **(R2 confirms with B&W where restraint is especially load-bearing — overdone B&W reads as crunchy HDR.)**

**Implication for chemigram.** L2 looks named for restraint stances (`look_portrait_natural_skin`, `look_landscape_intimate_quiet`, the proposed `look_bw_silver_efex_zone_balanced`) are not "weaker versions" of dramatic looks — they are **defining stylistic positions**, equally as much as `look_landscape_dramatic_moody`. The shipped vocabulary now ships restraint variants alongside dramatic ones; the visual-review checkpoint should specifically validate the restraint variants read as restrained (not flat).

### Pattern 5 — Tool-ecosystem differences cluster around three things

Across the survey, the moves that diverge between LR / Capture One / darktable workflows cluster around exactly three areas:

1. **Skin-tone color science** — Capture One's Skin Tone tool (Woloszynowicz, Adler, Nordqvist) has no first-class LR analog; LR users compose this from HSL + targeted color grading. **Chemigram has neither** as a named primitive — the gap is the same as Portrait Gap 1.
2. **Luminosity-mask compositing** — Photoshop + Lumenzia (Page, Adamus) has no LR or darktable analog at the *named* level; both can express it via parametric luminance masks but neither ships pre-named bands. **Chemigram inherits the same gap** — Landscape Gap 1.
3. **Multi-raw exposure blending** — Photoshop is the de-facto host for this; LR has Merge-to-HDR but it's a different aesthetic; darktable doesn't ship a fusion module. **Chemigram is per-image-as-edited and explicitly out-of-scope** for this — Landscape Gap 2.

The first two are vocabulary directions for chemigram; the third is a deliberate boundary.

### Pattern 6 — Workflow primitives recur but **batched**

Across all four genres, the same workflow shape appears: photographer specifies *N* regions and applies a per-region adjustment. Dodge/burn is the canonical example, but eye-contrast (Portrait), skin-region color smoothing (Portrait + Wedding), selective-color-band lifts (Landscape + B&W), Tjintjelaar's iSGM section-by-section workflow (B&W), and Thompson's 1-3% incremental dodge/burn layers (B&W) all share this shape. **(R2 strongly confirms; B&W especially.)**

**Implication for chemigram.** Closed by RFC-031 (`apply_per_region`, shipped this round) for the single-primitive case. The B&W extraction surfaces a new wrinkle: Thompson's discipline is *low-magnitude high-iteration* (1-3% per layer over weeks), which the agent loop can express as repeated `apply_per_region` calls but at a granularity finer than typical use. Visual review (debt tracker item 5) should validate this works in practice. RFC-036 (mixed-op apply_per_region, deferred) un-defer is reinforced by the B&W finding that the same region often needs both contrast AND color sculpting in one move.

### Pattern 7 — **(R2-new)** Anchor-and-sync as a workflow primitive

**(R2-new — surfaced strongly by Wedding/Event.)** 4/6 wedding photographers ship "edit one image, propagate to N" as a load-bearing technique — the genre is too high-volume for per-image editing. This pattern is *less* present in Portrait (where each portrait is bespoke) and B&W (where each image is iterated individually) but *very* present in Wedding (where 200+ similar-light images need the same edit). Landscape sits between — repeat trips to the same location may yield batches.

**Implication for chemigram.** The propagate-state pattern is a real architectural gap surfaced by Wedding. chemigram's `apply_primitive --stdin` propagates the same primitive call across N images, but doesn't propagate edit STATE (the resulting XMP / vocabulary entries) from a source image to N targets. **High-priority RFC candidate** for v1.11+ work — surfaces a wedding-specific need not seen in earlier genres. Specifically: a `propagate_state(source_image, target_image_ids, scope)` MCP verb where `scope` is one of "all," "exposure-only," "wb-only," etc.

### Pattern 8 — **(R2-new)** Genre-defining named-conversion primitives are missing

**(R2-new — surfaced cleanly by B&W.)** The B&W genre revealed that 6/6 photographers ship their work through a "B&W conversion" move that is fundamentally a *named* operation in their mental model ("convert to black and white"), but chemigram has no first-class B&W conversion primitive. The same probably-true conjecture holds for any genre where conversion-to-genre-aesthetic is itself a named move (e.g., "film emulation" in landscape, "matte fade" in portrait, etc.).

**Implication for chemigram.** Vocabulary should include **named genre-defining conversion primitives** — the highest-recurrence example is `bw_convert` (parameterized; channel weights + filter preset), and it should ship. Lower-recurrence examples (`film_emulation_*`, `matte_fade_*`) are L2-look territory. The R2 finding sharpens the v1.11 vocabulary direction: ship `bw_convert` as a parameterized primitive and a small constellation of B&W-specific L2 looks built on top.

---

## Gap summary (deduped, ranked by cross-genre recurrence — R1+R2)

The single ranked list across all 24 surveyed photographers (Portrait + Landscape + Wedding/Event + B&W). Each gap names what it is, who reaches for it, and what RFC / vocabulary / architectural response it suggests. Ordering is by total photographer recurrence count across the survey, with cross-genre signal weighted higher than within-genre. **Status column** indicates current chemigram response.

| Rank | Gap | Total recurrence | Cross-genre? | Status | Proposed response |
|-|-|-|-|-|-|
| 1 | **Named B&W conversion primitive** | 6/6 B&W — universal in B&W; partial in Wedding (3/6 ship B&W as parallel deliverable) | B&W + Wedding | **Open** | **L2 / parameterized primitive (top priority post-R2).** Ship `bw_convert` as a parameterized primitive with channel weights + filter preset (red / orange / yellow / green / blue / luminosity / saturation-kill). Compose with proposed `look_bw_*` family. Genre-defining absence — chemigram cannot author proper B&W vocabulary without this. |
| 2 | **Batched per-region adjustment workflow** (dodge/burn, eye contrast, skin spots, sky+foreground twin moves, B&W tonal sculpting) | 11/24 across 4 genres — P1 Nace, P3 Tucker, P4 Adler / L3 Page, L4 O'Leary, L5 Adamus, L6 Ramelli / BW2 Tjintjelaar, BW3 Thompson, BW4 Whalley, BW6 Stefano | ✓ All four | ✅ **Shipped (RFC-031)** | `apply_per_region` MCP verb + CLI. R2 confirms cross-genre relevance (B&W especially). Mixed-op extension (RFC-036) deferred until visual-review confirms single-op suffices. |
| 3 | **Named-mask vocabulary on v1.9.0 mask primitives** (luminosity bands, sky, skin-region, subject) | 10/24 — P2 Woloszynowicz, P4 Adler, P6 Nordqvist / L2 Heaton, L3 Page, L5 Adamus / W4 Hunter & Sarah, W5 Davidson / BW2 Tjintjelaar, BW4 Whalley | ✓ All four | ✅ **Shipped (RFC-032)** | 9 canonical maskdefs in expressive-baseline. R2 confirms cross-genre relevance. |
| 4 | **Anchor-and-sync workflow / "edit one image, propagate state to N"** **(R2-new)** | 4/6 wedding-only — W2 Flemming, W4 Hunter & Sarah, W5 Davidson, W6 SLR Lounge. **Wedding-defining.** | Wedding only (high-volume genre signal) | **Open — high priority** | **RFC candidate.** `propagate_state(source_image, target_image_ids, scope)` MCP verb. Surfaced specifically by Wedding/Event's high-volume workflow. Different shape from RFC-031 (per-region) — this is per-image-state propagation. Affects MCP surface; medium architectural work. |
| 5 | **Skin-tone uniformity primitive** | 5/12 across Portrait + Wedding — P2 Woloszynowicz, P4 Adler, P6 Nordqvist / W2 Flemming, W3 Ronald | Portrait + Wedding | ✅ **Shipped (RFC-033 Path B)** | `skin_uniformity` parameterized entry pre-baked with `mask_skin_region`. Visual-review checkpoint pending; wedding-specific validation worth running on mixed-light reception scenes. |
| 6 | **Inverted-mask shorthand on named refs** | Implicit across genres (background-only adjustment use cases) | Cross-genre, lower density | ✅ **Shipped (RFC-034)** | `{kind: named, name: X, invert: true}` parametric inversion. Resolved via deep-copy XOR of `range_filter.invert`. |
| 7 | **Discoverability of sky-detection via LLM-vision** | 5/6 landscape implicit + 0/6 wedding (no sky-specific moves at scale) + N/A B&W | Landscape only | **Partial — documented as Pattern 7** | Pattern 7 of `llm-vision-for-masks.md` documents the workflow; CLI hint surfaced on `vocab show-mask`. Routing through ADR-086 masker is photographer-driven. |
| 8 | **Frequency separation (texture-vs-color band split)** | 2/6 portrait + 1/6 wedding (Hunter & Sarah preset matrix approximates) | Portrait + Wedding minor | ⚠️ **Approximated (`skin_smooth_painterly` cheap-#4)** | Photoshop-native; chemigram approximates via masked clarity reduction. Visual-review checkpoint validates the approximation. True band decomposition deferred. |
| 9 | **Genre-specific named-conversion primitives** **(R2-new)** | Pattern 8 generalization | Cross-genre conjecture | **Open — informed by R2** | Generalize Gap #1 — chemigram should ship named conversion primitives for genre-defining moves (`bw_convert` first; `film_emulation_*` and `matte_fade_*` lower priority). RFC candidate after `bw_convert` lands. |
| 10 | **Background-only adjustment** | 3/6 portrait + 1/6 wedding | Mostly Portrait | ✅ **Shipped** | `look_portrait_background_dim` with `mask_subject + invert: true` (post-RFC-034). |
| 11 | **Within-image WB gradient** **(R2-new)** | 1/6 wedding — W5 Davidson | Wedding only (specific) | **Open — small RFC** | Drawn-gradient masks scope spatially but `temperature` parameter can't gradient-interpolate within a single primitive instance. Either extend `temperature` or compose via `apply_per_region`. |
| 12 | **Zone System surface** **(R2-new)** | 2/6 B&W explicit (Whalley, Boutwell) — underlies all 6 | B&W primarily | **Open — documentation** | chemigram's `tone_eq` IS Adams-zone-aligned; the gap is the AGENT'S ability to reason about it as zones. Update agent prompt template; no new vocabulary. |
| 13 | **Per-zone structure (Silver Efex tri-axis)** **(R2-new)** | 1/6 B&W — Whalley | B&W only | **Open — documentable as workflow** | Three `bilat` instances at different luminance bands via `apply_per_region` + `mask_luminosity_*`. Composable today. |
| 14 | **Multi-raw exposure blending / HDR fusion** | 2/6 landscape — L3 Page, L5 Adamus | Landscape only | **Deliberate boundary** | Multi-raw fusion is capture-time. Documented. |
| 15 | **Imagenomic Portraiture-style controlled smoothing** | 1/6 portrait | Portrait only | **Plugin-specific** | Not addressed. |
| 16 | **Preset-stack as workflow / Smart Adjustments AI batch** **(R2 reframe)** | 1/6 landscape (Ramelli) + 4/6 wedding (R2 reframe) | Landscape + Wedding | **Workflow philosophy** | Wedding's preset-stack pattern is functionally equivalent to chemigram's L2 looks + Phase 2 personal-pack. Smart-Adjustments AI is BYOA out-of-scope. Address via documentation of the L2-looks-as-presets pattern. |
| 17 | **Output sharpening per medium / dual-format export recipes** **(R2 reinforces)** | 2/6 landscape + 3/6 wedding | Landscape + Wedding | **Out of L2 scope** | Export-pipeline concern, not vocabulary. R2 (wedding) reinforces this is a real future RFC for the export pipeline. |
| 18 | **Asset management (rating, culling, sessions)** **(R2-new)** | All 6 wedding photographers | Wedding-defining | **Out of vocabulary scope** | chemigram operates on `image_id` post-culling. Document the boundary. |

### Direction signal from R1+R2 ranking

R2 promoted **Named B&W conversion** to the highest-recurrence gap (6/6 B&W universal). Shipping `bw_convert` parameterized primitive + `look_bw_*` L2 family is the clearest single direction for v1.11.

R2 surfaced **anchor-and-sync** as a new high-priority gap (Gap #4). Wedding-defining; load-bearing for genre adoption. **Candidate RFC for v1.11+.**

R2 reinforced existing R1 work — RFC-031, RFC-032, RFC-033 all confirmed cross-genre relevant. The visual-review checkpoint findings will inform whether RFC-035 (parametric L2 strength) and RFC-036 (mixed-op apply_per_region) need implementation.

R2 added three new patterns (7, 8 — anchor/sync, named-conversion-primitives) and three new low-priority gaps (within-image WB gradient, Zone System surface, per-zone structure) all of which are tractable.

R2 confirmed two deliberate boundaries (multi-raw, asset management) and one out-of-scope (Smart Adjustments AI batch) hold.

**Recommended v1.11 priorities (post-validation):**
1. `bw_convert` parameterized primitive + `look_bw_*` L2 family (Gap #1, top priority)
2. RFC-037 (new) — `propagate_state` MCP verb (Gap #4 — wedding-defining)
3. Genre-specific named-conversion primitives generalized after `bw_convert` ships (Gap #9)
4. RFC-035 / RFC-036 implementation IF visual-review surfaces real need

**Continuing the survey** — Nature/Wildlife + Food/Product remain (round 3). Recommended pairing for round 3: same maximal-contrast principle (Nature/Wildlife = subject-detail + unpredictable conditions; Food/Product = controlled studio + color accuracy). Should surface different gap classes again — likely concentrated around output sharpening (medium-specific), color accuracy (gray-card / chart-driven), and possibly compositing primitives (food retouching often involves multi-image compositing).

---

## Calibration checkpoint (post-R2)

This document is now updated through round 2 (Wedding/Event + B&W). After review, the user decides among:

- **(a) Continue to round 3 (Nature/Wildlife + Food/Product)** in the same shape — completes the 6-genre survey.
- **(b) Pause and act on R2 findings** — ship `bw_convert` + `look_bw_*` family (Gap #1), draft RFC-037 for `propagate_state` (Gap #4), then resume genre research.
- **(c) Visual-review session first** — close out the existing pending validation in `darkroom-session-debt.md` before more research, ensuring the architectural commitments (RFC-031/032/033/034) are sound under real photographer use.
- **(d) Shift focus entirely** — different priorities (e.g., the masker-routing maturity work, or the export-pipeline future).

---

## Sources

### Portrait

- [Phlearn — Professional Retouching Workflow (Aaron Nace)](https://phlearn.com/tutorial/professional-retouching-workflow/)
- [Capture One blog — Beauty retouch workflow (Michael Woloszynowicz)](https://www.captureone.com/blog/portrait-and-beauty-retouching-workflow)
- [Sean Tucker — Photography blog](https://www.seantucker.photography/blog)
- [Fstoppers — Sean Tucker on Authentic Portraits](https://fstoppers.com/bts/photographer-sean-tucker-explains-how-capture-authentic-portraits-people-137174)
- [CreativeLive — Lindsay Adler 3-step retouching process](http://www.creativelive.com/blog/fashion-retouching-tips-technique)
- [Lindsay Adler blog — Q&A fashion editing workflow](https://blog.lindsayadlerphotography.com/qa-fashion-fashion-editing-workflow)
- [Luxagraf — Scott Gilbertson, Developing Photos With Darktable](https://luxagraf.net/essay/craft/darktable-getting-started)
- [Retouching Academy — Jonas Nordqvist, Working On Skin Tones In Capture One](https://retouchingacademy.com/working-on-skin-tones-in-capture-one/)
- [Phase One blog — Jonas Nordqvist, Achieving Perfect Skin Tones](https://blog.phaseone.com/achieving-perfect-skin-tones-using-capture-one/)

### Landscape

- [On Landscape — Sarah Marino Featured Photographer](https://www.onlandscape.co.uk/2019/07/sarah-marino/)
- [CaptureLandscapes — Sarah Marino Photographer of the Month](https://www.capturelandscapes.com/photographer-of-the-month-sarah-marino/)
- [smallscenes.com — Sarah Marino & Ron Coscorrosa Photography](https://smallscenes.com/)
- [Imaging Resource — Thomas Heaton, 5 easy ways to improve landscape photos in Lightroom](https://www.imaging-resource.com/news/2022/06/29/video-5-easy-ways-to-improve-your-landscape-photos-in-adobe-lightroom)
- [thomasheaton.co.uk — Thomas Heaton Photography](https://thomasheaton.co.uk/)
- [Nick Page Photography — Mastering Luminosity Masks](https://www.nickpagephotography.com/masteringluminositymasks)
- [Improve Photography — Nick Page, Advanced Landscape Processing](https://improvephotography.com/44753/learning-advanced-landscape-processing-techniques/)
- [Fstoppers — Mike O'Leary, A Landscape Photographer's Editing Workflow](https://fstoppers.com/landscapes/landscape-photographers-editing-workflow-lightroom-and-photoshop-522537)
- [mikeoleary.photography — Mike O'Leary](https://www.mikeoleary.photography/)
- [500px — A Day In The Life Of Marc Adamus](https://iso.500px.com/a-day-in-the-life-of-landscape-photographer-marc-adamus/)
- [Photo Cascadia — Lexicon of Post-Processing Terms](https://www.photocascadia.com/a-lexicon-of-post-processing-terms-in-landscape-photography-today/)
- [marcadamus.com — Marc Adamus, About the Artist](https://www.marcadamus.com/page/bio/)
- [Shutterbug — Serge Ramelli, Pro's #1 Lightroom Secret](https://www.shutterbug.com/content/landscape-shooters-learn-pro%E2%80%99s-1-lightroom-secret-and-download-his-presets-free-video)
- [Lightroom Killer Tips — Serge Ramelli, AI Retouching Presets](https://lightroomkillertips.com/ai-retouching-presets-lightroom-serge-ramelli/)
- [photoserge.com — Serge Ramelli](https://www.photoserge.com/)

### Wedding / Event

- [Susan Stripling — Lightroom presets for wedding photographers](https://susanstripling.com/blog/lightroom-presets-wedding-photographers/)
- [CreativeLive — 30 Days of Wedding Photography with Susan Stripling](https://www.creativelive.com/class/30-days-wedding-photography-susan-stripling)
- [Capture One Blog — Smart wedding photography workflow (Alexander Flemming)](https://www.captureone.com/blog/capture-one-wedding-photography-workflow)
- [Capture One Blog — How to edit wedding photos faster (Eric Ronald)](https://www.captureone.com/blog/how-to-edit-wedding-photos-faster)
- [Hunter and Sarah — Post Production Secrets Step 5](https://hunterandsarah.com/post-production-secrets-5/)
- [mark-davidson.com — How to edit wedding photos](https://www.mark-davidson.com/blog/how-to-edit-wedding-photos)
- [SLR Lounge — Lightroom workflow tips](https://www.slrlounge.com/lightroom-workflow-tips/)

### B&W

- [Sean Tucker — Photography blog](https://www.seantucker.photography/blog)
- [PetaPixel — Sean Tucker dramatic B&W with curves and HSL](https://petapixel.com/2017/08/09/edit-dramatic-bw-photos-mobile-curves-hsl-sliders/)
- [BWVision — Joel Tjintjelaar](https://bwvision.com/)
- [ProImageEditors — Black and White Fine Art Masking by Joel Tjintjelaar](https://www.proimageeditors.eu/workflow/black-white-fine-art-masking-service-designed-by-joel-tjintjelaar/)
- [Cole Thompson Photography](https://colethompsonphotography.com/)
- [Cole Thompson — Secret to B&W Conversion](https://colethompsonphotography.com/2009/05/23/secret-bw-conversion/)
- [Lenscraft — Robin Whalley, Two Powerful Adjustments in Nik Silver Efex Pro](https://lenscraft.co.uk/photo-editing-tutorials/two-powerful-adjustments-in-nik-silver-efex-pro/)
- [Capture One Blog — Master your B&W conversion with the new Luma Curves (Richard Boutwell)](https://www.captureone.com/blog/master-your-bw-conversion-with-the-new-luma-curves)
- [B&W Mastery — Capture One Pro 8 B&W Workflows (Richard Boutwell)](https://www.bwmastery.com/blog/2015/black-and-white-with-capture-one-pro-8-part-2-workflows)
- [mel365.com — darktable black and white tutorial (Stefano)](https://mel365.com/darktable-black-and-white/)

### Reference (cross-genre / darktable analog)

- [avidandrew.com — The Darktable Scene-Referred Workflow](https://avidandrew.com/darktable-scene-referred-workflow.html) — used as the darktable analog of common moves where no working landscape essayist surfaced in that ecosystem.

---

*Photographer workflows survey · v0.2 · 2026-05-09 · Portrait + Landscape (R1) + Wedding/Event + B&W (R2). Tier 3 operational doc; companion to `capability-survey.md`. Feeds future `vocabulary-patterns.md` updates and `expressive-baseline` L2-layer additions. Round 3 (Nature/Wildlife + Food/Product) pending.*
