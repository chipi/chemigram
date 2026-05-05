# ADR-079 — `apply_primitive` `value` / `param` argument shape

> Status · Accepted
> Date · 2026-05-05
> TA anchor ·/contracts/mcp-tools ·/components/cli
> Related RFC · RFC-021 (closes); paired with ADR-077, ADR-078, ADR-080

## Context

ADR-078 declares a `parameters` schema on vocabulary manifest entries. Callers (CLI users, MCP agents) need a way to supply parameter values at apply time. RFC-021 §Open Q2 + §Q3 deliberated the user-facing surface: scalar shorthand vs explicit name-keyed flags, and what to do with out-of-range values.

## Decision

**CLI surface** — `chemigram apply-primitive` accepts two complementary flags:

- `--value V` — shorthand for the **single-parameter** case. Resolves to the entry's first (only) parameter declaration. Example: `chemigram apply-primitive img --entry exposure --value 0.7`.
- `--param NAME=V` — explicit name-keyed; repeatable. Required for **multi-parameter** entries. Example: `chemigram apply-primitive img --entry temperature --param temp=+0.4 --param tint=-0.1`.

If `--value` is supplied to a multi-parameter entry, the CLI rejects with `INVALID_INPUT` (no ambiguous resolution). If both `--value` and `--param` are supplied for a single-parameter entry, `--value` and `--param <its-name>=V` together are accepted only when they agree; conflicting values fail with `INVALID_INPUT`.

**MCP surface** — `apply_primitive` tool gains an optional `value` argument:

- For single-parameter entries: `value: 0.7` (scalar).
- For multi-parameter entries: `value: {"temp": 0.4, "tint": -0.1}` (object).

Schema validation of the `value` argument's shape (scalar vs object) keys off the resolved entry's `parameters` cardinality. Type mismatch (object on single-param entry, scalar on multi-param entry) fails with `INVALID_INPUT` and a descriptive message naming the entry's expected shape.

**Composition with `mask_spec`** — `value` and `mask_spec` are independent axes. Both, either, or neither may be supplied on a single call. `--value 0.7 --mask-spec '<json>'` produces a single snapshot with both transformations applied.

**Range validation** — values outside the manifest-declared `range` fail with `INVALID_INPUT` (hard reject; no soft clamp). Error message names the parameter, the supplied value, and the declared range, so the caller can correct directly. To extend the supported range, edit the manifest — runtime override is intentionally not provided.

**Default values** — when a parameter has a `default` and the caller omits it, the default is applied. For multi-parameter entries, omitting some parameters is allowed; the omitted ones use their defaults. (A multi-parameter entry with no defaults declared and no values supplied is a manifest authoring error caught at vocabulary-load time per ADR-078.)

## Rationale

- **`--value` shorthand serves the common case.** ~90% of priority modules are single-parameter (`exposure`, `vignette`, `bilat-clarity`, `grain`, etc.); typing `--value 0.7` is the natural ergonomic path. `--param` exists for the multi-parameter case where positional shorthand is ambiguous.
- **Hard reject on out-of-range** is consistent with the rest of the CLI's error contract (per ADR-072): predictable, no silent surprises, the caller fixes the input. A clamp-and-warn would hide the boundary; users would write code expecting `--value 5` to mean `+3` and break later when manifests evolve.
- **MCP `value` is shape-polymorphic** (scalar for single, dict for multi) because the agent already knows the entry's shape — `list_vocabulary` returns `parameters` cardinality; the agent emits the right shape per entry.
- **`value` + `mask_spec` independence** keeps the surface composable. Each axis has its own well-defined contract; combining them just means each runs on the same apply call.

## Alternatives considered

- **Always require `--param NAME=V` (no `--value` shorthand).** Rejected — forces verbose `--param ev=0.7` for the most common case. Doesn't reflect the user's mental model ("exposure +0.7" is a single concept).
- **Soft clamp + stderr warning for out-of-range values.** Rejected — silent semantic drift; later manifest changes silently change behavior.
- **`value` MCP arg always a dict (no scalar shorthand)** — rejected for the same reason as `--param`-only on the CLI side; verbose for the common case.
- **Parameter validation deferred to the engine** (let the decoder fail). Rejected — violates the CLI/MCP error-contract layering; range errors should surface at the user-facing layer with clear messages, not as decoder exceptions.

## Consequences

Positive:

- CLI ergonomics for the 90% case stay tight (`--value 0.7`).
- Multi-parameter modules have a clean repeatable flag form when they arrive.
- MCP tool schema cleanly polymorphic; agent emits the right shape per entry.
- Composes orthogonally with `mask_spec` — no nested-conditional logic.

Negative:

- Two flag forms (`--value` + `--param`) mean two paths to test. Mitigated: parsed into one canonical shape internally before the apply path runs.
- Hard-reject on out-of-range may surprise users testing extreme values; mitigated by descriptive error messages.

## Implementation notes

- CLI: `chemigram.cli.commands.edit._parse_value_or_params(value: str|None, param: list[str]) -> dict[str, float] | None`. Single canonical shape (dict keyed by param name) flows into the apply path.
- MCP: `chemigram.mcp.tools.vocab_edit._apply_primitive` gains `value` arg parsing — validates shape against the resolved entry's `parameters` cardinality, normalizes scalar → single-key dict.
- Range validation lives in `chemigram.core.vocab.validate_parameters(entry, values)`, called by both adapters. Returns the validated dict or raises a `ValueError` mapped to `INVALID_INPUT` at the adapter layer.

The integration tests in `tests/integration/cli/test_cli_edit.py` and `tests/integration/mcp/tools/test_vocab_edit_via_mcp.py` get parametrized cases for: single-param `--value`, single-param `--param NAME=V`, multi-param `--param ... --param ...`, out-of-range hard reject, scalar-on-multi rejection, dict-on-single rejection, and `value + mask_spec` together.
