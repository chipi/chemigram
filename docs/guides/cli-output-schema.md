# CLI output schema (`--json` / NDJSON)

> Schema reference for callers that parse the CLI's `--json` output.
>
> Output schema version: **`1.0`** (independent of package SemVer per ADR-072 / ADR-045).
> Surfaced at runtime via `chemigram status --json` (look for the `output_schema_version` field).

When you pass `--json` to any verb, the CLI emits **newline-delimited JSON** (NDJSON): one JSON object per line, each line a complete event. This makes the output trivially streamable (`while read line; do …`), parseable by `jq`, and indexable by line number.

This doc is the contract you can build against.

---

## Stream layout

- **`stdout`** carries `event` and `result` lines (informational + final summary).
- **`stderr`** carries `error` lines (terminal failures).

The two streams never interleave the same event — every payload goes to exactly one stream. You can collect them separately:

```bash
chemigram --json apply-primitive iguana --entry expo_+0.5 \
  > stdout.ndjson \
  2> stderr.ndjson
```

A successful invocation:
- `stdout` ends with exactly one `event=result, status=ok` line — usually the only line on a quiet verb, last of several on a verb that emits progress events.
- `stderr` is empty.

A failed invocation:
- `stderr` ends with exactly one `event=error, status=error` line.
- `stdout` may have prior `event` lines (progress) but no `result` line.

---

## The three event types

Every NDJSON object has at least these fields:

| Field | Type | Description |
|-|-|-|
| `schema_version` | string | Output schema version. `"1.0"` as of v1.5.0. Bump per ADR-072. |
| `event` | string | Event type (see below). |

Plus event-specific fields layered on top.

### `event = "result"`

The final summary line of a successful invocation. Always present on success, always last on stdout.

```json
{
  "schema_version": "1.0",
  "event": "result",
  "status": "ok",
  "image_id": "iguana",
  "entry": "expo_+0.5",
  "snapshot_hash": "a3f291…",
  "state_after": {
    "head_hash": "a3f291…",
    "entry_count": 2,
    "enabled_count": 2,
    "layers_present": {"L1": false, "L2": false, "L3": true}
  }
}
```

Guaranteed fields:
- `schema_version`, `event`, `status` (always `"ok"` for `result`)

Verb-specific fields vary — `apply-primitive` adds `image_id`, `entry`, `snapshot_hash`, `state_after`; `vocab list` adds `count`; `tag` adds `name`, `hash`; etc. Treat verb-specific fields as additive: a future minor schema bump may add fields, never remove them.

### `event = "error"`

Terminal failure. Always last line on `stderr`. No `result` line follows on stdout.

```json
{
  "schema_version": "1.0",
  "event": "error",
  "status": "error",
  "exit_code": 3,
  "exit_code_name": "NOT_FOUND",
  "message": "primitive 'no_such_entry' not found",
  "image_id": "iguana",
  "entry": "no_such_entry"
}
```

Guaranteed fields:
- `schema_version`, `event`, `status` (always `"error"` for `error`)
- `exit_code` (int) and `exit_code_name` (string, IntEnum name)
- `message` (string, human-readable explanation)

Process exit code matches `exit_code` field. See [Exit codes](#exit-codes) below.

### `event = <verb-specific>`

Progress / intermediate events. Suppressed when `--quiet`; verbose-gated when authored with a `_verbose_min` threshold.

Examples seen in v1.5.0:
- `event="vocabulary_entry"` — emitted by `vocab list`, one per entry
- `event="ingest_step"` — emitted by `ingest`, one per step (raw symlink, EXIF read, baseline build, etc.)
- `event="render_progress"` — emitted by `render-preview` / `export-final` (verbose only)

Verb-specific events have a free-form shape. They're useful for streaming consumers but you can ignore them and rely on the final `result` line for a complete summary.

---

## Quick parse patterns

### Just want the final summary

```bash
chemigram --json apply-primitive iguana --entry expo_+0.5 | tail -1 | jq .
```

### Branch on exit code

```bash
chemigram --json apply-primitive iguana --entry expo_+0.5
case $? in
  0) echo "ok" ;;
  3) echo "not found" ;;
  4) echo "workspace state error — re-ingest?" ;;
  *) echo "other failure" ;;
esac
```

### Stream every event

```bash
chemigram --json ingest /path/to/raw.NEF | while IFS= read -r line; do
  echo "$line" | jq -r '.event + " — " + (.message // "")'
done
```

### Parse error details from stderr

```bash
chemigram --json apply-primitive iguana --entry whatever 2>err
if [[ -s err ]]; then
  err_msg=$(jq -r .message err)
  err_code=$(jq -r .exit_code_name err)
  echo "Failed: $err_code — $err_msg"
fi
```

### Python (NDJSON-stream + final-event capture)

See [`examples/cli-agent-loop.py`](https://github.com/chipi/chemigram/blob/main/examples/cli-agent-loop.py) for a runnable example with full error handling.

---

## Exit codes

Stable per ADR-072 / RFC-020 §D. `chemigram --help` lists them; the JSON `error` event includes both `exit_code` (int) and `exit_code_name` (string).

| Code | Name | When it fires |
|-|-|-|
| `0` | `SUCCESS` | OK |
| `1` | `INTERNAL_ERROR` | Unhandled exception (bug — please report) |
| `2` | `INVALID_INPUT` | Bad arguments or schema validation failure |
| `3` | `NOT_FOUND` | image_id, entry, ref, or proposal not found |
| `4` | `STATE_ERROR` | Workspace in inconsistent state |
| `5` | `VERSIONING_ERROR` | Snapshot-graph integrity issue |
| `6` | `DARKTABLE_ERROR` | Render subprocess failure |
| `7` | `MASKING_ERROR` | Mask binding failed (malformed `mask_spec`) |
| `8` | `SYNTHESIZER_ERROR` | XMP composition failure |
| `9` | `PERMISSION_ERROR` | Filesystem or workspace permission |
| `10` | `NOT_IMPLEMENTED` | Tool not implemented at this slice |

For agent loops: codes 2/3/7 are typically *recoverable* (correct the input and retry); 4/5/6/8 indicate an environmental or workspace issue that needs investigation; 1/9/10 should halt the loop.

---

## Schema versioning rules (ADR-072 / ADR-045)

The output schema is versioned independently of the package's SemVer. Versioning rules:

- **Major bump (`1.0` → `2.0`)** — when an event field is removed or renamed, or when an existing field's type changes. Will be announced via CHANGELOG and a deprecation cycle.
- **Minor bump (`1.0` → `1.1`)** — when new event types are added or new fields are added to existing events. Old consumers continue to work.
- **No bump** — when error messages or `_verbose_min` event thresholds change.

You can read the active schema version at runtime:

```bash
chemigram --json status | jq .output_schema_version
```

Pin against major versions: `if (.schema_version | startswith("1.")) then ... else error("unsupported schema") end`.

---

## See also

- [`cli-reference.md`](cli-reference.md) — every verb, every flag, auto-generated from `--help`
- [`cli-env-vars.md`](cli-env-vars.md) — env vars that affect CLI behavior
- [`docs/getting-started.md`](../getting-started.md#driving-chemigram-from-a-script-or-agent-loop-cli) — bash / Python quickstart
- [`examples/cli-agent-loop.py`](https://github.com/chipi/chemigram/blob/main/examples/cli-agent-loop.py) — runnable Python example with error handling
- [`examples/cli-batch-watch.sh`](https://github.com/chipi/chemigram/blob/main/examples/cli-batch-watch.sh) — runnable bash watch-folder script
- [`docs/adr/ADR-072-cli-output-format-and-exit-codes.md`](../adr/ADR-072-cli-output-format-and-exit-codes.md) — design rationale
