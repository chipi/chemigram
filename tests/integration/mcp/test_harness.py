"""Integration: run the in-memory client/server harness end-to-end."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anyio
import pytest

from chemigram.core.vocab import VocabularyIndex
from chemigram.mcp._test_harness import in_memory_session
from chemigram.mcp.errors import ToolResult
from chemigram.mcp.prompts import PromptStore
from chemigram.mcp.registry import ToolContext, clear_registry, register_tool
from chemigram.mcp.server import build_server

REPO_ROOT = Path(__file__).resolve().parents[3]
VOCAB_TEST_PACK = REPO_ROOT / "tests" / "fixtures" / "vocabulary" / "test_pack"
SHIPPED_PROMPTS = REPO_ROOT / "src" / "chemigram" / "mcp" / "prompts"


@pytest.fixture(autouse=True)
def _isolated_registry() -> Any:
    clear_registry()
    yield
    clear_registry()


def test_in_memory_session_round_trip() -> None:
    """list_tools + call_tool over the harness."""

    async def ping_handler(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict]:
        return ToolResult.ok({"pong": True, "echo": args})

    register_tool(
        name="ping",
        description="ping",
        input_schema={
            "type": "object",
            "properties": {"msg": {"type": "string"}},
            "required": ["msg"],
        },
        handler=ping_handler,
    )

    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)
    server, _ = build_server(vocabulary=vocab, prompts=prompts)

    async def _exercise() -> tuple[list[str], dict]:
        async with in_memory_session(server) as session:
            tools_result = await session.list_tools()
            tool_names = [t.name for t in tools_result.tools]

            call_result = await session.call_tool("ping", arguments={"msg": "hi"})
            payload = json.loads(call_result.content[0].text)
            return tool_names, payload

    tool_names, payload = anyio.run(_exercise)
    assert "ping" in tool_names
    assert payload["success"] is True
    assert payload["data"]["pong"] is True
    assert payload["data"]["echo"] == {"msg": "hi"}
