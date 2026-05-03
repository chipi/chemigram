# ADR-069 — CLI alongside MCP, won't replace it

> Status · Accepted
> Date · 2026-05-03
> TA anchor ·/components/cli ·/components/mcp-server
> Related RFC · RFC-020 (closes here); related PRD-005

## Context

Chemigram v1.0.0–v1.2.0 shipped with MCP as the only invocation surface — long-lived stdio sessions for conversational editing through Claude Code, Cursor, Continue, Cline, Zed, Claude Desktop, and other MCP-capable clients (PRD-001 / Mode A is built around this).

Three groups of users were underserved by MCP-only:

1. **Local agent loops** — LangGraph pipelines, Claude Code scripts, custom Python loops that orchestrate Chemigram as one tool among several. Maintaining an MCP session, a transport, and the lifecycle is overhead for what is effectively a function call when the agent runs on the same machine.
2. **Batch processing** — `for f in *.NEF; do chemigram apply-primitive ...` over a folder of raws has no natural MCP expression.
3. **Developers + CI scripts** — debugging an integration is faster with `chemigram <verb> --json` and exit codes than with a JSON envelope nested inside a tool-result envelope nested inside a transcript line.

The engine had been the right shape for a CLI all along: per ADR-006 / ADR-033 / ADR-056, the MCP server is already a thin wrapper over `chemigram.core`. Adding a CLI is a second wrapper over the same surface; it does not require any new capability.

## Decision

**Add `chemigram.cli` as a sibling adapter to `chemigram.mcp`, alongside MCP. Neither replaces the other; both are first-class.**

The CLI ships in v1.3.0:

- 22 verbs mirroring the MCP tool surface verb-for-verb (with `_` → `-` for shell ergonomics — `apply_primitive` ↔ `apply-primitive`)
- 4 conversational MCP tools (`propose_taste_update`, `confirm_taste_update`, and the notes counterparts) intentionally do NOT have CLI mirrors; the CLI offers `apply-taste-update` / `apply-notes-update` as direct verbs because the propose/confirm protocol requires per-process state across two tool calls, which doesn't fit the subprocess-per-invocation CLI shape (a parallel `for f in *.NEF` loop would race on a shared proposal store).
- Output: human-readable text by default, NDJSON via `--json`. Exit codes are stable per ADR-072.
- Mask `generate` / `regenerate` exit `MASKING_ERROR (7)` because the subprocess CLI has no provider-injection path equivalent to MCP's `build_server(masker=...)`. List/tag/invalidate work fully without a provider. Future RFC may add config-driven provider selection.

**The MCP server is unchanged.** No tool removed, no parameter renamed, no transport altered. Existing integrations (Claude Code, Cursor, Claude Desktop, etc.) continue to work without modification.

**Both adapters are thin wrappers over `chemigram.core` (per ADR-071).** Lint-enforced via `scripts/audit-cli-imports.py` wired into `make ci`.

## Two planes of control

The choice between MCP and CLI is about **workflow shape**, not capability:

- **MCP (conversational):** Long-lived session with an agent in an MCP-capable client. Designed for one-image-deep collaborative editing — read context, propose moves, iterate over many turns, capture transcripts.
- **CLI (programmatic):** Subprocess calls from shell scripts, custom Python loops, batch jobs, watch-folder daemons, CI pipelines. No session lifecycle; each invocation is one operation. Designed for automation, scripting, and agent loops where MCP's session model is overhead.

Same engine, same vocabulary, same workspace state on disk. A photographer can move between them freely; the workspace is the shared state.

## Rationale

- **The engine was already there.** PRD-005 / RFC-020 documented that `chemigram.core` is shape-correct for both invocation styles; building the second adapter cost only the adapter, not new domain capability.
- **Avoids fragmentation.** Without first-party CLI, every developer integrating Chemigram writes their own thin wrapper around the library. Those wrappers would diverge in exit codes, output formats, and error handling.
- **Symmetric surface.** Mirroring the MCP tool surface verb-for-verb means agents and scripts can move between adapters fluidly; documentation and reasoning transfer.
- **Honest exception: propose/confirm.** Conversational protocols belong in conversational adapters. Forcing them into the CLI via cross-process state would create a footgun. RFC-020 §F documents the divergence.

## Consequences

**Positive:**

- Local agent loops shed the MCP session lifecycle overhead.
- Batch processing and scripting become natural.
- Debugging integrations is faster (subprocess + exit codes + NDJSON beats nested JSON envelopes for ad-hoc inspection).
- Future REST or gRPC adapters (if needed) follow the same thin-wrapper pattern.

**Negative:**

- Maintenance surface increases — two adapters to keep in sync when core behavior changes. Mitigated by the verb-parity audit (`tests/integration/cli/test_verb_parity.py`) which fails when an MCP tool gains/loses without a corresponding CLI verb.
- `propose_taste_update` / `confirm_taste_update` in MCP and `apply-taste-update` / `apply-notes-update` in CLI are *not* the same operation. Documentation (RFC-020 §F, getting-started.md) makes this explicit.

## Alternatives considered

### A. MCP stdio transport only

Some MCP clients support stdio. An agent can run the server as a subprocess and exchange JSON-RPC over stdin/stdout without a network. **Rejected:** the MCP session lifecycle still applies; stdio MCP is less commonly supported in agent frameworks than plain subprocess; debugging is harder.

### B. REST API instead of CLI

A local HTTP server is callable from any language. **Rejected for v1.3.0:** introduces port management, startup latency, server lifecycle, and a new dependency (HTTP server). The CLI starts in <300 ms cold and exits — no lifecycle. If multi-language or remote access becomes a requirement, REST is the right next step; that decision is independent of this ADR.

### C. Replace MCP with CLI

**Rejected outright.** The conversational, single-image editing experience MCP enables (PRD-001 / Mode A) is not replaceable by CLI. Both surfaces ship and are maintained.
