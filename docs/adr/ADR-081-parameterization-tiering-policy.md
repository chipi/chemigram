# ADR-081 — Parameterization tiering policy

> Status · Accepted
> Date · 2026-05-07
> TA anchor ·/components/synthesizer ·/contracts/vocabulary-manifest ·/constraints/opaque-hex-blobs
> Related RFC · RFC-022 (closes)
> Related ADRs · ADR-008 (opaque-blob default — explicitly amended by this ADR), ADR-077..080 (parameterization architecture; this ADR sets the policy for *which* modules use it), ADR-073 (Path C as authoring technique)

## Context

RFC-021 / ADR-077..080 settled *how* parameterized vocabulary entries work (the architecture: manifest schema, decoder registry, apply path, 5-layer test coverage). RFC-022 asked the next question — *which* modules should ride that architecture.

By the time RFC-022 closed, evidence existed for both shapes:

- **Phase 4** shipped the 8 magnitude-ladder modules (exposure, vignette, saturation_global, sigmoid_contrast, bilat_clarity_strength, grain_strength, highlights_clip_threshold, temperature). Direct replacement of v1.5.x discrete entries; low risk because primitives already existed.
- **RFC-022 Tier 2** shipped 4 brand-new-module expansions (sharpen, crop, colorbalancergb additional axes, toneequalizer). Stress-tested workflow vs taste, decoder extension, and 9-axis multi-parameter cases. Architecture held.

The remaining question was the *policy* — what's the principle that decides whether a future module gets a Path C decoder or stays opaque per ADR-008? RFC-022 proposed a four-tier framing; this ADR codifies it.

This ADR is written during the project's **build-comprehensive-baseline phase**: real-people review across distinct photographers and sessions is deliberately a later concern. The policy here favours *coverage* over *gating* during this phase. When the project transitions to multi-photographer review, the Tier 3 promotion threshold below will be revisited (see "Phase implications").

## Decision

Vocabulary modules are classified into one of four tiers. The tier captures the policy expectation; it is descriptive of intent, not a hard gate during the build-baseline phase.

**Tier 0 — Discrete-by-design. No parameterization.**

Entries whose photographic value is the discrete *intent*, not a magnitude on an axis. Parameterization would erase the semantic distinction the entry encodes.

Members: `clarity_painterly`, `blacks_lifted`, `blacks_crushed`, `whites_open`, the four `grade_*` per-zone color entries, the four mask-bound entries (`gradient_top_dampen_highlights`, `gradient_bottom_lift_shadows`, `radial_subject_lift`, `rectangle_subject_band_dim`), and the per-zone `chroma_boost_*` triple. Look entries (e.g., `look_neutral`) are also Tier 0 by construction (they're L2 composites, not module-direct).

**Tier 1 — Parameterized; the magnitude-ladder collapse floor.**

The 8 modules whose v1.5.x discrete entries collapsed into single parameterized vocabulary entries during Phase 4 (RFC-021). This tier exists to mark them as the floor of the parameterized baseline, not to re-argue them.

Members: `exposure`, `vignette`, `saturation_global`, `sigmoid_contrast`, `bilat_clarity_strength`, `grain_strength`, `highlights_clip_threshold`, `temperature`.

**Tier 2 — Parameterized; baseline expansion. Active during the build-baseline phase.**

The deliberate expansion of the parameterized baseline beyond the magnitude-ladder collapse. Modules join Tier 2 when they meet the cost-shape guidance below; growth continues until comprehensive baseline coverage is achieved.

Cost-shape guidance (advisory, not gates):

- Single or low-cardinality parameter set
- Struct layout stable and verifiable against darktable source
- Decoder cost roughly half a day per module (matches the actual measured cost of the modules already shipped)

Modules that fail this guidance (per-camera config, nested struct, surface that doesn't reduce to scalar parameters) are usually better off in Tier 3, but the call is per-module — this ADR doesn't enumerate hard exclusions.

Members at this ADR's acceptance:

- `sharpen` — 1-axis (amount); brand-new module; closes the "no real sharpening" gap from capability survey § 3
- `crop` — 4-axis (cx/cy/cw/ch); first workflow-primitive parameterized entry; closes the "no crop" gap from § 5
- `colorbalancergb` additional axes shipped as 3 separate single-axis entries: `vibrance` (replaces v1.5.x `vibrance_+0.3`), `chroma_global` (brand-new), `hue_angle` (brand-new)
- `toneequalizer` — 9-axis; closes the "no tone equalizer / zone tone" gap

Tier 2 remains **active** while the project is in the build-baseline phase. New modules joining Tier 2 do not require an individual closing ADR per module — a feature commit naming the module and crossing-referencing this ADR is sufficient. Closing-ADR overhead returns when the project transitions to multi-photographer review.

The next likely Tier 2 ship (called out here so it's not lost): `colorbalancergb` brilliance axes (`brilliance_global / brilliance_highlights / brilliance_midtones / brilliance_shadows`). Same decoder pattern as the other colorbalancergb additional axes; ~half a day of work; named in RFC-022 as a candidate but didn't make the Tier 2 batch.

**Tier 3 — Default-opaque per ADR-008.**

Every other darktable module. ADR-008's opacity policy continues to govern. Modules in Tier 3 are not parameterized today, not because they couldn't be, but because the project hasn't found photographic need or because their decoder shape is incompatible (per-camera config, nested struct, non-scalar surface).

Examples currently in Tier 3: `lens` (lensfun-coupled, per-camera config), `denoiseprofile` (camera-noise-profile-coupled), `colorzones` (3 spline curves with up to 8 nodes each — surface doesn't reduce cleanly to scalar `--value V`), and the long tail of niche modules in capability-survey.md § 12.

A specific Tier 3 module **promotes to Tier 2** when the project decides it's worth the decoder + tests + manifest entry. The promotion threshold is deliberately left light during the build-baseline phase: a feature commit naming the module, citing this ADR, and shipping the standard 5-layer coverage (per ADR-080) is the bar. The formal multi-photographer / multi-session evidence threshold the RFC mentioned is **explicitly deferred** to the later real-people-review phase; revisit then.

## Rationale

- **Honors ADR-008's structural reason for opacity.** Per-module decoders carry modversion-drift maintenance per darktable release. Tier 3 stays opaque by default; the project doesn't pay decoder maintenance for modules nobody uses.
- **Doesn't over-formalize during the build-baseline phase.** Tier 2 stays active; growth is feature-commit-driven, not ADR-per-module. Closing-ADR overhead returns at the multi-photographer transition.
- **The completeness instinct is honored at the Tier 1+2 line.** 14 parameterized entries cover tone, color, sharpening, local contrast, decorative, workflow, and tone-equalizer surfaces — the photographic foundation a real session needs. Brilliance is the visible next addition; the policy doesn't artificially gate it.
- **Tier classification is descriptive, not prescriptive.** The four tiers describe the project's relationship with each module — they don't prescribe a process that has to run before any module ships. A photographer who wants to add brilliance reads this ADR, sees Tier 2 is active, ships the decoder.
- **Multi-photographer review framing is deferred, not lost.** When the project transitions to that phase, this ADR's promotion threshold is revisited via a follow-on ADR. Until then, the current pace is appropriate.

## Alternatives considered

- **Stay incremental** (RFC-022 Alternative A) — author parameterized modules per gap, no defined tiering. Rejected: predictable gaps stayed open until friction surfaced them, when the project could already see the friction coming. Tier 2's active expansion captures that "see it coming, ship it" cadence.
- **Bulk full coverage** (RFC-022 Alternative B) — parameterize every common-use darktable module at once. Rejected: violates ADR-008's structural reason; lens/denoise carry decoder costs that dominate their photographic value; some module surfaces (colorzones HSL splines) don't reduce cleanly to scalar parameters.
- **Strict Tier 3 promotion gates from day one** (e.g., "≥3 sessions across ≥2 photographers"). Rejected for the build-baseline phase: the project is single-photographer; the threshold is meaningless until there are multiple photographers. Premature formalism. Revisit when real-people review begins.
- **Two ADRs (separate amendment of ADR-008)** — Considered. Rejected for compactness: this single ADR is sufficient since the new policy IS the ADR-008 amendment, and ADR-077 already partially superseded ADR-008 — explicit boundary statement here closes that gap without a separate small ADR.

## Consequences

Positive:

- New contributors can read the tiered list and immediately know where a proposed module fits.
- Tier 2 expansion stays fluid during build-baseline — no per-module ADR overhead, just feature commits citing this ADR.
- The capability-survey § 1–§ 9 gaps that map to Tier 3 (noise, lens, HSL, looks, etc.) have a clear path to becoming Tier 2 if the project decides to expand.
- The build-baseline vs multi-photographer-review phase distinction is explicit; later policy work has an obvious hook to revisit.

Negative:

- Tier 2 expansion is governed by judgment, not a hard rule. Mitigated: the cost-shape guidance + this ADR's named members give a clear precedent. A photographer adding a Tier 2 module who wants extra rigour can write a small ADR voluntarily.
- Multi-photographer review readiness is an open task. The current promotion path is appropriate for solo build-baseline use; it will need to tighten when distinct photographers run distinct sessions and the gap-log becomes load-bearing for vocabulary decisions.

## Implementation notes

- **No code changes required by this ADR alone.** The four-tier classification is policy / documentation; the apply-time mechanism is unchanged from ADR-077..080.
- The tier of each parameterized entry is documented in `vocabulary/packs/expressive-baseline/manifest.json` via the entry's tags and description. This ADR doesn't add a `tier:` field — the tier is inferred from parameterization status + cross-reference to this ADR's named lists.
- Tier 2 expansion (e.g., the brilliance axes called out above) ships as a normal feature commit naming the module and citing this ADR. The commit updates this ADR's "Members at this ADR's acceptance" list as a documentation-only edit. ADRs are append-only after acceptance per CLAUDE.md, but appending a member to an enumerated list under an existing decision is a documentation update, not a decision change.
- The capability-survey doc (`docs/capability-survey.md`) cross-references this ADR's tiers in its § 10 "Where chemigram is thin today" section — the "thin today" list IS the Tier 3 watchlist that informs future Tier 2 promotions.

## ADR-008 amendment

This ADR explicitly amends ADR-008's "Path C is the rare exception" framing. The new boundary:

- **For Tier 1+2 modules** — Path C parameterization is the default at apply time. Decoders live in `chemigram.core.parameterize.<module_name>`; manifest entries declare their `parameters` block per ADR-078.
- **For Tier 3 modules** — ADR-008's opacity continues. `op_params` and `blendop_params` are copied verbatim from `.dtstyle` files into synthesized XMPs; no decoding, no encoding.
- **For `blendop_params` universally** — ADR-008's opacity continues regardless of tier. Mask binding has its own byte-level codec at `chemigram.core.masking.dt_serialize` (per ADR-076); that's the only structured edit to `blendop_params` anywhere in `chemigram.core`.

ADR-008's original framing remains historically valid (it described the v1.0 / Phase 1 reality accurately). The amendment is a refinement for the parameterized-vocabulary era, not a repudiation.

## Phase implications

`IMPLEMENTATION.md`'s conditional Phase 5 ("Path C extension") is retired by this ADR. Phase 5's open question — *should the project commit to extending Path C beyond high-value modules?* — is answered: yes, for Tier 1+2 (already done at v1.6.0+ and ongoing); no for Tier 3 except when the project judges a specific module worth promoting. There is no "Phase 5" implementation work distinct from individual Tier 2 expansions or future Tier 3 promotions.

The next phase distinction the project will reach is the **multi-photographer review phase** (real-people review across distinct sessions, evaluating vocabulary breadth + coverage for real photographic goals). When that phase begins, this ADR's "deliberately light" Tier 3 promotion threshold needs revisiting via a follow-on ADR — the multi-photographer reality changes what evidence looks like and what threshold is appropriate.
