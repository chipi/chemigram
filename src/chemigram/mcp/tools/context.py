"""Real context tools (replaces v0.3.0 ``context_stubs.py``).

- ``read_context(image_id)`` — loads taste/brief/notes/recent_log/recent_gaps
  per RFC-011 (closes via ADR-059).
- ``propose_taste_update`` / ``confirm_taste_update`` — propose-and-confirm
  per ADR-031, multi-scope per ADR-048 (taste files live at
  ``~/.chemigram/tastes/``).
- ``propose_notes_update`` / ``confirm_notes_update`` — same pattern,
  per-image ``<workspace>/notes.md``.

Proposals live in :attr:`ToolContext.proposals` keyed by uuid; cleared on
confirmation or session end. v0.5.0 has no explicit ``decline_*`` tool —
unconfirmed proposals expire.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any
from uuid import uuid4

from chemigram.core.context import Brief, Notes, RecentGaps, RecentLog, Tastes
from chemigram.core.workspace import tastes_dir
from chemigram.mcp._state import resolve_workspace
from chemigram.mcp.errors import (
    ToolResult,
    error_invalid_input,
    error_not_found,
)
from chemigram.mcp.registry import Proposal, ToolContext, register_tool

logger = logging.getLogger(__name__)
_VALID_TASTE_CATEGORIES = ("appearance", "process", "value")


def _record_transcript_proposal(
    ctx: ToolContext, kind: str, proposal_id: str, summary: str
) -> None:
    if ctx.transcript is None:
        return
    try:
        ctx.transcript.append_proposal(kind, proposal_id, summary)
    except Exception:
        logger.warning("transcript append_proposal failed", exc_info=True)


def _record_transcript_confirmation(ctx: ToolContext, proposal_id: str) -> None:
    if ctx.transcript is None:
        return
    try:
        ctx.transcript.append_confirmation(proposal_id, accepted=True)
    except Exception:
        logger.warning("transcript append_confirmation failed", exc_info=True)


# --- read_context -------------------------------------------------------


async def _read_context(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))

    brief = Brief.load(workspace)
    tastes = Tastes.load(brief_genres=brief.tastes)
    notes = Notes.load(workspace)
    log = RecentLog.load(workspace, limit=10)
    gaps = RecentGaps.load(workspace, limit=10)

    return ToolResult.ok(
        {
            "tastes": {
                "default": tastes.default,
                "genres": tastes.genres,
                "conflicts": tastes.conflicts,
            },
            "brief": {
                "raw": brief.raw,
                "intent": brief.intent,
                "tastes": brief.tastes,
            },
            "notes": {
                "summary": notes.summary,
                "truncated": notes.truncated,
            },
            "recent_log": [asdict(e) for e in log],
            "recent_gaps": [asdict(e) for e in gaps],
        }
    )


register_tool(
    name="read_context",
    description=(
        "Load the agent's first-turn context: tastes (multi-scope), brief, "
        "notes (summarized), recent log entries, recent vocabulary gaps."
    ),
    input_schema={
        "type": "object",
        "properties": {"image_id": {"type": "string"}},
        "required": ["image_id"],
        "additionalProperties": False,
    },
    handler=_read_context,
)


# --- propose / confirm taste -------------------------------------------


async def _propose_taste_update(
    args: dict[str, Any], ctx: ToolContext
) -> ToolResult[dict[str, Any]]:
    content = args["content"]
    category = args["category"]
    file_arg = args.get("file")

    if not content.strip():
        return ToolResult.fail(error_invalid_input("content must be non-empty"))
    if category not in _VALID_TASTE_CATEGORIES:
        return ToolResult.fail(
            error_invalid_input(
                f"category must be one of {list(_VALID_TASTE_CATEGORIES)}, got {category!r}"
            )
        )

    target_file = file_arg or "_default.md"
    if not target_file.endswith(".md"):
        target_file = f"{target_file}.md"

    proposal_id = uuid4().hex
    ctx.proposals[proposal_id] = Proposal(
        kind="taste",
        content=content,
        category=category,
        target_file=target_file,
    )
    _record_transcript_proposal(ctx, "taste", proposal_id, content[:80])
    return ToolResult.ok(
        {
            "proposal_id": proposal_id,
            "target_file": target_file,
            "category": category,
        }
    )


register_tool(
    name="propose_taste_update",
    description=(
        "Propose a write to a taste file. Returns proposal_id; the photographer "
        "must call confirm_taste_update to commit."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "category": {
                "type": "string",
                "enum": list(_VALID_TASTE_CATEGORIES),
            },
            "file": {"type": "string"},
        },
        "required": ["content", "category"],
        "additionalProperties": False,
    },
    handler=_propose_taste_update,
)


async def _confirm_taste_update(
    args: dict[str, Any], ctx: ToolContext
) -> ToolResult[dict[str, Any]]:
    proposal_id = args["proposal_id"]
    proposal = ctx.proposals.get(proposal_id)
    if proposal is None or proposal.kind != "taste":
        return ToolResult.fail(error_not_found(f"taste proposal {proposal_id!r}"))

    target_dir = tastes_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / (proposal.target_file or "_default.md")
    _append_markdown(target, proposal.content)
    _record_transcript_confirmation(ctx, proposal_id)
    del ctx.proposals[proposal_id]

    return ToolResult.ok(
        {
            "written_to": str(target),
            "category": proposal.category,
        }
    )


register_tool(
    name="confirm_taste_update",
    description="Confirm a taste-update proposal; appends content to the target file.",
    input_schema={
        "type": "object",
        "properties": {"proposal_id": {"type": "string"}},
        "required": ["proposal_id"],
        "additionalProperties": False,
    },
    handler=_confirm_taste_update,
)


# --- propose / confirm notes -------------------------------------------


async def _propose_notes_update(
    args: dict[str, Any], ctx: ToolContext
) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    content = args["content"]

    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    if not content.strip():
        return ToolResult.fail(error_invalid_input("content must be non-empty"))

    proposal_id = uuid4().hex
    ctx.proposals[proposal_id] = Proposal(
        kind="notes",
        content=content,
        image_id=image_id,
    )
    _record_transcript_proposal(ctx, "notes", proposal_id, content[:80])
    return ToolResult.ok({"proposal_id": proposal_id, "image_id": image_id})


register_tool(
    name="propose_notes_update",
    description="Propose an append to <workspace>/notes.md; returns proposal_id.",
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["image_id", "content"],
        "additionalProperties": False,
    },
    handler=_propose_notes_update,
)


async def _confirm_notes_update(
    args: dict[str, Any], ctx: ToolContext
) -> ToolResult[dict[str, Any]]:
    proposal_id = args["proposal_id"]
    proposal = ctx.proposals.get(proposal_id)
    if proposal is None or proposal.kind != "notes":
        return ToolResult.fail(error_not_found(f"notes proposal {proposal_id!r}"))

    workspace = resolve_workspace(ctx, proposal.image_id or "")
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {proposal.image_id!r}"))

    target = workspace.root / "notes.md"
    _append_markdown(target, proposal.content)
    _record_transcript_confirmation(ctx, proposal_id)
    del ctx.proposals[proposal_id]

    return ToolResult.ok(
        {
            "written_to": str(target),
            "image_id": proposal.image_id,
        }
    )


register_tool(
    name="confirm_notes_update",
    description="Confirm a notes-update proposal; appends content to <workspace>/notes.md.",
    input_schema={
        "type": "object",
        "properties": {"proposal_id": {"type": "string"}},
        "required": ["proposal_id"],
        "additionalProperties": False,
    },
    handler=_confirm_notes_update,
)


def _append_markdown(target: Any, content: str) -> None:
    """Append content with a leading separator + trailing newline."""
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = "" if content.endswith("\n") else "\n"
    with target.open("a", encoding="utf-8") as fh:
        if target.stat().st_size > 0:
            fh.write("\n")
        fh.write(content + suffix)
