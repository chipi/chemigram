# ADR-083 — HSL Color Mixer via colorequal (3 multi-axis entries)

> Status · Accepted
> Date · 2026-05-07
> TA anchor ·/components/synthesizer ·/components/parameterize ·/contracts/vocabulary-manifest
> Related RFC · RFC-023 (closes)
> Related ADRs · ADR-008 (opaque-blob default — amended by ADR-081), ADR-077..080 (parameterization architecture), ADR-081 (parameterization tiering policy — this ADR ships an HSL Tier 2 module under that policy), ADR-082 (modversion drift handling — backstops the colorequal mv4 pin)

## Context

The Lightroom-parity capability survey (`docs/capability-survey.md` § 13) flagged HSL Color Mixer — Hue / Saturation / Luminance per color — as the largest remaining daily-use gap. RFC-023 deliberated which darktable module backs HSL parity and what the vocabulary shape should be. Two viable backing modules exist:

- `colorzones` (mv5) — the older module. 520-byte struct with 3 channels × 20 (x, y) spline-curve nodes, plus per-channel active-node count and curve-type enums. Photographically: per-channel curves indexed by hue.
- `colorequal` (mv4) — darktable's modern HSL module, introduced post-4.x as the recommended path. 128-byte struct with 24 per-color scalars (8 sat + 8 hue + 8 brightness) plus 7 globals and a boolean. No curves, no node counts. Photographically: 24 sliders mapped 1:1 to Lightroom's HSL Color Mixer.

The ADR-081-tier classification depends on this choice — `colorequal` is Tier 2-shaped (flat scalars, identical decoder shape to `colorbalancergb`); `colorzones` is genuinely Tier 3-shaped (variable-length curves, empirical-baseline blocker, non-local composition semantics).

## Decision

**Back HSL Color Mixer parity with `colorequal` mv4.** Ship as **3 multi-axis parameterized vocabulary entries** — one per HSL channel — with 8 per-color axes each:

- `hsl_saturation` — `sat_red, sat_orange, sat_yellow, sat_green, sat_cyan, sat_blue, sat_lavender, sat_magenta`. Each range [-1.0, 1.0], default 0.0.
- `hsl_hue` — `hue_red` through `hue_magenta`. Each range [-180.0, 180.0] degrees, default 0.0.
- `hsl_luminance` — `bright_red` through `bright_magenta`. Each range [-1.0, 1.0], default 0.0.

The 7 globals (threshold, smoothing_hue, contrast, white_level, chroma_size, param_size, use_filter) and trailing `hue_shift` are preserved verbatim through `patch()`.

**Tier classification: Tier 2.** This is an explicit reclassification of HSL Color Mixer from the Tier 3 placement ADR-081 named in its examples list ("colorzones — 3 spline curves with up to 8 nodes each — surface doesn't reduce cleanly to scalar `--value V`"). The reclassification is **not** because the tiering policy changed, but because the backing-module choice changed: ADR-081's Tier 3 placement was conditional on `colorzones` backing, which RFC-023 set aside in favour of `colorequal`. Under `colorequal`, HSL's struct shape is flat scalars — exactly the Tier 2 cost-shape guidance ADR-081 articulates.

## Rationale

- **Cost-shape parity with colorbalancergb.** `colorequal`'s 128-byte flat-scalar struct is structurally identical to `colorbalancergb`'s 132-byte mv5 struct. The decoder shape, the test-coverage shape, the manifest shape, and the apply-path integration are all known-good from the colorbalancergb 17-axis ship. No new architectural surface; pure additive expansion.
- **Curve-composition semantics fight Path C.** `colorzones`' spline-node patching is non-local: pulling one node affects the curve in a region around the node. Path C's "patch this byte at this offset" model handles this only by re-authoring whole-curve blobs per move, which works for discrete entries but breaks down for parameterized partial-update.
- **darktable's deprecation signal.** `colorequal` was introduced as the modern HSL path; `colorzones` is now legacy. Building Tier 2 parameterization on `colorzones` builds infrastructure on a module the project itself is moving away from.
- **Photographic workflow shape.** Lightroom users describe HSL work in channel-passes ("hue pass first, then sat pass"). The 3-entry split reflects that workflow framing. Compressing to a single 24-axis entry would be 2.5× the next-largest parameterized entry; splitting to 24 single-axis entries would invert the channel-as-unit framing without granularity gain.

## Alternatives considered

- **Back HSL with `colorzones`** (RFC-023 Alt 1) — Rejected. Empirical-baseline blocker (same trap that deferred tonecurve / #94); higher modversion-drift surface; non-local curve composition; deprecation signal from darktable itself.
- **Back HSL with both modules** (RFC-023 Alt 2) — Rejected. Two decoders + two manifest shapes + two test surfaces for marginal coverage gain. The 5% curve-precision case is tracked separately as a discrete-only `colorzones` Tier 3 fallback (#98).
- **Ship HSL as 24 single-axis entries** (RFC-023 Alt 3) — Rejected. Inverts the photographic workflow model. The 3-entry-per-channel split keeps per-color granularity (each entry exposes 8 axes) without sacrificing the channel-as-unit framing.
- **Ship HSL as one mega-entry with all 24 axes** (RFC-023 Alt 4) — Rejected. 2.5× larger than the next-biggest parameterized entry (toneequalizer's 9 axes); makes `vocab show hsl` a wall of text; harder to triage parameter errors.
- **Defer HSL** (RFC-023 Alt 5) — Rejected. The gap was named; deferring would mean shipping v1.8.0 with the largest Lightroom-parity gap still open.

## Consequences

Positive:

- Closes the largest Lightroom daily-use parity gap. Post-ship: ~22/23 daily-use controls covered (only tone curve remains, deferred as #94).
- Adds 24 per-color axes via 3 entries — the largest single Tier 2 expansion since `toneequalizer` (#91 Bucket A.5 was 9 axes; this is 24).
- Reuses the colorbalancergb-style decoder pattern with no new architectural shape; the table-driven `_AXIS_FIELD_INDICES` keeps `patch()` complexity bounded.
- The shipped Tier 2 status proves out ADR-081's "feature commit + cite the ADR + 5-layer coverage" pattern for Tier 3 → Tier 2 promotion at non-trivial scale (24 axes + 3 entries).

Negative:

- **Falloff control is coarser than Lightroom.** `colorequal`'s `smoothing_hue` and `param_size` globals shape zone-overlap globally, not per-zone. Lightroom's HSL Range slider gives per-zone falloff. For 90% of HSL workflow this is invisible; for the remaining ~10% (photographers tuning saturation curves with mathematical precision) it's a real gap, tracked as #98 (`colorzones` discrete-only fallback).
- **Visual-proof sweep coverage is incomplete at ship.** RFC-023's open question on sweep scope was resolved by shipping 3 representative axes (`sat_blue`, `hue_green`, `bright_blue`) — the remaining 21 axes don't have sweeps. This is documented in the ship commit message; expand if real-session feedback flags specific colors.
- **Lab-grade direction-of-change isn't measurable** on the synthetic ColorChecker chart for hue/luminance axes (HSL only fires on color-zone pixels; the chart's flat patches don't have the gradients needed for hue/lum direction signal). Saturation axes do shift chroma on the relevant patches; the lab-grade tests use render-completes-only for the hue/lum cases, with photographic effect verification deferred to visual-proof + on-real-raws review.

## Implementation notes

- Decoder: `src/chemigram/core/parameterize/colorequal.py` (commit `1b5db21`).
- Registry: `chemigram.core.parameterize._PATCH_REGISTRY` adds `("colorequal", 4): colorequal.patch`. Modversion-drift registry (per ADR-082) adds `colorequal` → 4.
- Vocabulary entries: `vocabulary/packs/expressive-baseline/layers/L3/colorequal/{hsl_saturation,hsl_hue,hsl_luminance}.dtstyle`.
- Manifest entries declare each axis's byte offset and type; offsets verified against the C struct layout in `colorequal.py`'s docstring.
- 5-layer test coverage per ADR-080: 33 parameterized entries now, up from 30 pre-ship.
- The discrete `colorzones` fallback for the curve-precision use case is tracked as #98 — discrete-only, no parameterized decoder, no modversion drift exposure.

## ADR-081 relationship

This ADR is the **first** Tier 3 → Tier 2 promotion under the policy ADR-081 articulated. The promotion path used:

1. Feature commit (`1b5db21`) names the module (`colorequal`) and demonstrates Tier 2-shaped cost (flat scalars, decoder pattern reused from colorbalancergb).
2. 5-layer coverage per ADR-080 ships green.
3. This ADR records the rationale for the colorzones-vs-colorequal choice and the vocabulary shape.

ADR-081's promotion bar — "feature commit naming the module, citing this ADR, and shipping the standard 5-layer coverage" — is met. The original Tier 3 placement of HSL Color Mixer in ADR-081's "Examples currently in Tier 3" list is now stale; the example was conditional on `colorzones` backing, which is no longer the project's choice. ADR-081's enumerated members aren't decisional content (the decision is the four-tier framing itself), so this ADR's reclassification doesn't supersede ADR-081 — it updates the example. The capability-survey doc and ADR-081's example list will be updated as documentation; no follow-on ADR amendment is required.
