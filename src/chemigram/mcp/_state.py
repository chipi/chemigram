"""Shared helpers for tool implementations.

Centralizes :func:`summarize_state` (used by ``apply_primitive``,
``remove_module``, ``reset``, ``get_state``) and :func:`resolve_workspace`
(``image_id`` → :class:`Workspace`-or-None lookup against the registry).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from chemigram.core.versioning import (
    ObjectNotFoundError,
    RefNotFoundError,
    RepoError,
    xmp_hash,
)
from chemigram.core.xmp import Xmp, parse_xmp_from_bytes

if TYPE_CHECKING:
    from chemigram.core.workspace import Workspace
    from chemigram.mcp.registry import ToolContext


def summarize_state(xmp: Xmp) -> dict[str, Any]:
    """Compact ``state_after`` summary returned by mutating tools.

    Per RFC-010 (closing in #16): head_hash + entry_count + per-layer
    presence flags. Agents call ``get_state`` for full detail; this is the
    cheap return-value shape for mutating tools.
    """
    layers = {p.multi_priority for p in xmp.history if p.enabled}
    return {
        "head_hash": xmp_hash(xmp),
        "entry_count": len(xmp.history),
        "enabled_count": sum(1 for p in xmp.history if p.enabled),
        "layers_present": {
            "L1": 0 in layers,
            "L2": 1 in layers,
            "L3": any(level >= 2 for level in layers),
        },
    }


def resolve_workspace(ctx: ToolContext, image_id: str) -> Workspace | None:
    """Look up a workspace by id; return ``None`` if absent."""
    return ctx.workspaces.get(image_id)


def current_xmp(workspace: Workspace) -> Xmp | None:
    """Read-only: resolve HEAD to an :class:`Xmp`, or ``None``.

    Read-only — does not move HEAD. Versioning's ``checkout`` is the
    write path (it touches HEAD). This helper is for tools that read
    state without intending to detach.
    """
    try:
        head_hash = workspace.repo.resolve_ref("HEAD")
        raw = workspace.repo.read_object(head_hash)
    except (RefNotFoundError, ObjectNotFoundError, RepoError):
        return None
    try:
        return parse_xmp_from_bytes(raw, source=f"sha256:{head_hash}")
    except Exception:
        return None
