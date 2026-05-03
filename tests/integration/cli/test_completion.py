"""Integration tests for shell completion (B2 / RFC-020 §Q1).

Typer's ``add_completion=True`` registers ``--install-completion`` and
``--show-completion`` on the root app. We verify the flags via Click's
parameter introspection (robust across Click 8.x render changes) rather
than scraping ``--help`` text — Click 8.3 separated stderr from the
CliRunner's combined output, and Rich's panel rendering varies enough
across CI/local TTY contexts that substring scraping is brittle.

The third test confirms the help still produces useful output (sanity
check that ``add_completion=True`` doesn't break sub-app listing) but
checks for sub-app names rather than the completion flags themselves.
"""

from __future__ import annotations

import pytest
from typer.main import get_command
from typer.testing import CliRunner

from chemigram.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _root_flags() -> set[str]:
    """All Click options registered on the root command.

    Robust to Click 8.x render changes — directly inspects the
    Click ``Command.params`` list rather than parsing rendered help.
    """
    cmd = get_command(app)
    return {opt for param in cmd.params for opt in (param.opts or [])}


def test_install_completion_flag_registered() -> None:
    """``--install-completion`` is a registered option on the root app
    (added by Typer when ``add_completion=True``).
    """
    assert "--install-completion" in _root_flags()


def test_show_completion_flag_registered() -> None:
    """``--show-completion`` is a registered option on the root app."""
    assert "--show-completion" in _root_flags()


def test_root_help_still_works_with_completion_enabled(runner: CliRunner) -> None:
    """Sanity: enabling add_completion=True doesn't break the help layout —
    sub-apps and top-level verbs are still listed in the rendered help.
    """
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("status", "vocab", "ingest", "apply-primitive"):
        assert cmd in result.output, f"missing {cmd!r} from root help"
