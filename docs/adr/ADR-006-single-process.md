# ADR-006 — Single Python process, MCP server, no daemon

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/constraints/single-process ·/components/mcp-server
> Related RFC · None (foundational architectural choice)

## Context

The agent communicates with Chemigram through MCP. The engine has multiple subsystems (synthesizer, render pipeline, versioning, masking, MCP server). A choice about process model — single process, daemon-plus-client, microservices, etc. — affects implementation complexity, deployment, debugging, and what kinds of state can exist.

## Decision

Chemigram runs as a single Python process. The MCP server is the entry point; subsystems are imported modules within the same process. State is the filesystem. No daemon, no IPC between subsystems, no inter-process state. Each render spawns a `darktable-cli` subprocess (per ADR-004); the subprocess exits when the render completes.

## Rationale

- **Simplicity** — one process, no IPC, no shared-memory concerns, no service-discovery, no port management. Smaller code surface.
- **Filesystem-as-state aligns with the project shape** — per-image directories, git-like versioning, `.dtstyle` files, sessions on disk. The state is already filesystem-shaped; adding in-memory cross-process state would duplicate it badly.
- **MCP's session model fits a single process** — MCP servers are typically launched per-session by the client; there's no intrinsic need for the engine to persist between sessions.
- **Debugging is straightforward** — one process, one log stream, standard Python tooling.

## Alternatives considered

- **Daemon + thin MCP-client process:** rejected — adds IPC complexity, daemon lifecycle management, port conflicts, configuration of where the daemon lives. v1 doesn't have any state that justifies the daemon (no expensive caches, no model loading we want to amortize, etc.).
- **Microservices (separate render service, versioning service, MCP service):** rejected — wildly disproportionate to the project size. We'd spend more code on service plumbing than on actual functionality.
- **Persistent in-memory cache (e.g., parsed vocabulary cached across sessions):** could be added later as an optimization without changing this ADR; vocabulary parsing is fast enough that it's not needed in v1.

## Consequences

Positive:
- Trivial deployment (run one Python script)
- Debugging is single-process Python
- No service-discovery or port management
- Filesystem state is the source of truth — easy to inspect, version, back up

Negative:
- Per-render subprocess startup cost (~500ms for darktable-cli init) repeats every render. In v1's conversational Mode A loop, this is acceptable.
- No in-process caching across sessions (vocabulary re-parsed each session). Acceptable at the ~30-100 entry vocabulary scale.
- If multiple agents wanted to drive the same engine concurrently (currently not a use case), the single-process model would need revisiting.

## Implementation notes

`src/chemigram_mcp/server.py` is the entry point. It imports `chemigram_core.{xmp,dtstyle,pipeline,versioning,masking,context}` directly. No services, no RPC.
