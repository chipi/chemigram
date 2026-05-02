"""Integration tests for CLI versioning verbs (#55)."""

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


def _head_hash(runner: CliRunner, root: Path, image_id: str = "test-image") -> str:
    """Read HEAD's hash via `chemigram --json get-state`."""
    result = runner.invoke(app, ["--json", "--workspace", str(root), "get-state", image_id])
    assert result.exit_code == ExitCode.SUCCESS.value
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    return payload["head_hash"]


# ----- snapshot --------------------------------------------------------


def test_snapshot_returns_new_hash(runner: CliRunner, cli_workspace_root: Path) -> None:
    """The fixture's baseline already snapshotted; `snapshot` again is a no-op
    on identical content (same hash) but the command itself succeeds."""
    result = runner.invoke(
        app,
        ["--json", "--workspace", str(cli_workspace_root), "snapshot", "test-image"],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["status"] == "ok"
    assert payload["hash"]
    assert payload["image_id"] == "test-image"


def test_snapshot_with_label(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "snapshot",
            "test-image",
            "--label",
            "manual-checkpoint",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["label"] == "manual-checkpoint"


def test_snapshot_unknown_image(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(app, ["--workspace", str(cli_workspace_root), "snapshot", "no-image"])
    assert result.exit_code == ExitCode.NOT_FOUND.value


# ----- branch ----------------------------------------------------------


def test_branch_at_head(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "branch",
            "test-image",
            "--name",
            "experiment",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["name"] == "experiment"
    assert "experiment" in payload["ref"]


def test_branch_duplicate_name_versioning_error(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    args = [
        "--workspace",
        str(cli_workspace_root),
        "branch",
        "test-image",
        "--name",
        "dup",
    ]
    first = runner.invoke(app, args)
    assert first.exit_code == ExitCode.SUCCESS.value
    second = runner.invoke(app, args)
    assert second.exit_code == ExitCode.VERSIONING_ERROR.value


def test_branch_from_explicit_ref(runner: CliRunner, cli_workspace_root: Path) -> None:
    """``branch --from baseline`` should branch off the existing baseline tag."""
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "branch",
            "test-image",
            "--name",
            "from-baseline",
            "--from",
            "baseline",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["from_ref"] == "baseline"
    assert payload["name"] == "from-baseline"


def test_branch_unknown_image(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "branch",
            "no-image",
            "--name",
            "x",
        ],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


# ----- tag -------------------------------------------------------------


def test_tag_at_head(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "tag",
            "test-image",
            "--name",
            "v1-export",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["name"] == "v1-export"


def test_tag_immutable_retag_fails(runner: CliRunner, cli_workspace_root: Path) -> None:
    """Tags are immutable per the engine contract — retagging must fail."""
    args = [
        "--workspace",
        str(cli_workspace_root),
        "tag",
        "test-image",
        "--name",
        "frozen",
    ]
    runner.invoke(app, args)
    second = runner.invoke(app, args)
    assert second.exit_code == ExitCode.VERSIONING_ERROR.value


def test_tag_empty_name_invalid(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "tag",
            "test-image",
            "--name",
            "  ",
        ],
    )
    assert result.exit_code == ExitCode.INVALID_INPUT.value


# ----- checkout --------------------------------------------------------


def test_checkout_existing_tag(runner: CliRunner, cli_workspace_root: Path) -> None:
    """The fixture has a `baseline` tag already."""
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "checkout",
            "test-image",
            "baseline",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["ref_or_hash"] == "baseline"
    assert payload["head_hash"]


def test_checkout_explicit_hash(runner: CliRunner, cli_workspace_root: Path) -> None:
    """The verb accepts a raw 64-hex hash as well as a ref name."""
    head = _head_hash(runner, cli_workspace_root)
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "checkout",
            "test-image",
            head,
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["head_hash"] == head


def test_checkout_unknown_ref(runner: CliRunner, cli_workspace_root: Path) -> None:
    """Mirrors MCP: unknown ref/hash collapses to VERSIONING_ERROR (5),
    not NOT_FOUND (3). The MCP `_versioning_error` helper does the same."""
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "checkout",
            "test-image",
            "no-such-ref",
        ],
    )
    assert result.exit_code == ExitCode.VERSIONING_ERROR.value


# ----- log -------------------------------------------------------------


def test_log_returns_baseline_entry(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        ["--json", "--workspace", str(cli_workspace_root), "log", "test-image"],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["event"] == "result"
    assert payload["count"] >= 1
    assert isinstance(payload["entries"], list)
    assert payload["entries"]  # at least the baseline snapshot's entry


def test_log_limit(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "log",
            "test-image",
            "--limit",
            "1",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    summary = json.loads(result.stdout.strip().splitlines()[-1])
    assert summary["count"] <= 1


# ----- diff ------------------------------------------------------------


def test_diff_identical_returns_empty(runner: CliRunner, cli_workspace_root: Path) -> None:
    head = _head_hash(runner, cli_workspace_root)
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "diff",
            "test-image",
            head,
            head,
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    summary = json.loads(result.stdout.strip().splitlines()[-1])
    assert summary["count"] == 0


def test_diff_after_apply_shows_change(runner: CliRunner, cli_workspace_root: Path) -> None:
    """Capture HEAD before + after `apply-primitive`; diff should show a change."""
    before = _head_hash(runner, cli_workspace_root)
    apply_result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "apply-primitive",
            "test-image",
            "--entry",
            "expo_+0.5",
        ],
    )
    assert apply_result.exit_code == ExitCode.SUCCESS.value
    after = _head_hash(runner, cli_workspace_root)
    assert before != after

    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "diff",
            "test-image",
            before,
            after,
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    summary = json.loads(result.stdout.strip().splitlines()[-1])
    assert summary["count"] >= 1


def test_workflow_branch_apply_diff(runner: CliRunner, cli_workspace_root: Path) -> None:
    """End-to-end multi-step workflow: capture baseline hash → branch →
    apply on the branch → diff baseline vs branch HEAD → checkout baseline.

    Catches integration regressions across the versioning + edit verb groups.
    """
    baseline_hash = _head_hash(runner, cli_workspace_root)

    branch_proc = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "branch",
            "test-image",
            "--name",
            "experiment-flow",
        ],
    )
    assert branch_proc.exit_code == ExitCode.SUCCESS.value, branch_proc.stdout

    checkout_proc = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "checkout",
            "test-image",
            "experiment-flow",
        ],
    )
    assert checkout_proc.exit_code == ExitCode.SUCCESS.value

    apply_proc = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "apply-primitive",
            "test-image",
            "--entry",
            "expo_+0.5",
        ],
    )
    assert apply_proc.exit_code == ExitCode.SUCCESS.value, apply_proc.stdout

    branch_head = _head_hash(runner, cli_workspace_root)
    assert branch_head != baseline_hash

    diff_proc = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "diff",
            "test-image",
            baseline_hash,
            branch_head,
        ],
    )
    assert diff_proc.exit_code == ExitCode.SUCCESS.value
    diff_payload = json.loads(diff_proc.stdout.strip().splitlines()[-1])
    assert diff_payload["count"] >= 1


def test_diff_unknown_hash_versioning_error(runner: CliRunner, cli_workspace_root: Path) -> None:
    """Mirrors MCP: unknown hash → VERSIONING_ERROR (5), not NOT_FOUND (3)."""
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "diff",
            "test-image",
            "0" * 64,
            "1" * 64,
        ],
    )
    assert result.exit_code == ExitCode.VERSIONING_ERROR.value
