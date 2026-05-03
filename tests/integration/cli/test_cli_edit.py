"""Integration tests for the CLI edit/state verbs (#54).

apply-primitive, remove-module, reset, get-state — driven through
``CliRunner`` against a hand-built workspace.
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


# ----- get-state ---------------------------------------------------------


def test_get_state_returns_summary(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(app, ["--workspace", str(cli_workspace_root), "get-state", "test-image"])
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    assert "head_hash" in result.stdout
    assert "entry_count" in result.stdout


def test_get_state_json_returns_full_summary(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        ["--json", "--workspace", str(cli_workspace_root), "get-state", "test-image"],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["status"] == "ok"
    assert "head_hash" in payload
    assert payload["head_hash"]  # non-empty (workspace has a baseline snapshot)
    assert "layers_present" in payload


def test_get_state_unknown_image_id(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        ["--workspace", str(cli_workspace_root), "get-state", "no-such-image"],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


# ----- apply-primitive ---------------------------------------------------


def test_apply_primitive_happy_path(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
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
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    assert "applied" in result.stdout.lower()


def test_apply_primitive_json_emits_snapshot_hash(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "apply-primitive",
            "test-image",
            "--entry",
            "expo_+0.5",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["status"] == "ok"
    assert payload["entry"] == "expo_+0.5"
    assert payload["snapshot_hash"]
    assert "state_after" in payload


def test_apply_primitive_with_mask_spec_routes_through_drawn_mask(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    """An expressive-baseline mask-bound entry routes through the drawn-mask
    apply path; the resulting XMP carries masks_history. Coverage gate for
    the ``vocab_entry.mask_spec is not None`` branch in cli/commands/edit.py
    (the e2e suite proves the binding actually shapes pixels under real
    darktable; this proves the dispatch logic works without darktable).
    """
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "apply-primitive",
            "test-image",
            "--entry",
            "gradient_top_dampen_highlights",
            "--pack",
            "expressive-baseline",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["status"] == "ok"
    snapshot_hash = payload["snapshot_hash"]

    from chemigram.core.versioning import ImageRepo

    repo = ImageRepo(cli_workspace_root / "test-image")
    raw = repo.read_object(snapshot_hash)
    assert b"masks_history" in raw, (
        "drawn-mask path should inject darktable:masks_history into the XMP "
        "for entries with mask_spec (ADR-076)"
    )


def test_apply_primitive_unknown_entry(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "apply-primitive",
            "test-image",
            "--entry",
            "no_such_primitive",
        ],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


def test_apply_primitive_unknown_image(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "apply-primitive",
            "no-image",
            "--entry",
            "expo_+0.5",
        ],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


def test_apply_primitive_mask_override_on_global_primitive_invalid(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    """--mask-override on a non-mask-bound primitive must error INVALID_INPUT."""
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "apply-primitive",
            "test-image",
            "--entry",
            "expo_+0.5",
            "--mask-override",
            "subject",
        ],
    )
    assert result.exit_code == ExitCode.INVALID_INPUT.value


# ----- remove-module ----------------------------------------------------


def test_remove_module_unknown_module_not_found(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "remove-module",
            "test-image",
            "--operation",
            "no_such_operation",
        ],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


def test_remove_module_strips_history(runner: CliRunner, cli_workspace_root: Path) -> None:
    """First apply expo_+0.5 to introduce an exposure entry, then remove it.

    Tests apply-primitive → remove-module round-trip end-to-end.
    """
    apply_result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "apply-primitive",
            "test-image",
            "--entry",
            "expo_+0.5",
        ],
    )
    assert apply_result.exit_code == ExitCode.SUCCESS.value, apply_result.stdout

    rm_result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "remove-module",
            "test-image",
            "--operation",
            "exposure",
        ],
    )
    assert rm_result.exit_code == ExitCode.SUCCESS.value, rm_result.stdout + rm_result.stderr
    payload = json.loads(rm_result.stdout.strip().splitlines()[-1])
    assert payload["operation"] == "exposure"
    assert payload["snapshot_hash"]


# ----- reset ------------------------------------------------------------


def test_reset_returns_to_baseline(runner: CliRunner, cli_workspace_root: Path) -> None:
    """Apply a primitive, then reset, then get-state should match baseline."""
    runner.invoke(
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
    result = runner.invoke(app, ["--workspace", str(cli_workspace_root), "reset", "test-image"])
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    assert "baseline" in result.stdout.lower()


def test_reset_unknown_image(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(app, ["--workspace", str(cli_workspace_root), "reset", "no-image"])
    assert result.exit_code == ExitCode.NOT_FOUND.value
