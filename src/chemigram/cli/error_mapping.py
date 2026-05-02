"""Map :class:`chemigram.mcp.errors.ErrorCode` → :class:`ExitCode`.

The mapping is total. Adding a new ``ErrorCode`` upstream produces a
mypy error here (the ``match`` statement is exhaustive); the audit
test in ``tests/integration/cli/test_error_code_parity.py`` is a
runtime safety net for the same property.
"""

from __future__ import annotations

from chemigram.cli.exit_codes import ExitCode
from chemigram.mcp.errors import ErrorCode


def error_code_to_exit(code: ErrorCode) -> ExitCode:
    """Map a structured :class:`ErrorCode` to a CLI :class:`ExitCode`.

    Each ``ErrorCode`` maps to exactly one non-zero ``ExitCode``. The
    match statement is exhaustive — a new enum value upstream surfaces
    as a mypy error here, in lockstep, so the contract can't drift
    silently.
    """
    match code:
        case ErrorCode.INVALID_INPUT:
            return ExitCode.INVALID_INPUT
        case ErrorCode.NOT_FOUND:
            return ExitCode.NOT_FOUND
        case ErrorCode.DARKTABLE_ERROR:
            return ExitCode.DARKTABLE_ERROR
        case ErrorCode.SYNTHESIZER_ERROR:
            return ExitCode.SYNTHESIZER_ERROR
        case ErrorCode.VERSIONING_ERROR:
            return ExitCode.VERSIONING_ERROR
        case ErrorCode.MASKING_ERROR:
            return ExitCode.MASKING_ERROR
        case ErrorCode.PERMISSION_ERROR:
            return ExitCode.PERMISSION_ERROR
        case ErrorCode.STATE_ERROR:
            return ExitCode.STATE_ERROR
        case ErrorCode.NOT_IMPLEMENTED:
            return ExitCode.NOT_IMPLEMENTED
