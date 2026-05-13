# Darkroom-session checklist

> Sequential, checkbox-driven version of [`darkroom-session-debt.md`](darkroom-session-debt.md).
> Use this when you're sitting down with darktable + real raws. Each item:
> goal → steps → what to record → pass/fail bar → what gets unblocked.
> The full rationale per item is in `darkroom-session-debt.md`; this is the
> "what to actually do."

Estimated session length: **4–6 hours total**. Realistically split across
2 sessions. You can do items in any order, but item-numbering matches
`darkroom-session-debt.md` so cross-references work both ways.

The 11 items split into three batches by downstream impact:

| Batch | Items | What flips on success |
|-|-|-|
| **A** — v1.10.0 ADRs | 7, 8, 9 | ADR-088 / 089 / 090 Draft → Accepted |
| **B** — v1.10.0 vocabulary | 10, 11 | 29 L2 looks + bw_convert v2 marked validated |
| **C** — pre-v1.10 debt | 1, 2, 3, 4, 5, 6 | RFC-033 / RFC-034 close; mask-doc updates |

If you're tight on time, **do Batch A first** — it unblocks the three
Draft ADRs that are blocking the v1.10.0 architectural commitments from
landing as Accepted.

---

## Pre-session setup (do once)

- [ ] **darktable installed and working** (v5.x; `brew install --cask darktable` on macOS Apple Silicon)
- [ ] **chemigram-cli on `$PATH`** — verify with `chemigram status`
- [ ] **darktable configdir bootstrapped** — `~/chemigram-phase0/dt-config/` exists (or set `CHEMIGRAM_DT_CONFIGDIR`)
- [ ] **Test-image directory created** — `~/Pictures/Chemigram/_validation_set/` for your reusable benchmark raws
- [ ] **Notebook / scratch file open** — for findings. A markdown file works; you'll paste from it back into `darkroom-session-debt.md`.

## Test-image inventory (gather once; reuse across sessions)

Per `darkroom-session-debt.md` § "Required test-image inventory". Mark
each as you collect:

**Portraits (5)** — ingest each as a separate `image_id`:

- [ ] `portrait_caucasian_window_natural` — single subject, soft window light, even skin
- [ ] `portrait_deep_studio_strobe` — single subject, hard studio strobe, deep skin tones
- [ ] `portrait_caucasian_makeup_editorial` — full editorial makeup — leakage probe
- [ ] `portrait_uneven_skin_unedited` — visibly uneven skin — uniformity probe
- [ ] `portrait_environmental_mixed_light` — environmental, cluttered background

**Landscapes (7):**

- [ ] `landscape_grand_vista_clean_sky`
- [ ] `landscape_intimate_forest_interior`
- [ ] `landscape_golden_hour_warm`
- [ ] `landscape_blue_hour_cool`
- [ ] `landscape_atmospheric_fog`
- [ ] `landscape_autumn_foliage`
- [ ] `landscape_water_long_exposure`

**Wildlife (1–2):**

- [ ] One close portrait with visible iris + lashes detail (for eye-region work)
- [ ] One subject + busy-background frame (for subject-sharpen / background-blur)

**Burst (1):**

- [ ] 5–10 images from a real shoot in consistent light (wedding lighting group, product variants, or landscape series). The anchor + targets for `propagate_state` validation.

**Ingest them all:**

```bash
for raw in ~/Pictures/_validation_raws/*.NEF; do chemigram ingest "$raw"; done
```

---

## Batch A — flip ADR-088 / 089 / 090 from Draft to Accepted

These three RFCs ship with the architectural decisions locked but the
ADRs in Draft until you confirm the implementation behaves visually right
on real raws. Each item below is the validation gate.

### Item 7 — `--strength` parameter on L2 looks (RFC-035 / ADR-088)

**Goal:** Verify that strength-scaled L2 looks read perceptually right at strengths 0.3 / 0.5 / 0.7. Path B Math: `interpolated = identity + strength * (authored - identity)`. The unit tests verify the math; you verify it *feels* right.

**Steps:**

- [ ] Pick 3 representative looks across genres (suggested: `look_landscape_dramatic_moody`, `look_portrait_natural_skin`, `look_bw_landscape_dramatic`)
- [ ] For each look × test raw matching the genre:
  - [ ] Render baseline (`chemigram render-preview <id>`)
  - [ ] Render at strength 0.0 (`chemigram apply-primitive <id> --entry <look> --strength 0.0`)
  - [ ] Render at 0.3, 0.5, 0.7, 1.0
  - [ ] Open all 6 (baseline + 5 strengths) side-by-side
- [ ] For each look, judge: does strength axis read monotonically? Is 0.5 visibly halfway?

**What to record (per look):**

- [ ] Monotonicity verdict (✅ smooth / ⚠️ jumps at certain levels / ❌ non-monotonic)
- [ ] "Half-effect at 0.5?" verdict (✅ yes / ⚠️ closer to 0.3 or 0.7 / ❌ no perceptual gradient)
- [ ] Any plugin types where Path B feels off (these become candidates for Path C hybrid in a future round)

**Pass bar:** At least 2 of 3 looks show monotonic, perceptually-meaningful strength axis.

**Unblocks:** ADR-088 flips Draft → Accepted.

---

### Item 8 — Mixed-op `apply_per_region` (RFC-036 / ADR-089)

**Goal:** Verify composite moves (eye-region lift + sharpen) land as one visually-correct snapshot.

**Steps:**

- [ ] Pick a portrait with clearly-defined iris + lashes regions
- [ ] Render the mixed-op recipe:

```bash
chemigram apply-per-region <id> --regions '[
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.45,"center_y":0.4,"radius_x":0.04,"radius_y":0.05,"border":0.02}},
   "ops":[{"primitive_name":"exposure","parameter_values":{"ev":0.3}},
          {"primitive_name":"sharpen","parameter_values":{"amount":0.8}}]},
  {"mask_spec":{"dt_form":"ellipse","dt_params":{"center_x":0.55,"center_y":0.4,"radius_x":0.04,"radius_y":0.05,"border":0.02}},
   "ops":[{"primitive_name":"exposure","parameter_values":{"ev":0.3}},
          {"primitive_name":"sharpen","parameter_values":{"amount":0.8}}]}
]'
```

- [ ] Now do the same thing as two separate single-op `apply-per-region` calls
- [ ] Render-preview both results; compare side-by-side
- [ ] Verify `log <id>` shows 1 entry for the mixed-op version vs 2 for the sequential version

**What to record:**

- [ ] Visual identity check (mixed-op should be indistinguishable from sequential)
- [ ] Snapshot count (1 vs 2)
- [ ] Op-log entry shape (`apply_per_region_mixed` event vs two `apply_per_region` events)
- [ ] Any edge cases that surfaced (atomic failure mode, multi_priority collision)

**Pass bar:** Renders are visually identical; mixed-op produces exactly 1 snapshot.

**Unblocks:** ADR-089 flips Draft → Accepted.

---

### Item 9 — `propagate_state` (RFC-037 / ADR-090) — wedding-burst anchor-and-sync

**Goal:** Verify the LR-Sync-parity discipline works on a real burst.

**Steps:**

- [ ] Pick 5–10 images from a real burst (wedding lighting group / product variants / landscape series)
- [ ] Edit the anchor with a full chemigram pipeline: WB + exposure + sigmoid + color grading + optionally a parametric range mask
- [ ] Snapshot the anchor (`chemigram tag <anchor_id> v1`)
- [ ] Propagate:

```bash
chemigram propagate-state <anchor_id> \
    --to <id1> --to <id2> --to <id3> --to <id4> \
    --label "darkroom-validation-2026-05-14"
```

- [ ] Render each target (`chemigram render-preview <target_id>`)
- [ ] Visually inspect each: does the look propagate sensibly?
- [ ] Run one with `--include-per-image` flag if you have a tripod-fixed series (or skip if not applicable)
- [ ] **Edge-case test:** try propagating to a target intentionally outside the burst (different lighting / different scene). Should look bad but not crash.

**What to record:**

- [ ] Per-target pass / approximate / fail (5–10 rows)
- [ ] Whether the framing-bound exclusion list is right (any ops that should have propagated but didn't? any that shouldn't have but did?)
- [ ] Cross-camera-mix edge-case behavior (modversion-drift hard-reject expected)
- [ ] Parametric range masks (color-range / luminance-range) — did they propagate? (Should.)

**Pass bar:** ≥80% of in-burst targets render visibly close to the anchor's look (the remaining 20% revealing differences in light / framing across the burst is expected).

**Unblocks:** ADR-090 flips Draft → Accepted. May surface refinements to `FRAMING_BOUND_OPS` registry.

---

## Batch B — v1.10.0 vocabulary validation

### Item 10 — v1.10.0 photographer-survey L2 looks (29 looks total)

**Goal:** Render each new L2 look at full strength on a representative raw. Verify the look matches its photographer-survey-cited intent.

**Steps (per genre — pick the genres that match your raw inventory):**

**B&W (5 looks)** — use a landscape with highlight + shadow detail:

- [ ] `look_bw_classic_neutral` — Adams baseline; does it read as "neutral B&W with classic tone curve"?
- [ ] `look_bw_high_contrast_chiaroscuro` — Page-style; do shadows go deep, highlights stay bright?
- [ ] `look_bw_landscape_dramatic` — red-filter sim; does the sky darken + land lighten?
- [ ] `look_bw_silver_efex_zone_balanced` — does the tonal distribution feel zone-balanced (Adams XI)?
- [ ] `look_bw_split_tone_warm_shadows` — selenium-print look; warm shadows visible?

**Landscape (9 looks):**

- [ ] `look_landscape_atmospheric_haze`
- [ ] `look_landscape_autumn_pop`
- [ ] `look_landscape_blue_hour_cool`
- [ ] `look_landscape_dramatic_moody`
- [ ] `look_landscape_golden_hour`
- [ ] `look_landscape_grand_vista`
- [ ] `look_landscape_intimate_quiet`
- [ ] `look_landscape_sky_enhance` (uses `mask_sky` — also tests Item 4)
- [ ] `look_landscape_water_silk`

**Portrait (5):**

- [ ] `look_portrait_background_dim`
- [ ] `look_portrait_editorial`
- [ ] `look_portrait_natural_skin`
- [ ] `look_portrait_skin_warm_lift` (uses `mask_skin_region`)
- [ ] `look_portrait_split_tone_moody`

**Wildlife (5):**

- [ ] `look_wildlife_background_blur` (uses `mask_subject` inverted)
- [ ] `look_wildlife_eye_lift` (uses `mask_eye_region` — also tests Item 4)
- [ ] `look_wildlife_high_iso_recovery`
- [ ] `look_wildlife_natural_warm`
- [ ] `look_wildlife_subject_sharpen` (uses `mask_subject`)

**Food / Product (5):**

- [ ] `look_food_appetizing_warm`
- [ ] `look_food_green_natural`
- [ ] `look_food_orange_pop`
- [ ] `look_food_texture_subtle`
- [ ] `look_product_packshot_clean`

For each look, render: baseline → strength 1.0 → strength 0.5 (in passing this also strengthens Item 7 evidence).

**What to record (per look):**

- [ ] Pass / approximate / fail
- [ ] Tunable adjustment if needed (e.g., "look_landscape_dramatic_moody is too aggressive — sigmoid 1.7 should be 1.5"). These accumulate as a v1.10.1 vocabulary tune-up commit.
- [ ] Any look that doesn't survive at all (re-author needed)

**Pass bar:** ≥80% pass; failures get tunable adjustments recorded; <5% need full re-author.

**Unblocks:** Confirms the 29 new entries' default values are sound. Surfaces tune-ups for a follow-up commit.

---

### Item 11 — `bw_convert` v2 (colorequal-based, 8 Adams-school axes)

**Goal:** Verify the new bw_convert mechanic produces useful B&W with photographer-controlled per-color-band luminance.

**Steps:**

- [ ] Pick a color landscape with sky + foliage + a red element (flower / skin / flag)
- [ ] Render baseline (color)
- [ ] Render `bw_convert` at defaults (all `bright_X = 0`) — pure grayscale
- [ ] Render with **red-filter sim**: `--param bright_red=0.3 --param bright_blue=-0.2`
- [ ] Render with **green-filter sim**: `--param bright_green=0.3`
- [ ] Render with **yellow-filter sim** (subject lightening): `--param bright_yellow=0.3 --param bright_red=0.2`
- [ ] For each filter sim: verify the right tones move in the expected direction
- [ ] Side-by-side with the v1.4.0 `bw_sky_drama` and `bw_foliage` (channelmixerrgb variants) for comparison

**What to record:**

- [ ] Filter-sim correctness per axis (red lightens skin/red flowers; blue darkens skies; green lightens foliage)
- [ ] Whether the 8-axis surface is the right ergonomic — or whether photographers want a smaller pre-baked recipe set
- [ ] Recommended `bright_X` magnitudes for canonical filters

**Pass bar:** All 3 filter sims (red / green / yellow) produce visibly-correct directional effects.

**Unblocks:** Confirms the Adams-school filter mental model translates correctly to colorequal mechanics.

---

## Batch C — pre-v1.10 outstanding debt

These items have been pending since RFC-033 (skin work) shipped its Path B
impl. They're not blocking v1.10.0 ADRs; they're blocking RFC-033 / RFC-034
closures and a few mask-leakage doc updates.

### Item 1 — `skin_uniformity` (RFC-033 Path B) visual quality bar

**Goal:** Verify natural skin (not "painted" or "plastic") at strengths -0.3 / -0.6 across representative skin tones and lighting.

**Steps:**

- [ ] Pick 3–5 portraits with varied skin tones + lighting (use the 5 portraits from the inventory)
- [ ] For each: baseline → `skin_uniformity --param sat_orange=-0.3` → `--param sat_orange=-0.6` → `-0.8` (failure-mode probe)
- [ ] Specifically check: does `mask_skin_region` color_h fallback leak onto lips / teeth / orange backgrounds at high opacity?

**What to record:**

- [ ] Pass / approximate / fail per (skin tone × lighting × strength)
- [ ] Specific leakage modes (lips, teeth, orange background, etc.)
- [ ] Recommended strength ceiling (e.g., "ship default at -0.3, document -0.5 as upper bound")
- [ ] Whether `mask_skin_region` needs LLM-vision construction (Pattern 7) for difficult cases

**Pass bar:** Default -0.3 produces natural smoothing; -0.5 is the documented upper bound; ≥-0.6 acceptable failure modes.

**Unblocks:** RFC-033 closes into ADR. Phase-2 portrait-pack-growth path unblocks.

---

### Item 2 — `skin_smooth_painterly` over-smoothing boundary

**Goal:** Find the strength where smoothing crosses from "subtle" to "waxy/plastic" per skin tone.

**Steps:**

- [ ] Same 3–5 portraits (close-up at 100% zoom for texture)
- [ ] For each: render at `--param clarity_strength=-0.3` / `-0.5` / `-0.7`
- [ ] Identify the crossover strength per skin tone

**What to record:**

- [ ] The boundary strength per skin tone (deeper tones may tolerate stronger smoothing)
- [ ] Whether `mask_skin_region` precision is adequate or if it needs LLM-vision construction
- [ ] Recommended default strength

---

### Item 3 — The 14 earlier survey-derived L2 looks (intent vs result)

**Goal:** Same as Item 10 but for the v1.9.0-era cinematic + decade looks (look_cinematic_teal_orange / look_70s_film / look_90s_grain / look_2000s_digital / look_film_kodachrome / look_film_portra / look_high_key_portrait / look_low_key_portrait / look_moody_dramatic / etc).

Largely overlaps with Item 10's process — do it on the same pass if you have time. Per-look pass/approximate/fail. Recommended only if you're already validating L2 looks; otherwise defer.

---

### Item 4 — Parametric mask leakage (named maskdefs)

**Goal:** Verify each named maskdef (RFC-032) produces the expected region on a real raw, not a synthetic chart.

The 9 named maskdefs that ship in expressive-baseline:

- [ ] `mask_sky` — apply `colorbalancergb hue_highlights` through it on a landscape; verify sky region only
- [ ] `mask_subject` — apply `exposure +0.3` through it on a portrait + wildlife; verify subject only
- [ ] `mask_eye_region` — apply `exposure +0.3 + sharpen` through it on a portrait/wildlife close-up; verify eye region only
- [ ] `mask_skin_region` — apply `colorequal sat_orange -0.3` through it; verify skin region only (not orange background)
- [ ] `mask_water_blue_cyan` — apply through it on a landscape with water; verify water only
- [ ] `mask_foliage_green` — apply through it on a landscape with foliage; verify foliage only
- [ ] `mask_luminosity_brightest_quartile` — apply `exposure +0.3` through it; verify only bright pixels affected
- [ ] `mask_luminosity_darkest_quartile` — same, dark pixels
- [ ] `mask_luminosity_midtones` — same, midtone band

**What to record:**

- [ ] Per-maskdef precision (✅ tight / ⚠️ approximate / ❌ broad leakage)
- [ ] Specific leakage cases (e.g., "mask_sky leaks onto bright clouds with red tones at sunset")
- [ ] Whether the maskdef warrants LLM-vision-construction-recommended in the maskdef's documentation

**Unblocks:** Updates to `docs/guides/llm-vision-for-masks.md` Pattern 7 with concrete leakage cases.

---

### Item 5 — `apply_per_region` dodge/burn on a real portrait

**Goal:** Verify the v1.9.0 single-op `apply_per_region` produces a visually-correct face-sculpting move on a real portrait.

- [ ] Pick a portrait with reasonably good baseline tone
- [ ] Identify 6 dodge regions (cheekbone left, cheekbone right, nose bridge, brow ridge, chin, forehead) + 4 burn regions (under-jaw, eye sockets ×2, neck shadow)
- [ ] Apply via single-op `apply_per_region exposure` with per-region ev values
- [ ] Compare to baseline

**What to record:**

- [ ] Does the face read "sculpted"?
- [ ] Any region that needed parameter tweaking (e.g., "cheekbone +0.3 was too much, 0.2 better")
- [ ] Whether 32-region cap is generous enough (likely yes)

**Unblocks:** Confirms RFC-031 single-op shape is usable in practice; informs the per-region typical-parameter recipe for the cookbook.

---

### Item 6 — Named-mask `invert` flag

**Goal:** Verify the `invert` flag on named-mask references works (RFC-034 — `look_portrait_background_dim` uses `mask_subject` inverted).

- [ ] Apply `look_portrait_background_dim` on a portrait
- [ ] Verify the dimming hits the BACKGROUND (the inverse of `mask_subject`)
- [ ] Also try a manual invert: `--mask-spec '{"kind":"named","name":"mask_subject","invert":true}'`

**What to record:**

- [ ] Did the invert work?
- [ ] Any edge cases (e.g., does invert preserve feather direction)

**Unblocks:** RFC-034 closes into ADR.

---

## Wrap-up (after each session, even partial)

- [ ] **Update `docs/guides/darkroom-session-debt.md`** for each item touched: mark ✅ pass / ⚠️ approximate / ❌ fail with the date + a paragraph of findings
- [ ] **File follow-up issues** for failures or tunable adjustments — milestone v1.11.0 unless urgent
- [ ] **For each ADR that flipped Draft → Accepted:** edit `docs/adr/ADR-NNN-*.md` status line from `Draft (impl shipped; flips to Accepted on darkroom validation)` to `Accepted`. Same in `docs/adr/index.md` + `docs/adr/TA.md` § map.
- [ ] **For RFC-033 or RFC-034 closure (if Batch C done):** flip RFC status to `Decided`, write closing ADR, update RFC + ADR indexes
- [ ] **If vocabulary tune-ups surfaced (Item 10/11):** stage them as a follow-up `feat(vocab): v1.10.1 tune-ups from darkroom session` commit
- [ ] **Optional — re-run visual proofs** for any tuned entries: `uv run scripts/generate-visual-proofs.py`

## What flips when (at-a-glance)

| Doing item(s) | Flips |
|-|-|
| 7 | ADR-088 Draft → Accepted |
| 8 | ADR-089 Draft → Accepted |
| 9 | ADR-090 Draft → Accepted |
| 7 + 8 + 9 | All three v1.10.0 architectural ADRs land as Accepted; capability-survey + IMPLEMENTATION can be updated |
| 10 | 29 L2 looks validated; tune-ups surface for v1.10.1 |
| 11 | bw_convert v2 mechanic validated |
| 1 | RFC-033 closes into ADR (skin uniformity) |
| 2 | Documents over-smoothing boundary (no RFC) |
| 4 | Surfaces leakage cases for `llm-vision-for-masks.md` Pattern 7 docs update |
| 6 | RFC-034 closes into ADR (invert flag) |

## After the full session

The post-darkroom commit shape:

```
docs(darkroom): post-session findings + ADR statuses flipped

ADR-088: Draft → Accepted (Item 7 validation: strength axis reads
  monotonically across landscape_dramatic_moody / portrait_natural_skin /
  bw_landscape_dramatic; 0.5 perceptually halfway as designed)
ADR-089: Draft → Accepted (Item 8: mixed-op produces visually identical
  result to sequential single-op; 1 snapshot vs 2)
ADR-090: Draft → Accepted (Item 9: 8/10 wedding-burst targets land
  within visual tolerance of anchor)

Findings recorded in darkroom-session-debt.md per item.
Vocabulary tune-ups for {N} L2 looks staged as follow-up commit.
RFC-033 closes into new ADR-091 (skin_uniformity Path B validated).
RFC-034 closes into new ADR-092 (invert flag verified).

Updates index.md / TA.md / RFC + ADR index files to reflect new
Accepted state.
```

## See also

- [`darkroom-session-debt.md`](darkroom-session-debt.md) — full rationale per item; the "why" behind each checkbox
- [`docs/guides/cookbook.md`](cookbook.md) — recipes you'll exercise during the session
- [`docs/guides/visual-review-survey-l2-looks.md`](visual-review-survey-l2-looks.md) — structured checklist for the L2-look subset (sister to Item 10)
- [`docs/adr/ADR-088-parametric-l2-strength-path-b.md`](../adr/ADR-088-parametric-l2-strength-path-b.md), [`ADR-089-mixed-op-apply-per-region.md`](../adr/ADR-089-mixed-op-apply-per-region.md), [`ADR-090-propagate-state-mcp-verb.md`](../adr/ADR-090-propagate-state-mcp-verb.md) — the three pending Draft ADRs
