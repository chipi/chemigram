"""Tool registry — the seam between tool batches and the MCP server.

Each tool is registered via :func:`register_tool` (or the ``@tool`` decorator)
with a name, JSON Schema for ``inputSchema``, an optional ``description``, and
a callable that returns a :class:`~chemigram.mcp.errors.ToolResult`. The
server bootstrap (``chemigram.mcp.server``) consumes the global registry to
wire MCP ``list_tools`` / ``call_tool`` handlers.

Tool callables receive ``arguments: dict[str, Any]`` and an injected
:class:`ToolContext` carrying server-side resources (vocabulary index,
prompt store, workspace registry). This keeps tool code pure:: easy to test
with a hand-rolled context.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from chemigram.mcp.errors import ToolResult


@dataclass(frozen=True)
class ToolContext:
    """Shared server-side resources passed to every tool invocation.

    Phase 1 carries vocabulary + prompts. Slice-3 tool batches that need a
    workspace registry use :attr:`workspaces`; the actual orchestrator type
    lands in #15 — until then the field is a free-form ``Any`` so #13/#14
    can be developed in parallel.
    """

    vocabulary: Any  # VocabularyIndex; Any to avoid circular import for stubs
    prompts: Any  # PromptStore
    workspaces: Any = None  # Workspace registry (lands in #15)


ToolHandler = Callable[[dict[str, Any], ToolContext], Awaitable[ToolResult[Any]]]


@dataclass(frozen=True)
class ToolSpec:
    """One tool's static metadata + handler. Stored in the global registry."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler


_REGISTRY: dict[str, ToolSpec] = {}


def register_tool(
    *,
    name: str,
    description: str,
    input_schema: dict[str, Any],
    handler: ToolHandler,
) -> None:
    """Register a tool. Raises ``ValueError`` on duplicate name."""
    if name in _REGISTRY:
        raise ValueError(f"tool {name!r} already registered")
    _REGISTRY[name] = ToolSpec(
        name=name,
        description=description,
        input_schema=input_schema,
        handler=handler,
    )


def list_registered() -> list[ToolSpec]:
    """All registered tools, sorted by name. Stable order for tests."""
    return sorted(_REGISTRY.values(), key=lambda s: s.name)


def get_tool(name: str) -> ToolSpec | None:
    return _REGISTRY.get(name)


def clear_registry() -> None:
    """Test-only: reset the registry between tests that exercise registration."""
    _REGISTRY.clear()
