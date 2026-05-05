# ADR-077 — Path C as default for parameterized modules

> Status · Accepted
> Date · 2026-05-05
> TA anchor ·/components/synthesizer ·/constraints/opaque-hex-blobs
> Related RFC · RFC-021 (closes); supersedes part of ADR-008
> Related ADRs · ADR-008 (opaque-blob default; partially superseded), ADR-073 (Path C as authoring technique; this ADR extends it to apply time)

## Context

ADR-008 made `op_params` and `blendop_params` opaque blobs by default, with **Path C** (programmatic decode/edit/re-encode) as a rare exception for high-value modules. RFC-012 / ADR-073 confirmed Path C is feasible and shipped it as an *authoring*-time technique (programmatically generate `.dtstyle` files at vocabulary-build time).

Operating on the discrete-vocabulary assumption produced a structural thinness: the vocabulary today has 4 hardcoded exposure entries (`expo_+0.3/-0.3/+0.5/-0.5`), 3 vignette intensities, 2 WB strengths (only subtle), and so on. Asking a photographer to pick `+0.7 EV` cannot be answered. Combinatorially enumerating every plausible magnitude is infeasible.

RFC-021 deliberated the architectural shift: extend Path C from authoring time to apply time, so the engine can synthesize an arbitrary-magnitude application of a parameterizable module without per-strength vocabulary entries.

## Decision

Path C is the **default** for vocabulary modules whose photographic axis is continuous magnitude and that explicitly declare a `parameters` block in their manifest entry. ADR-008's opacity policy continues to govern every other module (the vast majority of darktable's ~50 photographically-meaningful modules and the `blendop_params` blob universally).

A parameterized module ships with: (a) a manifest entry declaring its parameters with byte-level field offsets per ADR-078, (b) a Path C decoder/encoder pair in `chemigram.core.parameterize.<module_name>`, and (c) lab-grade test coverage per ADR-080. The synthesizer at apply time decodes the entry's `op_params`, applies the user-supplied parameter values, re-encodes, and proceeds with the existing apply pipeline (including drawn-mask binding per ADR-076).

Modules without a `parameters` block continue to behave as ADR-008 specifies — opaque blobs, copied verbatim. The two paths coexist; they don't conflict.

## Rationale

- **Escapes the discrete-vocabulary trap.** Continuous magnitude becomes a first-class parameter; no combinatorial vocabulary explosion.
- **ADR-008's opacity policy still earns its keep** for the modules where parameterization isn't worth the per-module decoder investment. The choice is now per-module instead of repo-wide.
- **Composes cleanly with ADR-076 mask binding.** Parameterization edits `op_params`; mask binding edits `blendop_params` + injects `masks_history`. They don't touch the same bytes.
- **Path C decoders are a known cost.** RFC-012 / ADR-073 demonstrated the engineering shape; reusing those decoders at apply time is a small extension, not a new investment.
- **Modversion drift handled per-decoder.** Each Path C decoder is modversion-pinned and refuses to operate on mismatched blobs. Adding a new modversion is a clear failure with a clear fix; no silent corruption.

## Alternatives considered

- **Keep ADR-008's framing unchanged; author more discrete strengths instead.** Rejected — combinatorially infeasible; documented in RFC-021 §Alternative A.
- **Parameterize at session/agent layer instead of engine.** Rejected — pushes the burden onto every integration; doesn't compose with masking; documented in RFC-021 §Alternative B.
- **Use `darktable-cli --style` for parameter overrides.** Rejected — ADR-011 already rejected `--style` for vocabulary application; doesn't expose per-parameter overrides; documented in RFC-021 §Alternative C.

## Consequences

Positive:

- Continuous magnitude is supported for any parameterized module
- Vocabulary entries collapse: 4 exposure entries → 1, 3 vignette → 1, etc. Manifest weight freed for genuinely new photographic moves.
- Agent reasoning over magnitude is direct (`apply_primitive(name="exposure", value=0.7)`) rather than producing stacking workarounds.
- No combinatorial vocabulary explosion required to cover the gap.

Negative:

- Per-module engineering cost for each Path C decoder (~half-day per simple single-axis module after architecture lands).
- Modversion drift risk for parameterized modules; mitigated by pinning + clear failure on mismatch.
- Manifest schema is more complex for parameterized entries (mitigated: optional; flat schema unchanged for non-parameterized entries).

## Implementation notes

`chemigram.core.parameterize.<module_name>` is the namespace for Path C decoders. Each module gets its own submodule with at minimum two functions: `decode(op_params: str) -> ModuleParams` and `encode(params: ModuleParams) -> str`. Round-trip equivalence (`encode(decode(blob)) == blob`) is the unit-test contract.

The synthesizer's apply path checks `entry.parameters` (per ADR-078). When present and the caller supplied values, the decoder is invoked; the resulting `op_params` replaces the entry's stored `op_params` for that one apply call. The original `.dtstyle` is not mutated.

ADR-008's "Path C is the rare exception" wording is partially superseded by this ADR. ADR-008 continues to apply to `blendop_params` universally, to non-parameterized modules, and as the documented baseline. This ADR adds: "for modules with a manifest `parameters` block, Path C runs by default at apply time."
