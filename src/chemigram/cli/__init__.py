"""Chemigram command-line interface (RFC-020).

Subprocess-callable adapter mirroring the MCP tool surface (ADR-033/056)
verb-for-verb. Like :mod:`chemigram.mcp`, the CLI is a thin wrapper over
:mod:`chemigram.core` — no domain logic lives here (ADR-071,
``scripts/audit-cli-imports.py`` enforces).

Output is human-readable by default and NDJSON via ``--json`` (the
schema is versioned independently of package SemVer, the same pattern
as prompt versioning per ADR-045).

Entry point: ``chemigram = "chemigram.cli.main:app"`` (pyproject.toml).
"""
