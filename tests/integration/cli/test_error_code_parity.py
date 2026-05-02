"""Audit: every ``ErrorCode`` maps to a non-zero ``ExitCode``.

This is the runtime safety net for the contract that the mypy
``match`` statement in :mod:`chemigram.cli.error_mapping` enforces at
typecheck time. If the contract drifts (someone adds an ``ErrorCode``
upstream and the match isn't updated), this test fails at runtime
even when mypy is bypassed.
"""

from __future__ import annotations

from chemigram.cli.error_mapping import error_code_to_exit
from chemigram.cli.exit_codes import ExitCode
from chemigram.mcp.errors import ErrorCode


def test_every_error_code_is_mapped() -> None:
    """Walks every ``ErrorCode`` and confirms a non-zero ``ExitCode`` comes back."""
    for code in ErrorCode:
        out = error_code_to_exit(code)
        assert out != ExitCode.SUCCESS, f"{code} mapped to SUCCESS — bug"


def test_mapping_is_injective() -> None:
    """Distinct ErrorCodes map to distinct ExitCodes (no agent-side ambiguity)."""
    seen: dict[ExitCode, ErrorCode] = {}
    for code in ErrorCode:
        ex = error_code_to_exit(code)
        assert ex not in seen, f"{code} and {seen[ex]} both → {ex}"
        seen[ex] = code


def test_exit_code_count_matches_documented_set() -> None:
    """RFC-020 §D + ADR-072: 11 codes (SUCCESS + INTERNAL_ERROR + 9 mapped).

    If this assertion fails, RFC-020 needs an amendment AND the
    enum needs updating in lockstep.
    """
    assert len(list(ExitCode)) == 11


def test_error_code_count_matches_mcp_contract() -> None:
    """ADR-056: there are 9 reachable + reserved ``ErrorCode`` values.

    If a new ``ErrorCode`` lands upstream, both this assertion and the
    ``error_mapping`` ``match`` need updating in the same PR.
    """
    assert len(list(ErrorCode)) == 9
