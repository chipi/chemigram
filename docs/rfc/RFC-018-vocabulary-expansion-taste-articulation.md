# RFC-018 — Vocabulary expansion for expressive taste articulation

> Status · Draft v0.1
> TA anchor ·/components/synthesizer ·/components/mcp-server ·/constraints
> Related · RFC-001, RFC-007, RFC-012, ADR-001, ADR-009, ADR-051, ADR-008
> Closes into · ADR-063 (Path B iop_order strategy), ADR-064 (Phase 1.2 vocabulary
>               authoring workflow)
> Phase · Phase 1.2 — vocabulary expansion. Slice-and-gate work that lands
>         before Phase 2's use-driven authoring begins. Ships as v1.2.0.
> Why this is an RFC · The vocabulary currently ships five entries covering
>                      exposure and white balance only. Expressive taste
>                      articulation — including every parameter in the six
>                      artist profiles developed in the taste-library POC —
>                      requires roughly 20 distinct parameter dimensions.
>                      Half can be addressed by authoring .dtstyle entries for
>                      modules already in the baseline (Path A, unblocked).
>                      The other half require Path B new-instance addition, which
>                      currently raises NotImplementedError because iop_order is
>                      absent from darktable 5.4.1 .dtstyle files (RFC-001 open
>                      question). This RFC argues the iop_order strategy and the
>                      full v1.2.0 vocabulary expansion plan across both paths.

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

## Pre-flight experiments

Two questions must be resolved by darktable authoring experiment **before** the
proposed approach can be finalized. These are not "open questions to deliberate";
they're empirical preconditions that decide the structure of the entry table.
Authoring 11 entries that turn out to clobber each other is wasted work, so the
experiments come first.

### Pre-flight 1: `colorbalancergb` axis independence

`colorbalancergb` is a single darktable module whose `op_params` is a single
opaque hex blob encoding *all* its parameters together: master saturation,
vibrance, per-channel HSL (red/green/blue × hue/sat), 4-way color grading
(shadows/midtones/highlights × hue/sat), brilliance, contrast — everything. When
darktable serializes a `colorbalancergb` entry to `.dtstyle`, it captures the
*full* module state at export time. Per ADR-002 SET semantics, applying two
`colorbalancergb` entries in sequence means the second's blob replaces the first's
entirely — including any axes the second entry didn't intend to touch.

**Concrete risk:** apply `sat_boost_strong` (intent: saturation only), then apply
`grade_highlights_warm` (intent: highlight color only). The second entry's
captured saturation values overwrite the first's. Photographer believes they
composed two moves; in reality the second wiped the first.

**Experiment to run before authoring:** in darktable's style editor, capture two
`colorbalancergb` entries that touch different axes. Apply both via the synthesizer
and inspect the resulting blob. If the second entry's non-touched axes default to
neutral values, axes are *not* independent — entries clobber. If darktable's
authoring workflow produces blobs that preserve "untouched" axes by some mechanism
(presets, partial-export flag, copy-style-elements dialog), entries can compose.

**Branching:**

- **If axes compose:** the entry table below stands. Discrete per-axis entries are
  authored as listed.
- **If axes clobber:** ~11 of the 19 Path B entries restructure as multi-axis
  "profiles" — e.g., `cb_vangogh_palette` covering sat + grade + per-channel HSL
  together. Composition is at the profile level, not the axis level.

Either outcome is shippable; this experiment decides which.

### Pre-flight 2: `localcontrast` instance independence

`localcontrast` is a different shape: it's expected to support *multiple
simultaneous instances* via `multi_priority`, where each instance carries its own
parameters. So `clarity_strong` and `clarity_painterly` would coexist as separate
`(operation="localcontrast", multi_priority=N)` entries rather than clobber.

**Experiment to run before authoring:** capture a `clarity_strong` entry at
`multi_priority=0`, and a `clarity_painterly` entry at `multi_priority=1`. Verify
both apply via the synthesizer and the rendered output reflects both. Lower
priority than Pre-flight 1 because the failure mode is just "same shape as
colorbalancergb" — covered by Pre-flight 1's branching.

### Where pre-flight results land

Both experiments are run before any Path B authoring begins. Results are recorded
in **ADR-063**'s "experiment evidence" section before the ADR is marked Accepted.
The entry table in this RFC is updated *after* the experiments, with the structure
the experiments validate.

---

## Proposed approach

### Part 1: iop_order strategy for Path B

The fundamental problem: darktable 5.4.1 does not write `<iop_order>` into
`.dtstyle` files. A `.dtstyle` produced by darktable's style editor contains
`<plugin>` entries with `op_params`, `blendop_params`, `operation`, `multi_priority`,
and `multi_name` — but no `iop_order` element. RFC-001 observed this empirically
in Phase 0.

ADR-009 anticipated this would be solved by "copying from the .dtstyle file's
`<iop_order>` element" — but that element is absent. Three strategies exist:

**Strategy X — XMP probe (proposed).**
During vocabulary authoring, run a darktable-cli render with the relevant module
active and inspect the resulting XMP sidecar. darktable writes the full history
including `iop_order` values for every module into the sidecar. Extract the
iop_order for the target operation from this probe XMP. Store it in the vocabulary
manifest entry alongside the .dtstyle path.

```json
{
  "name": "grain_heavy",
  "layer": "L3",
  "subtype": "grain",
  "path": "layers/L3/grain/grain_heavy.dtstyle",
  "touches": ["grain"],
  "iop_order": 47.4747,
  "iop_order_source": "xmp_probe",
  "iop_order_darktable_version": "5.4.1",
  ...
}
```

The synthesizer reads `iop_order` from the manifest entry (not from the .dtstyle
file itself) when executing Path B. The authoring script (`scripts/probe-iop-order.sh`)
automates the probe: given a raw file and a .dtstyle, it renders, parses the sidecar,
extracts iop_order for the specified operation, and writes it into the manifest.

Stability: iop_order values are determined by darktable's module pipeline order,
which is stable within a major version and changes only when darktable explicitly
reorders its pipeline (rare, usually announced). The manifest tracks the darktable
version at authoring time (`iop_order_darktable_version`). RFC-007 (modversion drift)
handles the validation/warning path when darktable versions diverge.

**Strategy Y — static lookup table.**
Maintain a hardcoded dict `{(operation, modversion): iop_order}` in the engine,
populated by reading darktable's source or iop_order registry. This is accurate but
brittle: darktable's pipeline order is not part of its public API, the table would
need manual maintenance per darktable release, and it couples the engine to internal
darktable implementation details.

**Strategy Z — runtime probe per apply.**
When Path B is triggered and iop_order is unknown, run a quick darktable-cli probe
at apply time to extract the value. Correct but adds latency to every first apply
of a Path B primitive and requires a raw file available at apply time (not always
guaranteed, especially in test environments).

**Proposed: Strategy X.** The probe happens once at authoring time, not at apply
time. The result is stored in the manifest alongside the .dtstyle. The synthesizer
reads it from the manifest. This keeps the hot path (apply_primitive) free of
darktable invocations and makes iop_order an explicit, inspectable part of the
vocabulary manifest — not implicit engine knowledge.

Authoring requirement: the `scripts/probe-iop-order.sh` script must be run as part
of vocabulary authoring for Path B entries. This is a workflow constraint, not a
code constraint. CONTRIBUTING.md documents it.

### Part 2: Path B synthesizer implementation

Once iop_order is available in the manifest, `synthesize_xmp` can implement Path B.
The `NotImplementedError` block becomes:

```python
# Path B — append new instance
# iop_order must be present in the entry's manifest metadata.
# Callers (apply_primitive tool) are responsible for ensuring the
# VocabEntry was loaded with iop_order from the manifest.
if entry.iop_order is None:
    raise VocabEntryMissingIopOrder(
        f"Path B entry {entry.name!r} has no iop_order; "
        "re-author using scripts/probe-iop-order.sh"
    )
new_entry = HistoryEntry(
    num=max(e.num for e in baseline_xmp.history) + 1,
    operation=plugin.operation,
    enabled=True,
    modversion=plugin.modversion,
    multi_name="",
    multi_priority=plugin.multi_priority,
    op_params=plugin.op_params,
    blendop_params=plugin.blendop_params,
    blendop_version=plugin.blendop_version,
    iop_order=entry.iop_order,
)
new_history = baseline_xmp.history + (new_entry,)
new_history_end = baseline_xmp.history_end + 1
```

`VocabEntry` gains an optional `iop_order: float | None` field. `VocabularyIndex`
loads it from the manifest. No changes to `DtstyleEntry` or the parser (the probe
result lives in the manifest, not the .dtstyle).

**Latent type bug to fix as part of Path B work.** The existing
`HistoryEntry.iop_order` field in `src/chemigram/core/xmp.py` (line 88) is typed
`int | None`, parsed via `_int_attr` at line 170. darktable's actual `iop_order`
values are floats (e.g., `47.4747` — the example in this RFC's Strategy X). The
field is currently dormant-buggy because dt 5.4.1 writes no `iop_order` to
`.dtstyle` files, so the int parse path is never exercised. Path B wakes it up.

The fix is part of this RFC's implementation:

- `HistoryEntry.iop_order: int | None` → `float | None`
- Parser uses `_float_attr` (or equivalent), not `_int_attr`
- `VocabEntry.iop_order` declared `float | None` from the start
- `synthesize_xmp`'s Path B branch passes the float through verbatim

Tests for the fix: parser round-trips a sidecar XMP containing float
`iop_order` values (the probe outputs are exactly such sidecars), and the
synthesizer's new Path B unit tests cover the float-typed append path.

### Part 3: v1.2.0 vocabulary plan

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
| Path B, new entries | 19 | iop_order in manifest + synthesizer Path B | `packs/expressive-baseline/` |
| Already shipped | 5 | — | `starter/` (unchanged) |
| **Total v1.2.0 target** | **40** | — | starter + expressive-baseline |

#### Authoring workflow for Path B entries

1. Open darktable. Load a reference raw file (the same one used for vocabulary
   calibration — `tests/fixtures/` includes suitable examples).
2. Enable the target module (e.g., grain). Dial in the desired parameters.
3. Export as `.dtstyle` to `vocabulary/packs/expressive-baseline/layers/L3/<subtype>/<name>.dtstyle`.
4. Run `scripts/probe-iop-order.sh <raw_file> <dtstyle_path> <operation>`.
   The script outputs the iop_order value and patches it into a manifest stub.
5. Add the manifest entry to `vocabulary/packs/expressive-baseline/manifest.json`
   with `iop_order` and `iop_order_source: "xmp_probe"` and
   `iop_order_darktable_version`.
6. Run vocabulary CI (`make vocab-check`) to validate.

This workflow is documented in full in CONTRIBUTING.md § Vocabulary authoring.

---

## Alternatives considered

**Alternative iop_order strategy: parse darktable's C source to build a static
table.** darktable maintains a `iop_order_version` system with a C-struct iop_list.
This could be parsed to produce a definitive lookup. Rejected: couples Chemigram to
darktable internals not exposed as a public API; would require maintenance per
darktable release; brittle to pipeline reorderings that don't bump iop_order_version.

**Alternative iop_order strategy: embed iop_order in the .dtstyle file manually.**
When authoring, manually add an `<iop_order>` element to the .dtstyle XML. Rejected:
requires vocabulary authors to know the exact float value, which they can't determine
without running the probe anyway. Storing it in the manifest (alongside the .dtstyle)
is cleaner separation.

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

**The probe workflow adds a step to Path B authoring.** Authors can't just dial in
darktable and export — they must also run the probe script. Mitigated by
automation: the script is one line and produces the manifest stub directly.

**iop_order in the manifest is version-pinned to the darktable version at authoring
time.** If darktable reorders its pipeline in a future version, Path B entries
authored against the old order will silently apply at the wrong pipeline position.
The `iop_order_darktable_version` field enables RFC-007's drift detection to catch
this. Real risk: darktable's pipeline order has been stable across 5.x; this is a
low-frequency concern.

**40 vocabulary entries is a meaningful authoring investment.** The 16 Path A entries
are straightforward; the 19 Path B entries each require the probe workflow. The
v1.2.0 plan in IMPLEMENTATION.md should phase the work internally: pre-flight
experiments first, then ADR-063 implementation + probe script, then Path A authoring
(immediate wins, no engine dependency), then Path B grouped by module (all grain
entries together, all colorbalancergb entries together, etc.).

**colorbalancergb covers many parameter dimensions.** Saturation, vibrance, HSL per
channel, and color grading all live in the same module. A single `sat_boost_strong`
entry may conflict unexpectedly with a `grade_highlights_warm` entry if both touch
the same colorbalancergb params. The SET semantics (ADR-002) mean later-applied
entries replace earlier ones; the agent must understand that these entries are not
independent along all axes. Resolved by Pre-flight 1 above; if axes clobber, the
entry table restructures as multi-axis profiles before authoring.

### Costs and risks

This is a v1.2.0 milestone, not a free upgrade. Honest accounting:

- **35 new e2e render tests.** Per `docs/testing.md`, every shipped primitive
  has an e2e render assertion against real darktable. 35 entries × one assertion
  each = 35 new e2e tests. Wall-clock for the full e2e suite grows from ~90s to
  an estimated 3–4 minutes. Acceptable for `make test-e2e` (gated, not in CI per
  ADR-040), but the suite-time line crosses into "non-trivial."

- **35 probe runs at authoring time.** Each Path B entry requires
  `scripts/probe-iop-order.sh`. Mitigated by automation but it's still 19
  authoring sessions × probe step.

- **Mode A prompt rework.** The agent currently sees 5 entries via
  `list_vocabulary`. With 40, the prompt's vocabulary-presentation section needs
  an iteration (Mode A `system_v3.j2`). Tasteful presentation of 40 entries is
  itself a design decision — list-by-tag, tier categorization, or some other
  scheme. Worth a short ADR or RFC sub-section in ADR-064.

- **Concentration risk under darktable drift.** All 40 entries are calibrated to
  darktable 5.4.1. If darktable bumps a module's `modversion` or reorders its
  pipeline, all 40 entries are simultaneously vulnerable to re-validation work.
  Spreading authoring over Phase 2 would have spread this risk across time.
  Mitigation: `iop_order_darktable_version` in each manifest entry, plus RFC-007
  (modversion drift) handling at load time. RFC-007 is still open; it should
  close before or alongside RFC-018.

- **Time investment.** Realistic estimate: pre-flight experiments (~1 day), engine
  unblock + probe + ADR-063/064 (~3 days), Path A authoring ×16 (~2–3 days at
  ~8 entries/day), Path B authoring ×19 (~4–5 days, slower per entry due to
  probe + per-module calibration), e2e tests for all 35 (~2 days, mostly
  parallelizable with authoring), Mode A prompt v3 + final polish (~1 day).
  **Total estimate: ~13–15 working days for v1.2.0.** This is a real milestone,
  not a side project.

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

(Pre-flight 1 + Pre-flight 2 above are *not* open questions; they're empirical
preconditions that block the entry table's structure and must be resolved by
darktable authoring experiment before authoring begins. The questions below are
real deliberation items that can be settled in the closing ADRs.)

**Q1: Does the probe script need a calibration fixture or can it use any raw?**
iop_order values should be stable across images (they're module-order, not
image-dependent), but this should be confirmed. Recommendation: use the same fixture
raw file (the Phase 0 raw at `~/chemigram-phase0/raws/raw-test.NEF`) for all probes
to ensure consistency in CI validation, with the script accepting any raw as a
fallback.

**Q2: Should L2 "artist profile" entries ship alongside the L3 primitives?**
A `look_rembrandt.dtstyle` baking all Rembrandt parameters into a single L2 is
useful for Mode B ("apply a Rembrandt-style edit to this batch"). The primitives are
needed for Mode A negotiation. Recommendation: ship the L3 primitives first; add L2
artist profiles as a follow-on if Mode B session evidence shows they're useful.

**Q3: How should `list_vocabulary` and the Mode A prompt present 40+ entries?**
Currently the prompt receives ~5 entries inline. With 40, options include
list-by-tag (one section per tag), tier-categorized (L1/L2/L3 with subsections by
subtype), or compressed (just names + one-line descriptions). Belongs in ADR-064 or
a Mode A prompt v3 sub-design.

---

## How this closes

This RFC closes into two ADRs:

**ADR-063 — Path B iop_order strategy.** Commits to Strategy X (manifest-stored,
probe-derived iop_order). Specifies the manifest schema extension, the synthesizer
change (removing `NotImplementedError`, implementing the append path with the
`int → float` type fix on `HistoryEntry.iop_order`), and the
`VocabEntry.iop_order` field. Includes an "experiment evidence" section recording
the Pre-flight 1 (colorbalancergb axis independence) and Pre-flight 2
(`localcontrast` instance independence) outcomes that decided the entry table's
structure.

**ADR-064 — Vocabulary authoring workflow for Path B.** Documents the probe script,
the CONTRIBUTING.md authoring steps, CI validation requirements for Path B manifest
entries, and the Mode A prompt v3 vocabulary-presentation strategy for 40+ entries.
Closes the gap between "author a .dtstyle" and "safely ship a Path B entry."

The specific entries shipped in v1.2.0 are recorded in
`vocabulary/packs/expressive-baseline/manifest.json` (the source-of-truth) and the
v1.2.0 CHANGELOG entry. No separate ADR is needed for "what shipped" — that's
manifest territory, not architectural decision territory.

RFC-018 closes when Pre-flight 1 + Pre-flight 2 are run, ADR-063 + ADR-064 land,
and the v1.2.0 release ships with the full expressive-baseline pack populated.

---

## Links

- TA/components/synthesizer — `synthesize_xmp` is the implementation surface
- TA/components/mcp-server — `apply_primitive` tool calls synthesize_xmp
- RFC-001 — synthesizer architecture; iop_order open question originated here
- RFC-007 — modversion drift handling; `iop_order_darktable_version` drift lands here. Should close before or alongside RFC-018 to handle the concentration risk on 40 entries calibrated to 5.4.1.
- RFC-012 — Path C (programmatic generation); complementary, not conflicting
- ADR-009 — Path A vs Path B semantics (this RFC decides iop_order for Path B)
- ADR-051 — formal deferral of Path B; this RFC picks it up
- ADR-008 — opaque-blob constraint (synthesizer does not decode op_params)
- ADR-024 — authoring discipline; underpins keeping `/starter` minimal
- `docs/IMPLEMENTATION.md` — Phase 1.2 row tracks this RFC's milestone
- `docs/TODO.md` — "Programmatic vocabulary entry generation" and color science items
- `vocabulary/starter/manifest.json` — minimal starter pack (5 entries, unchanged in v1.2.0)
- `vocabulary/packs/expressive-baseline/manifest.json` — v1.2.0 expansion (35 new entries)
- taste-library POC research — the artist profiles driving the parameter map
