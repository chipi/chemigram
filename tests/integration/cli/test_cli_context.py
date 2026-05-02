"""Integration tests for context CLI verbs.

read-context, log-vocabulary-gap, apply-taste-update, apply-notes-update.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chemigram.cli.exit_codes import ExitCode
from chemigram.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ----- read-context -----------------------------------------------------


def test_read_context_returns_full_shape(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "read-context",
            "test-image",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["status"] == "ok"
    for key in ("tastes", "brief", "notes", "recent_log", "recent_gaps"):
        assert key in payload, f"missing {key}"
    assert isinstance(payload["recent_log"], list)
    assert isinstance(payload["recent_gaps"], list)


def test_read_context_unknown_image(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        ["--workspace", str(cli_workspace_root), "read-context", "no-image"],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


# ----- log-vocabulary-gap -----------------------------------------------


def test_log_vocabulary_gap_appends_to_jsonl(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "log-vocabulary-gap",
            "test-image",
            "--description",
            "wanted painterly clarity, only have global contrast",
            "--intent-category",
            "tone",
            "--satisfaction",
            "0",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr

    gaps_path = cli_workspace_root / "test-image" / "vocabulary_gaps.jsonl"
    assert gaps_path.is_file()
    line = gaps_path.read_text(encoding="utf-8").strip().splitlines()[-1]
    record = json.loads(line)
    assert record["description"] == "wanted painterly clarity, only have global contrast"
    assert record["intent_category"] == "tone"
    assert record["satisfaction"] == 0
    assert record["session_id"] is None  # CLI has no MCP session


def test_log_vocabulary_gap_empty_description_invalid(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "log-vocabulary-gap",
            "test-image",
            "--description",
            "   ",
        ],
    )
    assert result.exit_code == ExitCode.INVALID_INPUT.value


def test_log_vocabulary_gap_invalid_satisfaction(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "log-vocabulary-gap",
            "test-image",
            "--description",
            "x",
            "--satisfaction",
            "5",
        ],
    )
    assert result.exit_code == ExitCode.INVALID_INPUT.value


def test_log_vocabulary_gap_unknown_image(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "log-vocabulary-gap",
            "no-image",
            "--description",
            "x",
        ],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


# ----- apply-taste-update (CLI-only direct verb) ------------------------


def test_apply_taste_update_appends_to_default(
    runner: CliRunner, isolated_tastes_dir: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "apply-taste-update",
            "--content",
            "I tend to lift mid-shadows on subject masks.",
            "--category",
            "process",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    target = isolated_tastes_dir / "_default.md"
    assert target.is_file()
    assert "lift mid-shadows" in target.read_text(encoding="utf-8")


def test_apply_taste_update_explicit_file(runner: CliRunner, isolated_tastes_dir: Path) -> None:
    result = runner.invoke(
        app,
        [
            "apply-taste-update",
            "--content",
            "Sea-floor shots: cooler whites.",
            "--category",
            "appearance",
            "--file",
            "underwater",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    target = isolated_tastes_dir / "underwater.md"
    assert target.is_file()


def test_apply_taste_update_invalid_category(runner: CliRunner, isolated_tastes_dir: Path) -> None:
    result = runner.invoke(
        app,
        [
            "apply-taste-update",
            "--content",
            "x",
            "--category",
            "nonsense",
        ],
    )
    assert result.exit_code == ExitCode.INVALID_INPUT.value


def test_apply_taste_update_empty_content(runner: CliRunner, isolated_tastes_dir: Path) -> None:
    result = runner.invoke(
        app,
        [
            "apply-taste-update",
            "--content",
            "   ",
            "--category",
            "process",
        ],
    )
    assert result.exit_code == ExitCode.INVALID_INPUT.value


# ----- apply-notes-update (CLI-only direct verb) ------------------------


def test_apply_notes_update_appends_to_workspace_notes(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "apply-notes-update",
            "test-image",
            "--content",
            "Highlights on the rock are clipping; consider dampen_highlights.",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    notes_path = cli_workspace_root / "test-image" / "notes.md"
    assert notes_path.is_file()
    assert "clipping" in notes_path.read_text(encoding="utf-8")


def test_apply_taste_update_two_sequential_appends_preserved(
    runner: CliRunner, isolated_tastes_dir: Path
) -> None:
    """Two back-to-back appends both land in the file with a separator.

    Proxy for concurrency-safety: real subprocess parallelism could
    interleave writes, but at minimum sequential calls must compose.
    """
    for content in ("first taste line", "second taste line"):
        result = runner.invoke(
            app,
            [
                "apply-taste-update",
                "--content",
                content,
                "--category",
                "process",
            ],
        )
        assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    target = isolated_tastes_dir / "_default.md"
    body = target.read_text(encoding="utf-8")
    assert "first taste line" in body
    assert "second taste line" in body
    # Order preserved
    assert body.index("first taste line") < body.index("second taste line")


def test_apply_notes_update_unknown_image(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "apply-notes-update",
            "no-image",
            "--content",
            "x",
        ],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value
