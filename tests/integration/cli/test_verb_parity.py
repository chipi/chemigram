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
        # #55 — versioning (snapshot grouped here)
        "branch",
        "tag",
        "checkout",
        "log",
        "diff",
        "snapshot",
        # #56 — layer binding
        "bind_layers",
        "unbind_layers",
        # #57 — render / export
        "render_preview",
        "compare",
        "export_final",
        # #58 — masks
        "list_masks",
        "generate_mask",
        "regenerate_mask",
        "tag_mask",
        "invalidate_mask",
        # MCP-only by design (conversational propose/confirm pattern; the
        # CLI offers `apply-taste-update` / `apply-notes-update` instead
        # of mirroring these. RFC-020 amendment in #61).
        "propose_taste_update",
        "confirm_taste_update",
        "propose_notes_update",
        "confirm_notes_update",
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
    # CLI verbs come back space-separated for sub-apps; flatten the rightmost
    # token (``masks list`` → ``masks-list`` doesn't apply — tools that
    # group via sub-apps in the CLI map to flat-named MCP tools, e.g.
    # ``masks list`` ↔ ``list_masks``).
    flat_verbs = {v.split()[-1] for v in cli_verbs}

    missing: set[str] = set()
    for tool in mcp_tools:
        if _verb_for_tool(tool) in flat_verbs or tool.replace("_", "-") in flat_verbs:
            continue
        if tool in _KNOWN_PENDING_VERBS:
            continue
        # Try the rev-mapping for tools whose CLI form drops a prefix
        # (e.g., MCP ``list_masks`` ↔ CLI ``masks list``).
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
