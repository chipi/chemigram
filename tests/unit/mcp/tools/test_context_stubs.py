"""Unit tests for chemigram.mcp.tools.context_stubs."""

from __future__ import annotations

import anyio
import pytest

from chemigram.mcp.errors import ErrorCode
from chemigram.mcp.registry import ToolContext, get_tool


@pytest.mark.parametrize(
    "name,args",
    [
        ("read_context", {"image_id": "x"}),
        ("propose_taste_update", {"content": "x", "category": "y"}),
        ("confirm_taste_update", {"proposal_id": "p1"}),
        ("propose_notes_update", {"image_id": "x", "content": "y"}),
        ("confirm_notes_update", {"proposal_id": "p1"}),
    ],
)
def test_stubs_return_not_implemented_with_slice_5(
    context: ToolContext, name: str, args: dict
) -> None:
    spec = get_tool(name)
    assert spec is not None
    result = anyio.run(spec.handler, args, context)
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_IMPLEMENTED
    assert result.error.details.get("slice") == 5
