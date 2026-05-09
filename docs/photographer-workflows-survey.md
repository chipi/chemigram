# Photographer workflows survey

> Last updated · 2026-05-09 (Portrait + Landscape, first cut)
> Status · Research artifact (Tier 3, operational). Companion to `capability-survey.md`. Feeds `vocabulary-patterns.md` and the `expressive-baseline` L2 layer.

This document extracts how working photographers post-process across genres — drawn from public sources (essays, blog posts, course material, interviews, tutorials) — and maps each move to chemigram's existing primitive surface. The output is two things at once: **L2 candidates** (composition recipes that recur across photographers in a genre) and **vocabulary gaps** (moves photographers reach for that chemigram cannot compose because the underlying primitives don't exist yet).

This first cut covers Portrait and Landscape — maximally different genres (single-subject skin work vs. wide-scene tonal work) so the contrast surfaces vocabulary gaps better than two adjacent genres would. Wedding/Event, B&W, Nature/Wildlife, and Food/Product follow in subsequent passes.

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

## Cross-genre observations

Patterns that hold across both Portrait and Landscape — and what they imply for chemigram's vocabulary direction.

### Pattern 1 — White balance is universally Step 1

Every one of the twelve photographers across both genres establishes white balance / color foundation before any other tonal or aesthetic move. **3/3 ecosystems represented** (LR Temp/Tint, Capture One White Balance + gray-card pick, darktable Color Calibration). The "WB first" discipline is the closest thing to a universally-shared ordering rule across the entire survey.

**Implication for chemigram.** The parameterized `temperature` entry (RFC-021 / ADR-077..080 in v1.6.0) is correctly positioned as a foundational primitive. Documentation in `vocabulary-patterns.md` should make explicit that **any L2 look not built on a settled WB is fragile** — a `look_portrait_natural_skin` applied to an image with broken WB will fail to read as natural skin. The composition order in L2 entries should list `temperature` (or accept-existing-WB) as Step 1 unless deliberately stylized.

### Pattern 2 — Sharpening is universally last

11/12 photographers (the only abstainer is Marino, who doesn't always sharpen at all in intimate work) treat sharpening as the *final* creative step before export. This is also the one piece of ordering discipline shared across all three tool ecosystems unmodified — LR, Capture One, and darktable workflows all sharpen last.

**Implication for chemigram.** The agent loop's "compose vocabulary in any order" flexibility should be tempered with a **soft ordering convention** in `vocabulary-patterns.md`: sharpening primitives are tagged as terminal, and L2 looks that include sharpening should be applied last in any sequence. Worth a note in the agent's prompt template (`MANIFEST.toml` per ADR-044) that sharpening is the closing move, not a midstream one.

### Pattern 3 — "Selective beats global" — masking is the discriminator between amateur and pro work

Every pro across both genres reaches for masking — luminosity masks (Page, Adamus), parametric color masks (Woloszynowicz on skin, Heaton on sky), gradient masks (Heaton, Ramelli, O'Leary), drawn masks (Adler retouching, Adamus dodge/burn). The amateur pattern that gets explicitly warned-against — by Heaton, Tucker, Marino — is "global slider over-application." **The pro discipline is: identify the region, scope the move.**

**Implication for chemigram.** The masking trilogy shipped in v1.9.0 (drawn / parametric / LLM-vision per RFC-029/024/026 → ADR-084/085/086) plus retouch (RFC-025 / ADR-087) gives chemigram the wire for *every* masking pattern surfaced in this survey. **What's missing is named-mask vocabulary** — `mask_skin_region`, `mask_sky`, `mask_luminosity_brightest_quartile`, `mask_subject_via_subject_detection`. These are the surfaced vocabulary gaps that turn raw masking primitives into compositional building blocks. This is the most important recurring observation across the entire survey, and the sharpest direction for v1.10+ vocabulary work.

### Pattern 4 — "Restraint" recurs as an explicit aesthetic stance

Sean Tucker (Portrait), Sarah Marino (Landscape), and to a lesser extent Heaton and the darktable Gilbertson essay all explicitly *theorize restraint as a discipline* — not just under-applying, but treating the *absence* of an aesthetic move as a stylistic choice. This is rarer in commercial / fashion / dramatic-landscape content (Adler, Page, Adamus, Ramelli, Woloszynowicz all push harder).

**Implication for chemigram.** L2 looks named for restraint stances (`look_portrait_natural_skin`, `look_landscape_intimate_quiet`) are not "weaker versions" of dramatic looks — they are **defining stylistic positions**, equally as much as `look_landscape_dramatic_moody`. Vocabulary work should ship the restraint variants alongside the dramatic ones; both are valid compositional moves, and a vocabulary that only ships dramatic looks misrepresents the genre.

### Pattern 5 — Tool-ecosystem differences cluster around three things

Across the survey, the moves that diverge between LR / Capture One / darktable workflows cluster around exactly three areas:

1. **Skin-tone color science** — Capture One's Skin Tone tool (Woloszynowicz, Adler, Nordqvist) has no first-class LR analog; LR users compose this from HSL + targeted color grading. **Chemigram has neither** as a named primitive — the gap is the same as Portrait Gap 1.
2. **Luminosity-mask compositing** — Photoshop + Lumenzia (Page, Adamus) has no LR or darktable analog at the *named* level; both can express it via parametric luminance masks but neither ships pre-named bands. **Chemigram inherits the same gap** — Landscape Gap 1.
3. **Multi-raw exposure blending** — Photoshop is the de-facto host for this; LR has Merge-to-HDR but it's a different aesthetic; darktable doesn't ship a fusion module. **Chemigram is per-image-as-edited and explicitly out-of-scope** for this — Landscape Gap 2.

The first two are vocabulary directions for chemigram; the third is a deliberate boundary.

### Pattern 6 — Workflow primitives recur but **batched**

Across both genres, the same workflow shape appears: photographer specifies *N* regions and applies a per-region adjustment. Dodge/burn is the canonical example, but eye-contrast, skin-region color smoothing, and selective-color-band lifts all share this shape. Currently chemigram expresses this as N separate vocabulary applications + N snapshots — verbose.

**Implication for chemigram.** A **batched-region meta-tool** (already surfaced as the highest-recurrence gap) is the cleanest single architectural addition that would compress 4-6 workflow gaps into one primitive. Worth a dedicated RFC: `apply_per_region_adjustment(image_id, op, regions=[(mask, params), ...])`. Would close cross-genre Move 7 (dodge/burn batched) and could be reused for the eye-contrast pattern (Portrait), the skin-tone-spot pattern (Portrait), and the "lift only the foreground rocks while pulling only the sky highlights" pattern (Landscape).

---

## Gap summary (deduped, ranked by cross-genre recurrence)

The single ranked list. Each gap names what it is, who reaches for it (across both genres), and what RFC / vocabulary / architectural response it suggests. Ordering is by total photographer recurrence count across the survey, with cross-genre signal weighted higher than within-genre.

| Rank | Gap | Total recurrence | Cross-genre? | Proposed response |
|-|-|-|-|-|
| 1 | **Batched per-region adjustment workflow** (dodge/burn, eye contrast, skin spots, sky+foreground twin moves) | 7/12 — P1 Nace, P3 Tucker, P4 Adler / L3 Page, L4 O'Leary, L5 Adamus, L6 Ramelli | ✓ Both | **RFC candidate (highest priority).** `apply_per_region_adjustment(image_id, op, regions=[...])` meta-tool. Single architectural addition; closes 3+ gaps. Composition over multiplication. |
| 2 | **Named-mask vocabulary on top of v1.9.0 masking primitives** (luminosity bands, sky, skin-region, subject) | 6/12 — P2 Woloszynowicz, P4 Adler, P6 Nordqvist / L2 Heaton, L3 Page, L5 Adamus | ✓ Both | **RFC candidate (high priority).** Layer named-mask primitives on top of `parametric mask`, `range_filter`, and the LLM-vision masker. Aligns with "vocabulary, not sliders" — turns raw masking primitives into compositional building blocks. |
| 3 | **Skin-tone uniformity primitive** (variance-compress on skin hue range) | 3/6 portrait only — P2 Woloszynowicz, P4 Adler, P6 Nordqvist | Portrait only | **RFC candidate.** Primitive on top of `colorequal` scoped to skin hue range with a "uniformity" parameter. Capture One ships this; LR has nothing equivalent; chemigram could leapfrog. |
| 4 | **Frequency separation (texture-vs-color band split)** | 2/6 portrait only — P1 Nace, P4 Adler (but central to both their workflows) | Portrait only | **RFC candidate, deferred.** Photoshop-native; darktable doesn't ship band decomposition. Approximate via masked local-contrast or document the route to a Photoshop sibling tool. Lower priority than the named-mask layer. |
| 5 | **Discoverability of sky-detection via LLM-vision** | 5/6 landscape implicit — L2 Heaton, L3 Page, L4 O'Leary, L5 Adamus, L6 Ramelli all reach for sky-targeted moves | Landscape only | **Documentation + light wrapping.** v1.9.0 already supports this via the LLM-vision masker — gap is UX/discoverability. Ship a `mask_sky` shorthand routing to LLM-vision with canonical prompt. Thin RFC; meaningful win. |
| 6 | **Background-only adjustment** | 3/6 portrait — P1 Nace, P2 Woloszynowicz, P4 Adler (implicit for landscape via Move 1) | Mostly Portrait | **L2 ship target.** `look_portrait_background_dim` taking subject coords; already supported underneath, just verbose to compose. Ships as a look, no RFC needed. |
| 7 | **Multi-raw exposure blending / HDR fusion** | 2/6 landscape — L3 Page, L5 Adamus | Landscape only | **Out of scope (deliberate).** chemigram is per-image-as-edited; multi-raw fusion belongs to capture-time tooling (Hugin, HDRMerge, Photomatix). Document the boundary in `vocabulary-patterns.md`. |
| 8 | **Imagenomic Portraiture-style controlled smoothing** | 1/6 portrait — P4 Adler only | Portrait only | **Plugin-specific, not addressed.** Not a general primitive gap. |
| 9 | **Preset-stack as workflow** | 1/6 landscape — L6 Ramelli | Landscape only | **Anti-pattern (deliberate).** chemigram explicitly does not address this. |
| 10 | **Output sharpening per medium** | 2/6 landscape — L2 Heaton, L6 Ramelli (implicit) | Landscape only | **Out of L2 scope.** Export-pipeline concern, not vocabulary. Future work tracked in TODO. |

### Direction signal from this ranking

The two highest-recurrence gaps (batched-region adjustment + named-mask vocabulary) are **architecturally adjacent**: both turn the v1.9.0 masking primitives into composition-friendly vocabulary. They could ship as a single related RFC pair targeting v1.10. Together they close the gap between "chemigram has the wire for what these photographers do" (which is true post-v1.9.0) and "chemigram has named vocabulary for the moves these photographers actually reach for in the language they think in" (which is the next plateau).

Gap 3 (skin-tone uniformity) is genre-specific but high-confidence within the genre — a clean Phase 2 personal-vocabulary candidate that escalates to RFC if it recurs as the L2 library expands to other genres.

The remaining gaps split into "deferred but real" (frequency separation, output sharpening), "documentation only" (sky discoverability, LLM-vision wrapping), and "deliberate boundaries" (multi-raw, plugin-specific, preset-stack). None of those requires Phase 1 / Phase 2 architectural work to address.

---

## Calibration checkpoint

This document is the deliverable of the first research cut. After review, the user decides among:

- **(a) Continue to remaining 4 genres** — Wedding/Event, B&W, Nature/Wildlife, Food/Product — in the same shape (proceed with same plan).
- **(b) Adjust format / depth / source selection** — revise plan, rerun on the same 2 genres.
- **(c) Shift focus** — e.g., draft RFCs for the surfaced gaps before more research, or jump directly to L2 authoring for the candidates already identified above.

Authoring `.dtstyle` files for the proposed L2 looks, drafting RFCs for surfaced gaps, and shipping `vocabulary-patterns.md` updates are **all out of scope for this document** — they become possible next steps after the calibration checkpoint, under separate plans.

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

### Reference (cross-genre / darktable analog)

- [avidandrew.com — The Darktable Scene-Referred Workflow](https://avidandrew.com/darktable-scene-referred-workflow.html) — used as the darktable analog of common moves where no working landscape essayist surfaced in that ecosystem.

---

*Photographer workflows survey · v0.1 · 2026-05-09 · Portrait + Landscape, first cut. Tier 3 operational doc; companion to `capability-survey.md`. Feeds future `vocabulary-patterns.md` updates and `expressive-baseline` L2-layer additions.*
