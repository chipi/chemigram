# RFC-023 — HSL Color Mixer parity

> Status · Draft v0.1
> Date · 2026-05-07
> TA anchor ·/components/synthesizer ·/contracts/vocabulary-manifest ·/constraints/opaque-hex-blobs ·/components/parameterize
> Related · ADR-008 (opaque-blob default; explicitly amended by ADR-081), RFC-021 / ADR-077..080 (parameterization architecture), RFC-022 / ADR-081 (parameterization tiering policy — this RFC argues an HSL-shaped Tier promotion), capability-survey.md § 13 (Lightroom daily-use mapping), #93 (the issue that opened this question)
> Closes into · ADR-NNN (pending — picks the backing module + manifest shape; possible amendment to ADR-081 if Tier reclassification is warranted)
> Why this is an RFC · The Lightroom-parity capability survey (§ 13) flagged HSL Color Mixer as the largest remaining daily-use gap. The initial framing assumed HSL meant decoding `colorzones` — a 520-byte struct with 60 (x,y) spline-curve nodes — and that the work was qualitatively Tier 3 because of variable-curve complexity. Closer reading of darktable 5.4 reveals a second viable backing module — `colorequal` — whose struct is flat 24 scalar fields plus 7 globals. That changes the cost/risk shape enough that the question is no longer "do we ship a spline-curve decoder?" but "which darktable HSL module backs HSL parity, and what's the right vocabulary shape?" The answer shapes whether HSL is genuinely Tier 3 (the previous assumption) or actually Tier 2 (the new framing the `colorequal` discovery suggests). Worth arguing now rather than committing to one path implicitly.

---

## The question

Lightroom's HSL Color Mixer panel is the slider grid every Lightroom user reaches for: Hue, Saturation, and Luminance per color (Red / Orange / Yellow / Green / Aqua / Blue / Purple / Magenta — 8 colors, 24 sliders total). It's the workflow surface for "make the sky deeper, the foliage warmer, the skin tones a touch less saturated." Per `capability-survey.md` § 13 it's the single most-used Lightroom panel chemigram doesn't cover.

darktable has two modules that map to this surface, and the choice between them is genuinely open:

1. **`colorzones` (mv5)** — the older module. Stores per-channel curves as `dt_iop_colorzones_node_t curve[3][20]` — a 3×20 array of (x, y) float pairs, plus per-channel active-node count and curve-type enums, plus a small set of globals. Total ~520 bytes. The 60 (x, y) slots are mostly inactive; `curve_num_nodes[i]` says how many of the 20 slots are real. Photographically: the user pulls anchor points on Hue/Sat/Luminance curves indexed by hue.

2. **`colorequal` (mv4)** — darktable's modern HSL module, introduced post-4.x as the recommended path for hue-dependent edits. Stores 24 per-color scalars directly — 8 saturation, 8 hue-shift, 8 brightness — plus 7 globals (threshold, smoothing, contrast, white_level, chroma_size, param_size, hue_shift) and one boolean. Total ~136 bytes. No curves, no node counts, no spline interpolation in the struct: the per-zone scalars are the parameters; darktable's runtime does the band-shaping internally.

These two modules represent qualitatively different decoder cost shapes. Picking one isn't aesthetic — the choice locks the vocabulary surface, the modversion-drift exposure, the test-coverage approach, and whether HSL belongs in Tier 2 or Tier 3 of ADR-081's tiering policy.

---

## Use cases

1. **Photographer wants the sky deeper.** Lightroom move: HSL → Blue Luminance −20. With `colorequal`: `--param bright_blue=-0.2`. With `colorzones`: pull the Blue node on the L-channel curve down. Both work; the parameter shape differs.
2. **Photographer wants foliage warmer.** Lightroom: HSL → Green Hue +15 (toward yellow). `colorequal`: `--param hue_green=15.0`. `colorzones`: shift the Green node on the H-channel curve.
3. **Skin-tone protection.** Lightroom: Orange Saturation −10 (subtle desaturation). Both modules can express this; the `colorequal` form is a single scalar, the `colorzones` form is a node pull.
4. **Composing two HSL moves on the same color.** Common in real workflow ("warm the green and slightly desaturate it"). With per-color scalars (`colorequal`), composition is two parameter axes patched independently. With curves (`colorzones`), composition means stacking node pulls — which is harder for the engine to reason about because curve nodes interact (pulling one node affects the spline's behavior near adjacent nodes).
5. **Vocabulary breadth.** A photographer running through `vocab list` should see HSL primitives at the same granularity as the existing `saturation_*` / `hue_*` colorbalancergb axes. The shape of the vocabulary surface (one entry per color × axis = 24 entries, vs one multi-axis entry, vs hybrid) directly impacts discoverability.

---

## Goals

- **Pick the backing module.** A clear, defensible answer to "which darktable module backs HSL parity" — `colorzones` or `colorequal` — with the trade-offs named honestly.
- **Pick the vocabulary shape.** Whether HSL ships as one multi-axis parameterized entry (24+ axes), a small set of multi-axis entries (one per color × HSL channel = 8), 24 single-axis entries (one per slider), or a hybrid.
- **Resolve the Tier classification.** ADR-081 places HSL under Tier 3 ("default-opaque") *under the assumption HSL meant variable-curve `colorzones`*. If `colorequal` is picked, HSL's struct shape is Tier 2 (flat scalars, additive offsets like the colorbalancergb 17-axis ship). The closing ADR needs to state the Tier classification of whichever module is picked.
- **Bound the modversion-drift surface.** Both modules add one more thing to the parameterize registry. Pick the one with the smaller drift surface and document the choice.
- **Preserve the architectural floor.** Whatever ships rides RFC-021 / ADR-077..080's parameterization architecture (manifest schema, decoder registry, apply path, 5-layer test coverage). No new architectural surface.

---

## Constraints

- **ADR-008** (`/constraints/opaque-hex-blobs`): opacity by default. RFC-021 amended this for parameterized modules; ADR-081 set the tiering policy. This RFC argues which side of ADR-081 HSL falls on.
- **ADR-077..080** (parameterization architecture): the manifest schema, decoder registry, apply path, and 5-layer test coverage gate are non-negotiable. New HSL decoders ride them without changes.
- **ADR-081** (parameterization tiering): Tier 1 (Phase 4 floor) is locked. Tier 2 ("active expansion") is where new decoders land if the cost is bounded. Tier 3 ("default-opaque") is where curve-based or struct-heavy modules live until promoted. HSL's current placement in Tier 3 is conditional on the assumption that HSL = `colorzones`; the new question reopens that.
- **CLAUDE.md three foundational disciplines**: agent-only-writer (parameter values flow only via tool calls); darktable-does-the-photography (we shuffle bytes, not implement HSL math); BYOA (no AI added).
- **TA/components/synthesizer** apply path: parameter values + mask spec + plain synthesize are orthogonal. HSL ships as one or many vocabulary entries riding this same path.

---

## Proposed approach

**Back HSL with `colorequal` mv4. Ship as 3 multi-axis parameterized entries — one per HSL channel — with 8 per-color scalars each.**

Three vocabulary entries:

- **`hsl_hue`** — 8 axes: `hue_red`, `hue_orange`, `hue_yellow`, `hue_green`, `hue_cyan`, `hue_blue`, `hue_lavender`, `hue_magenta`. Each range [-180, +180] degrees, default 0.0. Maps directly to Lightroom HSL Hue sliders.
- **`hsl_saturation`** — 8 axes: `sat_red` through `sat_magenta`. Each range [-1.0, +1.0], default 0.0. Maps to Lightroom HSL Saturation sliders.
- **`hsl_luminance`** — 8 axes: `bright_red` through `bright_magenta`. Each range [-1.0, +1.0], default 0.0. Maps to Lightroom HSL Luminance sliders.

Each entry shares the same baseline `op_params` blob (24 zero scalars + darktable defaults for the 7 globals + filter flag). The decoder is a single `colorequal.py` Path C module routing `**values` against a 24-axis `_AXIS_FIELD_INDICES` table, mirroring the colorbalancergb 17-axis pattern.

**Tier classification: Tier 2.** The `colorequal` struct is flat scalar — no nested arrays, no variable-length curves, no node-count metadata to track. The decoder shape is identical to colorbalancergb / temperature / hazeremoval (which are all Tier 2). The cost/benefit math that placed Tier 2 on `colorbalancergb` applies cleanly here.

This proposal trades two things for that simplicity:

1. **No anchor-point curve control.** A photographer who wants the *exact* Lightroom Range slider behavior — adjust a hue zone's edge falloff — won't get it. `colorequal`'s `smoothing_hue` and `param_size` globals control falloff but at a coarser grain than per-zone curves. For 90% of HSL workflow this is invisible; for the remaining 10% (photographers tuning saturation curves with mathematical precision), it's a real gap. Documented as a known limitation; revisit if the gap surfaces in real sessions.
2. **Three vocabulary entries instead of one.** Could compress to a single 24-axis `hsl` entry. The 3-entry shape was chosen because (a) it mirrors how Lightroom users describe their workflow ("I'll do a hue pass first, then saturation"); (b) `vocab list --tags hsl` produces a useful three-row summary instead of one giant entry; (c) parameterized entries in chemigram have so far stayed below ~10 axes; jumping to 24 in a single entry would be the largest by 2.5×. Trade-off favors readability.

---

## Alternatives considered

### Alt 1: Back HSL with `colorzones` mv5

Rejected. The 520-byte struct with 60 (x, y) curve nodes carries:

- **Higher byte-correctness risk.** Empirical baseline capture via darktable GUI is necessary (same blocker that deferred tone curve / #94). Without authored references, the curve-node-position bytes can't be safely synthesized — same trap that kept tonecurve from shipping in v1.7.0.
- **Higher modversion-drift surface.** colorzones has a longer history of struct churn than `colorequal`; the spline-version field in the struct (`splines_version`) hints at internal versioning that survived module modversion bumps. Each curve representation change is a re-author event for every shipped HSL entry.
- **Curve-composition semantics.** Two HSL moves on the same color — "warm the green and slightly desaturate" — compose by stacking spline-node pulls. The interaction is non-local: pulling a node affects the curve in a region, not just at the node. Path C's "patch this byte at this offset" model fights this.
- **darktable's own deprecation signal.** colorequal was introduced as the modern path; the darktable docs steer new users to it. Building on `colorzones` builds on infrastructure the project itself is moving away from.

### Alt 2: Back HSL with both modules — choose at apply time

Rejected. Means two decoders, two manifest entry shapes, two test surfaces. The `colorequal` proposal already covers ~95% of HSL use. The 5% of curve-based use can be authored as discrete `colorzones` dtstyles (not parameterized) when a real session surfaces the need — that's the existing Tier 3 fallback path from ADR-081.

### Alt 3: Ship HSL as 24 single-axis parameterized entries (one per slider)

Rejected. This was the initial instinct (matches the colorbalancergb pattern of one-axis-per-entry that we used through #91 Bucket A.5). For HSL it inverts the photographic model: a Lightroom user thinks in *channels* ("I'm doing the hue pass") not in *24 disconnected sliders*. Compressing to 3 multi-axis entries (one per H/S/L channel) keeps the channel-as-unit framing without losing the per-color granularity (each entry exposes 8 axes).

### Alt 4: Ship HSL as one mega-entry with all 24 axes

Rejected. The largest existing parameterized entry has 9 axes (toneequalizer, the post-#91 colorbalancergb extensions). 24 axes in a single entry would be 2.5× the next-largest, which makes `vocab show hsl` a wall of text and makes `--param` errors harder to triage. The 3-entry split is barely larger maintenance and notably more readable.

### Alt 5: Defer HSL until real sessions surface specific gaps

Rejected. Phase 2 is use-driven for *new* primitives, but HSL isn't a new primitive — it's a documented gap closing a panel every Lightroom user reaches for daily (`capability-survey.md` § 13). The gap is the case; deferring would mean shipping v1.8.0 with the largest-named Lightroom-parity gap still open, which contradicts v1.8.0's stated goal.

---

## Trade-offs

- **Falloff control is coarser than Lightroom.** `colorequal`'s `smoothing_hue` and `param_size` globals shape how aggressively each color zone bleeds into adjacent ones, but not as a per-zone parameter. Lightroom's HSL Range slider gives per-zone falloff; `colorequal` gives global falloff. For 90% of HSL workflow this is invisible. Mitigated: document as a known limitation in the closing ADR; reopen if real-session feedback flags it.
- **24 axes across 3 entries is more vocabulary surface than colorbalancergb's 17.** `vocab list` grows by 3 rows (manageable). The bigger cost is test coverage: each axis needs a sweep entry in `_PARAMETER_SWEEP_VALUES`, and parameter-name collisions across entries (e.g., if `hue_red` were named just `red` it'd collide with anything else color-named) need watching.
- **Parameter-name discipline.** All 24 axis names need to be globally unique across the vocabulary (per the visual-proof sweep machinery's flat keying). Naming convention `hue_<color>` / `sat_<color>` / `bright_<color>` keeps them disjoint from existing parameterized axes. Risk: future modules with similar per-color axes would need a different naming scheme. Acceptable.
- **Skip-curve users get a workflow gap.** A photographer comfortable in Lightroom's HSL Range curves (a small minority) will find chemigram's HSL parity less precise. If they need exactly that workflow, the discrete `colorzones` Tier 3 path is open.
- **`colorequal` is newer than the modules we already parameterize.** Module age affects modversion-stability priors. mv4 (current) means at least 4 modversion bumps since introduction. The drift-detection backstop (ADR-082) handles this; no special policy needed.

---

## Open questions

- **Tier reclassification language for ADR-081.** If HSL via `colorequal` ships as Tier 2, the closing ADR should explicitly note that "HSL Color Mixer" was previously placed under Tier 3 in ADR-081 and is now reclassified — *not* because the tier policy changed, but because the backing-module choice changed. Question: does this warrant a small amendment ADR to ADR-081, or just a `Related` reference in the closing ADR?
- **Lab-grade direction-of-change strategy.** 24 per-color axes on a synthetic chart — direction-of-change should be measurable for at least the saturation axes (per-color sat shift on the colorchecker patches should reduce/boost chroma in the affected color region). Hue and luminance per-color may need real-raw fixtures. Proposed: lab-grade the saturation axes; render-completes-only for hue/brightness with a note.
- **Visual-proof sweep coverage.** 24 axes × 5 values each = 120 sweep renders per HSL ship. That's manageable but big. Question: ship all 24 sweeps at v1.8.0 ship, or trim to one representative axis per HSL channel (e.g., hue_blue, sat_red, bright_green) and add others as gaps surface? Proposed: ship the 8 saturation sweeps (sat is the most-used HSL axis), defer the 16 hue/brightness sweeps to follow-up.
- **MCP tool surface impact.** The MCP `apply_primitive` tool already handles multi-axis values via the `parameters` block — no surface change. But `list_vocabulary` output expands. Question: does the MCP tool's response need a per-channel grouping for HSL entries to stay readable? Proposed: no — the existing flat list format scales.
- **Composition semantics.** Two HSL applies on the same image (e.g., apply `hsl_hue --param hue_blue=15` then later `hsl_hue --param hue_red=10`) — does the second apply preserve the first's blue shift? With multi-axis partial-update (which all our parameterized decoders support), yes. But if someone reauthors the same entry twice with different axes, the second instance carries only its own axis and zeros for the rest of *its* entry. Question: is that the right semantic, or should HSL entries chain? Proposed: status quo (no chaining) — chaining is a generic apply-path question, not HSL-specific.

---

## How this closes

This RFC closes into:

- **An ADR specifying `colorequal` as the HSL backing module + the 3-multi-axis-entry vocabulary shape**, citing the cost/risk argument against `colorzones` and the photographic-workflow argument against single-axis-per-slider.
- **A possible amendment to ADR-081** clarifying that HSL Color Mixer is now Tier 2 (under `colorequal`); the original Tier 3 placement assumed the `colorzones` backing.
- **The implementation ship**: a `colorequal.py` Path C decoder, 3 parameterized vocabulary entries (`hsl_hue` / `hsl_saturation` / `hsl_luminance`), 5-layer test coverage per ADR-080, and any deferred sweep coverage tracked as follow-up.

---

## Links

- TA/components/synthesizer
- TA/components/parameterize (the registry + decoder surface)
- TA/contracts/vocabulary-manifest
- TA/constraints/opaque-hex-blobs (and ADR-008's amendment by ADR-081)
- ADR-077, ADR-078, ADR-079, ADR-080 (parameterization architecture)
- ADR-081 (tiering policy this RFC may amend)
- ADR-082 (modversion drift handling — the backstop for whichever module ships)
- RFC-021 (architecture); RFC-022 (tiering — this RFC's nearest sibling)
- `docs/capability-survey.md` § 13 (Lightroom daily-use mapping)
- Issue #93 (the original HSL Color Mixer issue)
