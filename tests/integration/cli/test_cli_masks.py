"""Integration tests for ``chemigram masks ...`` (#58).

generate / regenerate are tested at the "no masker configured" surface
(MASKING_ERROR with hint). list / tag / invalidate are full integration
tests against a mask registered directly via the core API.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chemigram.cli.exit_codes import ExitCode
from chemigram.cli.main import app
from chemigram.core.versioning.masks import register_mask


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _register_a_mask(cli_workspace_root: Path, name: str = "current_subject_mask") -> None:
    """Register a real mask in the test workspace's repo via the core API.

    Mirrors what the masking provider would do — gives list/tag/invalidate
    something to operate on without needing a provider.
    """
    from chemigram.core.versioning import ImageRepo

    image_root = cli_workspace_root / "test-image"
    repo = ImageRepo(image_root)
    # Minimal valid PNG (1x1 black)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xfc\xff"
        b"\xff\xff?\x00\x05\xfe\x02\xfeA\xa3\xae\xa6\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    register_mask(repo, name, png_bytes, generator="test", prompt="test")


# ----- masks list -------------------------------------------------------


def test_masks_list_empty_returns_empty(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app, ["--json", "--workspace", str(cli_workspace_root), "masks", "list", "test-image"]
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["count"] == 0
    assert payload["masks"] == []


def test_masks_list_returns_registered_mask(runner: CliRunner, cli_workspace_root: Path) -> None:
    _register_a_mask(cli_workspace_root)
    result = runner.invoke(
        app, ["--json", "--workspace", str(cli_workspace_root), "masks", "list", "test-image"]
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["count"] == 1
    assert payload["masks"][0]["name"] == "current_subject_mask"


def test_masks_list_unknown_image(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app, ["--workspace", str(cli_workspace_root), "masks", "list", "no-image"]
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


# ----- masks generate / regenerate (no masker) --------------------------


def test_masks_generate_no_masker_returns_masking_error(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    """The CLI has no provider wiring; generate must return MASKING_ERROR."""
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "generate",
            "test-image",
            "--target",
            "subject",
        ],
    )
    assert result.exit_code == ExitCode.MASKING_ERROR.value
    assert "no masker configured" in result.stderr.lower()


def test_masks_regenerate_no_masker_returns_masking_error(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "regenerate",
            "test-image",
            "--name",
            "current_subject_mask",
        ],
    )
    assert result.exit_code == ExitCode.MASKING_ERROR.value


# ----- masks tag --------------------------------------------------------


def test_masks_tag_copies_entry(runner: CliRunner, cli_workspace_root: Path) -> None:
    _register_a_mask(cli_workspace_root)
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "tag",
            "test-image",
            "--source",
            "current_subject_mask",
            "--new-name",
            "subject_v1",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["name"] == "subject_v1"


def test_masks_tag_unknown_source_not_found(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "tag",
            "test-image",
            "--source",
            "nope",
            "--new-name",
            "x",
        ],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


def test_masks_tag_empty_new_name_invalid(runner: CliRunner, cli_workspace_root: Path) -> None:
    _register_a_mask(cli_workspace_root)
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "tag",
            "test-image",
            "--source",
            "current_subject_mask",
            "--new-name",
            "  ",
        ],
    )
    assert result.exit_code == ExitCode.INVALID_INPUT.value


# ----- masks invalidate -------------------------------------------------


def test_masks_invalidate_drops_entry(runner: CliRunner, cli_workspace_root: Path) -> None:
    _register_a_mask(cli_workspace_root)
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "invalidate",
            "test-image",
            "--name",
            "current_subject_mask",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    # Subsequent list returns empty
    list_result = runner.invoke(
        app,
        ["--json", "--workspace", str(cli_workspace_root), "masks", "list", "test-image"],
    )
    payload = json.loads(list_result.stdout.strip().splitlines()[-1])
    assert payload["count"] == 0


def test_masks_invalidate_unknown_not_found(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "invalidate",
            "test-image",
            "--name",
            "no_such_mask",
        ],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value
