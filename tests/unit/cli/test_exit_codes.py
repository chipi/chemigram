"""Unit tests for ``chemigram.cli.exit_codes`` (RFC-020 §D)."""

from __future__ import annotations

from chemigram.cli.exit_codes import ExitCode


def test_success_is_zero() -> None:
    assert ExitCode.SUCCESS.value == 0


def test_internal_error_is_one() -> None:
    """Reserved for unhandled exceptions (bugs). Distinct from any
    structured ErrorCode mapping.
    """
    assert ExitCode.INTERNAL_ERROR.value == 1


def test_no_two_codes_share_a_value() -> None:
    values = [c.value for c in ExitCode]
    assert len(values) == len(set(values))


def test_codes_are_dense_and_contiguous() -> None:
    """0..10 with no gaps. Adding a code requires bumping this assert
    in lockstep with ``error_mapping`` and the audit test.
    """
    assert sorted(c.value for c in ExitCode) == list(range(11))


def test_every_code_has_a_name() -> None:
    for code in ExitCode:
        assert code.name and code.name.isupper()
