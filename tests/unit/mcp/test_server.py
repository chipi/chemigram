"""Unit tests for chemigram.mcp.server bootstrap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from chemigram.core.vocab import VocabularyIndex
from chemigram.mcp.errors import ErrorCode, ToolResult, error_not_found
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


@pytest.fixture
def vocab() -> VocabularyIndex:
    return VocabularyIndex(VOCAB_TEST_PACK)


@pytest.fixture
def prompts() -> PromptStore:
    return PromptStore(SHIPPED_PROMPTS)


def test_build_server_carries_context(vocab: VocabularyIndex, prompts: PromptStore) -> None:
    server, ctx = build_server(vocabulary=vocab, prompts=prompts)
    assert ctx.vocabulary is vocab
    assert ctx.prompts is prompts
    assert server.name == "chemigram-mcp"


def test_build_server_with_no_tools_lists_empty(
    vocab: VocabularyIndex, prompts: PromptStore
) -> None:
    """No tools registered yet — list_tools returns empty list."""
    import anyio

    server, _ = build_server(vocabulary=vocab, prompts=prompts)

    async def _exercise() -> list:
        from mcp import types

        handler = server.request_handlers[types.ListToolsRequest]
        result = await handler(types.ListToolsRequest(method="tools/list"))
        return result.root.tools  # ServerResult unwrap

    tools = anyio.run(_exercise)
    assert tools == []


def test_call_unknown_tool_returns_not_found(vocab: VocabularyIndex, prompts: PromptStore) -> None:
    import anyio

    server, _ = build_server(vocabulary=vocab, prompts=prompts)

    async def _call() -> dict:
        from mcp import types

        handler = server.request_handlers[types.CallToolRequest]
        req = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(name="nope", arguments={}),
        )
        result = await handler(req)
        return result.root.structuredContent or {}

    payload = anyio.run(_call)
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_found"


def test_registered_tool_round_trip(vocab: VocabularyIndex, prompts: PromptStore) -> None:
    import anyio

    async def echo_handler(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict]:
        return ToolResult.ok({"got": args, "vocab_count": len(ctx.vocabulary.list_all())})

    register_tool(
        name="echo",
        description="echo back",
        input_schema={
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        },
        handler=echo_handler,
    )

    server, _ = build_server(vocabulary=vocab, prompts=prompts)

    async def _call() -> dict:
        from mcp import types

        handler = server.request_handlers[types.CallToolRequest]
        req = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(name="echo", arguments={"x": "hello"}),
        )
        result = await handler(req)
        return result.root.structuredContent or {}

    payload = anyio.run(_call)
    assert payload["success"] is True
    assert payload["data"]["got"] == {"x": "hello"}
    assert payload["data"]["vocab_count"] > 0


def test_validation_rejects_missing_required(vocab: VocabularyIndex, prompts: PromptStore) -> None:
    import anyio

    async def handler(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict]:
        return ToolResult.ok({"args": args})

    register_tool(
        name="needs_x",
        description="x",
        input_schema={
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        },
        handler=handler,
    )

    server, _ = build_server(vocabulary=vocab, prompts=prompts)

    async def _call() -> Any:
        from mcp import types

        h = server.request_handlers[types.CallToolRequest]
        req = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(name="needs_x", arguments={}),
        )
        return await h(req)

    result = anyio.run(_call)
    # MCP server's own validation kicks in before our handler — surfaces as
    # an error CallToolResult with isError=True.
    assert result.root.isError is True


def test_handler_failure_surfaces_error_payload(
    vocab: VocabularyIndex, prompts: PromptStore
) -> None:
    import anyio

    async def fails(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict]:
        return ToolResult.fail(error_not_found("widget abc"))

    register_tool(
        name="fails",
        description="x",
        input_schema={"type": "object", "properties": {}},
        handler=fails,
    )

    server, _ = build_server(vocabulary=vocab, prompts=prompts)

    async def _call() -> dict:
        from mcp import types

        h = server.request_handlers[types.CallToolRequest]
        req = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(name="fails", arguments={}),
        )
        result = await h(req)
        # text content also carries the JSON payload
        text = result.root.content[0].text
        return json.loads(text)

    payload = anyio.run(_call)
    assert payload["success"] is False
    assert payload["error"]["code"] == ErrorCode.NOT_FOUND.value
    assert "widget abc" in payload["error"]["message"]


def test_main_entry_point_resolves() -> None:
    """``chemigram-mcp`` shell entry point points at a real callable."""
    from importlib.metadata import entry_points

    eps = entry_points(group="console_scripts")
    target_eps = [ep for ep in eps if ep.name == "chemigram-mcp"]
    assert len(target_eps) == 1
    fn = target_eps[0].load()
    assert callable(fn)
