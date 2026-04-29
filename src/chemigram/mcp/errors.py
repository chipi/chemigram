"""Error contract types for MCP tool returns.

Per RFC-010 (closed at v0.3.0 by ADR-056): every tool returns a structured
``{success, data, error}`` payload. ``error.code`` is one of a fixed enum so
agents can branch on category without parsing messages.

This module is the canonical home for the contract types and helper
constructors. Tools (in ``chemigram.mcp.tools``) return :class:`ToolResult`;
the registry serializes that into an MCP ``CallToolResult`` shape.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Generic, TypeVar


class ErrorCode(StrEnum):
    """Canonical error categories. Agents branch on these without parsing messages."""

    INVALID_INPUT = "invalid_input"
    NOT_FOUND = "not_found"
    DARKTABLE_ERROR = "darktable_error"
    SYNTHESIZER_ERROR = "synthesizer_error"
    VERSIONING_ERROR = "versioning_error"
    MASKING_ERROR = "masking_error"
    PERMISSION_ERROR = "permission_error"
    STATE_ERROR = "state_error"
    NOT_IMPLEMENTED = "not_implemented"


@dataclass(frozen=True)
class ToolError:
    """Structured tool failure.

    Attributes:
        code: One of :class:`ErrorCode`. Agents branch on this.
        message: Human-readable summary; agents may show this to users.
        details: Free-form structured context (slice number for stubs,
            stderr from subprocess, validation diagnostics).
        recoverable: Hint to the agent — ``True`` means the same operation
            could plausibly succeed under different conditions; ``False``
            means the failure is structural.
    """

    code: ErrorCode
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    recoverable: bool = True


T = TypeVar("T")


@dataclass(frozen=True)
class ToolResult(Generic[T]):
    """Structured tool return: either ``success+data`` or ``success=False+error``.

    Construct via :meth:`ok` / :meth:`fail`; the public consumers
    (:func:`tool_result_to_mcp`) serialize this to MCP's wire shape.
    """

    success: bool
    data: T | None = None
    error: ToolError | None = None

    @classmethod
    def ok(cls, data: T) -> ToolResult[T]:
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: ToolError) -> ToolResult[T]:
        return cls(success=False, error=error)

    def to_payload(self) -> dict[str, Any]:
        """Wire-format dict per RFC-010 ``{success, data, error}``."""
        if self.success:
            return {"success": True, "data": self.data, "error": None}
        assert self.error is not None
        err = asdict(self.error)
        err["code"] = str(self.error.code)
        return {"success": False, "data": None, "error": err}


def error_invalid_input(message: str, **details: Any) -> ToolError:
    """Helper: ``ErrorCode.INVALID_INPUT`` shorthand."""
    return ToolError(code=ErrorCode.INVALID_INPUT, message=message, details=details)


def error_not_found(what: str, **details: Any) -> ToolError:
    """Helper: ``ErrorCode.NOT_FOUND`` shorthand."""
    return ToolError(
        code=ErrorCode.NOT_FOUND,
        message=f"not found: {what}",
        details=details,
    )


def error_not_implemented(reason: str, *, slice: int | None = None) -> ToolError:
    """Helper for stub tools: marks the slice that will land the real impl."""
    details: dict[str, Any] = {}
    if slice is not None:
        details["slice"] = slice
    return ToolError(
        code=ErrorCode.NOT_IMPLEMENTED,
        message=reason,
        details=details,
        recoverable=False,
    )
