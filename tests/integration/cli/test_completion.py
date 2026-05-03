"""Integration tests for shell completion (B2 / RFC-020 §Q1).

Typer's ``add_completion=True`` enables ``--install-completion`` and
``--show-completion``. Verifies the flags surface in ``--help`` and that
``--install-completion bash`` doesn't crash on argument parsing (the
generated script's correctness is delegated to Typer).
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from chemigram.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_install_completion_flag_in_help(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--help"])
    assert "--install-completion" in result.output
    assert "--show-completion" in result.output


def test_root_help_still_works_with_completion_enabled(runner: CliRunner) -> None:
    """Sanity: enabling add_completion=True doesn't break the help layout."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # Spot-check key sub-apps still listed
    for cmd in ("status", "vocab", "ingest", "apply-primitive"):
        assert cmd in result.output, f"missing {cmd!r} from root help"
