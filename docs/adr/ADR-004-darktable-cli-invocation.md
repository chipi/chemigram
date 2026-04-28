# ADR-004 — `darktable-cli` invocation form

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/render-pipeline ·/stack
> Related RFC · None (settled by Phase 0 testing)

## Context

The render pipeline shells out to `darktable-cli` for every preview and export. The exact invocation form affects performance, isolation, and predictability. Phase 0 testing surfaced specific flag behaviors in darktable 5.4.1 that pin down the canonical form.

## Decision

Chemigram invokes `darktable-cli` as:

```
darktable-cli \
  <raw_path> \
  <xmp_path> \
  <output_path> \
  --width <pixels> \
  --height <pixels> \
  --hq <bool> \
  --apply-custom-presets false \
  --core --configdir <isolated_configdir>
```

Positional arguments first (raw, XMP, output), CLI flags second, then `--core` as the separator into core darktable flags (`--configdir` and similar).

## Rationale

- Positional XMP path lets the synthesizer compose XMPs once and pass them directly. No need to import styles into a database first (Phase 0 finding 6).
- `--apply-custom-presets false` prevents the photographer's auto-applied presets from contaminating the render. Critical for reproducibility.
- `--core --configdir <path>` isolates Chemigram's darktable state from the photographer's everyday library.
- `--hq false` for previews (faster), `--hq true` for final exports (quality).
- Phase 0 confirmed wall-clock 1.7-2.3s for 1024px renders on Apple Silicon — within the predicted 1-3s envelope.

## Alternatives considered

- **`darktable-cli --style NAME`:** rejected (see ADR-011) — style-name lookup is unreliable in 5.4.1 and only finds GUI-imported (not GUI-created) styles.
- **`--apply-custom-presets true` (default):** rejected — risks the photographer's auto-presets contaminating the render and producing inconsistent output across machines.
- **No `--core` flag:** invalid for `darktable-cli`. The flag is the separator between cli-specific options and core darktable options. `darktable-cli` requires it; `darktable` (the GUI launcher) does *not* accept it (Phase 0 finding 1).

## Consequences

Positive:
- Reproducible renders across machines and runs
- Isolated state (no contamination of the photographer's real library)
- Predictable wall-clock time (1-3s for previews, longer for full-resolution exports)

Negative:
- Slightly verbose invocation (mitigated: it's wrapped in `DarktableCliStage` and the agent never sees the raw command)
- `--core` flag confusion for anyone who tries to pattern-match the invocation onto the GUI launcher (mitigated: documented in the architecture doc, section 8.2, and in CONTRIBUTING.md)

## Implementation notes

`src/chemigram_core/stages/darktable_cli.py` — the v1 stage that spawns this subprocess. See ADR-005 for the serialization constraint (one process per configdir at a time).
