# ADR-088 — Parametric L2 strength via Path B (per-parameter interpolation)

> Status · Draft (impl shipped 2026-05-10; flips to Accepted on darkroom validation)
> Date · 2026-05-10
> TA anchor · /components/synthesizer · /contracts/vocabulary-manifest
> Related RFC · RFC-035 (closes; Path B chosen)
> Related ADRs · ADR-077..080 (RFC-021 parameterized magnitudes), ADR-051 (same-module collision)

## Context

L2 looks ship as fixed-value composites — `look_landscape_dramatic_moody` has sigmoid contrast 1.7, full saturation grade, full clarity bite, all baked. Until v1.10.0 there was no shorthand for "this look at 50% strength." RFC-035 framed three real options: per-plugin opacity blending (Path A), per-parameter interpolation (Path B), hybrid (Path C). Full deliberation in RFC-035; this ADR captures the closing decision.

## Decision

Adopt **Path B — per-parameter interpolation** as the strength mechanism. At apply time, when an L2 look is invoked with `strength ∈ [0.0, 1.0]`, every parameterizable field in every plugin interpolates linearly between the module's identity value and the authored value:

> `interpolated = identity + strength * (authored - identity)`

`strength=1.0` preserves the look's authored values byte-for-byte (current behavior). `strength=0.0` pulls every parameterized field to identity, producing a no-op even though the plugins remain structurally present in history. `strength=0.5` is halfway. Non-parameterized fields (sigmoid mode, vignette shape, blendop bytes) preserve the look's authored values regardless of strength — strength only scales what's parameterizable. Modules without a registered Path C decoder pass through unchanged at any strength.

Identity values per axis ship in the per-module parameterize registry (e.g., `sigmoid.contrast` identity = 1.0; `colorequal.sat_red` identity = 0.0). The synthesizer pulls from the registry; no per-look manifest declarations.

## Rationale

- **Perceptually closer to "this look at half strength."** Parameter-space interpolation tracks photographers' mental model better than opacity dimming. Path A's opacity blending dimmed everything wholesale, which feels right for some plugins (vignette, grain) and wrong for others (sigmoid contrast, color grading).
- **Composes cleanly with masks.** Strength scales the *effect*; masks scope the *region*. Independent levers, no interference.
- **Single source of truth for identity values.** Each parameterize module already declares its identity-axis-by-axis (sigmoid_contrast=1.0, colorequal sat_X=0.0, etc) for the parameter ladder mechanic. Strength interpolation reuses the same registry — no per-look manifest authoring.
- **Backward compatible.** `strength=1.0` is the default; un-parameterized callers see no behavior change. Looks without the `parameters` array still apply at full strength.

## Alternatives considered

- **Path A — per-plugin opacity scaling.** Rejected as primary because opacity is not perceptually linear across plugin types (e.g., 50% sigmoid felt weaker than 50% color grading). Considered as a fallback for un-parameterized plugins; instead chose to leave those at authored values (the simpler discipline).
- **Path C — hybrid (opacity for non-parameterized, interpolation for parameterized).** Rejected as too complex for the v1.10 ship. The mixed routing is harder to reason about and the current registry coverage (11 parameterized modules) means almost everything routes through interpolation anyway. Reconsider if a real workflow surfaces a non-parameterized plugin where opacity scaling would matter.
- **Path D — author intensity ladders (`_subtle` / `_medium` / `_strong` per look).** Rejected because it triples the catalogue surface and contradicts RFC-021's parameterized-magnitudes discipline at the L2 layer.
- **Multi-axis strength (`strength_contrast` / `strength_color` / `strength_clarity`).** Reasonable per RFC-021's parametric-primitive convention; deferred. The dominant case "this look at 50%" is well-served by single-axis. Multi-axis remains a future refinement if visual review surfaces dial-the-facets-independently as a real need.
- **Strength via apply-time mask opacity** (apply the look through a parametric opacity-blend mask). Rejected because it conflates strength with masking — the photographer can no longer apply at strength + a real mask without nesting.

## Consequences

Positive:
- One named L2 look = one entry, dial-able from 0 to authored magnitude.
- No re-authoring of the 31 existing L2 looks.
- The agent can scene-adapt a look's strength based on the brief.
- Composes cleanly with `apply_per_region` (each region can carry its own strength).

Negative:
- Path B's perceptual linearity is hypothesis-tested at the unit level (interpolation math is right) and integration level (synthesizer wiring is right) but the *visual* quality at strength=0.3 / 0.5 / 0.7 needs darkroom validation against real raws. This ADR stays Draft until that pass completes.
- Modules without a registered Path C decoder pass through unchanged regardless of strength — at strength=0.0 they still apply at authored values. This is documented in the agent prompt template; visual review validates whether the divergence is intuitive.
- Strength scaling on a multi-plugin look means each plugin's effect dampens by the same fraction. Some looks may benefit from per-plugin strength curves (e.g., contrast dampens faster than color grade); deferred to multi-axis strength (alternative above).

## Implementation notes

- New module: `src/chemigram/core/strength.py` with `IDENTITY_VALUES` registry + `interpolate_plugin_strength()` + `apply_strength_to_dtstyle()`.
- `apply_entry()` in `helpers.py` accepts `strength: float | None`. Validation: `[0.0, 1.0]` raises `ValueError` outside.
- CLI: `chemigram apply-primitive --entry <look> --strength <float>`.
- MCP: `apply_primitive` tool accepts `strength_arg`.
- Tests: 14 new in `tests/unit/core/test_strength.py` covering identity-pull, midway interpolation, clamping, multi-plugin L2 looks, integration with `apply_entry`.
- Visual-review checkpoint: `docs/guides/darkroom-session-debt.md` — items pending validation include whether 0.5 strength reads as "half-effect" on real raws across genres.

## How this closes RFC-035

RFC-035 had three open paths (A/B/C) plus four open questions. This ADR locks Path B and answers:

1. **Single-axis strength** — yes (multi-axis deferred until visual review surfaces a need).
2. **Default value 1.0** — yes (backward compat).
3. **Composes with `apply_per_region`** — yes (mixed-op `apply_per_region` per RFC-036 supports per-region strength).
4. **Behavior at strength=0.0** — plugins remain structurally in history with parameters at identity; renders as no-op. Matches RFC-021's parameter=identity convention.
5. **Existing fixed-value looks remain valid** — yes; parametric strength is opt-in via the `--strength` flag, default = full authored.
