# ADR-090 — `propagate_state` MCP verb (anchor-and-sync workflow)

> Status · Draft (impl shipped 2026-05-10; flips to Accepted on darkroom validation)
> Date · 2026-05-10
> TA anchor · /contracts/mcp-tools · /components/synthesizer · /constraints/single-process
> Related RFC · RFC-037 (closes; LR-Sync-parity discipline)
> Related ADRs · ADR-002 (SET-replace semantics), ADR-018 (per-image snapshot store), ADR-082 (modversion drift), ADR-084..087 (mask + retouch)

## Context

The photographer-workflow survey surfaced anchor-and-sync as a genre-spanning move (4/6 wedding photographers cite it; landscape series, wildlife bursts, multi-shot product sets all echo it). The pattern: nail post-processing on one anchor image, then propagate that state to a list of related target images. Lightroom's Sync does this; chemigram had no analog. Full deliberation in RFC-037; this ADR captures the closing decision.

## Decision

Add a single MCP verb `propagate_state(source_workspace, target_workspaces, *, exclude_ops?, include_per_image?, label?)` that copies the source image's history entries to every target image, with framing-bound ops auto-excluded by default.

Inheritance discipline: **inherit everything by default, exclude framing-bound ops**. Same shape as Lightroom Sync — settings that depend on per-image content or coordinates don't propagate.

Default framing-bound exclusions:
- `ashift`, `crop`, `retouch`, `lens` (operation-level — coordinate-specific or per-camera)
- Drawn-mask-bound entries (gradient / ellipse / rectangle / path — coordinates are image-specific)

Parametric range masks (color-range / luminance-range) DO propagate — they're content-relative, not coordinate-bound.

Atomic semantics: every target validates first; any modversion mismatch / missing target / empty-history source / cap-exceeded aborts the entire batch. No target receives partial state.

Cap: `MAX_TARGETS_PER_CALL = 200`. Generous-but-finite; covers wedding lighting groups (~80-100 max), bird bursts (~30), product variants (~20).

CLI: `chemigram propagate-state --source <id> --targets <id1>,<id2>,... [--label <label>] [--include-per-image]`.

## Rationale

- **LR-parity is the right discipline.** Photographers' mental model for cross-image sync was shaped by Lightroom; matching that discipline reduces friction. The framing-bound exclusion list is what LR Sync excludes too.
- **Inherit-everything-by-default beats predefined scopes** ("wb_only", "color_only", etc). The early RFC framing proposed scope presets; survey feedback reframed this — photographers want the inverse: "everything except framing-specific moves." Predefined scopes would be a leaky enumeration.
- **Atomic-synchronous is fine for v1.** 200 targets × ~5s = ~17min worst case; the chemigram single-process constraint (TA/constraints/single-process) means async job tracking is a substantial scope expansion. Revisit if photographer feedback shows real wait pain.
- **Hard-reject on modversion drift.** Mirrors RFC-007 / ADR-082's discipline. Silent partial-propagation would mask real format bugs.

## Alternatives considered

- **Author an L2 look on the fly from the anchor and apply it.** Rejected as primary path — produces permanent vocabulary artifacts for ephemeral session decisions; scope control awkward; engineering cost high. A future enhancement could combine: photographer applies propagated state, then optionally promotes to a personal-pack L2 look.
- **Extend `apply_primitive --stdin` to accept N primitives.** Rejected — derived semantics need scope, atomicity, op-log surfaces that `--stdin` doesn't expose.
- **Use chemigram's existing branch/merge model.** Rejected — branches are per-image; cross-image state replication isn't what they're for.
- **Background-job model with polling.** Rejected for v1 — async job tracking is substantial scope expansion. Atomic-synchronous suffices today.
- **Per-target customization at propagation time** (e.g., apply with N% strength scaling per image). Deferred — would conflate RFC-035 with this verb; a future per-target-overrides extension is separable.

## Consequences

Positive:
- Closes the highest-recurrence cross-genre workflow gap not yet addressed.
- One snapshot per target with explicit propagation label; the source's hash is captured for traceability.
- Composes with the full RFC-024/025/029 mask architecture — drawn masks excluded, parametric masks propagate.
- Future "re-propagate from source's HEAD" recipe becomes possible from the captured source-hash.

Negative:
- +1 MCP verb. Adds to the agent's surface area; mitigated by clear semantics (LR-Sync analog).
- Drawn-mask exclusion is opinionated; some photographers may want them propagated. The default favors right-thing-by-default; the `include_per_image` opt-in preserves flexibility.
- Multi-modversion targets hard-reject. Documented; offers clear feedback rather than silent-bad-render.
- Cap of 200 may bite extreme batches (multi-camera cinematic shoots). Revisitable if real workflows hit it.

## Implementation notes

- New module: `src/chemigram/core/propagate.py` with `propagate_state()` core function + `FRAMING_BOUND_OPS = frozenset({"ashift", "crop", "retouch", "lens"})` + `_is_drawn_mask_bound()` helper that decodes blendop_params mask_mode field.
- `propagate_state` round-trips: each source HistoryEntry converts to PluginEntry, gets bundled into a synthetic DtstyleEntry, then routes through `synthesize_xmp` against each target's baseline (reuses the existing SET-replace / Path B Add discipline).
- CLI: `propagate-state` command in `src/chemigram/cli/commands/edit.py`.
- MCP: `propagate_state` tool registered in `src/chemigram/mcp/tools/vocab_edit.py`.
- Tests: 13 new in `tests/unit/core/test_propagate.py` covering source-state read, framing-bound exclusion, drawn-mask detection, atomic batch semantics, modversion-drift rejection, cap enforcement.

## Resolved RFC-037 open questions

1. **Scope presets** (`"wb_only"` / `"color_only"`) — abandoned in favor of inherit-everything-with-framing-bound-exclusions. Predefined scope enumerations would be leaky; the LR-Sync discipline of "everything that's portable" is cleaner.
2. **Op-log entry shape** — `{op: "propagate_state", source_image: "...", source_hash: "...", n_ops: N, label: "..."}`. Source hash anchors the propagation for traceability.
3. **Targets with unrelated edits already** — SET-replace per ADR-002; propagated ops replace matching ops on the target, non-matching target ops persist. Verified against wedding-burst use case.
4. **CLI shape** — explicit list via `--targets <id1>,<id2>,...`; stdin support is a follow-up if photographer feedback warrants.
5. **Render-validation feedback** — no for v1 (would slow large batches). Photographer-driven render-preview remains the validation tool.
