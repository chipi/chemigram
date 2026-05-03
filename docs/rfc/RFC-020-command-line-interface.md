# RFC-020 — Command-line interface for Chemigram

> Status · Decided · 2026-05-03 (closes via ADR-069/070/071/072 at v1.3.0 ship)
> Closes into · ADR-069 (CLI alongside MCP, won't replace), ADR-070 (CLI framework: Typer), ADR-071 (CLI–MCP–core thin-wrapper discipline), ADR-072 (CLI output format: human default, NDJSON via `--json`)
> PRD · PRD-005
> Anchors · TA/components/cli (new), TA/components/mcp-server, TA/components/render-pipeline, TA/components/synthesizer
> Phase · v1.3.0 — first minor release after v1.2.0 (engine + reference-image validation)
> Why this is an RFC · "Should we add a CLI?" is settled by PRD-005, but the *shape* of that CLI — framework, package layout, command surface, output protocol, exit-code design, and the discipline that prevents CLI/MCP drift — has real alternatives that need to be argued before code lands.

---

## Summary

Add a `chemigram` CLI binary to the existing distribution. The CLI exposes the same operations as the MCP server (per ADR-033/056) as subprocess-callable verbs, with documented exit codes and structured `--json` (NDJSON) output. Both interfaces remain thin wrappers over `chemigram.core` (per ADR-006). No domain logic moves; no MCP behavior changes; no new runtime dependency beyond Typer (which transitively brings Click + Rich, both small and stable).

The CLI verb names mirror the MCP tool names verbatim — `apply_primitive` ↔ `apply-primitive`, `render_preview` ↔ `render-preview`, `propose_taste_update` ↔ `propose-taste-update`. The only transformation is `_` → `-` for shell ergonomics. There is no friendly-alias layer.

The output schema is versioned independently of the package semver (the same pattern as prompt versioning per ADR-045) and is exposed in `chemigram status`.

---

## Motivation

PRD-005 lays out the user-value case. This section captures the *technical* motivation — why the engine architecture is in the right shape for this and why it would be wrong to defer.

### 1. Local agent loops should not pay MCP overhead

When an agent runs on the same machine as Chemigram, the MCP session lifecycle (initialize → list_tools → call_tool → close), the JSON-RPC envelope, and the long-lived server process are all overhead for what is effectively a function call. `subprocess.run(["chemigram", "apply-primitive", ...])` is simpler, more debuggable, and idiomatic Unix. Many agent frameworks (LangGraph, Smolagents, custom Python loops) shell out to subprocesses natively but require additional plumbing for MCP.

### 2. Batch and watch-folder uses have no natural MCP expression

Processing 200 raws in a `for` loop, a Makefile, or a cron job is a for-loop over files. MCP's session model adds nothing here. A standard CLI is the right shape.

### 3. The engine is already the thin-wrapper shape

Per ADR-006 and ADR-033, the MCP server is a thin adapter over `chemigram.core`. All domain logic — XMP parse/synthesize, render pipeline, versioning DAG, vocabulary resolution, masking provider, context loaders, session transcripts — lives in core. The CLI is a second adapter over the same surface. Adding it does not require any new capability; the implementation cost is bounded by "wire each MCP tool to a Typer command and an output writer."

### 4. Users will write hand-rolled wrappers if we don't

Without a first-party CLI, every developer integrating Chemigram writes their own thin Python wrapper around the library. Those wrappers diverge in exit codes, output formats, and error handling. A single supported CLI prevents fragmentation and lets us guarantee stability.

---

## Detailed design

### A. Package layout

The repo is single-distribution per ADR-034 (`chemigram.core`, `chemigram.mcp` under one namespace). The CLI follows the same pattern:

```
src/chemigram/
  core/                    ← unchanged
  mcp/                     ← unchanged
  cli/                     ← NEW
    __init__.py
    main.py                ← entry point; Typer root app + global-options callback
    commands/
      __init__.py
      vocab.py             ← vocab list / show / validate
      edit.py              ← apply_primitive / remove_module / reset / get_state / list_vocabulary
      versioning.py        ← branch / tag / checkout / log / diff
      binding.py           ← bind_layers
      render.py            ← render_preview / compare
      export.py            ← export_final
      masks.py             ← generate_mask / regenerate_mask / list_masks / tag_mask
      context.py           ← read_context / propose_*_update / confirm_*_update / log_vocabulary_gap
      lifecycle.py         ← ingest
      status.py            ← status (diagnostic, not a tool wrapper)
    output.py              ← HumanWriter + JsonWriter behind OutputWriter Protocol
    exit_codes.py          ← ExitCode IntEnum
    error_mapping.py       ← chemigram.mcp.errors.ErrorCode → ExitCode
```

`pyproject.toml` adds one entry point alongside the existing `chemigram-mcp`:

```toml
[project.scripts]
chemigram-mcp = "chemigram.mcp.server:main"
chemigram = "chemigram.cli.main:app"
```

The `chemigram.cli` module imports from `chemigram.core` and from `chemigram.mcp.errors` (for the `ErrorCode` taxonomy and `ToolResult` shape — these *are* the contract we mirror, per ADR-056). It does not import from `chemigram.mcp.tools.*`. The MCP adapter and the CLI adapter are siblings; both depend on core, neither depends on the other.

### B. Framework: Typer

Closing ADR-070. Typer over Click over argparse over hand-rolled — Typer's annotation-driven definition is concise for a ~27-verb surface, auto-generated `--help` reads docstrings, `typer.testing.CliRunner` makes tests synchronous and deterministic. Typer's transitive dependency on Rich is acceptable; Rich is already battle-tested and small. If Typer ever becomes a constraint, dropping to raw Click is mechanical.

```python
# chemigram/cli/main.py
import typer

from chemigram.cli.commands import (
    binding, context, edit, export, lifecycle, masks,
    render, status, versioning, vocab,
)

app = typer.Typer(name="chemigram", no_args_is_help=True, pretty_exceptions_enable=False)

# Sub-typers for grouped commands
app.add_typer(vocab.app, name="vocab")
app.add_typer(masks.app, name="masks")

# Direct command verbs (one per MCP tool)
app.command("apply-primitive")(edit.apply_primitive)
app.command("remove-module")(edit.remove_module)
app.command("reset")(edit.reset)
app.command("get-state")(edit.get_state)
app.command("render-preview")(render.render_preview)
# ... etc (full list in §F)

@app.callback()
def _global(
    ctx: typer.Context,
    json: bool = typer.Option(False, "--json"),
    workspace: pathlib.Path | None = typer.Option(None, "--workspace"),
    quiet: bool = typer.Option(False, "--quiet"),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["json"] = json
    ctx.obj["workspace"] = workspace
    ctx.obj["quiet"] = quiet
    ctx.obj["verbose"] = verbose
    ctx.obj["dry_run"] = dry_run
```

### C. Output protocol

Closing ADR-072. Human-readable text by default; NDJSON via `--json`. NDJSON (one JSON object per line) over single-document JSON because it's streamable and the standard log-processing shape; the final line is always a summary event, so non-streaming consumers have a single parse target.

The `OutputWriter` Protocol is the seam:

```python
# chemigram/cli/output.py
class OutputWriter(Protocol):
    def event(self, kind: str, **fields: object) -> None: ...
    def error(self, message: str, code: ExitCode, **fields: object) -> None: ...
    def result(self, **fields: object) -> None: ...

class HumanWriter:
    """Renders to terminal. Results to stdout, errors to stderr, prefixes
    via ✓/⚠/✗. Uses Rich for color when stdout is a TTY; falls back to
    plain when piped."""

class JsonWriter:
    """One NDJSON line per event to stdout; errors also NDJSON to stderr.
    Final line is the summary."""
```

No command module imports `print`, `typer.echo`, or `sys.stdout` directly. Everything goes through the writer. Lint-checked.

The NDJSON event shapes mirror the MCP `ToolResult` field structure (per ADR-056) wherever applicable. A consumer reading MCP tool results today can read CLI NDJSON tomorrow with the same parsing code, modulo transport framing.

### D. Exit codes

Closing ADR-072 covers the output schema; exit codes get their own enum but are shipped in the same ADR for cohesion.

```python
# chemigram/cli/exit_codes.py
class ExitCode(IntEnum):
    SUCCESS = 0
    INTERNAL_ERROR = 1            # unhandled core exception (bug)
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

Mapping is built directly on top of `chemigram.mcp.errors.ErrorCode`. Adding a new ErrorCode in core requires extending this enum in lockstep — enforced by an audit-style integration test that diffs the two enums.

### E. The thin-wrapper discipline

Closing ADR-071. The rule: **no domain logic in `chemigram.cli/` or `chemigram.mcp/`.** Both layers contain only argument parsing, output formatting, error mapping, and entry-point glue.

Auditable as forbidden imports:

```
# FORBIDDEN in chemigram/cli/ and chemigram/mcp/:
import xml.etree.ElementTree   # XMP parsing — belongs in core.xmp
import subprocess               # darktable invocation — belongs in core.pipeline
open(...)                       # file I/O — belongs in core (workspace, repo)

# PERMITTED:
from chemigram.core import ...  # all domain operations
from chemigram.mcp.errors import ErrorCode, ToolResult  # CLI maps these to exit codes + NDJSON
import typer                    # CLI framework
```

Enforcement: a custom ruff rule (or a small AST audit script in `scripts/audit-cli-imports.py`) wired into `make ci`. The CI job fails if a forbidden import appears in either adapter layer.

### F. Verb surface (full list, mirrors MCP per ADR-033/056)

Each verb takes the same parameter shape as its MCP tool. Bracketed flag groups are the inherited globals (`--json`, `--workspace`, `--quiet`, `--verbose`, `--dry-run`).

**Vocabulary:**
- `chemigram vocab list` → `list_vocabulary`
- `chemigram vocab show <name>` → no MCP equivalent; helper that prints the entry's manifest record + .dtstyle path

**Edit / state:**
- `chemigram apply-primitive <image_id> --entry <name> [--mask-override <ref>]` → `apply_primitive`
- `chemigram remove-module <image_id> --operation <op> [--multi-priority <N>]` → `remove_module`
- `chemigram reset <image_id>` → `reset`
- `chemigram get-state <image_id>` → `get_state`

**Versioning:**
- `chemigram branch <image_id> --name <branch>` → `branch`
- `chemigram tag <image_id> --name <tag>` → `tag`
- `chemigram checkout <image_id> <ref>` → `checkout`
- `chemigram log <image_id>` → `log`
- `chemigram diff <image_id> <ref_a> <ref_b>` → `diff`

**Layer binding:**
- `chemigram bind-layers <image_id> --l1 <name> --l2 <name>` → `bind_layers`
  *(MCP has no ``unbind_layers`` tool — layer removal is via ``remove-module``.
  An earlier draft of this RFC listed ``unbind-layers``; that was a drafting
  error and was dropped before v1.3.0 ship.)*

**Versioning (snapshot grouped here for cohesion):**
- `chemigram snapshot <image_id> [--message <m>]` → `snapshot`

**Render / export:**
- `chemigram render-preview <image_id> [--width <px>] [--height <px>]` → `render_preview`
- `chemigram compare <image_id> <ref_a> <ref_b>` → `compare`
- `chemigram export-final <image_id> [--format jpeg] [--quality <0-100>]` → `export_final`

**Masks:**
- `chemigram masks list <image_id>` → `list_masks`
- `chemigram masks generate <image_id> --target <subject>` → `generate_mask`
- `chemigram masks regenerate <image_id> --name <mask>` → `regenerate_mask`
- `chemigram masks tag <image_id> --name <mask> --tag <name>` → `tag_mask`
- `chemigram masks invalidate <image_id> --name <mask>` → `invalidate_mask`

**Context:**
- `chemigram read-context <image_id>` → `read_context`
- `chemigram propose-taste-update <image_id> --add <line>` → `propose_taste_update`
- `chemigram confirm-taste-update <image_id> --proposal <id>` → `confirm_taste_update`
- `chemigram propose-notes-update <image_id> --add <line>` → `propose_notes_update`
- `chemigram confirm-notes-update <image_id> --proposal <id>` → `confirm_notes_update`
- `chemigram log-vocabulary-gap <image_id> --description <text>` → `log_vocabulary_gap`

**Lifecycle:**
- `chemigram ingest <raw_path>` → `ingest`

**Diagnostic (not an MCP tool):**
- `chemigram status` — chemigram version, darktable-cli path + version, configured packs, workspace root, prompt store version, output schema version

### G. Testing strategy

The CLI test suite lives in `tests/integration/cli/` (CLI is integration-tier per ADR-036 — it spans Typer, the CLI command, the output writer, the core function, real workspace state on `tmp_path`; only darktable invocation is stubbed). Two patterns:

**Per-command round-trip:**
```python
from typer.testing import CliRunner
runner = CliRunner()

def test_apply_primitive_returns_zero_on_success(tmp_workspace):
    result = runner.invoke(app, ["apply-primitive", str(tmp_workspace.image_id), "--entry", "expo_+0.5"])
    assert result.exit_code == ExitCode.SUCCESS
    assert "applied" in result.stdout

def test_apply_primitive_json_mode(tmp_workspace):
    result = runner.invoke(app, ["--json", "apply-primitive", str(tmp_workspace.image_id), "--entry", "expo_+0.5"])
    events = [json.loads(line) for line in result.stdout.strip().splitlines()]
    assert events[-1]["status"] == "ok"
```

**CLI ↔ MCP parity audit:** a single test that walks every MCP tool and asserts a CLI verb exists with the right name + parameter shape. Fails if a new MCP tool is added without a CLI counterpart.

E2e: one e2e test that drives a tiny session through the CLI (ingest → apply-primitive → render-preview → export-final) end-to-end, including real `darktable-cli`. Lives next to the existing MCP e2e tests.

### H. `chemigram status`

```
$ chemigram status
chemigram        1.3.0
darktable-cli    5.4.1   /opt/homebrew/bin/darktable-cli
workspace root   ~/Pictures/Chemigram/
configured packs starter (5), expressive-baseline (35)
prompt store     mode_a/system → v3
output schema    v1.0
```

`chemigram status --json` returns the same fields as a single NDJSON line. The output schema version is what consumers should pin against.

---

## Migration / rollout

Additive. No migration. Users who only use MCP are unaffected. The `chemigram` binary appears on the path after `pip install chemigram` once the entry point ships.

Documentation:
- `README.md` gets a CLI quick-start section alongside the existing MCP block
- `docs/getting-started.md` gets a "Driving Chemigram from a script or agent loop" section showing the subprocess pattern
- A new `docs/guides/cli-reference.md` documents every verb (auto-generated from `--help` output by a `make docs-cli` target, kept in sync via CI)

---

## Alternatives considered

### A. MCP stdio transport instead of a CLI

MCP supports stdio. An agent can run the server as a subprocess and exchange JSON-RPC over stdin/stdout without a network. Rejected: the MCP session lifecycle still applies (initialize/list_tools/call_tool); stdio MCP is less commonly supported in agent frameworks than plain subprocess; debugging is harder. Subprocess + structured exit codes + NDJSON is the simpler interface for the same underlying capability.

### B. REST API instead of CLI

A local HTTP server is callable from any language. Rejected for v1.3.0: introduces port management, startup latency, server lifecycle, and a new dependency (HTTP server). The CLI starts in <300 ms cold and exits — no lifecycle. If multi-language or remote access becomes a requirement, REST is the right next step; that decision is independent of this RFC.

### C. Replace MCP with CLI

Rejected outright. The conversational, single-image editing experience MCP enables (PRD-001) is not replaceable by CLI. Both surfaces ship and are maintained.

### D. argparse instead of Typer

argparse is stdlib (no dependency). For a 27-verb surface with shared global options and grouped subcommands, argparse requires ~100 lines of repetitive `add_argument` calls and weaker `--help` formatting. Typer's annotation-driven definition is roughly half the line count and produces better diagnostics. The dependency cost (Typer + Click + Rich) is small relative to darktable being a hard dependency. ADR-070 captures the framework choice.

### E. Click directly instead of Typer

Typer is a thin annotation-driven layer over Click. We get Click's robustness with less boilerplate. If Typer's abstractions become a constraint, the migration to raw Click is mechanical (Typer exposes the underlying Click objects). Not worth taking the verbosity hit upfront.

### F. Friendly verb aliases (`chemigram edit`, `chemigram revert`)

Rejected. The CLI verbs mirror MCP tool names verbatim (with `_` → `-`). One source of truth, no translation layer, no surprise when reading the CLI alongside the MCP surface. ADR-056's tool names are the contract; the CLI inherits them.

---

## Open questions

These will become amendments to this RFC or follow-up RFCs based on implementation evidence:

1. **Stdin support for batch verbs.** Should `chemigram apply-primitive` accept image IDs from stdin (`find ~/Pictures/Chemigram -maxdepth 2 -name '.chemigram' | chemigram apply-primitive --entry expo_+0.5 --stdin`)? Low cost; high value for batch. Proposal: include in v1.3.0 as a flag-gated alternative to positional args.

2. **Multi-entry single call.** Should `apply-primitive` accept multiple `--entry` flags in one invocation? Composable from the caller (one subprocess per entry) but a single call would be cheaper for batch. Proposal: defer to a follow-up; v1.3.0 supports one entry per call.

3. **Workspace discovery.** The MCP server requires the agent to pass `image_id`. The CLI could optionally infer the workspace from `cwd` when invoked inside an image directory. Proposal: `--workspace` global flag explicit at v1.3.0; auto-detection in a follow-up if friction is real.

4. **Shell completion.** Typer generates completion scripts for bash/zsh/fish for free. Ship at v1.3.0 or wait for the verb surface to stabilize? Proposal: defer one release — v1.3.0 verbs land first, completion lands in v1.3.1 once we know there are no rename churns.

5. **Output schema version.** Major version bumps on breaking changes; minor on additive. The schema lives in `chemigram.core.events` (or similar). The exact module location is an implementation detail; surfaced in `chemigram status --json`.

---

*RFC-020 · Decided · 2026-05-03*
