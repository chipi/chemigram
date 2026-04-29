"""Unit tests for chemigram.mcp.registry."""

from __future__ import annotations

from typing import Any

import pytest

from chemigram.mcp.errors import ToolResult
from chemigram.mcp.registry import (
    ToolContext,
    clear_registry,
    get_tool,
    list_registered,
    register_tool,
)


@pytest.fixture(autouse=True)
def _isolated_registry() -> Any:
    clear_registry()
    yield
    clear_registry()


async def _noop_handler(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict]:
    return ToolResult.ok({"echo": args})


def test_register_then_list() -> None:
    register_tool(
        name="noop",
        description="No-op test tool.",
        input_schema={"type": "object", "properties": {}},
        handler=_noop_handler,
    )
    specs = list_registered()
    assert len(specs) == 1
    assert specs[0].name == "noop"


def test_get_unknown_returns_none() -> None:
    assert get_tool("does_not_exist") is None


def test_register_duplicate_raises() -> None:
    register_tool(
        name="dup",
        description="x",
        input_schema={"type": "object"},
        handler=_noop_handler,
    )
    with pytest.raises(ValueError, match="already registered"):
        register_tool(
            name="dup",
            description="x",
            input_schema={"type": "object"},
            handler=_noop_handler,
        )


def test_list_registered_sorted_by_name() -> None:
    for name in ("z_tool", "a_tool", "m_tool"):
        register_tool(
            name=name,
            description="x",
            input_schema={"type": "object"},
            handler=_noop_handler,
        )
    names = [s.name for s in list_registered()]
    assert names == ["a_tool", "m_tool", "z_tool"]
