"""MCP server bootstrap.

Loads the vocabulary (#10) and prompts (#11) at startup, wires the tool
registry (``chemigram.mcp.registry``) into the official ``mcp`` SDK's
``Server``, and runs the stdio transport. Single-session per process per
ADR-006.

Tools are registered via :mod:`chemigram.mcp.tools.*` (lands in #13/#14/#15).
This module is intentionally thin: most behavior is in the registry and the
tool implementations.
"""

from __future__ import annotations

import json
import logging
from importlib.resources import files as resource_files
from pathlib import Path
from typing import Any, cast

import anyio
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from chemigram.core.vocab import VocabularyIndex, load_starter
from chemigram.mcp.errors import ErrorCode, ToolError, ToolResult
from chemigram.mcp.prompts import PromptStore
from chemigram.mcp.registry import ToolContext, get_tool, list_registered
from chemigram.mcp.tools import register_all

logger = logging.getLogger(__name__)


def _resolve_prompts_root() -> Path:
    """Find the prompts directory (bundled or in-repo for editable installs)."""
    try:
        bundled = resource_files("chemigram.mcp.prompts")
        bundled_path = Path(cast(Any, bundled))
        if (bundled_path / "MANIFEST.toml").exists():
            return bundled_path
    except (ModuleNotFoundError, FileNotFoundError):
        pass
    repo_path = Path(__file__).resolve().parent / "prompts"
    if (repo_path / "MANIFEST.toml").exists():
        return repo_path
    raise RuntimeError("prompts directory not found via importlib.resources or in-repo fallback")


def build_server(
    *,
    vocabulary: VocabularyIndex | None = None,
    prompts: PromptStore | None = None,
    masker: Any = None,
    transcript: Any = None,
) -> tuple[Server[Any, Any], ToolContext]:
    """Construct the MCP ``Server`` with handlers wired to the tool registry.

    Args:
        vocabulary: Inject a custom :class:`VocabularyIndex` (tests). When
            ``None``, calls :func:`chemigram.core.vocab.load_starter`.
        prompts: Inject a custom :class:`PromptStore`. When ``None``,
            resolves the bundled prompts directory.
        masker: Inject a :class:`~chemigram.core.masking.MaskingProvider`.
            When ``None``, mask-generation tools return
            ``MASKING_ERROR`` ("no masker configured"). Production callers
            wire :class:`CoarseAgentProvider` against the MCP session's
            sampling callback at server startup.

    Returns:
        Tuple of (server, context). The context is also captured by the
        tool handlers via closure; it's returned so tests can inspect it.
    """
    if vocabulary is None:
        vocabulary = load_starter()
    if prompts is None:
        prompts = PromptStore(_resolve_prompts_root())

    register_all()
    context = ToolContext(
        vocabulary=vocabulary,
        prompts=prompts,
        masker=masker,
        transcript=transcript,
    )

    server: Server[Any, Any] = Server(
        name="chemigram-mcp",
        version="1.4.0",
        instructions="Chemigram — agent-driven photo editing on darktable.",
    )

    @server.list_tools()  # type: ignore[untyped-decorator,no-untyped-call,unused-ignore]
    async def _list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=spec.name,
                description=spec.description,
                inputSchema=spec.input_schema,
            )
            for spec in list_registered()
        ]

    @server.call_tool()  # type: ignore[untyped-decorator]
    async def _call_tool(
        name: str, arguments: dict[str, Any]
    ) -> tuple[list[types.ContentBlock], dict[str, Any]]:
        return await _dispatch_tool(name, arguments, context)

    return server, context


async def _dispatch_tool(
    name: str,
    arguments: dict[str, Any],
    context: ToolContext,
) -> tuple[list[types.ContentBlock], dict[str, Any]]:
    """One tool dispatch: transcript hooks + spec lookup + handler call."""
    _record_tool_call(context, name, arguments)

    spec = get_tool(name)
    if spec is None:
        err = ToolError(
            code=ErrorCode.NOT_FOUND,
            message=f"unknown tool {name!r}",
            recoverable=False,
        )
        payload = ToolResult.fail(err).to_payload()
        _record_tool_result(context, name, success=False, error_code=ErrorCode.NOT_FOUND.value)
        return (
            [types.TextContent(type="text", text=json.dumps(payload, indent=2))],
            payload,
        )

    result = await spec.handler(arguments, context)
    payload = result.to_payload()
    _record_tool_result(
        context,
        name,
        success=result.success,
        error_code=(result.error.code.value if result.error else None),
    )
    text = json.dumps(payload, indent=2, default=str)
    return ([types.TextContent(type="text", text=text)], payload)


def _record_tool_call(context: ToolContext, name: str, arguments: dict[str, Any]) -> None:
    if context.transcript is None:
        return
    try:
        context.transcript.append_tool_call(name, arguments)
    except Exception:
        logger.warning("transcript append_tool_call failed", exc_info=True)


def _record_tool_result(
    context: ToolContext,
    name: str,
    *,
    success: bool,
    error_code: str | None,
) -> None:
    if context.transcript is None:
        return
    try:
        context.transcript.append_tool_result(name, success=success, error_code=error_code)
    except Exception:
        logger.warning("transcript append_tool_result failed", exc_info=True)


async def _run_stdio() -> None:
    server, _ = build_server()
    init_options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, init_options)


def main() -> None:
    """Entry point for the ``chemigram-mcp`` shell command."""
    logging.basicConfig(level=logging.INFO)
    anyio.run(_run_stdio)


if __name__ == "__main__":
    main()
