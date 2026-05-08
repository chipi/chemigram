# Reading session transcripts

> The agent writes per-image session JSONL transcripts during Mode A loops. This guide covers the read-side tooling — list / show / find / replay across your workspace.

## Background

Each Mode A session writes to `<workspace>/<image_id>/sessions/<session_id>.jsonl` per ADR-029 + RFC-014 / ADR-061. The transcript is a JSONL file: a header line with session metadata, per-turn entries (`tool_call` / `tool_result` / `proposal` / `confirmation` / `note`), and an optional footer summary on session close.

Sister to `chemigram gap-log`: `gap-log` queries the gap-record stream; `session-log` queries the full transcript stream.

## Commands

```sh
chemigram session-log list   [--since 7d] [--image <id>]
chemigram session-log show   <session_id>
chemigram session-log find   --primitive <name> | --module <name> | --tool <name>
chemigram session-log replay <session_id>
```

All commands accept `--workspace` and `--json`.

### `session-log list` — newest-first enumeration

```sh
chemigram session-log list                  # all sessions ever
chemigram session-log list --since 7d       # last week
chemigram session-log list --image DSCF1234 # one image's sessions
```

Each row reports `image_id`, `session_id`, `started_at`, `mode`, `vocab_pack`, `entry_count`, footer `summary` (if present), and the transcript path.

### `session-log show <session_id>` — full transcript dump

Prints every entry chronologically. Useful for "what did I do in that session?"

```sh
chemigram session-log show abc123
```

`session_id` matches either the JSONL filename stem or the header's `session_id` field. The lookup walks all images.

### `session-log find` — query across all sessions

```sh
# Every session that applied the exposure primitive
chemigram session-log find --primitive exposure

# Every entry mentioning the colorbalancergb module (covers tool args + notes)
chemigram session-log find --module colorbalancergb

# Every snapshot tool call
chemigram session-log find --tool snapshot

# Combine with --image
chemigram session-log find --primitive exposure --image DSCF1234
```

`--primitive` matches `tool_call.args.name` (the apply_primitive name argument). `--tool` matches `tool_call.tool`. `--module` does a substring match across the entry's serialized JSON, covering tool arguments, error messages, and free-form notes.

At least one filter is required.

### `session-log replay <session_id>` — render as CLI invocations

```sh
chemigram session-log replay abc123
```

Re-emits each `tool_call` as a CLI invocation hint you could re-run. Best-effort:

- `apply_primitive` becomes `chemigram apply-primitive <name> --image <id> --value <v>`
- versioning verbs (`snapshot` / `tag` / `branch` / `checkout` / etc.) become `chemigram <verb> <image_id>`
- Other tool calls fall through as commented hints

Useful for "what would I do this time" reflection or manually scripting a session's moves.

## Workflow recipes

### "What did I work on yesterday?"

```sh
chemigram session-log list --since 1d
```

### "How many sessions touched the temperature module?"

```sh
chemigram --json session-log find --module temperature | grep '"event": "session_match"' | wc -l
```

### "Re-render this session's edits as a script"

```sh
chemigram session-log replay <session_id> > scripts/replay-<session>.sh
chmod +x scripts/replay-<session>.sh
# Inspect, then execute
```

### "Which primitives do I use most?"

```sh
chemigram --json session-log find --tool apply_primitive | \
  jq -r 'select(.event == "session_match") | .args.name' | \
  sort | uniq -c | sort -rn | head -20
```

## See also

- `gap-log` sister sub-app — `chemigram gap-log` (#106)
- ADR-029 (session transcript JSONL format)
- RFC-014 / ADR-061 (end-of-session synthesis flow)
- ADR-061 (transcript footer / summary shape)
