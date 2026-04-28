# ADR-028 — Configuration formats: TOML for config, JSON for manifests

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/stack
> Related RFC · None (engineering choice)

## Context

The project has multiple kinds of structured configuration: photographer's global config (camera bindings, paths, providers), vocabulary pack manifests, per-image metadata, mask registries, session transcripts. Each has a primary author (human-edited vs program-emitted), update pattern (occasional vs continuous), and consumer (human reading vs program reading).

Choosing one format universally would optimize for one of these use cases at the others' expense. Two formats — chosen for their respective strengths — fit better.

## Decision

- **TOML** for configuration files that humans hand-edit:
  - `~/.chemigram/config.toml` (global config: paths, bindings, providers)
  - Future: per-pack settings if needed
- **JSON** for files emitted and consumed primarily by programs:
  - `manifest.json` (vocabulary pack metadata)
  - Per-image `metadata.json` (EXIF cache, layer bindings, layer markers)
  - Mask registry `registry.json`
  - Session transcripts (JSONL — see ADR-029)
  - Operation log `log.jsonl`
  - Vocabulary gaps `vocabulary_gaps.jsonl`

## Rationale

- **TOML for human editing.** Comments, less syntax noise, forgiving formatting (trailing commas don't error). The photographer hand-edits `config.toml`; readability matters.
- **JSON for program emission.** Wider tooling support, faster parsing, no comments to handle (programs don't need them), schema validators readily available.
- **stdlib coverage.** Python 3.11+ has `tomllib` (read) and `json` in stdlib. Writing TOML still needs an external dependency (`tomli-w`); TOML files are written rarely (almost always hand-edited), so the dependency cost is low.
- **JSONL for append-only logs.** One JSON object per line; trivial to append, trivial to stream-read, robust to truncation (you can read up to the last complete line).

## Alternatives considered

- **All JSON:** rejected — hand-editing JSON is painful (no comments, strict trailing comma rules). `config.toml` is read often by photographers.
- **All YAML:** rejected — YAML's whitespace sensitivity, type-coercion surprises, and complex parsing make it worse than either alternative for both use cases. The `Norway problem` (`no` parsed as boolean) is real.
- **All TOML:** rejected — TOML is awkward for nested arrays of objects (the manifest schema would be ugly), and `tomli-w` isn't stdlib.

## Consequences

Positive:
- Each file format matches its use case
- Configuration files have comments
- Programs read/write without external dependencies (TOML read is stdlib; JSON is stdlib)
- JSONL append-only logs are robust

Negative:
- Two formats to teach contributors (mitigated: the distinction is clear and consistent)
- TOML write needs `tomli-w` dependency — only used in setup helpers, not in the runtime hot path

## Implementation notes

`src/chemigram_core/config.py` reads `config.toml` via `tomllib`. Manifest, metadata, registry, and JSONL files use `json` from stdlib. CI's schema validation happens via JSON Schema for JSON files; TOML is checked for syntax + required-keys-present.
