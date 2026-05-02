"""Unit tests for ``chemigram.cli.error_mapping``.

The mapping is total (every ``ErrorCode`` produces a non-zero ``ExitCode``).
The mypy ``match`` exhaustiveness in ``error_code_to_exit`` is the
compile-time safety; this test is the runtime safety net.
"""

from __future__ import annotations

import pytest

from chemigram.cli.error_mapping import error_code_to_exit
from chemigram.cli.exit_codes import ExitCode
from chemigram.mcp.errors import ErrorCode


@pytest.mark.parametrize("code", list(ErrorCode))
def test_every_error_code_maps_to_a_nonzero_exit(code: ErrorCode) -> None:
    out = error_code_to_exit(code)
    assert isinstance(out, ExitCode)
    assert out.value != ExitCode.SUCCESS.value


def test_specific_known_pairs() -> None:
    """Lock the canonical pairs documented in RFC-020 §D."""
    assert error_code_to_exit(ErrorCode.INVALID_INPUT) == ExitCode.INVALID_INPUT
    assert error_code_to_exit(ErrorCode.NOT_FOUND) == ExitCode.NOT_FOUND
    assert error_code_to_exit(ErrorCode.DARKTABLE_ERROR) == ExitCode.DARKTABLE_ERROR
    assert error_code_to_exit(ErrorCode.MASKING_ERROR) == ExitCode.MASKING_ERROR
    assert error_code_to_exit(ErrorCode.STATE_ERROR) == ExitCode.STATE_ERROR


def test_mapping_is_injective() -> None:
    """Distinct ``ErrorCode`` values map to distinct ``ExitCode`` values.

    If two ``ErrorCode``s collapsed to the same ``ExitCode``, agents
    consuming the CLI couldn't disambiguate. Catches accidental dupes
    in the match arms.
    """
    seen: dict[ExitCode, ErrorCode] = {}
    for code in ErrorCode:
        ex = error_code_to_exit(code)
        assert ex not in seen, f"{code} and {seen[ex]} both map to {ex}"
        seen[ex] = code
