# ADR-024 — Authoring discipline: uncheck non-target modules in dialog

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/synthesizer
> Related RFC · None (Phase 0 finding 2)

## Context

Phase 0 testing surfaced that darktable's create-style dialog includes "all modules in the active pipeline" by default — accepting the default produces a 12-14 module `.dtstyle` containing all of darktable's `_builtin_*` defaults plus the L0 always-on stack (rawprepare, demosaic, colorin, colorout, gamma, etc.). Without authoring discipline, every vocabulary primitive would be polluted with this noise.

The parser handles this defensively (ADR-010 filters by `_builtin_*` prefix and by manifest's `touches` list), but quality of output still depends on what the photographer authored.

## Decision

The standard authoring procedure for a single-module vocabulary primitive includes an explicit step: in darktable's create-style dialog, **uncheck every module except the target operation** before clicking create. The exported `.dtstyle` then contains exactly the user-authored entries, not a noisy 12-14 module dump.

For multi-module primitives (e.g., a WB entry that captures the WB / color calibration coupling — see ADR-025), uncheck everything except the declared `touches` list.

## Rationale

- **Correctness via defense in depth.** Parser filters provide a safety net (ADR-010), but a clean source file is easier to review, share, and trust.
- **Reviewability.** A vocabulary PR with a 1-plugin `.dtstyle` is reviewable at a glance; a 14-plugin one obscures intent.
- **Consistency.** All vocabulary contributions follow the same authoring pattern; reviewers know what to expect.
- **Phase 0 evidence.** The discipline was discovered empirically — authoring without it produced noisy files; authoring with it produced clean files.

## Alternatives considered

- **Trust the parser; accept noisy `.dtstyle` files:** rejected — even though the parser is defensive, polluted files harm review quality and bloat repository size.
- **Post-process `.dtstyle` files at PR time to strip `_builtin_*`:** rejected — adds tooling complexity for a problem that 30 seconds of dialog discipline solves.
- **Patch darktable to make "uncheck all" the default:** out of scope — we're not in a position to change darktable's UX defaults.

## Consequences

Positive:
- Vocabulary PRs are clean and reviewable
- Repository size stays small (1-3 plugin entries per file vs 14)
- Author intent is visible without parsing

Negative:
- Manual step in the authoring procedure (must be communicated in CONTRIBUTING.md and the create-style dialog UX is what it is)
- Photographers may forget the step (mitigated: parser is defensive; CI's render test catches gross errors; reviewer feedback educates over time)

## Implementation notes

`docs/CONTRIBUTING.md`/Authoring procedure documents the discipline as step 4 in the procedure. CI's `.dtstyle` schema validation counts `<plugin>` entries against the manifest's `touches` declaration; a mismatch warns the contributor but doesn't necessarily block (since the parser's defenses make it not strictly broken).
