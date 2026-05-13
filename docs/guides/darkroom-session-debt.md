# Darkroom-session debt — what to validate when you next sit down with darktable

> Last updated · 2026-05-14 (v1.10.0 + post-tag stabilization passes)
> Status · Operational tracker — single source of truth for visual / hands-on validation work that has accumulated and needs a human-in-the-loop session.
> **Doing the work?** See the sequential checkbox-driven [`darkroom-session-checklist.md`](darkroom-session-checklist.md). This doc is the "why" per item; the checklist is the "what to do."
> Companion to `visual-review-survey-l2-looks.md` (which is the *checklist* for one specific batch — this doc is the *running tracker* across all pending validation work, including future batches).

This file lives until the debt is paid down. After each darktable session, update the status of each item; mark closed items as resolved with a date and any follow-up tasks they spawned.

---

## How to use this doc

1. **Before the session** — read through. Pick which items you have time / energy / appropriate raws for. Not everything has to land in one session.
2. **During the session** — for each item, render through chemigram and visually compare against the stated intent. Capture findings inline (this is a working doc, not an aspirational one).
3. **After the session** — for each item touched, mark it ✅ pass / ⚠️ approximate / ❌ fail. Note specific failure modes and what they imply (parameter tune? mask refinement? primitive re-author? RFC re-open?).
4. **Update downstream** — close any RFC / GH issue that depended on this validation.

Recommended cadence: every 2-3 weeks while debt is high; less once it's small. Each session ~2-4 hours.

---

## Open debt — ranked by downstream impact

### 1. `skin_uniformity` (RFC-033 Path B) — visual quality bar

**What:** Verify `skin_uniformity` produces natural skin (not "painted" or "plastic") at strengths -0.3 / -0.6 across representative skin tones and lighting.

**Why:** RFC-033 closes into ADR only after visual sign-off. The RFC explicitly says: "If `colorize` at strengths 0.2-0.5 produces results indistinguishable from natural skin on representative portraits — Path C wins; ship the primitive, close the RFC." We shipped Path B (composition via masked colorequal sat_orange) instead of Path C; the same visual quality bar applies.

**How to validate:**
1. Pick 3-5 portraits with **varied skin tones** (caucasian-through-deep) and **varied lighting** (window light, studio strobe, golden-hour, mixed). At least one with visibly uneven skin.
2. For each: render baseline → render with `skin_uniformity` strength -0.3 → render with strength -0.6 → render with strength -0.8 (failure-mode probe).
3. Side-by-side: does the result read as "more uniform skin" or "painted-on color"? Where does it cross the line?
4. Specifically: does the parametric `mask_skin_region` color_h fallback (orange-red band) leak onto lips / teeth / orange backgrounds at high opacity?

**What to record:**
- Pass/approximate/fail per (skin tone × lighting × strength) cell
- Specific leakage modes
- Recommended strength ceiling (e.g., "ship default at -0.3, document -0.5 as upper bound")
- Whether mask_skin_region needs LLM-vision construction (Pattern 7 of `llm-vision-for-masks.md`)

**Downstream impact:** Closes RFC-033 into ADR. Unblocks the Phase-2 portrait-pack-growth path. If quality fails, fall back to Path A (heavy: full Path C decoder of colorequal — weeks of work).

**Test images needed:** 3-5 portraits as described. Worth having a small benchmark set you re-use across sessions.

---

### 2. `skin_smooth_painterly` (#4-cheap variant) — over-smoothing boundary

**What:** Verify the frequency-separation approximation produces "smoothed but still real" skin at strengths -0.3 / -0.5 / -0.7.

**Why:** This is a Photoshop-native technique we approximated via masked clarity reduction on bilat. The approximation could fail in two directions: (a) at strength -0.5 already produces over-smoothed waxy skin, or (b) even at strength -0.7 doesn't smooth enough to be useful. Both ship the entry but with narrower documented strength range.

**How to validate:**
1. Same 3-5 portraits as item 1, ideally with visible pore texture / micro-detail (not heavily made-up).
2. For each: render with strengths -0.3 / -0.5 / -0.7. Compare close-up at 100% zoom.
3. Specifically: at what strength does it cross from "subtle smoothing" to "waxy / plastic"? Document the boundary.

**What to record:**
- The boundary strength per skin tone (deeper skin tones may tolerate stronger smoothing)
- Compose with `skin_uniformity` test: does the chained skin pass (color + texture) read as a complete portrait skin pass?
- Any visible mask boundary at the skin/non-skin transition

**Downstream impact:** Determines the recommended strength range in the entry's description and (potentially) narrows the manifest's `range` field. Long-term: if quality is good, this is the cheapest viable answer to the Photoshop-frequency-separation gap. If quality is bad, RFC-033 Portrait Gap #4 stays open and routes to a Photoshop sibling tool eventually.

---

### 3. The 14 survey-derived L2 looks — intent vs result match

**What:** Walk the 14 new L2 looks (5 portrait + 9 landscape) against representative raws and verify each one's rendered output reads as its stated intent.

**Why:** Every survey L2 look ships with synthesis correctness verified (XMP loads, applies, history entries appear) but no visual-quality automation. The intent matters: `look_landscape_intimate_quiet` should read **less processed** than the baseline (the Marino restraint signal); `look_landscape_dramatic_moody` should read dramatic without crossing into HDR-crunchy; `look_portrait_natural_skin` should produce a portrait you'd actually leave alone after applying.

**How to validate:** Use the structured checklist in **`docs/guides/visual-review-survey-l2-looks.md`** (companion to this debt tracker). That doc lists per-look pass criteria, required test images, render commands, and what to record.

**What to record:** Per-look pass/approximate/fail. Specifically capture failures where the rendered result fights the named intent — those are the most valuable signals.

**Downstream impact:**
- Failures → file follow-up issues, mark the entry's manifest description with caveats, or re-author via `scripts/generate-l2-looks-survey.py` with adjusted parameter values
- Successes → closes the visual-review checkpoint and is part of the RFC-033-into-ADR sign-off
- If parametric leakage is heavy on the masked looks (`look_landscape_sky_enhance`, `look_landscape_water_silk`, `look_portrait_skin_warm_lift`), that informs Item 4 below

**Test images needed:** 3-5 portraits + 5-7 landscapes covering grand-vista / intimate / golden-hour / blue-hour / haze / dramatic / autumn / water.

---

### 4. Parametric mask leakage — `mask_sky`, `mask_subject`, `mask_eye_region`, `mask_skin_region`, `mask_water_blue_cyan`, `mask_foliage_green`

**What:** Identify which parametric fallbacks leak meaningfully on which scene types, so the LLM-vision escalation pattern (Pattern 7 of `llm-vision-for-masks.md`) becomes a concrete recommendation rather than a generic note.

**Why:** Today the docs say "for higher precision, escalate to LLM-vision construction" — generic. After session findings: "for sunsets / partial clouds / trees-against-sky, mask_sky's parametric fallback fails; here's a worked example of the path-form construction." Concrete recommendations are far more useful for the agent.

**How to validate:** Apply each masked entry across diverse scene types and see what leaks:
- `mask_sky` → grand vista / sunset / overcast / trees-against-bright-sky / partial clouds
- `mask_subject` → portrait / landscape with foreground feature
- `mask_eye_region` → close-up portrait
- `mask_skin_region` → portraits with various non-skin warm tones (orange backgrounds, lipstick, teeth, makeup)
- `mask_water_blue_cyan` → glassy lake / foamy ocean / cyan-tinted backgrounds (like seascape with sky)
- `mask_foliage_green` → spring / summer foliage / autumn (where green is partially gone)

**What to record:**
- Leakage modes per maskdef (specific scenes where the parametric fallback fails)
- For each leakage mode, the recommended LLM-vision construction (path form, prompt extension)
- Whether any maskdef's parametric fallback is so consistently leaky that the default should be tightened (e.g., `mask_sky` luminance threshold raised from 0.55 to 0.65)

**Downstream impact:** Updates `llm-vision-for-masks.md` Pattern 7 with concrete leakage cases. May tighten default values in maskdefs. Could trigger an RFC for "auto-routing to LLM-vision when scene-type metadata signals likely leakage" (speculative).

---

### 5. `apply_per_region` — dodge/burn workflow on a real portrait

**What:** Validate that the batched per-region adjustment workflow (RFC-031) actually reads as one move when applied. Render a typical portrait dodge-and-burn pass (6-8 regions) and verify the result.

**Why:** We have synthesis correctness (multi-instance stacking via multi_priority works in tests) and the wire is there end-to-end. Unknown: whether real photographers' dodge-burn intent translates cleanly when expressed as 6-8 atomic regions, or whether the per-region geometry is too coarse to capture what they actually want.

**How to validate:**
1. Pick a portrait that needs dodge-and-burn (face structure, eye lift, jaw deepening).
2. Construct ~6-8 regions per the recipe in `vocabulary-patterns.md` "Sculpt the face" section.
3. Apply via `chemigram apply-per-region`.
4. Compare against (a) baseline render, (b) the same dodge-burn done in darktable's GUI manually.

**What to record:**
- Does the chemigram result match what you'd produce in darktable?
- Are the region geometries (ellipse) too coarse, or are they fine? If too coarse, what's missing — feathered control, multi-region per-pixel handoff, etc.?
- Performance: is 6-8 regions in one snapshot too dense to reason about in the agent loop? (subjective; surface anyway)

**Downstream impact:** Validates RFC-031's atomic-batch design. Surfaces whether mixed-op batching (deferred per RFC-031, queued as RFC-036) is actually pressing or whether single-op-per-batch is fine in practice. Could surface need for per-region feathering controls beyond what `dt_form` supports.

---

### 6. Named-mask `invert` flag — the `look_portrait_background_dim` recipe

**What:** Once RFC-034 lands (inverted-mask shorthand on named refs), validate that `look_portrait_background_dim` with `mask_subject + invert: true` produces a usable "everything-but-subject" mask.

**Why:** `look_portrait_background_dim` ships without a pre-baked mask because the parametric `mask_subject` fallback (midtone luminance + center-bias) is too coarse to invert reliably. After RFC-034 ships the `invert` flag, this is the test of whether the shorthand actually works in practice or whether the photographer always falls back to a manual ellipse anyway.

**How to validate:**
1. Pick 3 portraits with **clear subject vs. background separation** (single subject, defocused background).
2. Apply `look_portrait_background_dim` with `mask_spec={"kind": "named", "name": "mask_subject", "invert": true}`.
3. Compare to the same recipe with a manually-drawn inverted-ellipse mask.

**What to record:**
- Does the `invert: true` shorthand work for the dominant case (clear subject separation)?
- Where does it fail? (cluttered background, multiple subjects, edge-cases the parametric fallback can't reason about)
- Is the result "good enough for first pass" or "always needs manual override"?

**Downstream impact:** Validates RFC-034's design. If the shorthand is consistently insufficient, the look should keep its caller-supplied-mask discipline; if it works for the dominant case, the manifest can pre-bake `mask_subject + invert: true` as the default and document overrides.

**Status:** Blocked on RFC-034 implementation landing.

---

### 7. `--strength` parameter on L2 looks (RFC-035 / ADR-088 — Path B per-parameter interpolation)

**What:** Verify that strength-scaled L2 looks read perceptually right at strengths 0.3 / 0.5 / 0.7 across the 29 new survey-derived L2 looks.

**Why:** RFC-035 / ADR-088 ships Path B (per-parameter interpolation: `interpolated = identity + strength * (authored - identity)`) on the hypothesis that parameter-space interpolation produces results photographers find usable. The unit + integration tests verify the math is right; the visual validation answers "does strength=0.5 actually feel like half-effect?"

**How to validate:**
1. Pick 3 representative L2 looks across genres: e.g. `look_landscape_dramatic_moody`, `look_portrait_natural_skin`, `look_bw_landscape_dramatic`.
2. For each, on a representative raw: render at strengths 0.0 / 0.3 / 0.5 / 0.7 / 1.0.
3. Side-by-side: does the strength axis read monotonically? Is 0.5 visually close to "halfway between baseline and full-strength"?
4. Specifically: any plugin types where Path B's interpolation produces non-linear-feeling results (color grading is the suspect — interpolating hue is not the same as interpolating chroma)?

**What to record:**
- Per-look monotonicity check
- Any plugin types where the strength feels off (these are candidates for Path C hybrid in a future round)
- Recommended default strengths (e.g., "0.5 reads as a useful 'softer' default for moody looks")

**Downstream impact:** Flips ADR-088 from Draft to Accepted. If Path B fails visually, Path C (hybrid) becomes the next deliberation in a follow-up RFC.

**Test images needed:** 3-5 raws across genres that exercise the looks meaningfully (a stormy landscape for `_dramatic_moody`, a portrait for `_natural_skin`, a B&W-suitable scene for `_landscape_dramatic`).

---

### 8. Mixed-op `apply_per_region` (RFC-036 / ADR-089) — eye-detail and dodge-and-burn-with-sharpening composites

**What:** Verify the new `ops`-array shape produces visually-correct composite moves on a real portrait.

**Why:** RFC-036 / ADR-089 ships per-(op, region) `multi_priority` allocation on the hypothesis that stacked instances of the same op (multiple `exposure` regions) coexist cleanly with different ops (`exposure` + `sharpen` on the same region). Unit tests verify the synthesizer produces correct XMP; visual review answers "does the eye-region look like the photographer's mental model?"

**How to validate:**
1. Pick a portrait with clearly-defined iris + lashes regions.
2. Apply the eye-region recipe: `+exposure(0.3)` + `+sharpen(0.8)` on each iris ellipse, atomically via mixed-op `apply_per_region`.
3. Compare to the same effect achieved via two separate single-op `apply_per_region` calls (per RFC-031 single-op shape). Should be visually identical.
4. Check the snapshot count is 1 (the whole point — composite move = one snapshot).

**What to record:**
- Visual identity of mixed-op vs sequential-single-op
- Snapshot-log entry shape (`apply_per_region_mixed` vs two `apply_per_region`)
- Edge cases — what happens if one op's parameter validation fails atomically (no partial state)

**Downstream impact:** Flips ADR-089 from Draft to Accepted.

**Test images needed:** 1-2 close portraits with visible iris/lashes detail.

---

### 9. `propagate_state` (RFC-037 / ADR-090) — wedding-burst anchor-and-sync

**What:** Verify the LR-Sync-parity discipline works on a real burst (wedding, portrait series, or product variants).

**Why:** RFC-037 / ADR-090 ships inherit-everything-with-framing-bound-exclusion on the hypothesis that this is right-thing-by-default. Unit tests verify atomic-batch + framing-bound exclusion. Visual review answers "do the targets actually look right after sync, or did we miss an exclusion?"

**How to validate:**
1. Pick 5-10 images from a real burst (wedding lighting group, product color variants, or landscape series with consistent light).
2. Edit one anchor with the full chemigram pipeline: WB, exposure, sigmoid, color grading, optionally a parametric range mask.
3. Run `chemigram propagate-state <anchor> --to <id1> --to <id2> ...`
4. Render each target. Visually inspect: does the look propagate? Are there obvious framing-bound issues (crop / retouch leaking through)?
5. Try a target intentionally outside the burst (different lighting / different scene). Does it look bad? (Should — propagating cross-genre is misuse but should fail gracefully not catastrophically.)

**What to record:**
- Per-target visual quality on the in-burst targets
- Edge cases — what happens with mixed-camera targets (modversion-drift hard-reject expected)
- Whether the framing-bound exclusion list is right (do we need to add anything? remove anything?)
- Any obvious gaps (e.g., parametric range masks should propagate but if they don't, that's a real bug)

**Downstream impact:** Flips ADR-090 from Draft to Accepted. May surface refinements to FRAMING_BOUND_OPS (the v1.10.0 single-source-of-truth registry per Gap D closure).

**Test images needed:** A burst of 5-10 from a real shoot. Wedding lighting group is canonical; product variants and landscape series also work.

---

### 10. v1.10.0 photographer-survey L2 looks — intent-vs-result match (29 looks)

**What:** Render each of the 29 new L2 looks at full strength on a representative raw for its genre. Verify the look matches the photographer-survey-cited intent.

**Why:** Each look ships against a survey citation (which photographer reaches for this move, in which genre, for what intent). Visual sign-off confirms the look's authored parameters actually produce the cited intent.

**Looks to validate:**

| Genre | Looks | Source raw recommendation |
|-|-|-|
| B&W (5) | `look_bw_classic_neutral`, `_high_contrast_chiaroscuro`, `_landscape_dramatic`, `_silver_efex_zone_balanced`, `_split_tone_warm_shadows` | A landscape scene with both highlight + shadow detail |
| Landscape (8) | `look_landscape_atmospheric_haze`, `_autumn_pop`, `_blue_hour_cool`, `_dramatic_moody`, `_golden_hour`, `_grand_vista`, `_intimate_quiet`, `_sky_enhance`, `_water_silk` | One per scene type per the "Landscapes" inventory above |
| Portrait (5) | `look_portrait_background_dim`, `_editorial`, `_natural_skin`, `_skin_warm_lift`, `_split_tone_moody` | One per "Portraits" inventory entry |
| Wildlife (5) | `look_wildlife_background_blur`, `_eye_lift`, `_high_iso_recovery`, `_natural_warm`, `_subject_sharpen` | A real wildlife frame with subject + busy background |
| Food/Product (5) | `look_food_appetizing_warm`, `_green_natural`, `_orange_pop`, `_texture_subtle`, `look_product_packshot_clean` | A food shot + a clean-product shot |

**How to validate (per look):**
1. Render baseline → render with the look at strength 1.0 → render with the look at strength 0.5 (validates RFC-035 in passing).
2. Compare to the survey citation: does the result match the intent the photographer was reaching for?
3. Note any looks where the authored parameters need a tune (e.g., "look_landscape_dramatic_moody is too aggressive — sigmoid 1.7 → 1.5").

**What to record:**
- Per-look pass / approximate / fail
- Tunable adjustments that surface from real raws (these become a v1.10.1 vocabulary tune-up commit)
- Any look that doesn't survive at all (re-author from a different survey citation)

**Downstream impact:** Confirms or tunes the 29 new entries' default values. May surface vocabulary gaps (a survey-cited intent that the chosen primitive composition doesn't actually produce).

**Test images needed:** 1-3 raws per genre (the validation set above is the reusable benchmark).

---

### 11. `bw_convert` v2 (colorequal-based, 8 Adams-school axes)

**What:** Verify the new bw_convert mechanic produces useful B&W with photographer-controlled per-color-band luminance. Specifically test the Adams-school filter sims: red filter (bright_red+0.3 / bright_blue-0.2) lightens skin and red flowers, darkens skies; green filter (bright_green+0.3) lightens foliage; etc.

**Why:** v1.10.0 redesigned bw_convert from channelmixerrgb-mv3 (3 hard-coded grey-weight variants) to colorequal-based (8 sat=-1 + 8 bright_X axes). Lab-grade tests verify chroma-zero (the base mechanic). Visual validation answers "does the per-band filter sim feel like a Silver Efex / Photoshop Channel Mixer (Monochrome) workflow?"

**How to validate:**
1. Pick a color landscape scene with sky + foliage + a red element (flower, skin, flag).
2. Render: baseline → bw_convert (defaults, all bright_X = 0) → bw_convert with red-filter sim (bright_red+0.3, bright_blue-0.2) → bw_convert with green-filter sim (bright_green+0.3).
3. Verify each filter sim affects the right tones in the expected direction.
4. Side-by-side with bw_sky_drama and bw_foliage (the v1.4.0 channelmixerrgb variants for comparison).

**What to record:**
- Filter-sim correctness per axis
- Whether 8 bright_X axes is the right surface or whether photographers want a smaller pre-baked recipe set (then we author L2 looks on top)
- Recommended bright_X magnitudes for the canonical filters (red / orange / yellow / green / blue)

**Downstream impact:** Confirms the Adams-school filter mental model translates to colorequal mechanics. If filter sims don't read right, the bright_X axis is misnamed or the magnitudes need tuning.

**Test images needed:** A landscape with sky + foliage + a saturated red element, and a portrait (skin tone × red filter is a classic test).

---

## Closed / resolved debt

(Empty — populate as items resolve.)

---

## Required test-image inventory

Maintain a small, stable benchmark set so findings are comparable across sessions. Recommended:

**Portraits (5):**
- `portrait_caucasian_window_natural` — single subject, soft window light, even skin
- `portrait_deep_studio_strobe` — single subject, hard studio strobe, deep skin tones
- `portrait_caucasian_makeup_editorial` — full editorial makeup (lipstick, eye makeup) — leakage probe
- `portrait_uneven_skin_unedited` — visibly uneven skin (red patches, yellow undertones) — uniformity probe
- `portrait_environmental_mixed_light` — environmental portrait with cluttered background — invert-mask probe

**Landscapes (7):**
- `landscape_grand_vista_clean_sky` — wide vista, clean sky, distinct foreground
- `landscape_intimate_forest_interior` — small-scene, no horizon — restraint probe
- `landscape_golden_hour_warm` — sunset / sunrise scene
- `landscape_blue_hour_cool` — twilight / pre-dawn
- `landscape_atmospheric_fog` — moody fog / haze
- `landscape_autumn_foliage` — orange/red autumn colors plus blue sky — autumn-pop probe
- `landscape_water_long_exposure` — silky water — water-silk probe

Image filenames here are placeholders; substitute your actual raws. Worth keeping a `~/Pictures/Chemigram/_validation_set/` directory dedicated to this.

---

## Decision-checkpoints downstream of this debt

These decisions are blocked until specific debt items resolve:

- **Closing RFC-033 into ADR** → blocked on items 1, 2, 3 (the skin primitives + the 14 L2 looks)
- **Updating `llm-vision-for-masks.md` Pattern 7 with concrete leakage cases** → blocked on item 4
- **RFC-031 mixed-op batching un-defer (RFC-036 / ADR-089)** → ✅ shipped 2026-05-10; ADR-089 flips Draft → Accepted on **item 8**
- **RFC-034 closing into ADR** → blocked on item 6 (validating the invert-flag shorthand actually works)
- **RFC-035 closing into ADR-088** → ✅ ADR drafted; flips Draft → Accepted on **item 7** (parametric L2 strength visual quality bar)
- **RFC-037 closing into ADR-090** → ✅ ADR drafted; flips Draft → Accepted on **item 9** (propagate_state on a real burst)
- **Tuning the 29 v1.10.0 L2 looks** → blocked on **item 10** (intent-vs-result match per genre)
- **Locking the bw_convert v2 mechanic** → blocked on **item 11** (Adams-school filter sims read right)
- **Continuing to remaining 4 genres** (Wedding/Event, B&W, Nature/Wildlife, Food/Product) of the photographer-workflows survey → ✅ all 6 genres shipped in v1.10.0

---

## See also

- `docs/guides/visual-review-survey-l2-looks.md` — structured checklist for items 1, 2, 3
- `docs/guides/llm-vision-for-masks.md` Pattern 7 — escalation workflow for content-aware named masks
- `docs/photographer-workflows-survey.md` — source survey that informed all this work
- `docs/rfc/RFC-033-skin-tone-uniformity.md` — RFC blocked on this checkpoint
