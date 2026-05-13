#!/usr/bin/env python3
"""Generate ``docs/guides/cli-reference.md`` from ``chemigram --help``.

Wired into ``make docs-cli``. CI runs the same generator and diffs the
result against the checked-in file — drift fails the build.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "docs" / "guides" / "cli-reference.md"
HEADER = """# CLI reference

> Auto-generated from `chemigram --help`. Do not edit by hand.
> Regenerate with `make docs-cli`. CI fails if this file drifts from
> the live `--help` output.

The chemigram CLI mirrors the MCP tool surface verb-for-verb (with
`_` → `-`). Output is human-readable by default and newline-delimited
JSON via `--json`. Exit codes are stable per RFC-020 §D / ADR-072.

For the user-value rationale and design discussion see
[PRD-005](../prd/PRD-005-command-line-interface.md) and
[RFC-020](../rfc/RFC-020-command-line-interface.md). When to reach for
the CLI vs the MCP server: see `docs/index.md` § Two planes of control.

## CLI ↔ MCP param name mapping

For most verbs, CLI flags and MCP schema fields use the same name
(modulo `_` ↔ `-`). A few verbs use deliberately different names — CLI
favors photographer-vocabulary (`--entry`, `--operation`); MCP favors
engine-API names (`primitive_name`, `module_name`). The full canonical
mapping is enforced by
`tests/integration/cli/test_cli_mcp_param_alignment.py`:

| CLI flag | MCP property | Verbs | Reason |
|-|-|-|-|
| `--entry` | `primitive_name` | `apply-primitive`, `apply-per-region` | Photographer vocab vs engine API |
| `--operation` | `module_name` | `remove-module` | Reads cleaner on the CLI |
| `--l1` / `--l2` | `l1_template` / `l2_template` | `bind-layers` | Short flag forms |
| `--from` | `from_` | `branch` | Python keyword collision |
| `--hash` | `hash` (schema spelled `hash_` only via Typer) | `tag` | Same shape |
| `--format` | `format` (Typer collides with builtin) | `export-final` | Same shape |
| `--to` (repeatable) | `target_image_ids` (array) | `propagate-state` | CLI singular-flag, MCP array |
| `--exclude-op` (repeatable) | `exclude_ops` (array) | `propagate-state` | Same shape |
| `--tag` (repeatable) | `tags` (array) | `vocab list`, `vocab list-masks` | CLI singular-flag, MCP array |

CLI-only flags (no MCP equivalent, by design): `--stdin` (batch mode),
`--param NAME=VAL` (shorthand for the MCP `value` dict), `--pack -p`
(per-invocation pack loading; MCP loads packs at server startup),
`--label` on `apply-spot` (snapshot label override), the global flags
`--workspace`/`--configdir`/`--json`/`--quiet`/`--verbose`/`--dry-run`.

MCP-only props: `workspace_root` on `ingest` (CLI uses the global
`--workspace` flag instead).

## Global options

These apply to every verb. See `chemigram --help` for the canonical
listing; this section captures the same content.

| Flag | Env var | Description |
|-|-|-|
| `--json` | — | Emit NDJSON to stdout instead of human-readable text. |
| `--workspace <path>` | `CHEMIGRAM_WORKSPACE` | Workspace root (default `~/Pictures/Chemigram`). |
| `--configdir <path>` | `CHEMIGRAM_DT_CONFIGDIR` | darktable-cli configdir (must be pre-bootstrapped per ADR-005). |
| `--quiet`, `-q` | — | Suppress informational events; errors still surface. |
| `--verbose`, `-v` | — | Increase log verbosity (stackable: `-v`, `-vv`). |
| `--dry-run` | — | Describe what would happen without writing. (No-op for v1.3.0; verbs honor it incrementally.) |

## Exit codes

| Code | Name | Meaning |
|-|-|-|
| 0 | `SUCCESS` | OK |
| 1 | `INTERNAL_ERROR` | Unhandled exception (bug — please report) |
| 2 | `INVALID_INPUT` | Bad arguments or schema validation failure |
| 3 | `NOT_FOUND` | image_id, entry, ref, mask, or proposal not found |
| 4 | `STATE_ERROR` | Workspace in inconsistent state |
| 5 | `VERSIONING_ERROR` | Snapshot-graph integrity issue |
| 6 | `DARKTABLE_ERROR` | Render subprocess failure |
| 7 | `MASKING_ERROR` | Masking provider failure |
| 8 | `SYNTHESIZER_ERROR` | XMP synthesis failure |
| 9 | `PERMISSION_ERROR` | Filesystem permission denied |
| 10 | `NOT_IMPLEMENTED` | Tool stub or feature gate |

## Verbs

"""


def _strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences (Typer/Rich emit them even when stdout
    is not a TTY for some terminals).

    Covers both CSI (``\\x1b[...m``) sequences — including 256-color and
    truecolor variants with arbitrary semicolons — and OSC (``\\x1b]...\\x07``)
    sequences. Defensive against Rich/Typer formatting changes that could
    leak codes into the auto-generated cli-reference.md.
    """
    text = re.sub(r"\x1b\[[^m]*m", "", text)
    text = re.sub(r"\x1b\][^\x07]*\x07", "", text)
    return text


def _strip_borders(text: str) -> str:
    """Strip Rich's box-drawing borders so the help reads cleanly in markdown."""
    out_lines: list[str] = []
    for line in text.splitlines():
        # Drop pure border lines (start with box-drawing top/bottom).
        if not line.strip():
            out_lines.append("")
            continue
        if line.lstrip()[:1] in {"╭", "╰", "├", "┤", "─"} and not line.strip().startswith("│"):
            continue
        # Strip leading + trailing │ and the spaces immediately inside.
        stripped = line
        if stripped.lstrip().startswith("│"):
            stripped = stripped[stripped.find("│") + 1 :]
        if stripped.rstrip().endswith("│"):
            stripped = stripped[: stripped.rfind("│")]
        out_lines.append(stripped.rstrip())
    # Collapse runs of blank lines to one
    cleaned: list[str] = []
    prev_blank = False
    for line in out_lines:
        if not line.strip():
            if prev_blank:
                continue
            prev_blank = True
        else:
            prev_blank = False
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _run_help(args: list[str]) -> str:
    binary = shutil.which("chemigram")
    if binary is None:
        # Fallback: invoke the module the same way the e2e test does.
        cmd = [sys.executable, "-m", "chemigram.cli.main", *args, "--help"]
    else:
        cmd = [binary, *args, "--help"]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        env={"NO_COLOR": "1", "TERM": "dumb"},
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"`chemigram {' '.join(args)} --help` exited {proc.returncode}\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    return proc.stdout


def _section(title: str, body: str) -> str:
    return f"### `chemigram {title}`\n\n```\n{body.strip()}\n```\n\n"


# Order mirrors the README quick-start grouping; grows as the CLI grows
# per ADR-069's verb-for-verb discipline. New verbs MUST be added here
# or the auto-generated cli-reference will silently miss them.
_VERBS: tuple[tuple[str, list[str]], ...] = (
    ("status", ["status"]),
    ("ingest", ["ingest"]),
    # Edit / state
    ("apply-primitive", ["apply-primitive"]),
    ("apply-per-region", ["apply-per-region"]),
    ("apply-spot", ["apply-spot"]),
    ("wb-from-gray-card", ["wb-from-gray-card"]),
    ("propagate-state", ["propagate-state"]),
    ("remove-module", ["remove-module"]),
    ("reset", ["reset"]),
    ("get-state", ["get-state"]),
    # Versioning
    ("snapshot", ["snapshot"]),
    ("branch", ["branch"]),
    ("tag", ["tag"]),
    ("checkout", ["checkout"]),
    ("log", ["log"]),
    ("diff", ["diff"]),
    # Binding / rendering / export
    ("bind-layers", ["bind-layers"]),
    ("render-preview", ["render-preview"]),
    ("compare", ["compare"]),
    ("export-final", ["export-final"]),
    # Context
    ("read-context", ["read-context"]),
    ("log-vocabulary-gap", ["log-vocabulary-gap"]),
    ("apply-taste-update", ["apply-taste-update"]),
    ("apply-notes-update", ["apply-notes-update"]),
    # Vocab sub-app
    ("vocab list", ["vocab", "list"]),
    ("vocab show", ["vocab", "show"]),
    ("vocab list-masks", ["vocab", "list-masks"]),
    ("vocab show-mask", ["vocab", "show-mask"]),
    ("vocab validate", ["vocab", "validate"]),
    # Analytics sub-apps (CLI-only — no MCP mirror)
    ("gap-log list", ["gap-log", "list"]),
    ("gap-log rank", ["gap-log", "rank"]),
    ("gap-log show", ["gap-log", "show"]),
    ("gap-log clear", ["gap-log", "clear"]),
    ("session-log list", ["session-log", "list"]),
    ("session-log show", ["session-log", "show"]),
    ("session-log find", ["session-log", "find"]),
    ("session-log replay", ["session-log", "replay"]),
    ("cache list", ["cache", "list"]),
    ("cache size", ["cache", "size"]),
    ("cache clear", ["cache", "clear"]),
)


def render() -> str:
    parts = [HEADER]
    for label, argv in _VERBS:
        raw = _run_help(argv)
        cleaned = _strip_borders(_strip_ansi(raw))
        parts.append(_section(label, cleaned))
    # Pre-commit's end-of-file-fixer normalizes to a single trailing newline;
    # match that exactly so the sync check doesn't flicker.
    return "".join(parts).rstrip() + "\n"


def main() -> int:
    output = render()
    if "--check" in sys.argv:
        if not TARGET.exists():
            print(f"{TARGET} missing — run `make docs-cli` to generate.", file=sys.stderr)
            return 1
        current = TARGET.read_text(encoding="utf-8")
        if current != output:
            print(
                f"{TARGET} is out of sync with `chemigram --help`. "
                "Run `make docs-cli` to regenerate.",
                file=sys.stderr,
            )
            return 1
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(output, encoding="utf-8")
    print(f"wrote {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
