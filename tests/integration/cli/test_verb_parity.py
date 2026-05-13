"""Audit: every MCP tool has a CLI verb (RFC-020 §F discipline).

Maintains a ``_KNOWN_PENDING_VERBS`` allowlist that shrinks as #54..#59
land their verb groups during v1.3.0. The audit fails if:

- a new MCP tool is added but isn't in either set (regression)
- a verb in the allowlist is actually implemented (housekeeping — remove it)

The CLI may have extras not in MCP (``status``, ``vocab show``); the
audit only checks the MCP → CLI direction.

When v1.3.0 ships, ``_KNOWN_PENDING_VERBS`` should be empty and the
final closing PR can simplify this test to a strict equality check.
"""

from __future__ import annotations

import typer
from typer.main import get_command

from chemigram.cli.main import app
from chemigram.mcp.registry import list_registered
from chemigram.mcp.tools import register_all

# MCP tool names that don't yet have a CLI verb. Shrink as verb groups
# land their issues. The audit fails if this list disagrees with reality.
_KNOWN_PENDING_VERBS: frozenset[str] = frozenset(
    {
        # MCP-only by design (conversational propose/confirm pattern; the
        # CLI offers `apply-taste-update` / `apply-notes-update` instead
        # of mirroring these. RFC-020 amendment in #61).
        "propose_taste_update",
        "confirm_taste_update",
        "propose_notes_update",
        "confirm_notes_update",
        # apply_spot CLI shipped v1.10.0 alongside the audit pass that
        # closed the verb-for-verb gap.
    }
)


def _walk_typer_verbs(t: typer.Typer, prefix: str = "") -> set[str]:
    """Collect every ``space-joined`` verb the Typer app accepts."""
    verbs: set[str] = set()
    cmd = get_command(t)
    if hasattr(cmd, "commands"):
        for name, sub in cmd.commands.items():  # type: ignore[attr-defined]
            full = f"{prefix} {name}".strip()
            verbs.add(full)
            if hasattr(sub, "commands"):
                # Sub-app
                for sub_name in sub.commands:  # type: ignore[attr-defined]
                    verbs.add(f"{full} {sub_name}")
    return verbs


def _verb_for_tool(tool_name: str) -> str:
    """Convert MCP tool name → expected CLI verb (with ``_`` → ``-``)."""
    return tool_name.replace("_", "-")


def test_mcp_tool_has_cli_verb_or_is_pending() -> None:
    register_all()
    mcp_tools = {spec.name for spec in list_registered()}

    cli_verbs = _walk_typer_verbs(app)
    # CLI verbs come back space-separated for sub-apps; flatten to the
    # rightmost token so a top-level verb and its sub-app commands all
    # match by their shortest form.
    flat_verbs = {v.split()[-1] for v in cli_verbs}

    missing: set[str] = set()
    for tool in mcp_tools:
        if _verb_for_tool(tool) in flat_verbs or tool.replace("_", "-") in flat_verbs:
            continue
        if tool in _KNOWN_PENDING_VERBS:
            continue
        synth = tool.split("_")[0]
        if synth in flat_verbs:
            continue
        missing.add(tool)

    assert not missing, (
        f"MCP tools without CLI verbs and not in _KNOWN_PENDING_VERBS: {sorted(missing)}. "
        "Either implement the verb or add the tool name to the allowlist with the "
        "issue number that will close it."
    )


def test_batch_2_verbs_are_implemented() -> None:
    """Explicit assertion: the seven verbs that landed in v1.3.0 Batch 2
    (#54 + #59 lifecycle/context split) are still wired.

    Catches accidental removal from main.py during refactors. Each name
    is the CLI form (with ``_`` → ``-``).
    """
    cli_verbs = _walk_typer_verbs(app)
    flat_verbs = {v.split()[-1] for v in cli_verbs}
    expected = {
        "ingest",
        "apply-primitive",
        "remove-module",
        "reset",
        "get-state",
        "read-context",
        "log-vocabulary-gap",
        # CLI-only direct verbs (no MCP equivalent)
        "apply-taste-update",
        "apply-notes-update",
    }
    missing = expected - flat_verbs
    assert not missing, f"Batch 2 verbs missing from CLI: {sorted(missing)}"


def test_cli_reference_generator_covers_every_live_verb() -> None:
    """Every command path in the live Typer app must appear in
    ``scripts/generate-cli-reference.py``'s ``_VERBS`` allowlist.

    Catches the bug class that silently shipped past v1.10.0: the
    allowlist was hard-coded at the v1.3.0 22-verb surface and
    stopped being updated, so the auto-generated ``cli-reference.md``
    was missing every verb added in v1.9.0 and v1.10.0 (apply-spot,
    apply-per-region, propagate-state, wb-from-gray-card, plus the
    gap-log/session-log/cache analytics sub-apps + the vocab sub-app
    additions). CI's ``--check`` passed because the generator and
    the checked-in file were both wrong consistently.

    This test reads the generator's allowlist directly, walks the
    live CLI, and asserts every command path is covered. If a new
    verb ships, this fails immediately; if a verb is removed, this
    flags the stale generator entry so it can be deleted from the
    allowlist before the file regrows.

    Closes the v1.10.0 holistic-audit follow-up (see commit adbc04e).
    """
    import importlib.util
    from pathlib import Path

    # Load the generator script as a module without executing main().
    repo_root = Path(__file__).resolve().parents[3]
    generator_path = repo_root / "scripts" / "generate-cli-reference.py"
    assert generator_path.exists(), f"generator script missing: {generator_path}"

    spec = importlib.util.spec_from_file_location("_gen", generator_path)
    assert spec is not None and spec.loader is not None
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    allowlist_entries: tuple[tuple[str, list[str]], ...] = gen._VERBS

    # Each generator entry maps to a space-joined verb path.
    allowlist_verbs = {label for label, _argv in allowlist_entries}

    # Walk the live Typer app — leaf paths only (skip pure sub-app names
    # like ``vocab`` since they're just namespaces; the generator's
    # allowlist documents the leaves like ``vocab list`` / ``vocab show``).
    def _leaf_verbs(t: typer.Typer, prefix: str = "") -> set[str]:
        verbs: set[str] = set()
        cmd = get_command(t)
        if not hasattr(cmd, "commands"):
            return verbs
        for name, sub in cmd.commands.items():  # type: ignore[attr-defined]
            full = f"{prefix} {name}".strip()
            if hasattr(sub, "commands") and sub.commands:  # type: ignore[attr-defined]
                # Sub-app: recurse into leaves.
                for sub_name in sub.commands:  # type: ignore[attr-defined]
                    verbs.add(f"{full} {sub_name}")
            else:
                verbs.add(full)
        return verbs

    live_verbs = _leaf_verbs(app)

    missing_from_generator = live_verbs - allowlist_verbs
    stale_in_generator = allowlist_verbs - live_verbs

    failure_lines: list[str] = []
    if missing_from_generator:
        failure_lines.append(
            f"Live CLI verbs missing from scripts/generate-cli-reference.py's "
            f"_VERBS allowlist: {sorted(missing_from_generator)}. Add them — "
            "auto-generated cli-reference.md silently misses them otherwise."
        )
    if stale_in_generator:
        failure_lines.append(
            f"Generator allowlist entries for verbs that no longer exist in "
            f"the live CLI: {sorted(stale_in_generator)}. Remove them."
        )

    assert not failure_lines, "\n\n".join(failure_lines)


def test_pending_verbs_are_actually_pending() -> None:
    """If a verb is in ``_KNOWN_PENDING_VERBS`` but already shipped in the CLI,
    remove it from the allowlist — keeps the audit honest.
    """
    register_all()
    mcp_tools = {spec.name for spec in list_registered()}
    cli_verbs = _walk_typer_verbs(app)
    flat_verbs = {v.split()[-1] for v in cli_verbs}

    accidentally_shipped: set[str] = set()
    for pending in _KNOWN_PENDING_VERBS:
        if pending not in mcp_tools:
            continue
        if _verb_for_tool(pending) in flat_verbs:
            accidentally_shipped.add(pending)

    assert not accidentally_shipped, (
        f"These tools have CLI verbs but are still in _KNOWN_PENDING_VERBS: "
        f"{sorted(accidentally_shipped)}. Remove them from the allowlist."
    )
