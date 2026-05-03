# RFC-019 — Reference-image validation baseline

> Status · Decided (v1.4.0; Tier A synthetic shipped in v1.2.0; Tier B real-RAW deferred per ADR-068)
> Date · 2026-05-02 (decided); originally drafted 2026-04-29
> TA anchor · /components/pipeline · /components/eval
> Related · RFC-017 (eval harness, Mode B), RFC-018 (vocabulary expansion), ADR-036 (test tiers), ADR-062 (v1.1.0 validation)
> Closes into · ADR-066 (reference fixture policy), ADR-067 (pixel-level assertions), ADR-068 (darktable version gate)
> Companion guide · [docs/guides/standardized-testing.md](../guides/standardized-testing.md) — industry methodology, Calibrite reference values, Delta E interpretation, synthetic-fixture generation
> Why this is an RFC · The current validation suite verifies *structural*
>                       correctness (valid XMP, darktable renders without
>                       error, correct op_params bytes). It does not verify
>                       *photographic* correctness — whether the rendered
>                       pixels actually express the intended color, tone,
>                       and exposure adjustments. The question is: what
>                       reference inputs and metrics give us a scientifically
>                       grounded baseline for detecting regressions in
>                       output quality?

## v0.2 changes

- **ADR numbering shifted** to 066 / 067 / 068. RFC-018 retains 063 + 064 (already referenced from `docs/IMPLEMENTATION.md`, the v1.2.0 plan, and several issue bodies).
- **Real-RAW Tier B dropped** from v1.2.0 scope. The project doesn't ship physical chart shoots, and CI must run end-to-end without a Nikon D850 and a sunny afternoon. The path forward is **synthetic-only validation** that can run anywhere — generated CC24 + grayscale TIFFs from published L\*a\*b\* values. If a community-contributed downloadable reference RAW pack appears later, Tier B reopens via a follow-on RFC.
- **Companion guide** moved to `docs/guides/standardized-testing.md` (the file at the docs root was the wrong location for a long-form companion).

## The question

Chemigram's e2e tests currently answer: "does the pipeline produce a file that darktable accepts and renders?" They do not answer: "does applying `wb_warm_subtle` to a known input actually shift white balance in the expected direction, by the expected amount?"

The 519 tests in v1.1.0 are strong on structural integrity. But a `.dtstyle` that silently produces wrong exposure, a darktable upgrade that reinterprets `op_params` bytes differently, or a vocabulary entry captured against the wrong module version — all of these would pass every current test while producing wrong photographs.

The photography and imaging industry solved this problem decades ago with standardized test targets: inputs with *known, published reference values* so that pipeline output can be compared against ground truth. The question is how to adapt this methodology to Chemigram's specific pipeline — XMP synthesis → darktable-cli rendering — in a way that is practical, automated, and scientifically sound.

## Use cases

1. **Vocabulary authoring.** When a contributor captures a new `.dtstyle` entry (e.g., `tone_lift_shadows_gentle`), the reference fixture validates that applying it to a known input produces the expected tonal shift — not just that the XMP parses.

2. **darktable version upgrades.** When darktable ships a new version (5.4.1 → 5.6.0), `modversion` and `op_params` semantics may drift. The reference baseline detects this before the upgrade silently changes all future renders.

3. **XMP synthesizer changes.** When the synthesizer's SET-replace or ADD logic changes (RFC-001 Path A refinements), reference-image assertions catch regressions that structural tests miss — e.g., wrong `multi_priority` ordering that produces a valid XMP but applies modules in wrong sequence.

4. **CI confidence.** The existing e2e tier is local-only (ADR-040). Reference-image assertions on *synthetic digital fixtures* (no darktable needed) can run in CI, catching color-math and composition-logic regressions on every push.

5. **Cross-platform reproducibility.** macOS vs Linux darktable builds may produce subtly different renders. A reference baseline makes this visible and measurable rather than anecdotal.

## Goals

1. **Known ground truth.** Test inputs with published, externally verifiable reference values (CIE L\*a\*b\*, density steps, etc.) — not "a photo that looked right last time we checked."
2. **Objective, numeric assertions.** Delta E, histogram statistics, tonal curve fit — things that go in a test assertion, not things a human eyeballs.
3. **CI-friendly validation.** Synthetic digital fixtures (CC24 + grayscale TIFFs generated from published L\*a\*b\* values) — no darktable subprocess, no physical chart, runs anywhere. Real-RAW Tier B is deferred (no chart shoots in scope; see v0.2 changes).
4. **Immutable reference data.** Same principle as RFC-017's golden datasets: once a reference version ships, it is frozen. New reference data ships as a new version.
5. **Practical.** All inputs generated computationally from published references — zero hardware cost, zero acquisition time.

## Constraints

- From TA/constraints: "darktable does the photography, Chemigram does the loop." This RFC validates the pipeline *math* — the synthesizer + pixel-level assertions — without bypassing darktable's RAW path. The synthetic-fixture path tests the deterministic transforms; if darktable's RAW path needs validation that's a future Tier B reopened by RFC.
- From ADR-036: three test tiers; reference-image assertions live alongside the existing integration tier (synthetic fixtures, CI-safe).
- From ADR-040: e2e tests are not in CI (darktable dependency). Synthetic-fixture reference tests *can* be in CI — that's the point of choosing synthetic over real-RAW.
- darktable's rendering is deterministic for a given (binary version + XMP + raw) tuple. The synthetic path's deterministic transforms (sRGB ↔ L\*a\*b\* D50) make pixel-level assertions viable without darktable in the loop.

## Proposed approach

### 1. Reference inputs — synthetic only (v0.2)

No chart shooting. All reference inputs are generated computationally from
published ground-truth values, committed to the repo, runnable in CI:

| Target | Source | What it gives us |
|-|-|-|
| Synthetic CC24 sRGB TIFF | Generated from X-Rite published L\*a\*b\* D50 values (post-Nov 2014 formulation) | Per-patch Delta E assertions after any vocabulary move or pipeline change |
| Synthetic grayscale ramp TIFF | Generated from a deterministic linear-density step model | Gamma/linearity assertions on tonal-curve vocabulary; tonal-clipping detection |

The synthetic CC24 is rendered as a 6×4 grid of 100×100 pixel patches at the
sRGB values that result from converting each patch's published L\*a\*b\* D50
through the Lindbloom L\*a\*b\* → XYZ → sRGB pipeline (D50 illuminant, 2°
observer). Out-of-gamut patches (notably Cyan #18) are clipped to sRGB and
flagged in the reference JSON so assertions don't expect impossible values.

The grayscale ramp is a 24-step linear ramp from sRGB(0,0,0) to sRGB(255,255,255)
plus 6 sub-stops below black and above white to test under/over-clip behavior.

**Why synthetic-only:** zero hardware cost, runs in CI on any platform, and
deterministic across builds. The trade-off is that this validates the
*software pipeline math* (sRGB ↔ L\*a\*b\*, the synthesizer's transform
chain, the assertion library) in isolation from darktable's RAW path. If
the project later needs to validate darktable's RAW pipeline against
reference-target ground truth, a community-contributed downloadable RAW
pack reopens the discussion via a follow-on RFC.

### 2. Reference data — published ground truth

X-Rite publishes official CIE L\*a\*b\* D50 reference values for both chart formulations (pre- and post-November 2014) as downloadable CGATS text files. BabelColor provides averaged spectral data from 30 measured charts plus synthetic L\*a\*b\* TIFF images. These are the ground truth — not "what my monitor shows" but "what CIE colorimetry says these patches are."

The reference data is committed to the repo as a small JSON file:

```
tests/fixtures/reference-targets/
├── README.md
├── colorchecker24_lab_d50.json          # 24 patches × (L*, a*, b*)
├── grayscale_density_steps.json         # N steps × optical density
├── colorchecker_synthetic_srgb.tiff     # 640×426, synthetic (for CI tier)
└── grayscale_synthetic_linear.tiff      # synthetic ramp (for CI tier)
```

The JSON files are tiny (<2 KB). The synthetic TIFFs are computer-generated from the reference L\*a\*b\* values (per BabelColor/Lindbloom methodology) — pixel-perfect, zero noise, zero lens distortion. These are the CI-tier inputs: they test the *software pipeline* in isolation from any camera.

### 3. Assertion library — `chemigram.core.assertions`

A new module providing reusable assertion functions:

```python
from chemigram.core.assertions import (
    assert_color_accuracy,      # Delta E 2000 per patch vs reference
    assert_tonal_response,      # gamma fit, linearity R², black/white clip
    assert_exposure_shift,      # "did applying expo_+0.5 shift mean L* by ~+N?"
    assert_wb_shift,            # "did wb_warm_subtle move a* and b* in the expected direction?"
    assert_histogram_stats,     # mean, stddev, clipping % for a region
    extract_patch_values,       # given a rendered image + patch coordinates, extract avg L*a*b*
)
```

**Delta E 2000** is the industry standard metric for perceptual color difference. A Delta E of ~1 is a just-noticeable difference; professional calibration targets mean Delta E < 2.0, max < 4.0. These thresholds give us concrete pass/fail numbers:

| Assertion | Pass threshold | Fail threshold |
|-|-|-|
| Mean Delta E (identity render) | < 3.0 | > 5.0 |
| Max Delta E (identity render) | < 6.0 | > 10.0 |
| Exposure shift direction | Correct sign | Wrong sign |
| Exposure shift magnitude | Within ±0.3 EV of expected | > 0.5 EV off |
| WB shift direction (a\*, b\*) | Correct quadrant | Wrong quadrant |
| Tonal linearity (R²) | > 0.98 | < 0.95 |
| Grayscale neutrality (max chroma) | < 3.0 | > 6.0 |

Note: the "identity render" thresholds are deliberately loose because darktable's scene-referred pipeline applies auto-presets (sigmoid, etc.) — the baseline is *not* a camera-to-sRGB linear transform. The thresholds assert that *darktable's own processing* is stable, not that it matches a theoretical ideal.

### 4. Test structure — synthetic-only (v0.2)

The reference-target tests live in the **integration** tier (CI-safe per
ADR-036/-040), at `tests/integration/test_reference_synthetic.py`. Uses
the committed synthetic TIFF fixtures — no darktable subprocess, no real
RAW file. Validates the assertion library itself and the *color math* in
the synthesizer and pipeline logic.

Example identity-render assertion:
```python
def test_identity_colorchecker_synthetic():
    """The synthetic CC24 patches, extracted and converted back to
    L*a*b*, should match the published reference within Delta E < 1.0
    (limited only by sRGB gamut clipping on out-of-gamut patches)."""
    img = load_tiff("tests/fixtures/reference-targets/colorchecker_synthetic_srgb.tiff")
    patches = extract_patch_values(img, CC24_PATCH_COORDS)
    reference = load_reference("tests/fixtures/reference-targets/colorchecker24_lab_d50.json")
    result = assert_color_accuracy(patches, reference, max_mean_de=1.0, max_max_de=2.0)
    assert result.passed
```

Example direction-of-change assertion (no darktable required — synthesize
applies modules to a baseline XMP, the assertion verifies the L\*a\*b\*
shift the synthesizer produces is in the right direction):
```python
def test_synthesize_expo_plus_0p5_shift_direction():
    """Applying expo_+0.5 should cause the synthesized XMP's history
    to encode a positive exposure shift; this is verified by inspecting
    the resulting op_params bytes against a known mapping (or by a
    follow-on darktable e2e test if the chart shoot ever happens)."""
    # Implementation detail: the synthesizer doesn't render. Direction-
    # of-change at the synthesizer tier asserts the *intent* of the
    # change is encoded correctly. Pixel-level direction-of-change is
    # validated at the existing e2e tier with the Phase 0 raw.
```

**Note.** Real-RAW pixel-level assertions on vocabulary entries (the
"Tier B" of v0.1 of this RFC) are out of scope for v1.2.0. The existing
direction-of-change e2e helpers (`tests/e2e/conftest.py` + the
`tests/e2e/expressive/` scaffolds from RFC-018 §Costs) cover this for
each shipped vocabulary entry. They use the Phase 0 raw and ad-hoc
heuristic measurements (`highlight_clip_pct`, `corner_vs_center_luma_ratio`,
etc.) rather than reference-target Delta E. That's a deliberate trade-off
for v1.2.0: full reference-target pixel validation requires hardware
the project doesn't own.

### 5. darktable version gating (deferred)

darktable version gating is only relevant if reference-target tests run
darktable. The synthetic-only path doesn't, so this section is deferred
to whenever Tier B reopens. The existing per-entry `darktable_version`
manifest field (per RFC-018) plus RFC-007 (modversion drift) are the
current drift-detection mechanism.

### 6. Relationship to RFC-017

RFC-017's eval harness validates *agent behavior* — did the agent follow the brief, respect taste, use the right vocabulary? This RFC validates *pixel output* — did the pipeline produce photographically correct results?

They're complementary:
- RFC-017 golden scenarios use arbitrary artistic RAWs. The question is "did the agent make good choices?"
- RFC-019 reference fixtures use standardized test targets. The question is "does the pipeline produce correct output?"

RFC-017's mechanical metrics (`vocab_purity`, `expected_primitives_used`) could incorporate RFC-019's pixel assertions as a new metric category: "did the agent's chosen primitives produce the expected pixel-level effects?" This bridges the gap between "structurally correct tool calls" and "photographically correct output."

## Alternatives considered

### A. Visual diff testing (screenshot comparison)

Capture a rendered PNG as a golden reference, compare future renders pixel-by-pixel.

**Why rejected.** Extremely brittle — any darktable version change, any platform difference, any floating-point rounding change produces a "failure" even when the output is perceptually identical. Delta E absorbs perceptual irrelevance; pixel diff does not. Also violates the "known ground truth" principle: the golden PNG is "what the pipeline produced last time," not "what colorimetry says is correct."

### B. Perceptual hash (pHash / SSIM)

Use perceptual similarity metrics instead of colorimetric ones.

**Why rejected.** pHash and SSIM answer "do these two images look similar?" but not "is this image correct?" Two images can be very similar (high SSIM) while both being wrong (e.g., both have the same WB error). Reference-target methodology answers a different question: "does this image match externally published ground truth?"

SSIM/pHash may be useful *alongside* Delta E for regression detection (e.g., "did the overall image change?") but cannot replace colorimetric assertions.

### C. Use existing `CHEMIGRAM_TEST_RAW` (Nikon D850 landscape)

Add pixel assertions to the existing test raw instead of acquiring new reference targets.

**Why rejected.** The existing raw is an arbitrary photograph with no published reference values. You can measure what darktable produces from it, but you can't assert whether that output is *correct* — only whether it *changed*. This is the visual-diff trap under a different name.

### D. Use only synthetic digital fixtures (chosen for v0.2)

Generate all reference data computationally; never shoot a physical chart.

**v0.2 chooses this.** Synthetic fixtures are tractable, deterministic, and CI-friendly. They do skip darktable's RAW path (demosaicing, color matrix, lens corrections), but for the v1.2.0 problem — validating that the synthesizer + assertion library produce correct colorimetric output — synthetic-only is sufficient. The existing direction-of-change e2e tier (Phase 0 raw + ad-hoc heuristic measurements) covers the darktable-RAW path for direction-of-change purposes.

If a community-contributed downloadable reference RAW pack appears later, this opens up via a follow-on RFC. v1.2.0 ships synthetic-only.

## Trade-offs

1. **Validation gap.** Synthetic-only doesn't validate darktable's RAW path against reference-target ground truth. Mitigated by: (a) the existing e2e direction-of-change tests cover the RAW path heuristically; (b) the synthetic path validates the deterministic transforms (sRGB ↔ L\*a\*b\*, the synthesizer's compose+append behavior); (c) future RFC reopens Tier B if the gap matters in practice.
2. **Out-of-gamut clipping.** Some published L\*a\*b\* values (Cyan #18) are outside the sRGB gamut. The synthetic CC24 clips these to the nearest in-gamut value. Reference JSON marks the clipped patches and assertions excuse them from the strict mean/max Delta E thresholds.
3. **Scope creep risk.** It's tempting to add resolution testing, noise profiling, distortion measurement — the photography testing industry has dozens of chart types. The proposal deliberately limits to two synthetic targets and two metric families (color + tone). Expansion is a future RFC.

## Open questions

1. **What Delta E variant?** CIE2000 is the industry standard, but CIE76 is simpler to implement and debug. Proposal: implement CIE2000 hand-rolled (no `colour-science` dependency); offer CIE76 as a diagnostic fallback if CIE2000's complexity is debuggable trouble.

2. **Should the assertion library be a separate package?** It could be useful outside Chemigram (any darktable-based workflow). For now, propose keeping it inside `chemigram.core` — extraction to a standalone package is a future decision.

## How this closes

| ADR | Decision |
|-|-|
| ADR-066 | **Reference fixture policy (synthetic-only for v1.2.0).** Synthetic CC24 sRGB TIFF + grayscale ramp TIFF generated from published X-Rite L\*a\*b\* D50 values; reference JSON committed; immutable versioning (`reference_v1` frozen, improvements ship as `v2`); real-RAW Tier B deferred to follow-on RFC if community-contributed downloadable RAW pack appears. |
| ADR-067 | **Pixel-level assertion protocol.** Delta E 2000 (CIE DE2000) as primary metric, hand-rolled (no `colour-science` dependency); CIE76 as diagnostic fallback; sRGB ↔ L\*a\*b\* D50 conversion via Lindbloom matrices; tonal linearity (R²) as secondary metric; thresholds documented in `chemigram.core.assertions`. |
| ADR-068 | **darktable version gate (deferred).** Currently no-op — synthetic-only path doesn't run darktable. Reopens whenever Tier B reopens. Per-entry `darktable_version` in vocabulary manifests + RFC-007 (modversion drift) cover the current drift-detection path. |

## Links

- RFC-017 — Evaluation harness and auto-research (complementary; agent behavior vs pixel output)
- RFC-018 — Vocabulary expansion (the existing direction-of-change e2e helpers will use the new `chemigram.core.assertions` module where appropriate)
- ADR-036 — Test tiers
- ADR-040 — e2e tests are local-only
- ADR-062 — v1.1.0 validation milestone
- `docs/guides/standardized-testing.md` — companion guide; industry methodology, Calibrite reference values, Delta E interpretation, synthetic-fixture generation
- `tests/fixtures/README.md` — Current fixture conventions
