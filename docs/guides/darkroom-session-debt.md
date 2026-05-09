# Darkroom-session debt — what to validate when you next sit down with darktable

> Last updated · 2026-05-09
> Status · Operational tracker — single source of truth for visual / hands-on validation work that has accumulated and needs a human-in-the-loop session.
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
- **RFC-031 mixed-op batching un-defer (RFC-036)** → informed by item 5 findings (whether single-op-per-batch is fine in practice)
- **RFC-034 closing into ADR** → blocked on item 6 (validating the invert-flag shorthand actually works)
- **Continuing to remaining 4 genres** (Wedding/Event, B&W, Nature/Wildlife, Food/Product) of the photographer-workflows survey → not blocked but informed by how Portrait + Landscape validation went

---

## See also

- `docs/guides/visual-review-survey-l2-looks.md` — structured checklist for items 1, 2, 3
- `docs/guides/llm-vision-for-masks.md` Pattern 7 — escalation workflow for content-aware named masks
- `docs/photographer-workflows-survey.md` — source survey that informed all this work
- `docs/rfc/RFC-033-skin-tone-uniformity.md` — RFC blocked on this checkpoint
