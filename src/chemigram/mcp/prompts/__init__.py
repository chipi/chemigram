"""Versioned prompt system for the MCP server.

Per ADR-043 / ADR-044 / ADR-045 (closing RFC-016): prompts live as Jinja2
templates at ``<task>_v<N>.j2``, declared active in ``MANIFEST.toml``, and
versioned independently of package SemVer.

Public API:
    - :class:`PromptStore` — load + render
    - :class:`PromptError`, :class:`PromptNotFoundError`,
      :class:`PromptVersionNotFoundError`, :class:`PromptContextError`
"""

from chemigram.mcp.prompts.store import (
    PromptContextError,
    PromptError,
    PromptNotFoundError,
    PromptStore,
    PromptVersionNotFoundError,
)

__all__ = [
    "PromptContextError",
    "PromptError",
    "PromptNotFoundError",
    "PromptStore",
    "PromptVersionNotFoundError",
]
