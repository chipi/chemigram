"""Context-read stubs (batch 1 of Slice 3).

The real implementations land in Slice 5 (context layer). The tools are
declared now so the MCP surface is shape-stable from v0.3.0 onward — agents
get a well-formed ``NOT_IMPLEMENTED`` response with ``details.slice == 5``
rather than "tool unknown".
"""

from __future__ import annotations

from typing import Any

from chemigram.mcp.errors import ToolResult, error_not_implemented
from chemigram.mcp.registry import ToolContext, register_tool

_SLICE = 5
_REASON = "context layer ships in Slice 5; v0.3.0 declares the surface only."


async def _read_context(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    return ToolResult.fail(error_not_implemented(_REASON, slice=_SLICE))


async def _propose_taste_update(
    args: dict[str, Any], ctx: ToolContext
) -> ToolResult[dict[str, Any]]:
    return ToolResult.fail(error_not_implemented(_REASON, slice=_SLICE))


async def _confirm_taste_update(
    args: dict[str, Any], ctx: ToolContext
) -> ToolResult[dict[str, Any]]:
    return ToolResult.fail(error_not_implemented(_REASON, slice=_SLICE))


async def _propose_notes_update(
    args: dict[str, Any], ctx: ToolContext
) -> ToolResult[dict[str, Any]]:
    return ToolResult.fail(error_not_implemented(_REASON, slice=_SLICE))


async def _confirm_notes_update(
    args: dict[str, Any], ctx: ToolContext
) -> ToolResult[dict[str, Any]]:
    return ToolResult.fail(error_not_implemented(_REASON, slice=_SLICE))


register_tool(
    name="read_context",
    description="(Stub — Slice 5) Load taste/brief/notes/recent log for an image.",
    input_schema={
        "type": "object",
        "properties": {"image_id": {"type": "string"}},
        "required": ["image_id"],
        "additionalProperties": False,
    },
    handler=_read_context,
)

register_tool(
    name="propose_taste_update",
    description="(Stub — Slice 5) Propose a write to a taste file; returns proposal_id.",
    input_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "category": {"type": "string"},
        },
        "required": ["content", "category"],
        "additionalProperties": False,
    },
    handler=_propose_taste_update,
)

register_tool(
    name="confirm_taste_update",
    description="(Stub — Slice 5) Confirm a previously-proposed taste update.",
    input_schema={
        "type": "object",
        "properties": {"proposal_id": {"type": "string"}},
        "required": ["proposal_id"],
        "additionalProperties": False,
    },
    handler=_confirm_taste_update,
)

register_tool(
    name="propose_notes_update",
    description="(Stub — Slice 5) Propose a write to an image's notes.md.",
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

register_tool(
    name="confirm_notes_update",
    description="(Stub — Slice 5) Confirm a previously-proposed notes update.",
    input_schema={
        "type": "object",
        "properties": {"proposal_id": {"type": "string"}},
        "required": ["proposal_id"],
        "additionalProperties": False,
    },
    handler=_confirm_notes_update,
)
