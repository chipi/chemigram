"""MCP tool implementations.

Each tool batch lives in its own module and imports
:func:`~chemigram.mcp.registry.register_tool` to register itself when the
module loads. The server bootstrap (``chemigram.mcp.server``) imports
:func:`register_all` from this package so every tool is registered before
the MCP transport accepts connections.

Modules:
    - :mod:`chemigram.mcp.tools.vocab_edit` — list_vocabulary, get_state,
      apply_primitive, remove_module, reset (#13)
    - :mod:`chemigram.mcp.tools.context_stubs` — read_context, taste/notes
      propose-and-confirm stubs (#13; real impl in Slice 5)
"""

from __future__ import annotations


def register_all() -> None:
    """Register every tool batch's tools with the global registry.

    Each tool module is reloaded via :mod:`importlib` so the top-level
    ``register_tool(...)`` calls run again — this matters because
    :func:`~chemigram.mcp.registry.register_tool` overrides on duplicate
    rather than raising, which keeps both startup and test
    ``clear_registry → register_all`` cycles deterministic.
    """
    import importlib

    modules = [
        "chemigram.mcp.tools.vocab_edit",
        "chemigram.mcp.tools.context_stubs",
    ]
    for name in modules:
        mod = importlib.import_module(name)
        importlib.reload(mod)
