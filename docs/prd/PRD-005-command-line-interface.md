# PRD-005 — A command-line interface for Chemigram

> Status · Draft v0.1 · 2026-05-02
> Sources · 04/Architecture, 03/MCP tool surface
> Audiences · photographer (PA/audiences/photographer), developer-integrator (PA/audiences/developer-integrator)
> Promises · vocabulary-as-voice, the-loop-is-fast, photographer-controls-everything (PA/promises)
> Principles · agent-is-the-only-writer, restraint-before-push (PA/principles)
> Why this is a PRD · A second invocation surface for the engine is a user-value argument, not a settled detail. Adding a CLI commits us to a stable shell-level contract that batch users, scripted agents, and developers will rely on for years; the case has to be made before we lock the surface in.

It's 2 AM. A folder of 200 raws from the morning's expedition is sitting on the disk; the Tuesday client wants the keepers contact-sheeted by sunrise. The photographer doesn't open Claude Desktop. They don't start a session. They write a four-line shell loop — `for f in *.NEF; do chemigram apply-primitive "$f" --entry expo_+0.5 --json; done` — and walk away. Two minutes later, every raw has the morning-light correction applied; the sidecars are committed; the JSON event log is on disk. They could have done this with the MCP server too, in principle, but it would have meant standing up a long-lived agent loop and orchestrating the round-trip themselves. The CLI was always the right shape for this work; they just hadn't had it before.

A different evening, a different photographer is hand-debugging why an ingest pipeline is producing the wrong baseline tag. They want to see exactly what `ingest` does when it sees their folder, without spinning up a Claude session and reading a tool-result envelope. `chemigram ingest ~/Pictures/Chemigram/IMG_2041 --dry-run --verbose` prints the EXIF lookup, the L1 binding decision, the proposed objects-store layout, and exits with code 0. Five minutes earlier than the same investigation through MCP would have ended.

## The problem

Chemigram's only invocation surface today is MCP over stdio: an agent connects, calls tools, gets envelopes back. That works for the conversational, single-image editing session that PRD-001 is built around — but it's the wrong shape for everything else.

A photographer who wants to apply one vocabulary entry across a folder writes a shell loop, not a conversation. A developer integrating Chemigram into a LangGraph pipeline shells out to subprocesses, not to a long-lived MCP session. Someone debugging an ingest workflow wants `--dry-run --verbose` and stdout, not a JSON envelope nested inside a tool-result envelope nested inside a transcript line. CI scripts want exit codes. Watch-folder daemons want stdin.

These are not exotic uses. They are the standard Unix shape of "a tool that does one thing per invocation," and Chemigram's engine is structurally already that — the MCP layer is the thin wrapper, not the engine. What's missing is a second wrapper that exposes the same operations as a binary on the path.

## The experience

The expedition photographer who needs the morning's contact sheet writes `chemigram apply-primitive *.NEF --entry expo_+0.5 --json | tee process.log`. The CLI iterates the glob, applies the primitive to each image's workspace, and emits one NDJSON line per state change. Exit code 0 means every image succeeded; nonzero means at least one failed and the photographer can grep the log.

The agent-loop builder writes `result = subprocess.run(["chemigram", "apply-primitive", path, "--entry", entry, "--json"], ...)` inside their custom Python loop, parses the NDJSON, branches on the exit code. Their loop has no MCP session lifecycle to manage, no transport to configure, no server process to keep alive — just a subprocess per call. The exit-code surface lets them distinguish "image not found" from "darktable failed" from "bad entry name" without parsing stderr text.

The developer debugging a problem types `chemigram status`. They get a five-line block: chemigram version, darktable-cli path and version, configured packs, workspace root, prompt store version. Three of those lines change each release; one of them is the thing that was misconfigured. They fix it and move on.

The CLI mirrors the MCP tool surface exactly. There is no second vocabulary, no friendly aliases, no place where the CLI behaves differently from MCP for the same operation. `chemigram apply-primitive` and the MCP `apply_primitive` tool call the same engine function. Their inputs and outputs are isomorphic.

## Why now

The engine is in the right shape. After Phase 1 the MCP layer is already a thin wrapper over `chemigram.core` (ADR-006, ADR-033, ADR-056). All domain logic — XMP synthesis, render pipeline, versioning, masking, vocabulary, context — lives in core. Adding a CLI is a second wrapper over the same surface; it does not require any new capability.

The use cases are concrete. Three groups of users are already underserved: agent-loop builders writing custom tools (LangGraph, Claude Code scripts, hand-rolled Python loops), batch and watch-folder photographers, and developers debugging integrations. The lack of a CLI today produces hand-rolled wrappers in user code, with inconsistent exit codes and ad-hoc output formats. First-party CLI is better.

The cost is low and bounded. Typer over the existing core gives 1:1 parity with the MCP tool surface in roughly the same number of lines as the MCP adapter, plus an output writer abstraction (human + NDJSON), plus an exit-code enum, plus tests. No new domain logic. The maintenance discipline is enforced by the thin-wrapper rule (no XML, subprocess, or filesystem imports in the CLI layer), lint-checked.

## Success looks like

1. **Every MCP tool has a CLI verb with the same name and same parameter shape.** `apply_primitive` ↔ `apply-primitive`; `render_preview` ↔ `render-preview`; `propose_taste_update` ↔ `propose-taste-update`. No surprises, no friendly-rename layer.
2. **`--json` mode produces NDJSON that matches the MCP tool-result schema field-for-field.** A consumer that parses MCP results can parse CLI `--json` output with the same code, modulo transport framing.
3. **Exit codes are documented and stable.** The set is closed; new ones go through an ADR. Domain errors map to numeric codes; `0` is success; `1` is reserved for unhandled internal errors.
4. **Subprocess startup is well under one second** for non-render commands. `chemigram status` returns in <300 ms cold; `chemigram apply-primitive` returns within 200 ms of the underlying core function returning.
5. **The CLI ships in v1.3.0.** Tagged release on PyPI; `chemigram` binary on the path post-`pip install chemigram`.

## Out of scope

- **Interactive REPL mode.** Stateless per-invocation. If you want a conversation, MCP is the surface for that.
- **Shell completion at v1.** Typer can generate completion scripts for free; we'll ship them in a follow-up after the core verb surface stabilizes. Tracked in TODO.
- **Watch mode (`chemigram watch <dir>`).** Orthogonal to the CLI shape. Could be its own command later; not in v1.3.0.
- **Windows.** Linux + macOS only at v1.3.0, mirroring the v1 darktable-cli constraint (ADR-040 is macOS-only for CI; CLI follows the same scope until darktable's macOS/Linux surface diverges).
- **A REST or gRPC interface.** That's a different decision (server lifecycle, port management, authentication); not the same trade-off as CLI.
- **Replacing MCP.** Both surfaces ship and are maintained. Conversational use stays on MCP; programmatic use goes to CLI.
- **Direct calls into core from new entry points.** All external surfaces remain thin wrappers. If you find yourself writing logic in `chemigram.cli/`, it belongs in `chemigram.core/`.

## The sharpest threat

The biggest risk is **CLI–MCP drift over time**. Two interfaces over the same core can diverge in subtle ways: a parameter renamed in one but not the other, an error mapped to different codes, an output field present in MCP results but missing from CLI `--json`. If that happens, the "two surfaces over one core" promise becomes a maintenance trap, and consumers can't write portable tooling.

The mitigation is structural: both layers import from `chemigram.core` only, both are tested against the same fixtures, the CLI's per-tool integration tests assert against the same `ToolResult` shapes the MCP tests assert against. A lint check (or AST audit) flags forbidden imports in the CLI layer (`subprocess`, `xml`, raw `open()`). The closing ADR — "thin-wrapper discipline" — is what holds this in place; the dependency graph enforces it.

The secondary threat is the output schema becoming a public API people lock onto faster than we expect. Once agents are parsing NDJSON events, breaking changes hurt. Mitigation: version the schema independently of the CLI semver (mirroring how prompt versioning is independent of package semver, ADR-045), and surface the schema version in `chemigram status`.

## Open threads

- **RFC-020** — full design: package layout, framework choice (Typer), command shape, output protocol, exit codes, testing strategy.
- **Closing ADRs** (written when the CLI ships in v1.3.0): CLI alongside MCP (won't replace); CLI framework choice; thin-wrapper discipline lint; CLI output format (NDJSON via `--json`).
- **TA edit** — add `TA/components/cli` next to `TA/components/mcp-server`.
- **Stdin support, multi-entry single call, config layering** — all currently in RFC-020's open-questions section; will surface as follow-up RFCs or get folded into v1.3.0 if implementation evidence shows they're cheap.

## Links

- PA/audiences/photographer, PA/audiences/developer-integrator
- PA/promises/vocabulary-as-voice, PA/promises/the-loop-is-fast
- 04/Architecture, 04/MCP tool surface
- Related: PRD-001 (Mode A), RFC-020 (CLI design), ADR-006 (single process, no daemon), ADR-033 (MCP tool surface), ADR-056 (tool parameter + error contracts)
