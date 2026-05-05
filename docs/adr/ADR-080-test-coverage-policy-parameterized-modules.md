# ADR-080 — Test-coverage policy for parameterized modules

> Status · Accepted
> Date · 2026-05-05
> TA anchor ·/contracts/vocabulary-manifest ·/components/synthesizer
> Related RFC · RFC-021 (closes); paired with ADR-077, ADR-078, ADR-079

## Context

Parameterized vocabulary entries (per ADR-078) introduce a class of failure modes that discrete entries don't have: the encoder/decoder round-trip can be wrong, the magnitude can be off by a factor, the masked variant can fail to localize, the modversion mismatch can silently corrupt. The cost of catching these failures at apply time (in a real photographer's session) is much higher than the cost of catching them in CI.

RFC-021 §Open Q5 deliberated whether test coverage should be a soft convention or a hard CI gate. The answer hinges on whether "we forgot to write tests" is a tolerable failure mode for parameterized modules. It is not.

## Decision

Every parameterized vocabulary entry (any manifest entry with a `parameters` field per ADR-078) must ship with the following test coverage. This is a **hard CI gate**, not a soft convention; a PR that adds a parameterized entry without all five layers of coverage fails CI.

### Required coverage layers

1. **Unit tests** — `tests/unit/core/parameterize/test_<module>.py` exercises the decoder/encoder round-trip:
   - `encode(decode(blob)) == blob` for the entry's reference `op_params`.
   - `decode(encode(decode(blob), <param>=v)).<param> == v` for `v` across the declared range.
   - Modversion mismatch raises with a clear error.

2. **Integration tests** — `tests/integration/core/test_parameterize_<module>.py` exercises the apply path completion:
   - Apply succeeds for at least 5 distinct values across the declared range, including the endpoints and zero / midpoint.
   - Resulting XMP carries the expected `op_params` bytes (decoded re-comparison).
   - Out-of-range value fails with the documented error.

3. **Lab-grade global tests** — entry registered in `tests/e2e/_lab_grade_deltas.py` `EXPECTED_EFFECTS`:
   - For at least 3 parameter values (including zero and a positive + negative if the range spans both), assert direction-of-change matches the photographic intent on the synthetic reference targets.
   - For modules where clean math is feasible (`exposure` is the canonical case: `+v EV` doubles linear-RGB at `+1`, halves at `-1`), assert the expected ratio within tolerance.

4. **Lab-grade masked tests** — entry registered in the masked test layer (`tests/e2e/test_lab_grade_masked_universality.py` or successor):
   - Apply at a representative non-zero value through a centered ellipse mask.
   - Assert spatial localization: zone delta exceeds complement delta by a documented factor (catches "mask not localizing" regressions).
   - **This layer is non-negotiable.** Parameterization without masked-coverage tests is half-shipped — the engine technically works, but a real failure mode (mask binding ignored on a parameterized blob) goes undetected until a user hits it.

5. **Visual proof** — `scripts/generate-visual-proofs.py` renders a parameter-sweep row for the entry showing the same primitive at multiple values side-by-side. The gallery (`docs/guides/visual-proofs.md`) carries the regenerated row.

### CI enforcement

A linter test, `tests/unit/core/test_parameterized_module_coverage.py`, runs as part of the existing CI test suite. It:

1. Loads the vocabulary manifest.
2. Identifies every entry with a `parameters` field.
3. For each, checks that all five coverage layers reference the entry by name.
4. Fails CI if any layer is missing.

The linter is allowed to be evaded for one specific case: an entry annotated `"parameters": [...], "_test_coverage_exempt": "<reason>"` in its manifest. This is intentionally awkward; the comment field documents *why* the exemption exists and forces the contributor to articulate the reason in the manifest itself, not just the PR description. In practice no v1.6.0 entry uses the escape hatch.

## Rationale

- **Parameterization expands the failure surface in ways discrete vocabulary doesn't.** A discrete entry either applies or doesn't; a parameterized entry has a continuous space of values where the decoder can be subtly wrong (off-by-one offset, wrong endianness, sign flip, range-edge clipping). Coverage layers 1 and 2 catch the byte-level errors; layers 3 and 4 catch the photographic-result errors.
- **Masked coverage is the one most likely to be skipped under deadline pressure.** "We'll add masked tests next sprint" is exactly the path to shipping a half-broken feature. Hard-gating it means we either ship coverage or don't ship the entry.
- **Visual proof is the only layer that surfaces the ship to a human reviewer at PR time.** Without it, parameterization PRs are invisible to non-author reviewers (manifest deltas + decoder code aren't where the regression risk lives).
- **The exemption escape hatch exists** for the rare case where one of the layers genuinely doesn't apply (e.g., a future module whose photographic effect can't be measured against the synthetic reference targets). Forcing it into the manifest with a justifying string makes "skip the test" a deliberate, reviewable decision.

## Alternatives considered

- **Soft convention, documented in CONTRIBUTING.md, no CI enforcement.** Rejected — RFC-021 §Q5: "the trap that gets us a v1.6.0 with broken parameterization." Conventions without enforcement decay; the shape of "parameterized vocab without test coverage" is exactly the shape we want CI to catch.
- **Require only 3 of the 5 layers (skip lab-grade global or masked).** Rejected — masked is the highest-value layer (catches the failure mode farthest from the unit tests' visibility); cutting it defeats the purpose.
- **Allow `_test_coverage_exempt` without a reason string** (just a boolean flag). Rejected — too easy to flip silently. The required string forces articulation.

## Consequences

Positive:

- Parameterized modules ship with end-to-end confidence; regressions caught at PR time.
- The hard gate gives reviewers a clear "is this complete?" signal.
- Future contributors see the existing test layers as the template; coverage policy propagates by example.

Negative:

- New parameterized modules cost more PR time than a soft policy would (mitigated: the test-layer infrastructure is already built; new entries plug into existing harnesses).
- The linter adds one more test to maintain (mitigated: small; reads manifest, checks references; ~50 lines of test code).

## Implementation notes

The linter test:

```python
def test_every_parameterized_entry_has_full_coverage():
    manifest = load_full_manifest()
    parameterized = [e for e in manifest if "parameters" in e]
    for entry in parameterized:
        if entry.get("_test_coverage_exempt"):
            continue
        assert _has_unit_test(entry["name"]), f"missing unit test for {entry['name']}"
        assert _has_integration_test(entry["name"]), ...
        assert _in_lab_grade_global(entry["name"]), ...
        assert _in_lab_grade_masked(entry["name"]), ...
        assert _in_visual_proofs(entry["name"]), ...
```

The five `_has_*` / `_in_*` helpers grep the relevant test files and the gallery script for the entry's name. False negatives are possible if a contributor names the entry inconsistently in tests; that's surfaced during PR review and corrected before merge.

For v1.6.0 (the first ship under the new architecture), `exposure` and `vignette` are the two parameterized entries that must satisfy this policy. Their test coverage lands in the same PR as their manifest entries and decoders.
