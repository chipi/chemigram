# RFC-025 — Spot removal / heal architecture

> Status · Draft v0.1
> Date · 2026-05-08
> TA anchor ·/components/synthesizer ·/contracts/per-image-repo ·/components/masking ·/constraints/opaque-hex-blobs
> Related · ADR-076 (drawn-mask only architecture; this RFC argues to extend), RFC-024 (range masks; this RFC's mask-architectural sibling), ADR-007 (BYOA principle), capability-survey.md § 10 ("Truly novel-shape gaps" — retouch / spot healing is named as the major portrait gap), #108 (the issue that opened this question)
> Closes into · ADR-NNN (pending — the architectural shape decision); possible follow-up RFC-026 for AI-content-aware variants if the sibling-provider path is chosen
> Why this is an RFC · ADR-076 settled v1.5.0's mask architecture as drawn-only after the PNG-mask path was discovered to be a silent no-op. RFC-024 argued the extension for content-derived range masks. The third major mask-adjacent gap is **stroke-based pixel-level edits** — Lightroom's spot removal / heal / clone — which are notably absent from chemigram's vocabulary today. capability-survey § 10 names this as "*the* major portrait gap." Initial framing assumed pixel-level edits don't fit byte-patching cleanly and would need a sibling provider, but reading darktable's `retouch` module reveals the struct is form-array-based with each form referencing a `mask_id` from `masks_history` — the same shape ADR-076 already serializes for drawn forms. That changes the cost shape from "qualitatively different architectural arc" to "extension of drawn-mask byte serialization." Worth deliberating which path lands here.

---

## The question

Lightroom's spot removal / heal / clone is the workflow for blemish removal, dust spots, sensor-dust cleanup, distracting-element removal, and the canonical portrait retouch (skin clean-up). Today chemigram has no equivalent. The drawn-mask path can *select* a region (ellipse, gradient, rectangle), but no primitive *replaces* the pixels — the photographer's mental model "remove this spot" doesn't have a vocabulary verb.

darktable's `retouch` module (mv3) is the obvious target. Reading the struct reveals:

```c
typedef struct dt_iop_retouch_params_t
{
  dt_iop_retouch_form_data_t rt_forms[RETOUCH_NO_FORMS];  // 300-form fixed array
  dt_iop_retouch_algo_type_t algorithm;                   // clone / heal / blur / fill
  // ... wavelet / preview / blur / fill globals ...
} dt_iop_retouch_params_t;
```

Each `rt_forms[i]` carries a `formid` referencing a `<mask>` element in `masks_history` — the **same** byte-level wire chemigram already serializes for drawn-form masks per ADR-076. The form additionally carries an `algorithm` enum picking clone / heal / blur / fill, and per-algorithm parameter scratch space.

So the architectural question shifts. The naive framing was "this needs a sibling provider because pixels happen outside the byte-patching architecture." The closer reading: **the user-action (mark this spot) is identical to drawing a small mask, with one extra field saying "do heal/clone here."** darktable runs the heal/clone math; chemigram serializes the form + algorithm + mask reference.

The genuinely open question now: **where does AI / content-aware spot-finding fit?** "User says remove this exact spot" is byte-level tractable via the form-array path. "User says clean up the manta's belly" is a different operation — content-aware spot detection, requires ML, returns a list of small regions. That's the BYOA-shaped surface, separate from the byte-level wire.

Two viable paths emerge with materially different scope:

1. **Native via darktable retouch + drawn-form geometry** — extend `dt_serialize` to emit the retouch form-array + algorithm enum + mask references. Vocabulary entries declare `mask_spec` with a new `retouch_algo` axis. Covers user-driven spot removal directly (the dominant Lightroom workflow). Cheap, additive, byte-correct.
2. **Sibling-provider scaffolding for content-aware spot detection** — `chemigram-spotter-something` returns a list of (x, y, radius) regions; the engine emits N retouch forms via path (1)'s mechanism. This is the AI-find-the-spots arc, layered on top of (1).

These are NOT mutually exclusive — (1) is the foundation, (2) extends it. But they have separate scope, and conflating them produced the original "pixel-level edits don't fit byte-patching" misframing.

---

## Use cases

1. **Photographer manually removes a sensor-dust spot.** Lightroom: click on the spot; LR auto-picks a source region. chemigram: `apply-primitive spot_heal --x 0.3 --y 0.5 --radius 0.05` → byte-emit one retouch form at that location with `algorithm=heal`. Pure path (1).
2. **Photographer manually removes a blemish from a portrait.** Same mechanism as (1); the photographer specifies the mask geometry (ellipse) directly.
3. **Photographer wants the manta's belly cleaned up across 200+ small white dots.** Manual mark-each-spot is impractical. The agent calls a content-aware spotter (BYOA provider) which returns the list of regions; the engine emits 200 retouch forms in one apply call. Path (2) layered on (1).
4. **Photographer wants to clone a subject's other eye onto a copy.** This is `algorithm=clone` not heal. Same path (1); the mask spec declares source + destination geometry.
5. **Compositional retouch: heal one large region + clone-source from another.** Multiple retouch forms in one apply call. Already supported by darktable's 300-form array; path (1) just needs to serialize multiple forms in sequence.

---

## Goals

- **Pick the architectural shape** that handles user-driven spot removal cleanly. AI-driven content-aware variants are valuable but architecturally orthogonal.
- **Honor ADR-076's structural lesson** — don't introduce dead Protocol infrastructure. Whatever scaffolding the AI-content-aware path needs has to consume the byte-level wire path (1) ships, not bypass it.
- **Stay byte-level-correct.** retouch mv3 form-array serialization is the same shape as drawn-mask serialization; the codec extension is bounded.
- **Reuse drawn-mask geometry.** A retouch form references a `mask_id`; the masks_history element lives in the same `<darktable:masks_history>` array `dt_serialize` already writes. No new mask-storage concept.
- **Bound the modversion-drift surface.** retouch mv3 adds one more module's drift exposure; same backstop policy as ADR-082.

---

## Constraints

- **ADR-076** (drawn-mask only architecture): the masks_history serialization layer is the substrate this RFC extends. retouch forms reference masks_history elements via formid.
- **ADR-007** (BYOA): no AI dependencies in `chemigram.core`. AI content-aware spotters live in sibling projects.
- **ADR-008 (amended by ADR-081)**: `op_params` is opaque except where parameterization is registered. Extending the codec for retouch's form-array adds another tracked module.
- **CLAUDE.md three foundational disciplines**: agent-only-writer (spot decisions via tool calls); darktable-does-the-photography (heal/clone math runs in darktable); BYOA (content-aware spotters are sibling projects).
- **TA/components/masking**: `chemigram.core.masking.dt_serialize` is the home of the wire-level mask codec; this RFC extends it.

---

## Proposed approach

**Native via darktable retouch + drawn-form geometry. Path (1) only for v1.9.0/v1.10.0; AI content-aware variants deferred to a future RFC-026.**

Three concrete decisions:

### 1. `retouch` Path C decoder + form-array serializer

Extend `chemigram.core.parameterize` with a `retouch.py` decoder for retouch mv3 (the 300-form-array + globals struct). Like other Path C decoders, it reads / patches / writes the byte blob. Unlike most, it operates on a multi-form array, not a flat scalar set — the patch shape is "append a form" or "replace forms[i]" rather than "set field X to value Y."

Companion piece in `chemigram.core.masking.dt_serialize`: extend the masks_history writer to support multiple-form bindings per plugin (one masks_history element per retouch form, all referenced by the same plugin's retouch op_params).

**Tier classification**: Tier 2 under ADR-081's policy. The struct is fixed-size; the variable-length-effective behavior comes from the 300-form ceiling, not from variable byte layout. Same cost shape as colorbalancergb (132 bytes, 17 axes) or colorequal (128 bytes, 24 axes) — just with form-array semantics.

### 2. Vocabulary entry shape — `spot_heal` / `spot_clone` primitives

A new entry layer (or sub-shape under the existing L3) with `mask_spec` declaring the spot location + geometry:

```python
# Single-form spot heal
mask_spec = {
    "kind": "retouch",
    "algorithm": "heal",
    "forms": [{
        "form_kind": "ellipse",
        "form_params": {"center_x": 0.3, "center_y": 0.5, "radius_x": 0.05, "radius_y": 0.05, "border": 0.02},
    }],
}

# Multi-form retouch (e.g. from a content-aware spotter)
mask_spec = {
    "kind": "retouch",
    "algorithm": "heal",  # or per-form algorithm
    "forms": [
        {"form_kind": "ellipse", "form_params": {...}},
        {"form_kind": "ellipse", "form_params": {...}},
        # ... up to 300 forms ...
    ],
}
```

The `apply-primitive` CLI / MCP surface accepts a `--spot-form-json` parameter (or equivalent) to thread the form geometry through. Discrete entries like `spot_heal_default` ship with sensible defaults; the photographer / agent overrides via parameter.

### 3. AI content-aware spot detection — defer to RFC-026

Path (2) — sibling provider returns spot regions — is genuinely a separate architectural arc. Its shape depends on:

- What the provider returns (list of (x, y, radius) tuples? raster mask we threshold into spots?)
- How the engine batches multiple spots into one retouch apply call (already supported by the form-array; just need a multi-spot CLI invocation shape)
- How AI-detected spots compose with user-marked spots (compose: append? replace?)

These questions belong in RFC-026 (provider scaffolding for AI-mask + AI-spot-detection), not RFC-025. Drafting RFC-025 to ship path (1) gives RFC-026 a stable substrate to layer on.

---

## Alternatives considered

### Alt 1: Sibling-provider scaffolding for everything (no native retouch decoder)

Rejected. Reading the retouch struct reveals the user-driven spot-removal case is byte-level tractable — the form-array path is structurally identical to what `dt_serialize` already handles for drawn-form masks. Routing the user-driven case through a provider re-creates ADR-076's dead-infrastructure problem (Protocol with the wrong shape for what darktable consumes). The provider shape is correct for AI / content-aware variants but overkill for "user clicks on this spot."

### Alt 2: Defer all spot removal until a content-aware provider lands

Rejected. The user-driven spot-removal case is the bulk of Lightroom's spot-removal usage in real-world workflows (sensor dust, single blemish, single distracting element). Deferring means shipping v1.9.0+ without the most common version of this gap addressed, while waiting for the harder AI-content-aware path to land. Wrong sequencing — ship the cheap correct path first.

### Alt 3: Stroke recording (record start/end + radius for each painted stroke)

Rejected. darktable's retouch isn't stroke-shaped at the byte level — it's form-shaped. A "stroke" in the user's mental model serializes to one or more `dt_iop_retouch_form_data_t` entries with mask_id references. The translation layer between "stroke" and "form" is just CLI / MCP parameter shape; the byte serializer operates on forms, not strokes. Going stroke-shaped at the wire would diverge from darktable's actual data shape.

### Alt 4: Approximate via existing drawn-mask + L1 baseline

Rejected. Drawn masks select a region and apply a primitive (exposure, sigmoid, etc.) inside that region. Retouch *replaces* pixels with healed / cloned content. These are categorically different operations; no combination of existing primitives + drawn masks reproduces the heal algorithm's content-aware texture continuation.

### Alt 5: Wait for a Lightroom-ish UI before architecting

Rejected. The architectural decision about the wire format is independent of the UI. CLI / MCP-driven spot removal works fine with explicit form parameters; a hypothetical future UI (or a sibling project's interactive painter) sits on top of the same wire. Deferring the wire decision until the UI shape is known forces the UI to either invent its own wire or wait for one.

---

## Trade-offs

- **Form-array byte serializer is more complex than flat-scalar decoders.** retouch's 300-element form array + per-form parameters is structurally bigger than a colorbalancergb-style flat field set. Mitigated: the per-form sub-struct is itself flat scalars; the array dimension is the only complexity addition. The decoder's interface stays patch()-shaped (replace one form, append a form, clear all forms — three operations cover the use cases).
- **Form geometry depends on image dimensions.** Coordinates are normalized 0..1; the photographer specifies fractions of the frame. This is consistent with how drawn-mask coordinates work today (per ADR-076), but worth calling out that an entry authored on a 4:3 image may not localize identically on a 16:9 image without aspect adjustment.
- **300-form ceiling for AI-driven multi-spot scenes.** The manta's-belly use case may need more than 300 small spots. Mitigated: 300 is darktable's limit, not chemigram's; if hit, the agent applies multiple retouch passes (each a separate plugin with its own 300-form array). Documented limitation, not a fundamental architectural one.
- **AI-content-aware variants deferred to RFC-026.** Shipping path (1) only means the manta's-belly use case stays manual until AI providers land. Mitigated: RFC-024 has the same shape for AI-subject masks; the provider-scaffolding work is consolidated in RFC-026 and lands once.
- **Visual proof on synthetic charts is impossible.** Heal / clone require image content with continuity (skin texture, sky gradient, etc.) for the algorithm to produce sensible output. The synthetic ColorChecker / grayscale fixtures don't have any. Real-raw fixture (#103) is required for visual-proof rendering — same shape as the HSL skip-list pattern.

---

## Open questions

- **retouch mv3 form-array byte layout.** Need to read `src/iop/retouch.c` end-to-end to map the per-form sub-struct exactly. The summary in this RFC lists the field names; the byte-level offsets need empirical verification (likely a darktable-session exercise — a small spot-heal authored in the GUI, exported, byte-diffed against a constructed baseline).
- **mask_spec.kind extension semantics.** RFC-024 already proposed extending mask_spec.kind for range masks; RFC-025 adds another kind. The two RFCs need to land their kind-vocabulary cohesively. Lean: make mask_spec.kind extensible (open enum), with each RFC's closing ADR documenting the new value.
- **Patching shape on the 300-form array.** Three operations cover the use cases: replace_all (for entries that ship a fixed set of forms), append (for AI-driven additions), clear (cleanup). Should patch() expose all three, or just replace_all (with the higher-level apply path computing the diff)?
- **Per-form algorithm vs. global algorithm.** retouch mv3 has both: a `forms[i].algorithm` per-form field AND a global `algorithm` field. Need to verify which one wins at runtime. If per-form wins, the vocabulary surface should expose per-form algorithm; if global, simpler.
- **Composition with drawn / range / parametric masks.** Can a retouch form's mask_id reference a parametric (color-range) mask? darktable's data model probably allows this but workflow is unclear. Worth investigating in the closing ADR.
- **5-layer test coverage for retouch entries.** Real-raw fixture is required (per visual-proof gap above); the coverage rubric mirrors what RFC-024 needs. Possible joint amendment to ADR-080 covering both.

---

## How this closes

This RFC closes into:

- **A primary ADR** specifying the native-retouch-decoder approach + the mask_spec.kind="retouch" extension. Records the form-array byte serialization choice, the patching semantics, and the deferred scope (AI content-aware variants in RFC-026).
- **An implementation issue** for the retouch decoder + 2-3 starter spot-heal vocabulary entries.
- **A possible amendment to ADR-080** unified with RFC-024's coverage extension, if both land near the same time.
- **A pointer to RFC-026** for AI-content-aware spot-detection provider scaffolding.

---

## Links

- TA/components/masking — `chemigram.core.masking.dt_serialize` extension target
- TA/components/synthesizer — apply path
- TA/contracts/per-image-repo — `mask_spec` schema
- TA/constraints/opaque-hex-blobs — ADR-008's amended boundary
- ADR-007 — BYOA principle (relevant for the deferred AI path in RFC-026)
- ADR-076 — drawn-mask only architecture (this RFC argues to extend)
- RFC-024 — range masks (sibling RFC; same kind-extension shape)
- ADR-077..080 — parameterization architecture (retouch decoder rides this)
- ADR-081 — Tier 2 cost-shape guidance
- ADR-082 — modversion-drift handling (backstop for retouch mv3 byte serializer)
- capability-survey.md § 10 — names "Retouch / spot healing" as the major portrait gap
- Issue #108 — the issue that opened this question
- Future RFC-026 — AI-mask + AI-spot-detection provider scaffolding (placeholder)
