#!/usr/bin/env python3
"""Audit forbidden imports in the CLI + MCP adapter layers (RFC-020 §E, ADR-071).

The discipline: ``chemigram.cli/`` and ``chemigram.mcp/`` are thin wrappers
over ``chemigram.core``. They contain only argument parsing, output
formatting, error mapping, and entry-point glue — never domain logic.

Forbidden in either adapter (with a small allowlist):

- ``import subprocess`` / ``from subprocess import ...``
- ``import xml.*`` / ``from xml.* import ...``

Allowlisted callsites:

- ``chemigram.cli.commands.status`` — ``subprocess.run([darktable-cli, "--version"])``.
  Justified because reporting the binary's version is metadata about an
  external dependency, not domain logic. ``chemigram status`` is itself
  not an MCP tool wrapper.
- ``chemigram.mcp.server`` — ``subprocess`` may appear in test
  scaffolding; legitimate MCP tools call ``chemigram.core`` instead. No
  current callsites; left here so additions can be reviewed if introduced.

Run as a script (``./scripts/audit-cli-imports.py``) or via Make
(``make ci`` includes it). Exit 0 on a clean tree; exit 1 with a
list of offenders otherwise.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_MODULES = ("subprocess", "xml")
ADAPTER_DIRS = (
    REPO_ROOT / "src" / "chemigram" / "cli",
    REPO_ROOT / "src" / "chemigram" / "mcp",
)
ALLOWLIST = {
    "chemigram.cli.commands.status": ("subprocess",),
}


def _module_name(path: Path) -> str:
    """``src/chemigram/cli/commands/status.py`` → ``chemigram.cli.commands.status``."""
    rel = path.relative_to(REPO_ROOT / "src")
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _check_file(path: Path) -> list[str]:
    """Return a list of human-readable offense strings; empty means clean."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [f"{path}: SyntaxError: {exc}"]

    module = _module_name(path)
    allowed = set(ALLOWLIST.get(module, ()))
    offenses: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in FORBIDDEN_MODULES and root not in allowed:
                    offenses.append(
                        f"{path}:{node.lineno}: forbidden 'import {alias.name}' "
                        f"in adapter layer (module {module})"
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root in FORBIDDEN_MODULES and root not in allowed:
                offenses.append(
                    f"{path}:{node.lineno}: forbidden 'from {node.module} import ...' "
                    f"in adapter layer (module {module})"
                )

    return offenses


def main() -> int:
    all_offenses: list[str] = []
    for adapter_dir in ADAPTER_DIRS:
        if not adapter_dir.exists():
            continue
        for py in sorted(adapter_dir.rglob("*.py")):
            all_offenses.extend(_check_file(py))

    if all_offenses:
        print("Adapter-layer import audit FAILED:", file=sys.stderr)
        for line in all_offenses:
            print(f"  {line}", file=sys.stderr)
        print(
            "\nThe CLI and MCP layers must remain thin wrappers (ADR-071, RFC-020 §E).",
            file=sys.stderr,
        )
        print(
            "Domain logic — subprocess invocations, XML parsing, raw file I/O — "
            "belongs in chemigram.core.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
