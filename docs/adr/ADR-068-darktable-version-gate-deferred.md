# ADR-068 — darktable version gate (deferred)

> Status · Accepted (deferred)
> Date · 2026-05-02
> TA anchor ·/components/eval ·/components/pipeline
> Related RFC · RFC-019 v0.2 (closes here), RFC-007 (modversion drift)

## Context

RFC-019 v0.1 proposed a darktable-version-pinning mechanism: each reference-target test recorded the darktable version it was calibrated against, and a session-scope fixture warned (not failed) when the installed version diverged. The fixture made sense for Tier B (real-RAW reference tests, which depend on darktable's RAW pipeline). RFC-019 v0.2 dropped Tier B for v1.2.0 — the synthetic-only path (Tier A) doesn't run darktable at all.

This ADR records the decision to defer the version gate.

## Decision

No darktable version gate ships in v1.2.0. The assertion library and synthetic-fixture tests don't invoke darktable; there's nothing to pin against.

When (if) Tier B reopens — via a follow-on RFC if a community-contributed downloadable RAW pack appears — the version-gate mechanism reopens with it. At that point the implementation is straightforward:

```python
@pytest.fixture(autouse=True, scope="session")
def check_darktable_version():
    version = get_darktable_version()
    if version != CALIBRATED_DT_VERSION:
        warnings.warn(
            f"Reference baseline calibrated against darktable {CALIBRATED_DT_VERSION}; "
            f"installed is {version}. Thresholds may need recalibration."
        )
```

Until then, the project's existing drift-detection mechanism — `darktable_version` per vocabulary manifest entry + RFC-007 (modversion drift handling) — covers the Path A and Path B vocabulary entries. v1.2.0 ships 35 entries calibrated against darktable 5.4.1; if a future dt version regresses, RFC-007 surfaces the affected entries.

## Rationale

- **No dependency, no gate.** The synthetic-only path uses `chemigram.core.assertions` over Pillow only. There's nothing for the gate to check.
- **Drift detection happens elsewhere.** The vocabulary manifest's per-entry `darktable_version` field is the canonical drift signal. RFC-007 is the closing mechanism.
- **Reopens cleanly.** When Tier B reopens, the version-gate fixture is ~10 lines. Premature implementation now would either be dead code or (worse) be surface area that must be maintained without exercising it.

## Alternatives considered

- **Implement the gate now even though it has nothing to check.** Rejected: dead code; per CLAUDE.md "Don't add features... beyond what the task requires."
- **Use a synthetic-pipeline version gate** (e.g., warn if Pillow version drifts). Rejected: Pillow version-stability is broad and irrelevant — the colour math we use (RGB ↔ HSV, image loading, histogram) is decade-stable.

## Consequences

Positive:
- One fewer thing to maintain in v1.2.0.
- The shape of the gate is documented; future-us doesn't need to rediscover it.

Negative:
- If Tier B reopens later and the calibration drifts in a way the per-entry `darktable_version` field misses, the regression surfaces only when an e2e test fails (not at session start). Acceptable: the test failures point at the right place.

## Implementation notes

- Nothing to implement under this ADR. The future implementation lives wherever Tier B lives — likely `tests/e2e/test_reference_real_raw.py` if it ever ships.
- RFC-007 closure under a future ADR will detail the per-vocabulary-entry drift-detection path.
