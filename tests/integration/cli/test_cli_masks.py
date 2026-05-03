"""Integration tests for ``chemigram masks ...`` (#58, #73).

list / tag / invalidate are full integration tests against a mask
registered directly via the core API. generate / regenerate cover both
the v1.3.0 "no provider" MASKING_ERROR surface and the v1.4.0
``--provider {gradient|radial|rectangle}`` flow (ADR-074); the preview
render is monkey-patched away so darktable doesn't have to run for the
CLI plumbing tests.
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


# ----- masks generate / regenerate (built-in provider — ADR-074) --------


@pytest.fixture
def stub_preview(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Skip the darktable render in ``ensure_preview_render`` and return a
    real JPEG of known size that the geometric provider can read."""
    from PIL import Image

    preview_path = tmp_path / "preview_for_masking.jpg"
    Image.new("RGB", (256, 128), (180, 180, 180)).save(preview_path, "JPEG")

    def _fake_ensure(_workspace: object) -> Path:
        return preview_path

    # Patch where the symbol is *looked up*, not where it's defined.
    monkeypatch.setattr("chemigram.cli.commands.masks.ensure_preview_render", _fake_ensure)
    return preview_path


def test_masks_generate_with_gradient_provider_registers_mask(
    runner: CliRunner, cli_workspace_root: Path, stub_preview: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "generate",
            "test-image",
            "--target",
            "sky",
            "--provider",
            "gradient",
            "--config",
            '{"angle_degrees": 90, "peak": 1.0}',
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["name"] == "current_sky_mask"
    assert payload["generator"] == "gradient"


def test_masks_generate_with_radial_provider_default_config(
    runner: CliRunner, cli_workspace_root: Path, stub_preview: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "generate",
            "test-image",
            "--target",
            "subject",
            "--provider",
            "radial",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["generator"] == "radial"


def test_masks_generate_with_rectangle_provider(
    runner: CliRunner, cli_workspace_root: Path, stub_preview: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "generate",
            "test-image",
            "--target",
            "lower-third",
            "--provider",
            "rectangle",
            "--config",
            '{"x0": 0.0, "y0": 0.66, "x1": 1.0, "y1": 1.0, "feather": 0.05}',
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["generator"] == "rectangle"


def test_masks_generate_unknown_provider_returns_masking_error(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "generate",
            "test-image",
            "--target",
            "x",
            "--provider",
            "wat",
        ],
    )
    assert result.exit_code == ExitCode.MASKING_ERROR.value
    assert "unknown provider" in result.stderr.lower()


def test_masks_generate_invalid_config_json_returns_masking_error(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "generate",
            "test-image",
            "--target",
            "x",
            "--provider",
            "gradient",
            "--config",
            "{not json",
        ],
    )
    assert result.exit_code == ExitCode.MASKING_ERROR.value


def test_masks_generate_provider_validation_error_returns_masking_error(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    """Out-of-range provider params should surface as MASKING_ERROR, not
    a stack trace (geometric providers raise MaskGenerationError)."""
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "generate",
            "test-image",
            "--target",
            "x",
            "--provider",
            "gradient",
            "--config",
            '{"peak": 5.0}',
        ],
    )
    assert result.exit_code == ExitCode.MASKING_ERROR.value


def test_masks_regenerate_with_provider_overwrites_registered_mask(
    runner: CliRunner, cli_workspace_root: Path, stub_preview: Path
) -> None:
    _register_a_mask(cli_workspace_root, name="current_sky_mask")
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "masks",
            "regenerate",
            "test-image",
            "--name",
            "current_sky_mask",
            "--provider",
            "gradient",
            "--config",
            '{"angle_degrees": 270}',
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["generator"] == "gradient"


def test_masks_regenerate_unknown_mask_returns_not_found(
    runner: CliRunner, cli_workspace_root: Path, stub_preview: Path
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
            "ghost",
            "--provider",
            "gradient",
        ],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


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
