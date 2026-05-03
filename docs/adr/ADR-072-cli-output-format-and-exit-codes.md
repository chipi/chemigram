# ADR-072 — CLI output format: human default, NDJSON via `--json`; exit-code IntEnum

> Status · Accepted
> Date · 2026-05-03
> TA anchor ·/components/cli
> Related RFC · RFC-020 (closes here); related ADR-045 (prompt versioning is independent of package SemVer — same pattern applied here for the output schema)

## Context

The CLI (ADR-069) serves two distinct consumers:

1. **Humans** running commands interactively or reading output in a terminal. They want readable, aligned text. They do not want to parse JSON.
2. **Agents and scripts** consuming output programmatically. They want structured, parseable output. They do not want to parse human-readable text with regex.

These two requirements are in tension. The output format must be a first-class decision, not an afterthought. Similarly, exit codes must be stable and documented so script callers can branch on them without parsing stderr text.

## Decision

### Output format

**Human-readable text is the default. JSON mode is opt-in via `--json`.**

JSON output uses **newline-delimited JSON (NDJSON)** — one JSON object per line — rather than a single JSON document. The final line of NDJSON output is always a summary event (kind `result` for success, kind `error` for failure).

Both modes go through a shared `OutputWriter` Protocol in `chemigram/cli/output.py`. Commands never call `print()` or `sys.stdout` directly. Lint-enforceable; audit-tested.

### Output schema versioning

The NDJSON event schema is **versioned independently of package SemVer** — the same pattern as prompt versioning per ADR-045. Locked at `1.0` for v1.3.0; surfaced via `chemigram status`. Future additions (new optional fields, new event types) bump the minor; breaking changes (removed field, changed field type, removed event type) bump the major.

### Exit codes

```python
class ExitCode(IntEnum):
    SUCCESS = 0
    INTERNAL_ERROR = 1            # unhandled exception (bug)
    INVALID_INPUT = 2             # bad args, schema validation failure
    NOT_FOUND = 3                 # image_id, primitive name, snapshot, mask, etc.
    STATE_ERROR = 4               # workspace in inconsistent state
    VERSIONING_ERROR = 5          # snapshot-graph integrity issues
    DARKTABLE_ERROR = 6           # render subprocess failure
    MASKING_ERROR = 7             # masking provider failure
    SYNTHESIZER_ERROR = 8         # XMP synthesis failure
    PERMISSION_ERROR = 9          # filesystem permission
    NOT_IMPLEMENTED = 10          # tool stub or feature gate
```

The mapping `chemigram.cli.error_mapping.error_code_to_exit(ErrorCode) → ExitCode` is total (every `ErrorCode` from `chemigram.mcp.errors` produces a non-zero `ExitCode`); the `match` statement is mypy-exhaustive, with a runtime audit-style integration test as a safety net.

The set is **closed**; new exit codes go through an ADR amendment. Adding a new `ErrorCode` upstream requires extending this enum in lockstep.

### Diagnostic command

`chemigram status` is a **diagnostic that always exits 0** and reports missing components in fields and `warnings`. Erroring out on missing darktable would defeat the discoverability use case (you can't ask "is darktable installed?" if the answer is to fail when it isn't). Scripts needing a hard check for darktable can branch on `payload["darktable_cli_path"] is None` in the JSON output.

## Rationale

### Why not JSON by default

The primary interactive use case is a human at a terminal. A `chemigram` command invoked directly should be readable without piping to `jq`. Industry convention (grep, git, curl, darktable-cli) defaults to human output and provides machine output via flags.

### Why NDJSON instead of a single JSON document

Single JSON document:

- Requires buffering the entire output before the consumer can parse
- Cannot be streamed
- For long operations, the consumer gets nothing until completion

NDJSON:

- Each event is parseable as it arrives
- Compatible with streaming: `result.stdout.split('\n')`, `json.loads()` per line
- Standard in log processing (Logstash, Loki, etc.) and tool output (eslint `--format json`, etc.)
- The summary-line convention (last line is always a summary) gives non-streaming consumers a single parse target

### Why an OutputWriter abstraction

Without it, each command module would contain conditionals (`if json_mode: print(json.dumps(...)) else: typer.echo(...)`). This duplicates the branching across every command and couples command logic to output format. The Protocol pattern isolates the format decision; commands write to `ctx.obj["writer"].event(...)` and never know which writer they're talking to.

### Why a closed exit-code set

Exit codes are a *contract*. Agents shelling out to the CLI branch on the numeric value to distinguish "image missing" from "darktable failed" from "bad entry name" without parsing stderr text. A closed enum + mypy-exhaustive mapping prevents accidental drift between the engine's `ErrorCode` taxonomy and the CLI's exit codes.

### Why versioned independently of package SemVer

`chemigram` may release patch versions without changing output schema (a typo fix in a help string isn't a schema change). Conversely, an output schema may need a major version bump even when the package SemVer doesn't (e.g., changing the shape of `state_after` is breaking for script consumers but doesn't necessarily break the CLI's behavior). Decoupling them — same pattern as prompt versioning per ADR-045 — gives both surfaces stable contracts.

## Consequences

**Positive:**

- Human default is approachable for first-time users and manual invocation.
- `--json` gives agents and scripts a stable, parseable surface without regex.
- NDJSON supports streaming consumption; no buffering required.
- `OutputWriter` abstraction makes commands testable without format coupling.
- Exit codes are stable; agents branch on category without parsing messages.
- Schema versioning lets the schema evolve without forcing a CLI major bump.

**Negative:**

- **Schema maintenance.** The event schema is a public API. Breaking changes require a version bump and changelog entry. Discipline must be enforced in review.
- **NDJSON is less familiar than single JSON.** Consumers expecting a single object need one extra parse step (`splitlines()` → last line). The summary-last-line convention is documented to mitigate.
- **`rich` dependency for colored human output.** Typer uses Rich for colored output by default. Acceptable: Rich is already in the dependency tree via Typer (ADR-070).

## Verification

- Per-verb integration tests assert both human and `--json` output shapes for every verb.
- Exit-code parity audit (`tests/integration/cli/test_error_code_parity.py`) walks every `ErrorCode` and confirms a unique non-zero `ExitCode` mapping.
- `OUTPUT_SCHEMA_VERSION = "1.0"` constant is exposed in `chemigram status`; locked-in regression test in `tests/unit/cli/test_output.py`.

## Alternatives considered

### JSON by default, human output via `--text`

**Rejected.** Most invocations are interactive. Industry convention defaults to human output.

### Single JSON document, no NDJSON

**Rejected.** Buffering the entire output before parsing is wrong for streamable verbs (`log`, `vocab list`); a streaming-first format is the better default.

### Free-form exit codes (1 for any error)

**Rejected.** Forces consumers to parse stderr text to distinguish error categories — defeats the purpose of having structured errors at the engine level.
