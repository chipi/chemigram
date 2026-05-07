# RFC-022 — Bulk parameterization of common-use darktable modules

> Status · Draft v0.1
> Date · 2026-05-07
> TA anchor ·/components/synthesizer ·/contracts/vocabulary-manifest ·/constraints/opaque-hex-blobs ·/components/cli ·/contracts/mcp-tools
> Related · ADR-008 (opaque-blob default — the central tension), RFC-012 / ADR-073 (Path C as authoring), RFC-021 / ADR-077..080 (parameterization architecture; this RFC's foundation), capability-survey.md §1, §10, §12, IMPLEMENTATION.md Phase 4 / Phase 5
> Closes into · ADR-NNN (parameterization tiering policy; pending) · ADR-NNN (per-tier shipping cadence; pending) · possibly an amending ADR to ADR-008's framing
> Why this is an RFC · RFC-021 settled the *architecture* for parameterized vocabulary entries and Phase 4 is collapsing six existing magnitude-ladder modules into the parameterized form. The question this RFC opens is what comes *after* Phase 4: should we commit to parameterizing every common-use darktable module as an architectural baseline before further session/agent work, or stay incremental and author new modules as photographic need surfaces? ADR-008's "high-value modules only, when there's a clear bottleneck" framing was load-bearing through Phase 1; the v1.6.0+ shift is real enough that a foundational answer is worth arguing now rather than rediscovering through accumulated ad-hoc decisions.

---

## The question

Phase 4 (per `capability-survey.md` §10) takes the six existing magnitude-ladder modules — `colorbalancergb-saturation` ✅ (shipped 2026-05-07 as `saturation_global`), `sigmoid-contrast`, `bilat-clarity-strength`, `grain-strength`, `highlights-clip-threshold`, `temperature` (multi-axis) — and collapses each into a single parameterized entry. The cost is roughly half a day per module; the photographic primitives already exist, so the work is decoder + tests + manifest cleanup with no new authoring. After those six ship, the survey notes plainly: "open the question of brand-new module authoring (sharpen / toneequal / denoise / lens / crop) — those address the 'where chemigram is thin' gaps."

The genuinely open question: is the *complete-baseline-first* path the right one — parameterize every common-use darktable module as the architectural foundation before agent loop work expands — or is the *incremental* path right, where new modules are authored as real sessions surface specific gaps?

The instinct toward completeness has merit. A parameterized baseline that covers tone, color, sharpening, local contrast, optical correction, and crop is what most photographic workflows reach for; building agent capabilities on top of an incomplete foundation means later agent sessions either avoid those moves (vocabulary still feels thin) or trigger Phase 2's manual capture loop mid-session (workflow-breaking). Equally, Phase 2's whole framing was *use-driven* growth — vocabulary expands because real photographers reach for moves and find them missing — and bulk parameterization without that pull risks shipping decoders for modules nobody actually uses.

The matter is not whether more parameterized modules are valuable. They obviously are. The matter is what threshold the project sets for *which* modules clear the cost/benefit bar of a Path C decoder, and whether that threshold is set proactively (a baseline) or reactively (per gap).

---

## Use cases

1. **Photographer authors a marine-photography session.** Reaches for sharpening on the manta's eye region. Today: no `sharpen` entry exists; agent picks `clarity_strong` instead, which is a different photographic move. Bulk-parameterized: `sharpen --value V --mask-spec '<eye region>'` works without the photographer breaking flow to author a primitive.
2. **Agent reasons about a portrait.** Wants gentle skin-tone-protective sharpening. Today: same gap. Bulk-parameterized: `toneequal` and `sharpen` are both first-class.
3. **Photographer uploads a wide-angle architectural shot.** Wants lens correction. Today: no `lens` entry. Bulk-parameterized: `lens --value V` per axis, parameterized from camera EXIF.
4. **Photographer needs a crop on a 3:2 file to 1:1.** Today: must drop into darktable. Bulk-parameterized: `crop` entry (parameterized aspect ratio + offsets) keeps the work in the chemigram loop.
5. **Vocabulary breadth survey** (the diagnostic case). The capability survey identifies thin gaps; the agent's vocabulary-gap log surfaces specifics from real sessions; the question is whether to fill those gaps proactively or as they're hit.

---

## Goals

- **Decide the threshold.** A clear, defensible answer to "which modules get a Path C decoder" — not as a list, but as a *policy* the project applies consistently as new modules surface.
- **Honor ADR-008's structural reason for opacity.** ADR-008's "opaque-blob default" wasn't stylistic preference; per-module decoders compound modversion-drift maintenance with each darktable release. Whatever the answer, the project must own that cost honestly.
- **Sequence cleanly with Phase 4.** Whatever this RFC concludes, it doesn't re-litigate the six Phase 4 modules — those are already shipping. The question is only what happens after.
- **Avoid speculative engineering.** Per CLAUDE.md, "Don't design for hypothetical future requirements." If the answer is "expand to N modules," each must have a real photographic case, not just architectural symmetry.
- **Bound the modversion-drift surface.** Each parameterized module is one more thing that breaks on a darktable release. The threshold needs to weigh that cost.

---

## Constraints

- **ADR-008** (`/constraints/opaque-hex-blobs`): the opacity-by-default policy. RFC-021 amended this for the explicit set of parameterized modules; this RFC argues whether to amend it further. The amending ADR will need to state the new policy crisply.
- **ADR-077..080** (RFC-021 closure): the parameterization architecture (manifest schema, decoder registry, apply path, 5-layer test coverage policy). New parameterized modules ride this architecture without changes.
- **TA/components/synthesizer**: the apply path (`chemigram.core.helpers.apply_entry`) handles parameter values, mask binding, and plain synthesize as three orthogonal axes. Adding modules costs decoders + tests; the apply path itself is one-time.
- **TA/contracts/vocabulary-manifest**: each parameterized entry declares parameter name(s), type(s), range(s), default(s), and the byte location in `op_params`. Multi-parameter entries are supported from RFC-021 day one (the `temperature` multi-axis Phase 4 module exercises this).
- **CLAUDE.md three foundational disciplines**: agent-only-writer (parameterization changes don't introduce silent mutations); darktable-does-the-photography (Path C decoders edit darktable's bytes; we don't reimplement); BYOA (no AI dependency added).
- **Phase 2 framing**: the project's vocabulary growth model is *use-driven* — gaps surface through real sessions, the photographer captures the move in darktable, drops the `.dtstyle` into a personal pack. Bulk parameterization sits in tension with this if pursued aggressively; the RFC must address how the two coexist.
- **Phase 5 (conditional)** in `IMPLEMENTATION.md`: was framed as "Path C extension" — a future phase if accumulated evidence warranted it. This RFC is the test of whether that evidence is now present.

---

## Proposed approach

### A tiered baseline policy, not a flat list

The recommendation: define the baseline as a *policy with named tiers*, not a fixed enumeration. Each tier carries different cost expectations, different photographic justifications, and a different shipping cadence. New modules join a tier when the policy says they belong, not when an ad-hoc judgment call is made per module.

**Tier 1 — Parameterize. Already authored.**
The six Phase 4 modules. Already in flight; this tier exists to mark them as the floor of the baseline, not to re-argue them. After Phase 4 finishes: 8 parameterized modules total (`exposure`, `vignette`, `saturation_global`, `sigmoid-contrast`, `bilat-clarity-strength`, `grain-strength`, `highlights-clip-threshold`, `temperature`).

**Tier 2 — Parameterize. Authored next, as a deliberate baseline expansion.**
Modules that meet *all* of:
- Single or low-cardinality parameter set (≤4 floats / ints; no per-camera config; no nested struct).
- High photographic frequency in the use cases identified in the survey (§1: thin gaps).
- The struct layout is stable and well-documented in darktable source — verifiable in <1 hour of source reading + empirical diffing of GUI-authored `.dtstyle` files.
- The decoder cost is roughly half a day per module (matching Phase 4's actual measured cost).

Concrete candidates that clear this bar:
- `sharpen` — 4 floats (radius, amount, threshold, clip), well-documented struct.
- `toneequal` (toneequalizer) — 8-band curve, predictable structure, photographically central.
- `crop` — 4 floats (x0, y0, x1, y1) + optional aspect lock; trivial decoder; large workflow value.
- `colorbalancergb` *additional axes* (vibrance, chroma_global, hue_angle, brilliance) — already have the colorbalancergb decoder pattern from `saturation_global`; expanding the same module to additional fields is incremental rather than new module authoring.

Estimated cost: ~4 modules × half a day = 2 days of focused work, distributed over 3–4 sessions. Each ships as a single commit following the Phase 4 pattern.

**Tier 3 — Stay opaque. Parameterize only on real bottleneck.**
Modules that violate any of Tier 2's criteria:
- `lens` (lensfun) — camera-specific config, lensfun database lookup, nested struct. Decoder cost dominates the photographic value.
- `denoiseprofile` — per-camera noise profile, complex struct, probably useful but rarely *parameterized* in a way the agent would emit (most photographers want auto, not manual).
- `colorzones` — 3 spline curves with up to 8 nodes each. Parameterizable but the photographic surface (which axis, which node, which curve) is wider than a `--value V` shape supports cleanly.
- `colorin`, `colorout`, `demosaic`, `temperature` (the *raw* temperature settings, distinct from the white-balance module already in Tier 1) — pipeline plumbing; rarely authored as taste moves.
- Long tail of niche modules in the §12 catalog that don't appear in real session use.

The policy: these stay opaque under ADR-008 as originally framed. If a real session surfaces a bottleneck — vocabulary-gap log entries accumulate against one of these — the project promotes that single module into Tier 2 with an ADR documenting the photographic case. The promotion path is explicit, not vibes-based.

**Tier 0 — Don't parameterize, ever (but keep the discrete vocabulary).**
Modules where the photographic move *is* the discrete intent, not a magnitude. `clarity_painterly` vs `clarity_strong` is a *kind* difference; per-zone `grade_*` entries are *direction* differences; mask-bound `gradient_*`, `radial_*`, `rectangle_*` entries are *geometry* differences. RFC-021 already settled this distinction; this RFC restates it for completeness — these are intentionally not parameterizable, not "haven't been parameterized yet."

### Sequencing

1. **Finish Phase 4 first.** Six modules, ~3 sessions. No deviation from RFC-021's plan.
2. **Tier 2 expansion next.** Four modules (`sharpen`, `toneequal`, `crop`, plus colorbalancergb additional axes), ~3–4 sessions. Each ships as the Phase 4 pattern: decoder + manifest + 5-layer test coverage + visual-proof sweep.
3. **Pause and observe.** After Tier 2 ships, run real sessions for 4–6 weeks. Check: does the vocabulary-gap log surface anything in Tier 3? Do agent sessions feel like the foundation is *complete* now, or still thin?
4. **Tier 3 promotions on evidence.** Each promotion is an individual ADR. No bulk Tier 3 expansion.

This sequencing answers "incremental or baseline?" with *both, in order*: a deliberate baseline expansion (Tier 2), then incremental promotions on evidence (Tier 3). The completeness instinct is honored at the Tier 1+2 line; the use-driven growth instinct continues to govern Tier 3.

### Phase numbering

The Phase 4 framing in `IMPLEMENTATION.md` covers the magnitude-ladder collapse. This RFC's Tier 2 expansion is best framed as **Phase 4.5** or **Phase 5a**, depending on whether `IMPLEMENTATION.md` keeps its current Phase 5 (Path C extension) framing. Either way, it sits between Phase 4 (mechanical) and the formerly-conditional Phase 5 (open-ended). The closing ADR will state which.

---

## Alternatives considered

### A. Stay incremental — author parameterized modules per gap

The current default. Phase 4 finishes; future modules ship one at a time as real session needs surface them through the vocabulary-gap log.

**Why it might be right.** Aligns with Phase 2's use-driven growth model. Avoids speculative engineering — every shipped module has a documented photographic case. Bounds the modversion-drift surface tightly: only modules that have demonstrated photographic value pay the maintenance cost.

**Why it's not chosen.** The marine-photography use case (the project's grounding case) reaches for sharpening, toneequal, and crop in workflows that exist *now*, not workflows that will surface later. Waiting for the gap log to fire on these modules is waiting for friction the project can already predict. The incremental path is right *for the long tail* but understates the foundation case.

### B. Bulk full coverage — parameterize every common-use module

Parameterize every module in the §12 catalog that gets routine use. Roughly 20–30 modules, depending on where "common-use" is drawn.

**Why it might be right.** Maximally complete foundation. Every photographic move expressible as a `--value V` is available without authoring overhead. Aesthetically clean.

**Why it's not chosen.** Violates ADR-008's structural reason for opacity. `lens` and `denoiseprofile` carry decoder costs that dominate their photographic value at the parameterized layer (most photographers want lens correction *automatic from EXIF*, not manual via `--value V`). The modversion-drift surface scales linearly: 25 decoders means 25 things that can break per darktable release. Some modules (`colorzones`, `bloom`, `liquify`) have surfaces that don't reduce cleanly to scalar parameters; forcing them into the `--value V` shape produces a worse UX than the existing discrete vocabulary or the `apply-primitive` flow against an authored `.dtstyle`. Speculative engineering — the photographic use cases for several of these modules are not present in the project's grounding photography (marine + portrait + landscape).

### C. Tiered baseline (recommended)

The proposed approach above. Combines a small deliberate expansion (Tier 2) with incremental promotion (Tier 3) and explicit no-go zones (Tier 1+2 ceiling, Tier 0 immutability). Provides a *policy* answer rather than a one-time list — so when the project hits an as-yet-unanticipated module, the policy says where it goes.

**Why it's chosen.** Honors ADR-008's structural reason for opacity (Tier 3 stays opaque by default). Honors the completeness instinct (Tier 2 fills the predictable gaps). Honors Phase 2's use-driven growth (Tier 3 promotions are evidence-based). The modversion-drift surface stays bounded: ~12 parameterized modules total at the Tier 1+2 line, with growth to Tier 3 gated on documented sessions.

**Where it might be wrong.** The Tier 2 list is a judgment call — `sharpen` and `toneequal` are obvious; `crop` is more of a workflow primitive than a taste primitive (it might belong in a separate "workflow ops" category that doesn't ride RFC-021's manifest schema). `colorbalancergb` additional axes might be better as a separate RFC since the multi-axis surface raises new questions (which axes compose, which clobber). The ADR closing this RFC will need to confirm or trim the Tier 2 list.

### D. A different mechanism entirely — `darktable-cli` parameter overrides

In principle, `darktable-cli` could expose a way to override module parameters at render time without a per-module decoder — a `--param exposure.ev=0.7` flag, say. Investigated for completeness.

**Why it's not chosen.** No such interface exists. Adding one would require darktable upstream work, which this project explicitly cannot drive — Chemigram is a *consumer* of darktable, not a contributor (per the foundational discipline "darktable does the photography"). Even if such an interface shipped tomorrow, it would only cover modules whose params are documented in dt's introspection metadata, which not all modules expose at the Python level. The Path C byte-level decoder is the project's mechanism by structural choice, not by absence of alternatives.

---

## Trade-offs

**What Tier 2 expansion costs:**
- ~3–4 sessions of focused decoder + test work after Phase 4 finishes.
- Adds 4 modules to the modversion-drift surface (now 12 total at Tier 1+2 line; if darktable bumps any one of these, that module's vocabulary needs re-validation per RFC-007).
- Each Tier 2 module increases the test surface by ~5 layers (per ADR-080's coverage policy). Manageable but not free.
- Visual-proofs gallery grows accordingly (one new entry per parameterized module, with a sweep row).

**What Tier 2 expansion buys:**
- Closes the largest predictable gaps in the §1 capability survey ("where chemigram is thin").
- Makes the agent loop substantially more capable without changing the loop architecture itself — agents can emit `sharpen --value V` etc. directly.
- Locks the `.dtstyle` authoring discipline at a single coherent baseline ("everything common is parameterized; uncommon stays opaque") rather than distributing the same decision across many small ad-hoc commits.

**What the Tier 3 default-opaque policy costs:**
- Some sessions will surface gaps in modules the project decided not to parameterize. Friction will be real until a Tier 3 promotion ADR lands.
- The promotion path adds a small process overhead — a session-evidence-driven ADR rather than just shipping the decoder.

**What it buys:**
- ADR-008's structural opacity reason stays intact for everything outside the named baseline.
- The modversion-drift surface stays bounded by photographic use, not architectural symmetry.

---

## Open questions

- **Is `crop` actually the right shape for parameterization?** Crop is a workflow primitive (every image has one) more than a taste primitive (some images get one). Might belong in a separate manifest category (`workflow_ops`?) that rides a different surface than `--value V`. Defer to the closing ADR.
- **Multi-axis `colorbalancergb` parameterization** — does each axis (vibrance, chroma_global, hue_angle, brilliance) ship as a separate parameterized entry, or do we move toward multi-parameter entries of the form `colorbalancergb --vibrance V1 --chroma V2`? The latter is more compact but raises composition questions (what if the photographer applies the multi-param entry on top of an existing `colorbalancergb` op?). Closes alongside `temperature` (the first multi-parameter Phase 4 module; whatever shape `temperature` lands on probably guides this).
- **Which ADR amends ADR-008?** The closing ADR for this RFC needs to state the new policy crisply ("opaque-blob is the default for Tier 3 and beyond; Path C decoders are the default for Tier 1+2"). Does it amend ADR-008 in place or supersede it? RFC-021 said "supersedes part of ADR-008's framing" without an explicit superseding ADR, which left the boundary fuzzy. Worth doing cleaner this time.
- **Tier 3 promotion threshold.** How much evidence is enough? "N gap log entries against the same module across M sessions" with concrete N and M values would be cleanest, but might not match how real sessions evolve. The closing ADR needs to either commit to numbers or honestly say "judgment call, documented in the promotion ADR each time."
- **Sequencing with the Phase 4 close.** Does Tier 2 work start the moment Phase 4 finishes, or does the project pause and run real sessions on the Phase 4 vocabulary first, validating that the parameterization architecture is solid before expanding it? Probably the latter — but the question is worth naming.

---

## How this closes

Likely two ADRs out of this RFC:

- **ADR-NNN — Parameterization tiering policy.** States the four-tier framing (Tier 0 immutable discrete; Tier 1 already-shipped; Tier 2 deliberate baseline expansion; Tier 3 default-opaque, evidence-promoted). Names the Tier 2 modules concretely. States the Tier 3 promotion path (each promotion is its own ADR). Amends or supersedes ADR-008 explicitly to remove the boundary fuzziness left by RFC-021.
- **ADR-NNN — Tier 2 shipping cadence and Phase numbering.** States how Tier 2 modules sequence (probably alphabetical or by photographic-frequency-priority, both defensible). Renames the conditional Phase 5 in `IMPLEMENTATION.md` to align with whatever framing the tiering policy adopts. Documents the "pause and observe" step before Tier 3 promotions begin.

Possibly a third ADR if the multi-axis `colorbalancergb` question above proves substantive — though it might just close inside ADR-080's coverage policy with a note on multi-parameter entries.

---

## Links

- TA/components/synthesizer — apply path with parameter values + mask
- TA/contracts/vocabulary-manifest — `parameters` block schema
- TA/constraints/opaque-hex-blobs — ADR-008's foundational policy this RFC amends
- Related: ADR-008, ADR-073, ADR-076, ADR-077, ADR-078, ADR-079, ADR-080, RFC-007, RFC-012, RFC-021, capability-survey.md §1, §10, §12
