# RFC-010 — MCP tool surface — parameter shapes and error contracts

> Status · Draft v0.1
> TA anchor ·/components/mcp-server ·/contracts/mcp-tools
> Related · ADR-033, RFC-001, RFC-009
> Closes into · ADR (pending) — locks parameter shapes and error contracts
> Why this is an RFC · ADR-033 lists the 30 v1 MCP tools. But the parameter shapes (types, required vs optional, default values), return shapes (success and error formats), and error contracts (what conditions surface as which errors) are open. The agent's behavior depends critically on these — clear contracts make the agent reliable; ambiguous contracts make it brittle.

## The question

For each of the 30 tools in ADR-033, what's the precise parameter shape and return contract? Where do errors surface (raised exceptions, error objects in returns, special error tool calls)? What do default values look like? How are types declared?

This RFC isn't aiming to spec all 30 tools exhaustively — that's tedious and the result lives in code anyway. Instead: establish the **conventions** for parameters, returns, and errors that all tools follow.

## Use cases

- Agent calls `apply_primitive(image_id="abc", primitive_name="expo_+0.5")` — expects success result with `state_after` and `snapshot_hash`, or a clear error if the primitive isn't found.
- Agent calls `render_preview(image_id="abc", size=1024)` — expects a path. What if rendering fails (darktable error)?
- Agent calls `log_vocabulary_gap(image_id="abc", description="...", workaround="...")` — expects acknowledgement; what if the log is unwritable?
- New tool gets added to ADR-033 — its shape should follow established conventions, not invent new ones.

## Goals

- Predictable, consistent tool contracts
- Clear error reporting that lets the agent recover or escalate
- Type-safe parameter validation at the MCP boundary
- Conventions that scale to new tools without re-deciding

## Constraints

- TA/components/mcp-server — tools wrap engine operations
- ADR-033 — the 30-tool surface is fixed
- MCP spec — tool definitions are JSON Schema-like

## Proposed approach

**Parameter conventions:**

1. **`image_id` is always the first parameter** for image-scoped tools. Type: string (UUID or photographer-chosen identifier).
2. **Optional parameters use `null`** rather than absence. Tools declare which parameters accept null. If null, the engine applies the documented default.
3. **String unions over enums.** Where the parameter has a small fixed set of values (e.g., `format: "jpeg" | "png"`), use string unions for ergonomic agent calls and document the allowed values in the tool description.
4. **`label` parameters allow null.** When null, the engine generates a default label (e.g., timestamp).
5. **No magic strings.** "head", "main", "current" are all valid strings; engine resolution is explicit.

**Return shape conventions:**

All tools return a structured result with two top-level fields:

```python
{
    "success": bool,
    "data": { ... } | None,     # if success=True; tool-specific
    "error": { ... } | None,    # if success=False
}
```

Error object shape:

```python
{
    "code": str,                # "invalid_input", "not_found", "darktable_error", ...
    "message": str,             # human/agent-readable
    "details": dict | None,     # tool-specific structured info
    "recoverable": bool,        # whether the agent might retry or fall through
}
```

**Error categories:**

- `invalid_input` — bad parameters (e.g., `size=-100`)
- `not_found` — referenced entity doesn't exist (e.g., primitive name unknown)
- `darktable_error` — subprocess returned nonzero or render produced no output
- `synthesizer_error` — XMP synthesis failed (RFC-001 errors bubble up here)
- `versioning_error` — snapshot/checkout/diff failed
- `masking_error` — mask provider failed
- `permission_error` — filesystem permission issue
- `state_error` — operation invalid for current state (e.g., `reset` on uninitialized image)

**Type declarations:**

Tools declare parameters via JSON Schema embedded in the tool description (MCP-standard). The engine validates input at the MCP boundary; invalid input returns `error.code = "invalid_input"`.

**Consistent return for state changes:**

All tools that mutate state (`apply_primitive`, `remove_module`, `reset`, `snapshot`, `branch`, etc.) return:

```python
{
    "success": True,
    "data": {
        "state_after": { ... },     # current XMP state summary
        "snapshot_hash": "...",     # if applicable
    }
}
```

This lets the agent always know "what's the current state after this call" without a separate `get_state` round-trip.

## Alternatives considered

- **Raise exceptions instead of returning error objects:** rejected — exceptions don't cross the MCP wire cleanly. Errors-as-values are the right pattern for tool calls.

- **Per-tool error codes:** considered. Prefer global error categories — agent's recovery logic is shared across tools.

- **Optional parameters as kwargs vs positional:** moot for MCP (it's all named params). Document defaults clearly.

- **Streaming responses for long operations:** rejected — `render_preview` is ~2 seconds; that's not long enough to need streaming. If a future tool is genuinely long-running, revisit.

## Trade-offs

- The structured-error pattern is verbose compared to raising. Acceptable: the agent's recovery logic benefits.
- Always returning `state_after` on state changes adds a small payload to every response. Acceptable: it eliminates frequent `get_state` round-trips.
- JSON Schema for parameters is verbose but standard. Worth the cost; the agent's tool-input quality improves with declared schemas.

## Open questions

- **What's in `state_after`?** Just the head hash and entry count? Or full XMP? Or recent log? Proposed: head hash, entry count, layer markers, mask registry summary. Full XMP is too much; head hash + entry count is too little.
- **Error code stability.** Once locked, error codes shouldn't change (agents may have decision logic keyed on them). Treat error codes as part of the public API.
- **Streaming of `render_preview`?** When generating large exports (full-resolution), the render can take 30+ seconds. Should the tool return a job ID and let the agent poll? Defer until evidence shows it matters.
- **Tool versioning.** Future tool changes (parameter additions, return shape evolution) — how does the agent handle? Proposed: tools declare `version` in their MCP metadata; engine warns on incompatible agent expectations.

## How this closes

This RFC closes into:
- **An ADR locking the parameter and return conventions** as proposed.
- **A reference document** (probably part of TA/contracts/mcp-tools or a sibling section) listing each tool's parameter schema and return shape. This is more like a generated artifact (from the tool registrations themselves) than a hand-written ADR.

## Links

- TA/components/mcp-server
- TA/contracts/mcp-tools
- ADR-033 (MCP tool surface)
- RFC-001 (synthesizer errors bubble through)
- RFC-009 (mask provider errors bubble through)
