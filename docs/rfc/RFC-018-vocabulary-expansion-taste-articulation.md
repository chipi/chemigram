# RFC-018 — Vocabulary expansion for expressive taste articulation

> Status · Draft v0.2 (engine + assertion library + scaffold ship in v1.2.0; authoring deferred to v1.4.0)
> TA anchor ·/components/synthesizer ·/components/mcp-server ·/constraints
> Related · RFC-001, RFC-007, RFC-012, ADR-001, ADR-009, ADR-051, ADR-008
> Closes into · ADR-063 (Path B unblocking + empirical evidence on iop_order),
>               ADR-064 (Phase 1.2 vocabulary authoring workflow)
> Phase · Phase 1.2 — engine unblock + scaffold (ships as v1.2.0).
>         Phase 1.4 — actual 35-entry authoring (ships as v1.4.0,
>         post-v1.3.0 CLI). The split was made on 2026-05-02 because
>         authoring is hands-on darktable work that doesn't gate the
>         engine work; engine and assertion library land first so the
>         authoring phase can use them.
> Why this is an RFC · The vocabulary currently ships five entries covering
>                      exposure and white balance only. Expressive taste
>                      articulation — including every parameter in the six
>                      artist profiles developed in the taste-library POC —
>                      requires roughly 20 distinct parameter dimensions.
>                      Half can be addressed by authoring .dtstyle entries for
>                      modules already in the baseline (Path A, unblocked).
>                      The other half require Path B new-instance addition,
>                      which previously raised NotImplementedError per ADR-051.
>                      Empirical evidence (collected during v0.2 of this RFC,
>                      see ``tests/fixtures/preflight-evidence/``) shows
>                      darktable 5.4.1 does **not** require per-entry
>                      ``iop_order`` for Path B — overturning RFC-001's prior
>                      assumption. This RFC commits to the simplified Path B
>                      implementation and the v1.2.0 vocabulary expansion plan.

## v0.2 changes

- **Strategy X (probe-iop-order workflow) dropped.** Empirical evidence
  shows darktable 5.4.1 resolves pipeline order from the description-level
  ``iop_order_version`` + its internal iop_list; per-entry ``iop_order``
  is unnecessary for Path B. See "The iop_order question, resolved" below.
- **ADR-063 simplified.** Was "Path B iop_order strategy"; now closes the
  RFC-001 iop_order open question with the empirical evidence + commits
  to the trivial implementation (``iop_order=None`` for new entries).
- **Probe script + manifest schema fields removed** from the plan.
  Path B authoring is now: capture .dtstyle in darktable → drop into pack
  → add manifest entry → done. No probe step.
- **Pre-flight 1 retained** as a separate question (``colorbalancergb``
  axis composition under SET-replace) — unrelated to ``iop_order``.
- **Pre-flight 2 closed.** Empirical evidence covers the ``localcontrast``
  multi-instance case (``temperature``, ``exposure``, ``channelmixerrgb``
  all confirmed at ``multi_priority=1``).

---

## The question

The starter vocabulary is deliberately minimal — five entries, Phase 1's explicit
choice (IMPLEMENTATION.md). Phase 2's mandate is vocabulary maturation "from real
session evidence." Taste-library research has now produced a concrete, externally-
validated parameter map: six artist profiles (Van Gogh, Rembrandt, Picasso, Adams,
Capa, Leiter), each specifying tonal, color, texture, and finish parameters. This
gives us a principled target vocabulary — not speculation about what photographers
might want, but a measured inventory of what expressive taste articulation actually
requires.

**Phase positioning.** This RFC inserts a slice-and-gate "Phase 1.2 — vocabulary
expansion" between Phase 1.1 (validation, closed at v1.1.0) and Phase 2 (use-driven
maturation). Ships as **v1.2.0**. Without it, Phase 2 sessions hit the engine
NotImplementedError on Path B and have no path past exposure + WB articulation.
Phase 1.2 closes the engine gap *and* ships the comprehensive baseline vocabulary,
so Phase 2's use-driven work can grow the personal pack on top of a real foundation
rather than bootstrap from five entries.

The parameter map has two tiers:

**Path A (unblocked):** Modules already in the baseline XMP — highlights, sigmoid,
channelmixerrgb — just need .dtstyle entries authored in darktable. No engine
changes. Clean wins.

**Path B (currently blocked):** Modules NOT in the baseline — colorbalancergb,
localcontrast, grain, vignette — need new-instance addition via `synthesize_xmp`,
which raises `NotImplementedError` because the iop_order source-of-truth is
unresolved (RFC-001 left this open; ADR-051 formally deferred it).

The question this RFC argues: **what is the right iop_order strategy for Path B,
and what is the complete Phase 2 vocabulary expansion plan across both paths?**

---

## Use cases

These all come from the taste-library research directly. Each artist profile maps
to a real photographer's workflow:

- **Ansel Adams / Robert Capa (B&W):** agent must convert to B&W via
  `channelmixerrgb` and tune per-channel luminance (blues up for sky drama, greens
  up for foliage). These are Path A. Completely unaddressable today — the module
  is in the baseline but has zero vocab entries.

- **Rembrandt / Robert Capa (deep blacks, vignette):** agent must crush blacks via
  sigmoid and apply heavy vignette. sigmoid is Path A; vignette is Path B.

- **Van Gogh / Saul Leiter (saturation, clarity):** agent must push global
  saturation and make per-channel HSL moves. These require `colorbalancergb` (Path
  B). Leiter's defining move — negative clarity — requires `localcontrast` (Path B).
  Neither is addressable today.

- **Robert Capa (grain):** agent must apply heavy, coarse film grain. Requires the
  `grain` module (Path B). Not addressable today.

- **All profiles (global shadow control):** `tone_lifted_shadows_subject` ships but
  is mask-bound only. A global shadow lift/crush primitive covering highlights and
  shadows in both directions is missing.

---

## Goals

1. Resolve the iop_order source-of-truth question for Path B in a way that is
   practical for vocabulary authors, stable across darktable minor versions, and
   doesn't require Chemigram to decode module param structs.

2. Unblock Path B in `synthesize_xmp` (remove the `NotImplementedError`).

3. Ship a complete Phase 2 vocabulary covering all 20 parameter dimensions from
   the taste-library research, organized as Path A entries (immediately authorable)
   and Path B entries (unblocked by this RFC's decision).

4. Define an authoring workflow that any photographer can follow to author new
   vocabulary entries without knowing darktable internals.

---

## Constraints

- TA/constraints/opaque-hex-blobs — synthesizer does not decode op_params. iop_order
  is metadata, not param content; this constraint doesn't prohibit reading it from
  an XMP probe.
- ADR-008 — .dtstyle capture is the vocabulary mechanism. Path B does not change
  this; it extends what the synthesizer does with the captured file.
- ADR-009 — specifies Path B semantics (must supply iop_order, append new rdf:li,
  increment history_end). This RFC decides the iop_order source, which ADR-009
  left implicit.
- ADR-051 — formally deferred Path B pending this RFC. Synthesizer's
  `NotImplementedError` is the implementation surface that closes when this RFC
  resolves.
- RFC-012 — Path C (programmatic generation) is a separate and complementary
  mechanism. Path B in this RFC is still .dtstyle-based; Path C supplements it
  with per-module encoders for continuous-value control. They coexist.

---

## The iop_order question, resolved

RFC-001 / ADR-051 deferred Path B because Phase 0 evidence suggested
darktable would silently drop new-instance entries that lacked an
``iop_order`` value. This RFC's v0.1 inherited that assumption and built
a probe-iop-order workflow + manifest schema fields around it.

**v0.2 finding:** that assumption is wrong for darktable 5.4.1.

Five Path B scenarios were tested against the Phase 0 raw with
``iop_order`` *absent* from per-entry metadata (only the description-level
``darktable:iop_order_version="4"`` set):

| Scenario | Module | Form | Result |
|-|-|-|-|
| 1 | ``vignette`` | new operation (not in baseline) | applied ✓ |
| 2 | ``grain`` | new operation | applied ✓ |
| 3 | ``exposure`` | new instance at ``multi_priority=1`` | applied ✓ |
| 4 | ``temperature`` | new instance at ``multi_priority=1`` | applied ✓ |
| 5 | ``channelmixerrgb`` | new instance at ``multi_priority=1`` | applied ✓ |

Evidence committed to ``tests/fixtures/preflight-evidence/`` with a
runnable reproducer script. Each rendered output's bytes differ from the
baseline render — a silent drop would have produced identical output.

**Conclusion:** darktable 5.4.1 resolves pipeline order from the
description-level ``iop_order_version`` + its internal iop_list,
regardless of whether per-entry ``iop_order`` is present. Path B can
ship with ``iop_order=None`` for all new entries; the ``HistoryEntry``
field stays Optional in the engine; no probe-iop-order workflow is
needed; no manifest schema extension is needed.

**Forward risk.** If a future darktable version regresses to "drops
entries without iop_order," RFC-018 can reopen and re-introduce the
probe workflow. RFC-007 (modversion drift handling) covers the
detection path. Until then, the simplification stands.

## Pre-flight experiment (one remaining)

### `colorbalancergb` axis independence

Separate question, unrelated to ``iop_order``. Resolved by darktable
authoring experiment before authoring the 11 colorbalancergb entries.

`colorbalancergb` is a single darktable module whose `op_params` is a
single opaque hex blob encoding *all* its parameters together: master
saturation, vibrance, per-channel HSL (red/green/blue × hue/sat), 4-way
color grading (shadows/midtones/highlights × hue/sat), brilliance,
contrast — everything. When darktable serializes a `colorbalancergb`
entry to `.dtstyle`, it captures the *full* module state at export time.
Per ADR-002 SET semantics, applying two `colorbalancergb` entries in
sequence means the second's blob replaces the first's entirely —
including any axes the second entry didn't intend to touch.

**Concrete risk:** apply `sat_boost_strong` (intent: saturation only),
then apply `grade_highlights_warm` (intent: highlight color only). The
second entry's captured saturation values overwrite the first's.
Photographer believes they composed two moves; in reality the second
wiped the first.

**Experiment to run before authoring:** in darktable's style editor,
capture two `colorbalancergb` entries that touch different axes. Apply
both via the synthesizer and inspect the resulting blob. If the second
entry's non-touched axes default to neutral values, axes are *not*
independent — entries clobber. If darktable's authoring workflow
produces blobs that preserve "untouched" axes by some mechanism
(presets, partial-export flag, copy-style-elements dialog), entries
can compose.

**Branching:**

- **If axes compose:** the entry table below stands. Discrete per-axis
  entries are authored as listed.
- **If axes clobber:** ~11 of the 19 Path B entries restructure as
  multi-axis "profiles" — e.g., `cb_vangogh_palette` covering sat +
  grade + per-channel HSL together. Composition is at the profile
  level, not the axis level.

Either outcome is shippable; this experiment decides which.

### Where pre-flight results land

The experiment is run before colorbalancergb authoring begins. Result
recorded in **ADR-063**'s evidence section. The entry table in this
RFC is updated *after* the experiment, with the structure it validates.

---

## Proposed approach

### Part 1: Path B synthesizer implementation

With the iop_order question resolved (see "The iop_order question, resolved"
above), Path B becomes a trivial append:

```python
# Path B — append new instance. dt 5.4.1 resolves pipeline order from
# the description-level iop_order_version + internal iop_list, so
# per-entry iop_order stays None.
new_entry = HistoryEntry(
    num=max(e.num for e in baseline_xmp.history) + 1,
    operation=plugin.operation,
    enabled=True,
    modversion=plugin.modversion,
    multi_name=plugin.multi_name,
    multi_priority=plugin.multi_priority,
    op_params=plugin.op_params,
    blendop_params=plugin.blendop_params,
    blendop_version=plugin.blendop_version,
    iop_order=None,
)
new_history = baseline_xmp.history + (new_entry,)
new_history_end = baseline_xmp.history_end + 1
```

No new `VocabEntry` field. No probe step. No manifest schema extension.
The existing `_plugin_to_history` helper already produces a `HistoryEntry`
with `iop_order=None`; Path B's append branch just uses it.

**Latent type bug** (already shipped, see issue #42): the existing
`HistoryEntry.iop_order` field was typed `int | None` and parsed via
`_int_attr`. darktable's `iop_order` values are floats when present
(though absent in dt 5.4.1's `.dtstyle` files and `<rdf:li>` entries
when not set). Fixed by changing the field to `float | None` and adding
a `_float_attr` helper. Independent of this RFC's iop_order resolution
— sidecars and rendered embedded XMP can still surface floats; the
parser must handle them.

### Part 2: v1.2.0 vocabulary plan

The full parameter map from the taste-library research, organized by path and
priority. All 35 new entries ship in a new pack at
`vocabulary/packs/expressive-baseline/`, distinct from the existing minimal
`vocabulary/starter/` (which preserves its character as a 5-entry teaching
artifact). Photographers opt in by listing `expressive-baseline` in their pack
config alongside `starter`. See "Pack location" in the trade-offs section for
the rationale.

#### Path A — author now, no engine changes

| Entry name | Module | What it covers | Artist profiles |
|---|---|---|---|
| `highlights_recovery_subtle` | highlights | Gentle highlight pull-back | Rembrandt, Adams |
| `highlights_recovery_strong` | highlights | Aggressive highlight pull-back | Capa |
| `contrast_low` | sigmoid | Flatten contrast (compressed range) | Leiter, Picasso |
| `contrast_medium` | sigmoid | Moderate contrast boost | Van Gogh, Leiter |
| `contrast_high` | sigmoid | Strong contrast (Capa/Rembrandt range) | Rembrandt, Capa, Adams |
| `blacks_lifted` | sigmoid | Lift black point (Leiter: +15) | Leiter |
| `blacks_crushed` | sigmoid | Crush black point (Rembrandt/Capa: -60) | Rembrandt, Capa |
| `whites_open` | sigmoid | Open white point (Adams Zone X) | Adams |
| `bw_convert` | channelmixerrgb | Desaturate to B&W, neutral mix | Adams, Capa |
| `bw_sky_drama` | channelmixerrgb | B&W + blue channel luminance down | Adams (Zone sky) |
| `bw_foliage` | channelmixerrgb | B&W + green channel luminance up | Adams (luminous trees) |
| `wb_cool_subtle` | temperature | Cool white balance, subtle | Picasso, Adams |
| `shadows_global_lift` | exposure | Global shadow lift without mask | Leiter, Van Gogh |
| `shadows_global_crush` | exposure | Global shadow crush without mask | Rembrandt, Capa |
| `expo_+0.3` | exposure | Finer exposure step | All |
| `expo_-0.3` | exposure | Finer exposure step | All |

#### Path B — blocked on iop_order; unblocked by this RFC

| Entry name | Module | What it covers | Artist profiles |
|---|---|---|---|
| `sat_boost_strong` | colorbalancergb | Global saturation +60–70 | Van Gogh |
| `sat_boost_moderate` | colorbalancergb | Global saturation +20–30 | Leiter |
| `sat_kill` | colorbalancergb | Global desaturation -55 | Picasso, Capa |
| `vibrance_lift` | colorbalancergb | Vibrance +30–40 | Van Gogh, Leiter |
| `grade_highlights_warm` | colorbalancergb | Highlight color grade → amber | Rembrandt, Van Gogh |
| `grade_highlights_cold` | colorbalancergb | Highlight color grade → blue-white | Picasso |
| `grade_shadows_warm` | colorbalancergb | Shadow color grade → warm brown | Rembrandt |
| `grade_shadows_cold` | colorbalancergb | Shadow color grade → blue-grey | Picasso |
| `hsl_yellows_vg` | colorbalancergb | Yellow hue +15° toward green, sat +60 | Van Gogh |
| `hsl_blues_vg` | colorbalancergb | Blue hue -10° toward cyan, sat +55 | Van Gogh |
| `hsl_oranges_purge` | colorbalancergb | Orange saturation -60 (purge warmth) | Picasso |
| `clarity_strong` | localcontrast | Local contrast +50 (texture/sharpness) | Van Gogh, Adams, Capa |
| `clarity_painterly` | localcontrast | Local contrast -20 (edge softness) | Leiter |
| `grain_fine` | grain | Fine grain, low density (Adams/Leiter) | Adams, Leiter |
| `grain_medium` | grain | Medium grain, moderate density | Rembrandt |
| `grain_heavy` | grain | Heavy grain, high roughness (Capa: 85–90) | Capa, Van Gogh |
| `vignette_subtle` | vignette | Subtle vignette (-15) | Adams |
| `vignette_medium` | vignette | Moderate vignette (-40) | Capa, Picasso |
| `vignette_heavy` | vignette | Heavy vignette (-70) | Rembrandt |

#### Entry counts

| Tier | Count | Engine work required | Pack |
|---|---|---|---|
| Path A, new entries | 16 | None — authoring only | `packs/expressive-baseline/` |
| Path B, new entries | 19 | synthesizer Path B (shipped post-v0.2) | `packs/expressive-baseline/` |
| Already shipped | 5 | — | `starter/` (unchanged) |
| **Total v1.2.0 target** | **40** | — | starter + expressive-baseline |

#### Authoring workflow for Path B entries

Same as Path A — the iop_order resolution removes the probe step:

1. Open darktable. Load a reference raw file (the same one used for vocabulary
   calibration — `tests/fixtures/` includes suitable examples).
2. Enable the target module (e.g., grain). Dial in the desired parameters.
3. Export as `.dtstyle` to `vocabulary/packs/expressive-baseline/layers/L3/<subtype>/<name>.dtstyle`.
4. Add the manifest entry to `vocabulary/packs/expressive-baseline/manifest.json`
   with the standard fields (`name`, `layer`, `path`, `touches`,
   `darktable_version`, etc.).
5. Run vocabulary CI (`make vocab-check`) to validate.

The synthesizer's Path B implementation handles the rest: when the
agent applies the entry, the synthesizer detects the new
`(operation, multi_priority)` tuple and appends a `HistoryEntry` with
`iop_order=None`. darktable resolves pipeline position at render time.

This workflow is documented in full in CONTRIBUTING.md § Vocabulary authoring.

---

## Alternatives considered

**Strategy X — XMP probe at authoring time** (RFC-018 v0.1's proposal).
During vocabulary authoring, run a darktable-cli render with the
relevant module active and inspect the resulting XMP sidecar to extract
`iop_order` for the target operation. Store it in the vocabulary
manifest. The synthesizer reads it from the manifest at apply time.
Rejected in v0.2 because the empirical evidence shows darktable 5.4.1
doesn't require per-entry `iop_order` — Strategy X would ship
infrastructure (probe script, manifest schema fields, validator rules)
that solves a non-problem.

**Strategy Y — static lookup table** (parse darktable's C source).
Maintain a hardcoded dict `{(operation, modversion): iop_order}` in the
engine. Rejected: couples Chemigram to darktable internals not exposed
as a public API; would require maintenance per darktable release;
brittle to pipeline reorderings that don't bump iop_order_version.

**Strategy Z — runtime probe per apply.** Run darktable-cli at apply
time when iop_order is unknown. Rejected: adds latency to every first
apply of a Path B primitive, requires a raw at apply time (not always
available, especially in test environments).

**Alternative vocabulary strategy: defer Path B entirely, expand Path A only.**
The five Path A wins (B&W, sigmoid, highlights) are real and immediately useful. We
could ship them alone without resolving the iop_order question. Rejected: the most
distinctive and artistically significant parameters — saturation, clarity, grain,
vignette, color grading — are all Path B. Shipping Path A alone produces a vocabulary
that handles Adams and Capa but cannot begin to articulate Van Gogh, Leiter, or
Rembrandt. The research is clear that these are the high-value targets.

**Alternative vocabulary strategy: use LUT-based looks (L2) for the complex painter
profiles instead of discrete L3 primitives.** Van Gogh's color tension could be
captured as a single L2 `.dtstyle` with all HSL moves baked in. Rejected for two
reasons. First, it conflicts with Chemigram's compositional philosophy: the agent
should be able to mix and match discrete moves, not only apply baked looks. Second,
it doesn't solve the underlying capability gap — a baked L2 still requires the
same modules (colorbalancergb) that Path B needs.

**Alternative vocabulary structure: one "profile" .dtstyle per artist rather than
discrete primitives.** Ship `look_vangogh.dtstyle` as a single L2 entry applying
all of Van Gogh's moves at once. This would work for Mode B autonomous edits but
doesn't serve Mode A collaborative editing where the photographer and agent negotiate
individual dimensions. Rejected as primary strategy; can be shipped as a convenience
L2 entry alongside the discrete L3 primitives.

---

## Trade-offs

**Trust in the empirical finding.** The simplification rests on five
empirical scenarios (vignette, grain, exposure mp=1, temperature mp=1,
channelmixerrgb mp=1) confirming Path B works without per-entry
`iop_order` in dt 5.4.1. We didn't test every module; if a module
exists where darktable does silently drop iop_order-less entries, that
specific module would need Strategy X re-introduced. Mitigation: each
authored Path B entry's e2e test asserts direction-of-change against
real bytes — so any silently-dropped entry surfaces as a test failure
during authoring, not in production.

**Pipeline-order drift in future darktable versions.** All entries are
authored against darktable 5.4.1's iop_order_version=4. If a future
darktable bumps `iop_order_version` and reorders modules in its
internal iop_list, vocabulary entries may render at a different
pipeline position than intended. RFC-007 (modversion drift) handles
the detection + warning path. Real risk: darktable's pipeline order
has been stable across 5.x; this is a low-frequency concern.

**40 vocabulary entries is a meaningful authoring investment.** The
16 Path A entries are straightforward; the 19 Path B entries follow
the same workflow now (no probe step). The v1.2.0 plan in
IMPLEMENTATION.md phases the work internally: pre-flight 1 (cb axis
test) first, then ADR-063 implementation, then Path A authoring
(immediate wins), then Path B grouped by module.

**colorbalancergb covers many parameter dimensions.** Saturation, vibrance, HSL per
channel, and color grading all live in the same module. A single `sat_boost_strong`
entry may conflict unexpectedly with a `grade_highlights_warm` entry if both touch
the same colorbalancergb params. The SET semantics (ADR-002) mean later-applied
entries replace earlier ones; the agent must understand that these entries are not
independent along all axes. Resolved by Pre-flight 1 above; if axes clobber, the
entry table restructures as multi-axis profiles before authoring.

### Costs and risks

This is a v1.2.0 milestone, not a free upgrade. Updated accounting after
the v0.2 simplification:

- **35 new e2e render tests.** Per `docs/testing.md`, every shipped primitive
  has an e2e render assertion against real darktable. 35 entries × one assertion
  each = 35 new e2e tests. Wall-clock for the full e2e suite grows from ~90s to
  an estimated 3–4 minutes. Acceptable for `make test-e2e` (gated, not in CI per
  ADR-040), but the suite-time line crosses into "non-trivial."

- **Mode A prompt rework.** The agent currently sees 5 entries via
  `list_vocabulary`. With 40, the prompt's vocabulary-presentation section needs
  an iteration (Mode A `system_v3.j2`). Tasteful presentation of 40 entries is
  itself a design decision — list-by-tag, tier categorization, or some other
  scheme. Worth a short ADR or RFC sub-section in ADR-064.

- **Concentration risk under darktable drift.** All 40 entries are calibrated to
  darktable 5.4.1. If darktable bumps a module's `modversion` or reorders its
  pipeline, all 40 entries are simultaneously vulnerable to re-validation work.
  Spreading authoring over Phase 2 would have spread this risk across time.
  Mitigation: each entry's manifest carries `darktable_version: "5.4"`, plus
  RFC-007 (modversion drift) handling at load time. RFC-007 is still open;
  it should close before or alongside RFC-018.

- **Time investment.** Updated estimate post-simplification: pre-flight 1
  (colorbalancergb axis test) ~0.5 day, engine unblock (synthesizer Path B
  + ADR-063) ~1 day, Path A authoring ×16 ~2–3 days, Path B authoring ×19
  ~3–4 days (no probe step), e2e tests for all 35 ~2 days (parallelizable),
  Mode A prompt v3 + ADR-064 + polish ~1 day. **Total estimate: ~10–12
  working days for v1.2.0** (down from 13–15 in v0.1).

### Pack location

Why `vocabulary/packs/expressive-baseline/` rather than expanding `vocabulary/starter/`:

- `/starter` was deliberately a *minimal teaching artifact* (ADR-024,
  IMPLEMENTATION.md Slice 6). Inflating it to 40 entries changes its character
  from "show me 5 well-shaped entries so I see the pattern" to "comprehensive
  baseline vocabulary." Two distinct artifacts deserve two distinct locations.
- The pack architecture already exists conceptually (manifest pack roots are
  parameterized in `VocabularyIndex`). This is the natural home.
- Photographers opt-in: starter gets you running and teaches the conventions;
  expressive-baseline gets you to the artist-profile parameter map. Two-line
  config in `~/.chemigram/packs.toml`.
- If genre packs (`/packs/underwater`, `/packs/wedding`) ship later, the
  architecture extends with no backward-incompat surprises.

The starter pack stays at 5 entries, unchanged in v1.2.0. Documentation in
`getting-started.md` is updated to recommend the expressive-baseline pack as the
default-on installation.

---

## Open questions

(Pre-flight 1 above is *not* an open question; it's an empirical
precondition that blocks the entry table's structure and must be resolved
by darktable authoring experiment before authoring begins. The questions
below are real deliberation items that can be settled in the closing ADRs.)

**Q1: Should L2 "artist profile" entries ship alongside the L3 primitives?**
A `look_rembrandt.dtstyle` baking all Rembrandt parameters into a single L2 is
useful for Mode B ("apply a Rembrandt-style edit to this batch"). The primitives are
needed for Mode A negotiation. Recommendation: ship the L3 primitives first; add L2
artist profiles as a follow-on if Mode B session evidence shows they're useful.

**Q2: How should `list_vocabulary` and the Mode A prompt present 40+ entries?**
Currently the prompt receives ~5 entries inline. With 40, options include
list-by-tag (one section per tag), tier-categorized (L1/L2/L3 with subsections by
subtype), or compressed (just names + one-line descriptions). Belongs in ADR-064 or
a Mode A prompt v3 sub-design.

---

## How this closes

This RFC closes into two ADRs:

**ADR-063 — Path B unblocking.** Closes RFC-001's iop_order open
question with the empirical evidence in
``tests/fixtures/preflight-evidence/``: darktable 5.4.1 doesn't require
per-entry ``iop_order``. Documents the trivial Path B implementation
(append `HistoryEntry` with `iop_order=None`; increment `history_end`),
references the `HistoryEntry.iop_order: float | None` type fix, and
records the Pre-flight 1 (colorbalancergb axis independence) outcome
that decided the entry table structure. Supersedes ADR-051's
"NotImplementedError until iop_order is resolved" stance.

**ADR-064 — Vocabulary authoring workflow.** Documents the
CONTRIBUTING.md authoring steps for both Path A and Path B (now the
same workflow), CI validation requirements, and the Mode A prompt v3
vocabulary-presentation strategy for 40+ entries.

The specific entries shipped in v1.2.0 are recorded in
`vocabulary/packs/expressive-baseline/manifest.json` (the source-of-truth)
and the v1.2.0 CHANGELOG entry. No separate ADR is needed for "what
shipped" — that's manifest territory, not architectural decision territory.

RFC-018 closes when Pre-flight 1 (colorbalancergb axes) is run, ADR-063
+ ADR-064 land, and the v1.2.0 release ships with the full
expressive-baseline pack populated.

---

## Links

- TA/components/synthesizer — `synthesize_xmp` is the implementation surface
- TA/components/mcp-server — `apply_primitive` tool calls synthesize_xmp
- RFC-001 — synthesizer architecture; iop_order open question originated here
- RFC-007 — modversion drift handling; concentration risk on 40 entries calibrated to dt 5.4.1 (each entry's manifest `darktable_version: "5.4"` field is the drift-detection key). Should close before or alongside RFC-018.
- RFC-012 — Path C (programmatic generation); complementary, not conflicting
- ADR-009 — Path A vs Path B semantics (this RFC decides iop_order for Path B)
- ADR-051 — formal deferral of Path B; this RFC picks it up
- ADR-008 — opaque-blob constraint (synthesizer does not decode op_params)
- ADR-024 — authoring discipline; underpins keeping `/starter` minimal
- `docs/IMPLEMENTATION.md` — Phase 1.2 row tracks this RFC's milestone
- `docs/TODO.md` — "Programmatic vocabulary entry generation" and color science items
- `tests/fixtures/preflight-evidence/` — the empirical evidence that overturned RFC-018 v0.1's iop_order assumption
- `vocabulary/starter/manifest.json` — minimal starter pack (5 entries, unchanged in v1.2.0)
- `vocabulary/packs/expressive-baseline/manifest.json` — v1.2.0 expansion (35 new entries)
- taste-library POC research — the artist profiles driving the parameter map
