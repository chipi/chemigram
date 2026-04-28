# ADR-010 — Vocabulary parser identifies user entries by empty `<multi_name>`

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/synthesizer ·/contracts/dtstyle-schema
> Related RFC · RFC-001

## Context

`.dtstyle` files exported from darktable's GUI contain a mix of user-authored entries and darktable's auto-applied `_builtin_*` defaults (scene-referred default exposure, sigmoid, channelmixerrgb; auto flip; the L0 always-on stack: rawprepare, demosaic, colorin, colorout, gamma).

Even with proper authoring discipline (uncheck non-target modules in the create-style dialog, per ADR-024), some `_builtin_*` entries are present. The parser needs a reliable rule to distinguish "what the photographer actually authored" from "what darktable auto-applied around it."

Phase 0 experiment 2 surfaced the discriminator empirically: user-authored entries have empty `<multi_name>`; auto-applied entries have `<multi_name>` starting with `_builtin_`.

## Decision

The vocabulary parser identifies user-authored entries by the predicate:

```
multi_name == "" or not multi_name.startswith("_builtin_")
```

When loading a `.dtstyle` file, the parser:
1. Parses all `<plugin>` elements
2. Filters to entries where `<multi_name>` is empty or non-`_builtin_*`
3. Further filters by the manifest's `touches: [...]` declaration (entries whose `<operation>` is in `touches`)
4. Returns those entries for XMP composition

## Rationale

- Empirical: Phase 0 testing on darktable 5.4.1 confirmed `_builtin_*` is darktable's consistent labeling for auto-applied defaults across multiple module types (`_builtin_scene-referred default`, `_builtin_auto`).
- Reliable: contributors can't accidentally produce a `_builtin_*`-labeled entry through normal authoring.
- Defensive: even when contributors don't follow the create-style dialog discipline (ADR-024), the parser correctly extracts what they authored vs. what darktable added.
- Combines well with the manifest's `touches`: parser does both filters in one pass.

## Alternatives considered

- **Trust the create-style dialog discipline (don't filter):** rejected — would break for any contributor who doesn't follow the discipline. Phase 0's first iteration captured 14 modules; a parser without filtering would wrongly include all 14 in synthesis.
- **Filter by `<num>` ordering (assume the last entry is user-authored):** rejected — fragile, breaks when the user authors multiple entries (e.g., a multi-module move like coupled WB / color calibration).
- **Filter by `<modversion>` matching the manifest:** redundant with the manifest's `touches` filter; doesn't add discriminative power for the `_builtin_*` distinction.
- **Store user entries in a separate XML element, not plugin:** would require darktable changes; out of scope.

## Consequences

Positive:
- Parser is robust to authoring noise (extra `_builtin_*` entries don't affect output)
- Authoring discipline (ADR-024) becomes a quality-of-output discipline, not a correctness discipline
- The combination (filter `_builtin_*` + filter by `touches`) is small and testable

Negative:
- The parser is coupled to darktable's `_builtin_*` naming convention; if darktable changes this in a future version, the parser breaks (mitigation: version-pin and test on each darktable release; see ADR-026 / RFC-007)
- A pathological contributor could name a user entry `_builtin_*` deliberately and the parser would skip it (mitigation: schema validation in CI rejects this)

## Implementation notes

`src/chemigram_core/dtstyle.py.parse_dtstyle(path, touches)` returns the filtered list. The `touches` parameter is the manifest's `touches: [...]`. The function is the canonical entry point — callers should always pass `touches` rather than getting all entries and filtering downstream.
