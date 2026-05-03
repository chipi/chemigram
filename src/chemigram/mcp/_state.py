"""MCP-server-only state helper: ``image_id`` → :class:`Workspace` lookup
against the per-session ``ToolContext.workspaces`` registry.

Other helpers that previously lived here (``summarize_state``,
``current_xmp``) and the cross-adapter helpers from
``chemigram.mcp.tools.*`` (``parse_xmp_at``, ``materialize_mask_for_dt``,
``stitch_side_by_side``, ``serialize_mask_entry``) lifted to
:mod:`chemigram.core.helpers` in v1.4.0 (closes ADR-071's
"future cleanup" note). Import from there directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chemigram.core.workspace import Workspace
    from chemigram.mcp.registry import ToolContext


def resolve_workspace(ctx: ToolContext, image_id: str) -> Workspace | None:
    """Look up a workspace by id against the MCP session's registry.

    MCP-only: the per-session ``ToolContext.workspaces`` dict doesn't
    exist outside an MCP server lifecycle. The CLI loads workspaces
    from disk via ``chemigram.cli._workspace.load_workspace`` instead.
    """
    return ctx.workspaces.get(image_id)


__all__ = ["resolve_workspace"]
