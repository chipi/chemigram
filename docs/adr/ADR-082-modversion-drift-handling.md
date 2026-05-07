# ADR-082 — Modversion drift handling: warn-loud at load, hard-fail at apply

> Status · Accepted
> Date · 2026-05-07
> TA anchor ·/constraints/modversion-pinning ·/components/synthesizer ·/contracts/vocabulary-manifest
> Related RFC · RFC-007 (closes)
> Related ADRs · ADR-008 (opaque-blob default), ADR-077 (Path C as default for parameterized modules), ADR-080 (5-layer test coverage policy), ADR-081 (parameterization tiering policy)

## Context

RFC-007 was filed in the Phase 1 era when Path C was a "rare exception" per ADR-008. Modversion drift was a small surface — at most one or two parameterized modules — and the RFC was deferred while the architecture stabilised.

Post-Phase-4 / Tier 2 / brilliance: **the parameterize registry holds 11 Path C decoders**, each pinned to a specific darktable modversion. The drift surface is no longer small. Concretely, when darktable releases a version that bumps a module's modversion, the result depends on what protections are in place:

- Without drift detection: the user upgrades darktable, applies a vocabulary entry, and discovers the breakage when `patch_op_params` raises `PatchError` mid-session.
- With drift detection: the user is warned at vocab load time that specific entries are calibrated for a different modversion, can proactively re-author or pin darktable.

The Phase-1-era "hardcoded modversion in the manifest" annotation already captures the *expected* version. What's been missing is a runtime check that compares manifest expectations against the engine's pinned reality.

## Decision

A two-tier policy aligned with the parameterization tiering of ADR-081:

**For parameterized modules (Tier 1+2)** — modules with a registered Path C decoder in `chemigram.core.parameterize`:

1. **At vocabulary load time**, walk every entry's `modversions` dict; for each module that's in the parameterize registry, compare the manifest's declared modversion to the decoder's `SUPPORTED_MODVERSION`. On mismatch, emit a `UserWarning` naming the entry, the module, the declared modversion, and the engine's pinned modversion.
2. **The vocab still loads** with a warning — the photographer can render and judge whether the bump actually changes the binary format meaningfully (modversion bumps sometimes don't affect the relevant fields).
3. **Strict mode** is opt-in via `CHEMIGRAM_VOCAB_STRICT_MODVERSION=1`. When set, drift becomes a `ManifestError` that prevents the vocab from loading. Useful for CI / production scenarios where silent drift would mask bugs.
4. **At apply time**, the `patch_op_params` registry router already raises `PatchError` on `(module, modversion)` mismatch. This is the runtime backstop — even if the load-time warning is dismissed, applying a drifted entry fails loudly with a clear message before any rendering happens.

**For non-parameterized modules (Tier 3 + `blendop_params` universally)** — no project-side detection. ADR-008's opacity policy applies; the synthesizer copies bytes verbatim. If darktable's runtime can't read a stale blob, it surfaces as a render error from `darktable-cli`. The project doesn't intercept here.

## Rationale

- **The Phase-1-era manifest annotation finally earns its keep.** `modversions: {<module>: N}` was authored into manifests since the start; this ADR closes the loop by checking it at runtime.
- **Warn-loud aligns with photographer agency.** Modversion bumps often DON'T change the binary format meaningfully (e.g., adding a new optional field at the end of the struct). Blocking on every bump would force re-authoring even when the existing bytes still render correctly. The warning gives the photographer the signal; the render gives them the verdict.
- **The hard-fail apply-time backstop is non-negotiable.** Even if the load-time warning is missed, `PatchError` fires before bytes hit darktable — silent corruption is impossible.
- **Strict mode is a single env var, not a config file knob.** Per CLAUDE.md "no half-finished implementations": the env var is enough; if richer per-pack policy becomes necessary later, it ships as a follow-on.
- **Tier 3 is intentionally not covered.** Detecting drift for non-parameterized modules requires darktable-cli introspection (slow, fragile) or hardcoded version registries (drifts). The cost outweighs the benefit when the apply-time failure mode is "darktable returns an error" — already loud enough.

## Alternatives considered

- **Strict-by-default at load time** — rejected. Modversion bumps that don't change binary format would over-block. The RFC's preferred direction was warn-loud.
- **Per-module per-modversion compatibility matrix** — rejected as scope creep. Maintaining "5.4 mv4 ↔ 5.6 mv5 are wire-compatible" assertions would require empirical testing per release; expensive and the photographer's render is the truth anyway.
- **Best-effort migration (translate old op_params to new format)** — rejected per ADR-008. Per-module migration logic re-introduces the per-module engineering cost ADR-008 was designed to avoid.
- **`darktable-cli` introspection at load time** — rejected for the load-time check. Subprocess call per vocab load adds noticeable latency (100-300 ms) for a check that's accurate only at the moment darktable is consulted, not later. The pinned-decoder-vs-manifest check is faster and catches the same mismatches that matter for the parameterized surface.
- **Configuration via TOML file** — rejected as scope creep. The env var is sufficient; config-file policy follows if we genuinely need per-pack overrides later.

## Consequences

Positive:

- Photographers upgrading darktable mid-session see the drift signal at vocab load, before they apply anything.
- CI / production environments get a hard failure mode via `CHEMIGRAM_VOCAB_STRICT_MODVERSION=1` — no need for special test infrastructure.
- The manifest's `modversions` field, which existed but was only checked at unit-test time (per #85's `test_manifest_modversion_consistency.py`), now has a runtime use.
- The 11 currently-pinned Path C decoders all benefit; the policy scales automatically as new decoders ship (the registry self-extends).

Negative:

- Vocab load is marginally slower (one dict comparison per entry that declares parameterized modversions). Negligible — measured at <1 ms for the current 32-entry expressive-baseline pack.
- Tier 3 modules don't get drift detection. Acceptable per the rationale; darktable's render-time error is the safety net there.
- Strict mode is a global flag; if a pack contains a known-drifted entry the photographer wants to ignore, they can't go strict-on-the-rest. Acceptable; the warning surface tells them which entries to fix.

## Implementation notes

The implementation lives in `src/chemigram/core/vocab/_modversion_drift.py`:

- `_build_known_pinned_modversions()` — imports the 11 parameterize submodules (lazy, function-scoped to avoid circular imports) and returns `{module_name: SUPPORTED_MODVERSION}`.
- `check_entry_modversion_drift(entry)` — pure function, returns the list of mismatch messages for one entry. Modules without registered decoders are skipped.
- `emit_drift_signals(entries)` — walks the loaded entries, emits `UserWarning` per mismatch in default mode, raises `ManifestError` in strict mode.

`VocabularyIndex.__init__` calls `emit_drift_signals` once after entries are loaded but before the constructor returns. The check is bypass-able by user code that constructs entries directly without going through the index, but every supported entry-point (`load_packs`, `load_starter`, direct `VocabularyIndex(...)`) routes through it.

Tests live at `tests/unit/core/vocab/test_modversion_drift.py`:

- Clean starter + expressive-baseline packs load drift-free
- Synthetic pack with deliberate drift produces UserWarning in default mode
- Same synthetic pack raises `ManifestError` in strict mode
- Strict-mode env var accepts 1 / true / yes / on (case-insensitive); falsy values preserve default behavior
- Modules without registered decoders (e.g., channelmixerrgb — see RFC-022 / Tier 0) are correctly skipped

## Phase implications

This ADR doesn't introduce new phases or work. It closes RFC-007's open question by codifying the runtime detection that the parameterization work made both possible and pressing.

A follow-on ADR may be needed when the project transitions to multi-photographer review (per ADR-081's "real-people-review phase" deferral) — at that point per-photographer pinning, distributed pack versioning, and other multi-user concerns surface. For now, single-photographer use is fully covered.
