# ADR-011 — Reject `darktable-cli --style NAME` for vocabulary application

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/render-pipeline ·/components/synthesizer
> Related RFC · None (settled by Phase 0 testing)

## Context

`darktable-cli` accepts a `--style NAME` flag that applies a named style during export. On the surface, this looks like a tempting alternative to XMP synthesis: the photographer authors styles in the GUI, and `darktable-cli --style NAME` applies them.

Phase 0 testing surfaced two reliability issues with this approach.

## Decision

Chemigram does not use `darktable-cli --style NAME`. Vocabulary application happens through XMP synthesis (per ADR-001, ADR-002, ADR-008, ADR-009): the synthesizer reads `.dtstyle` files, composes them into XMPs, and passes the XMP positionally to `darktable-cli`.

## Rationale

Phase 0 finding 6: `--style NAME` lookup is unreliable in darktable 5.4.1. Specifically:
- Styles **created** in the GUI (saved via "create" button in the styles panel) are NOT findable by `darktable-cli --style NAME` even when they appear in the styles list and a `.dtstyle` file exists at the expected path in the configdir.
- Styles **imported** in the GUI (loaded via "import" button) ARE findable.
- Both produce identical files on disk and look identical in the GUI; the distinction is invisible.

This makes `--style NAME` fragile in any setup workflow that creates styles programmatically or in the GUI. Even when it works, it requires a database-import step that XMP synthesis avoids entirely.

XMP synthesis (the path Chemigram commits to) is also strictly more capable: it composes multiple primitives in a single call, supports SET semantics across vocabulary entries, doesn't require any database state, and the architectural critical path (Phase 0 experiment 4) is already validated end-to-end.

## Alternatives considered

- **Use `--style NAME` and require photographers to import styles into the configdir:** rejected — adds a setup step, requires runtime synchronization between vocabulary directory and configdir database, and the create-vs-import distinction would silently break some setups.
- **Pass `.dtstyle` paths via `--style /full/path/to.dtstyle`:** tested in Phase 0; same "cannot find the style" error. The flag does not accept file paths.
- **Use `--style-overwrite`:** doesn't address the underlying lookup issue.

## Consequences

Positive:
- One source of truth: the synthesized XMP. Vocabulary directory and runtime configdir don't need to stay in sync.
- Multi-primitive composition works in one render call (no chained `--style` flags would be needed).
- Robust across machines and configdir states.

Negative:
- Slightly more synthesizer work upfront (build the XMP) compared to the hypothetical `--style NAME` shortcut, but Phase 0 confirmed the synthesizer cost is small and the result is more reliable.

## Implementation notes

The `DarktableCliStage` invocation (per ADR-004) passes the synthesized XMP path positionally: `darktable-cli RAW XMP OUT --width N ...`. The `--style` flag is never used. 04/8.2 documents this canonical form. CONTRIBUTING.md does not mention `--style` as a vocabulary application path.
