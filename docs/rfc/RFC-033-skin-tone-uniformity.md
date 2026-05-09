# RFC-033 — Skin-tone uniformity primitive

> Status · Draft v0.1
> TA anchor · /components/synthesizer · /contracts/vocabulary-manifest
> Related · RFC-021 (parameterized vocabulary / ADR-077..080), RFC-022 (bulk parameterization / ADR-081), RFC-023 (HSL color mixer parity / ADR-083), RFC-031 (batched per-region adjustment), RFC-032 (named-mask vocabulary), `docs/photographer-workflows-survey.md`
> Closes into · ADR-NNN (pending; depends on which alternative is chosen — see "How this closes")
> Why this is an RFC · Three recurring approaches surfaced in the survey, none of them obviously dominant: (a) Path C parameterization of `colorequal` (decode op_params, ship a real variance-compress primitive); (b) composition of existing `colorequal` entries via `apply_per_region` from RFC-031, scoped by `mask_skin_region` from RFC-032; (c) lean on a different darktable module like `colorize` that already does region-toward-reference color replacement at low strengths. The right answer is genuinely not obvious — it depends on whether the result needs to be statistically derived from the image, on how much byte-level work `colorequal` decoding entails, and on whether `colorize` produces a result that reads as "natural skin" or as "painted-on color." This RFC argues the alternatives so the choice is made deliberately.

## The question

The photographer-workflows survey ranked **skin-tone uniformity** as the third-highest gap (3/6 portrait recurrence: Woloszynowicz, Adler, Nordqvist — three of the six surveyed portrait photographers, including all three Capture One users). Within portrait, this is a *defining* primitive of the genre — Capture One's Skin Tone Color Editor with Uniformity Hue / Saturation / Lightness sliders is its signature feature, used early in every workflow that targets it.

The intent is precise: **compress variance** in the masked region (typically skin) toward a chosen reference color. A face with red patches on the forehead, slightly yellow undertones on the cheeks, and desaturated regions under the eyes — applying high Uniformity Hue pulls all those hue patches toward a single reference, producing skin that reads as "one continuous tone-space" instead of "fighting patches."

This is *not* the same as "set the hue to X" — it's "pull all pixels in this region toward X by N%." The variance-compress framing is what makes it a uniformity tool rather than a color replacement.

Three things are simultaneously true:

1. **darktable doesn't ship a uniformity-named primitive.** No module in v5.x natively exposes "compress variance toward reference."
2. **chemigram has the wire for region-scoped color manipulation.** `colorequal` adjusts hue/sat/lightness per hue band; the parametric mask machinery scopes it to a region.
3. **The composition is non-obvious.** "Pull toward reference" is not the same as "shift hue band by N degrees." It's a different operation conceptually, and there's no clean approximation via a single existing op.

The question: how does chemigram express this, given the three available paths?

## Use cases

- **Beauty / commercial portrait** (Woloszynowicz, Adler) — highest priority. The skin-uniformity move is Step 2 or Step 3 of the workflow, after WB foundation. Without it, every downstream move (color grade, dodge/burn, sharpening) inherits the patchy skin and can't paper over it.
- **Editorial / fashion** (Adler) — same pattern, with the additional caveat that uniformity must not flatten makeup or lipstick. The masked-region scope (`mask_skin_region` from RFC-032) is what protects this.
- **Wedding / event portrait** (future genre research; recurrence likely confirmed there) — same intent under different lighting; Mike's note from the landscape Mike-O'Leary survey hinted at this carrying into mixed-genre work.
- **Documentary / environmental portrait** — Sean Tucker's restraint-driven work explicitly *avoids* heavy uniformity (he wants real skin). Worth noting that the primitive should be parameterizable down to "very subtle" — not just shipped at high strength.

The intent is consistent: uniform skin without losing texture (frequency separation handles texture; this handles color). Strength varies by genre and subject.

## Goals

1. **One named primitive** — `skin_uniformity` or similar — usable via `apply_primitive` and `apply_per_region` (RFC-031), with `mask_spec=mask_skin_region` (RFC-032) as the canonical composition.
2. **Parameterizable strength** — at minimum, a single `strength` parameter [0.0, 1.0]. Possibly separate `uniformity_hue`, `uniformity_sat`, `uniformity_lightness` axes mirroring Capture One's three-slider surface.
3. **Configurable reference** — the target hue/sat/lightness pulled toward. Defaults to a neutral skin reference; overridable per-image (or per-photographer via `taste.md`).
4. **Result reads as natural skin** — no detectable "painted-on" or "plastic" look at typical strengths (0.3-0.6).
5. **Dependencies named** — RFC-032 ships first (named masks), RFC-031 may or may not be needed. This RFC names the dependency rather than re-litigating either prior decision.

## Constraints

- **TA/components/synthesizer** — the primitive must produce a deterministic dtstyle (or set of dtstyles) that synthesizes into a valid darktable XMP. Whatever path is chosen must respect ADR-002 (SET-replace semantics) and ADR-051 (same-module collision).
- **TA/constraints/dt-orchestration-only** — no chemigram-side image processing. Whatever the variance-compression operation is, it has to be expressible as darktable module configuration. No PIL / NumPy / OpenCV pixel manipulation in `chemigram.core`.
- **ADR-008 / opaque op_params** — bytes-level work on `op_params` requires either a tight Path C contract (RFC-012 / ADR-073) or an explicit RFC-022-style amendment (which already amends ADR-008 for documented modules).
- **ADR-079 / parameter validation** — any `strength` parameter is hard-rejected outside [0.0, 1.0]; the parameterized vocabulary contract enforces this.
- **TA/constraints/byoa** — a stats-based variant (compute median skin color from the image) requires either rendered-preview-then-respond loop semantics (which fits the agent loop already) or AI-provided stats (BYOA / MCP-mediated). Don't assume either; surface the dependency where it bites.

## Proposed approach

**This is the RFC's open question — three real paths, each with different costs and capabilities. The proposal is to *name the choice* and decide deliberately:**

### Path A — Path C parameterization of `colorequal`

Decode `colorequal` op_params bytes (the spline-curve representation darktable uses internally for per-hue adjustments) and synthesize a parameterized "uniformity" primitive. The primitive takes a strength parameter and writes a colorequal curve that compresses *all hue bands within a target color range* toward a single reference value. Strength=0 → identity curve; strength=1 → flat curve at the reference.

**Costs.** Real Path C work — decoding colorequal is non-trivial; the spline-curve format isn't documented externally and would need reverse-engineering against darktable source. Estimated 2-4 weeks; produces a permanent maintenance liability against modversion drift (RFC-007 / ADR-082 covers this but it's still a real cost).

**Capabilities gained.** A clean, deterministic, single-call primitive. No render-and-respond loop. No statistics computed externally. Synthesizes one dtstyle; closes into one ADR.

### Path B — Composition via `apply_per_region` + named mask + `colorequal` per band

Use RFC-031's batched per-region adjustment + RFC-032's `mask_skin_region` to emit a single `apply_per_region` call with N region-specific `colorequal` shifts toward the reference. Each region is one mask + one parameter set. The agent computes (or the manifest pre-bakes) the per-region parameters from a target reference and a strength.

**Costs.** Depends on RFC-031 + RFC-032 landing first. No new bytes-level work. The primitive is a *composition pattern*, not a new primitive — it ships as an L2 look (`look_skin_uniform`) plus a documented agent prompt for "apply skin uniformity." Conceptually leaner.

**Capabilities gained.** Works with no new capability beyond the two prerequisite RFCs. The strength parameter generalizes naturally (it's just per-region `colorequal` shift magnitude).

**Capabilities missed.** No true variance-compression — this is *targeted shifts at known patch locations*, not a statistical pull. Quality depends on the agent (or the L2 look's preset) correctly identifying the N patch locations. For 90% of portraits this works; for the remaining 10% (extreme variance, multiple light sources on the face), it under-corrects.

### Path C — Use `colorize` module at low strength

darktable ships a `colorize` module that applies a target HSL to a region with a strength/blend parameter. Used with `mask_skin_region` and a low strength (0.2-0.4), it pulls masked pixels toward a target color *without* full replacement.

**Costs.** Verify `colorize` exists in darktable 5.x and produces results that read as natural skin (it's typically used for stylized color replacement, not subtle pulls). One-day capability survey to confirm. If it works: shipping is trivial — one new parameterized vocabulary entry wrapping `colorize` with a strength parameter.

**Capabilities gained.** Cleanest primitive of the three options. One module, one strength slider, one mask. Composes with everything.

**Risk.** `colorize` may produce a "painted" look at any strength noticeable enough to actually correct uniformity. The module is designed for color replacement, not variance compression. If a strength of 0.4 produces visibly "fake" skin, this path doesn't work.

### Recommendation

**Capability-survey Path C first** (a half-day to a day of work). If `colorize` at strengths 0.2-0.5 produces results indistinguishable from natural skin on representative portraits — Path C wins; ship the primitive, close the RFC.

**If Path C fails the visual quality bar — do Path B** as the v1.10 ship target. Path B is significantly less work than Path A and depends on capabilities (RFC-031, RFC-032) that already need to land. The remaining 10% case (extreme variance) gets handled by the photographer reaching for stronger explicit per-region adjustments — same workflow, more deliberate.

**Defer Path A** unless Path B's quality ceiling proves insufficient in real Phase 2 use. Path A is a substantial bytes-level investment; do it once we have evidence the simpler paths fall short, not before.

## Alternatives considered

**Add chemigram-side image statistics computation (compute skin-region median, apply delta).** Rejected because it crosses the "darktable does the photography" line (TA/constraints/dt-orchestration-only). Statistics on rendered previews is acceptable (the render is darktable's output) — but using those statistics to drive the next synthesis is fine; we already do this implicitly in the agent loop. Don't introduce a chemigram-side op-on-pixels primitive.

**Wrap an external tool (G'MIC, ImageMagick) for variance-compression and let the agent invoke it.** Rejected because it expands the dependency surface dramatically and creates a new orchestration target (we already orchestrate one image-processing system; making it two is a large step). The "one image-processing engine" constraint is structural, not stylistic.

**Defer to a Photoshop sibling tool (analogous to how multi-raw HDR fusion is deferred).** Rejected because uniformity isn't capture-time-only the way HDR fusion is — it's a single-image edit-time move. Routing to PS for one specific portrait move when chemigram handles every other portrait move would be jarring. The deferral pattern is reserved for multi-raw fusion (genuinely capture-time) and frequency separation (genuinely PS-architectural).

**Bake the canonical reference colors into the manifest; no per-image reference selection.** Tempting because it avoids the "where does the reference come from" question, but rejected because skin reference varies meaningfully by ethnicity, lighting, and intentional stylistic warmth — a single canonical reference produces wrong results for half the use cases. The reference must be configurable per-image (or per-photographer via taste.md).

**Ship `mask_skin_region` (RFC-032) plus existing `colorequal` entries; document it as a workflow pattern.** Rejected because the move is named in the photographers' own language ("skin uniformity"), and chemigram's vocabulary discipline turns named moves into named primitives. A workflow pattern in `vocabulary-patterns.md` is what we have *today*; this RFC exists because that's not enough.

## Trade-offs

- **Capability-survey first** — adds a day of pre-RFC-decision work. Acceptable; cheaper than committing to Path A and discovering Path C would have worked.
- **Dependency on RFC-031 + RFC-032** — Path B requires both; Path C requires only RFC-032. Sequencing implication: RFC-032 must land first regardless; RFC-031 lands before this if Path B is chosen.
- **No variance-compression in v1.10 if Path B wins** — the result is "named, mask-scoped, parametric color shifts" not "true statistical compression." Acceptable for the surveyed photographers' use cases (they articulate it as "make skin uniform" — strong color shifts within a skin mask read as uniform to viewers). Revisit only if real Phase 2 use produces complaints.
- **Genre-bound primitive** — this primitive is portrait-specific. The other two RFCs (031, 032) are cross-genre. Worth being explicit that not every gap is cross-genre and not every primitive needs to be.

## Open questions

1. **Capability survey of `colorize`.** Does the module exist in darktable 5.x? What are its parameter shapes? At what strengths does it produce natural skin vs painted skin? Half-day-to-day investigation; results determine which path closes.
2. **Reference selection mechanism.** If the agent (or photographer) needs to choose a target skin color, how is it specified? Proposal: parameter `target_hex` defaulting to a neutral skin reference (e.g., `#D4A57C`); overrideable per-call. taste.md can ship a per-photographer default.
3. **Three-axis vs single-axis strength.** Capture One ships three sliders (Uniformity Hue / Saturation / Lightness). Worth shipping all three or simplifying to one combined `strength`? Proposal: ship the combined `strength` for v1.10; expose three axes only if Phase 2 use shows real demand.
4. **Interaction with frequency separation gap.** Frequency separation (Portrait Gap #4) is also about skin but at the texture level, not the color level. They compose naturally — uniformity first (color band), frequency separation second (texture band). But frequency separation is deferred (no clear darktable analog). Worth naming explicitly that this RFC handles only the color half.
5. **Handling of non-skin pixels in the mask.** `mask_skin_region` (RFC-032) is approximate — eyes, lips, hairline edges may leak in. The uniformity primitive should handle leakage gracefully (low strength → leaked pixels barely shift; high strength → noticeable). Worth a real-image test in the capability survey.

## How this closes

Depends on the path chosen:

- **If Path C wins (capability survey shows `colorize` produces natural skin):** one ADR — **ADR-NNN — `skin_uniformity` primitive backed by `colorize` at masked low strength** — formalizes the parameterized vocabulary entry, the strength parameter shape, the canonical mask composition with RFC-032's `mask_skin_region`, and the bundled L2 look (`look_skin_uniform`).
- **If Path B wins (capability survey shows `colorize` insufficient; `apply_per_region` carries it):** one ADR — **ADR-NNN — `skin_uniformity` as composed L2 look on `colorequal` + `apply_per_region`** — formalizes the L2 look composition, names RFC-031 and RFC-032 as hard prerequisites.
- **If Path A wins (rare; Path B's quality ceiling proves insufficient in Phase 2 use):** one ADR closing this RFC + one ADR amending ADR-008 + ADR-073 to add `colorequal` to the Path C decoder set. Heavier; only if forced by evidence.

The capability survey gates the path choice; the RFC remains Draft until the survey decides. **This RFC does not close until the capability survey runs.**

## Links

- TA/components/synthesizer (where the parameterized primitive ships)
- TA/contracts/vocabulary-manifest (one new entry; possibly L2 look)
- Related: RFC-031 (batched per-region — Path B prerequisite), RFC-032 (named-mask vocabulary — all paths require `mask_skin_region`), RFC-021 / ADR-077..080 (parameterized vocabulary contract — strength parameter), RFC-022 / ADR-081 (bulk parameterization precedent), RFC-012 / ADR-073 (Path C decoder pattern — only relevant if Path A is forced)
- Source survey: `docs/photographer-workflows-survey.md` (gap rank #3, 3/6 portrait recurrence; defining for the genre)
