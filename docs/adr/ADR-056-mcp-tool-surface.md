# ADR-056 — MCP tool surface: parameter shapes and error contract

> Status · Accepted
> Date · 2026-04-29
> TA anchor · /components/mcp-server, /contracts/mcp-tools
> Related RFC · RFC-010 (closes); supersedes the implementation note in ADR-033

## Context

RFC-010 left four open questions about the agent-callable MCP surface:
parameter shapes (types, required-vs-optional, defaults), the return
contract (success and error response formats), the error category enum,
and what `state_after` includes. v0.3.0 (Slice 3) shipped the surface
across issues #12–#15: 27 tools registered through
`chemigram.mcp.registry`, dispatched via the official `mcp>=1.27` SDK
over stdio, exercised end-to-end by
`tests/integration/mcp/test_full_session.py`.

This ADR closes RFC-010 with concrete contracts based on the surface as
implemented and tested. ADR-033 (the initial sketch) is preserved; this
ADR supersedes its implementation-note path (`src/chemigram_mcp/server.py`
underscore form was an artifact of an earlier package layout — the
shipped path is `src/chemigram/mcp/server.py`).

## Decision

### Return contract

Every tool returns a structured JSON payload via the MCP
`CallToolResult.content` text block AND `structuredContent` field:

```json
{
  "success": true,
  "data": <tool-specific>,
  "error": null
}
```

or

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "<error_code>",
    "message": "<human-readable>",
    "details": {<free-form>},
    "recoverable": true | false
  }
}
```

Implemented by `chemigram.mcp.errors.ToolResult.to_payload()`. Tools
construct via `ToolResult.ok(data)` or `ToolResult.fail(ToolError(...))`;
helper constructors (`error_invalid_input`, `error_not_found`,
`error_not_implemented`) keep call sites short.

### Error code enum (`ErrorCode`)

The fixed set is:

| Code | When it fires |
|-|-|
| `invalid_input` | Argument shape valid by JSON Schema but semantically wrong (unknown enum value, empty required string, layer mismatch) |
| `not_found` | Image / primitive / mask / module / ref unknown to the server |
| `darktable_error` | `darktable-cli` exited non-zero or rendering failed; `details.stderr` carries a tail of stderr |
| `synthesizer_error` | XMP synthesis failed (Path B not implemented, `op_params` mismatch) |
| `versioning_error` | Repo invariant violated (detached-HEAD snapshot, unknown ref, hash collision, ref already exists) |
| `masking_error` | Mask registry inconsistency (registered hash missing from object store) |
| `permission_error` | Filesystem operation refused (reserved; not currently raised) |
| `state_error` | Workspace not in a state that supports the operation (no baseline yet, image_id collision, fresh workspace bind_layers without history) |
| `not_implemented` | Stub or deferred path. `details.slice` indicates the slice that lands the real impl (`4` = masking, `5` = context layer) |

Tool callers branch on `error.code` without parsing `message`. The enum
is closed: new categories require an ADR amendment.

### Parameter shapes

Each tool's `inputSchema` is a JSON Schema (`type: "object"`,
`additionalProperties: false`) declared at registration time inside
`chemigram.mcp.tools.*`. Schema validation is performed by the MCP SDK
before the handler runs: a missing required key surfaces as
`isError: true` on the `CallToolResult` (handled by the SDK's own
validation path, not as a structured `ToolError`).

The full surface (27 tools) is enumerated in `docs/adr/TA.md`
`contracts/mcp-tools` and instantiated in `chemigram.mcp.tools.*`. The
canonical reference is the running registry — `chemigram.mcp.registry.list_registered()`
returns every `ToolSpec` (name, description, input_schema, handler).

### `state_after` shape

`apply_primitive`, `remove_module`, `bind_layers`, `reset`, `get_state`,
and `checkout` return:

```json
{
  "head_hash": "<sha256 hex | null>",
  "entry_count": <int>,
  "enabled_count": <int>,
  "layers_present": {"L1": <bool>, "L2": <bool>, "L3": <bool>}
}
```

`head_hash` is `null` only on a workspace with no snapshot yet; once
`ingest` snapshots a baseline, every state has a hash. Implemented by
`chemigram.mcp._state.summarize_state`. The full XMP can be retrieved via
`checkout` + an inspection workflow agents are expected to handle out-of-
band; v0.3.0 doesn't expose a "dump entire history" tool because the diff
+ log + state-summary trio covers the agent's actual information needs.

### Tool naming and surface stability

Tool names are flat (no namespacing or dotting). Schemas are
`additionalProperties: false` so unknown args fail validation. New tools
land in new ADRs; renames require deprecation cycles.

## Rationale

- **Structured payload over raw exceptions:** the MCP transport doesn't
  preserve Python exception types, so the tools must encode error
  intent in JSON. The `{success, data, error}` envelope is verbose but
  explicit.
- **Closed error enum:** agents branch on category without prompt-engineering
  retry strategies for each tool. Open enums leak transport details.
- **`recoverable` flag:** lets agents distinguish "try again with
  different args" from "this tool can't help you here." Not all tools
  set it meaningfully today; convention is `False` for `not_implemented`
  and category-default `True` otherwise.
- **`details` is free-form:** structured enough for agents to branch on
  (`slice`, `stderr`), unstructured enough that adding new fields is not
  a contract change.
- **Schema validation by the SDK:** offloads the work and surfaces the
  same way for every tool. Our handlers never see argument-shape errors.

## Alternatives considered

- **Return raw values, raise exceptions on failure** — rejected: MCP
  serializes results as JSON; exception types don't survive. Agents can't
  branch on category.
- **Open error string, no enum** — rejected: agents would either
  hard-match strings or build classifier-style retry logic. Both
  brittle.
- **Per-tool error dataclasses** — rejected: 27 tools × N error shapes is
  a maintenance burden. The shared envelope keeps the contract one place.
- **Embed full XMP in `state_after`** — rejected: bloats every mutating
  tool's response. Agents who need history call `log` or `checkout` then
  inspect.
- **Tool namespacing (`vocab.list`, `versioning.snapshot`)** — rejected:
  flat names map cleanly to the action vocabulary in the system prompt;
  agents pattern-match on the verb without parsing dotted prefixes.

## Consequences

Positive:
- Surface is pinned. Slice 4 (masking) and Slice 5 (context) replace
  stubs without changing the response envelope or error enum.
- Eval reproducibility: a transcript replays deterministically because
  every tool response is structurally regular.
- Contract diffs are concrete: if `state_after` gains a field, mypy and
  the integration tests catch it.

Negative:
- `{success, data, error}` is verbose. Acceptable for ~30 tools; would be
  ugly at 300.
- Free-form `details` means agents can't statically know what's in there
  per error code. Mitigated by docstrings on each tool that document the
  `details` keys an agent might branch on.

## Implementation notes

- Surface entry: `chemigram.mcp.server.build_server()` calls
  `chemigram.mcp.tools.register_all()` then dispatches via the registry.
- Contract types: `chemigram.mcp.errors.ToolResult` /
  `ToolError` / `ErrorCode`.
- Test evidence: `tests/integration/mcp/test_full_session.py` exercises
  the full Mode A flow end-to-end through the in-memory harness; per-batch
  tests in `tests/unit/mcp/tools/` and `tests/integration/mcp/tools/`
  exercise each tool's schema + handler in isolation.
- ADR-033 is preserved; its `src/chemigram_mcp/server.py` implementation
  note refers to a discarded layout. The actual path is
  `src/chemigram/mcp/server.py`.
