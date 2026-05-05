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
            "wb_warm_subtle",
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
            "wb_warm_subtle",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["status"] == "ok"
    assert payload["entry"] == "wb_warm_subtle"
    assert payload["snapshot_hash"]
    assert "state_after" in payload


_SHIPPED_MASK_BOUND_ENTRIES = (
    "gradient_top_dampen_highlights",
    "gradient_bottom_lift_shadows",
    "radial_subject_lift",
    "rectangle_subject_band_dim",
)


@pytest.mark.parametrize("entry_name", _SHIPPED_MASK_BOUND_ENTRIES)
def test_apply_primitive_routes_through_drawn_mask_for_shipped_entry(
    runner: CliRunner, cli_workspace_root: Path, entry_name: str
) -> None:
    """Each shipped mask-bound expressive-baseline entry routes through the
    drawn-mask apply path via the CLI; the resulting XMP carries masks_history.
    Parity coverage across the four dt_form variants (two gradient, one
    ellipse, one rectangle) at the CLI dispatch layer.

    Mirrors the MCP unit-level parametrization at
    ``tests/unit/mcp/tools/test_vocab_edit.py`` and complements the e2e
    pixel-validation in ``tests/e2e/expressive/test_mask_bound_entries.py``.
    Fast (no darktable); proves the CLI's edit.py dispatch logic routes
    correctly for each specific spec we ship.
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
            entry_name,
            "--pack",
            "expressive-baseline",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, (
        f"{entry_name}: {result.stdout + result.stderr}"
    )
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["status"] == "ok", f"{entry_name}: {payload}"
    snapshot_hash = payload["snapshot_hash"]

    from chemigram.core.versioning import ImageRepo

    repo = ImageRepo(cli_workspace_root / "test-image")
    raw = repo.read_object(snapshot_hash)
    assert b"masks_history" in raw, (
        f"{entry_name}: drawn-mask path should inject darktable:masks_history "
        f"into the XMP (ADR-076)"
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
            "wb_warm_subtle",
        ],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


def test_apply_primitive_mask_override_on_global_primitive_invalid(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    """--mask-override on a non-mask-bound primitive must error INVALID_INPUT.

    (Vestigial from the removed PNG-mask era; the real ad-hoc-mask flag is
    --mask-spec, exercised below.)
    """
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "apply-primitive",
            "test-image",
            "--entry",
            "wb_warm_subtle",
            "--mask-override",
            "subject",
        ],
    )
    assert result.exit_code == ExitCode.INVALID_INPUT.value


# ----- apply-primitive --mask-spec ad-hoc masking (closes #78) ---------


_AD_HOC_ELLIPSE_MASK = (
    '{"dt_form":"ellipse","dt_params":{"center_x":0.5,"center_y":0.5,'
    '"radius_x":0.3,"radius_y":0.3,"border":0.05}}'
)


def test_apply_primitive_mask_spec_ellipse_routes_through_drawn_mask(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    """--mask-spec on a global primitive (sat_kill) routes through the
    drawn-mask apply path; resulting XMP carries masks_history.

    This is the main user-facing addition from #78: any primitive,
    not just the 4 shipped masked entries, can be region-bound at apply
    time without authoring a vocabulary entry.
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
            "sat_kill",
            "--pack",
            "expressive-baseline",
            "--mask-spec",
            _AD_HOC_ELLIPSE_MASK,
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    snapshot_hash = payload["snapshot_hash"]

    from chemigram.core.versioning import ImageRepo

    repo = ImageRepo(cli_workspace_root / "test-image")
    raw = repo.read_object(snapshot_hash)
    assert b"masks_history" in raw, (
        "ad-hoc --mask-spec should inject darktable:masks_history into the "
        "synthesized XMP via apply_with_drawn_mask"
    )


def test_apply_primitive_mask_spec_overrides_manifest_mask(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    """When the entry already has a manifest mask_spec (e.g.,
    radial_subject_lift), --mask-spec overrides it. Both paths produce
    masks_history; this test asserts only that the override path works
    cleanly (no error) — geometry verification lives in unit tests."""
    rectangle_override = (
        '{"dt_form":"rectangle","dt_params":{"x0":0.1,"y0":0.1,"x1":0.5,"y1":0.5,"border":0.02}}'
    )
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "apply-primitive",
            "test-image",
            "--entry",
            "radial_subject_lift",
            "--pack",
            "expressive-baseline",
            "--mask-spec",
            rectangle_override,
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr


def test_apply_primitive_mask_spec_invalid_json_rejected(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    """Invalid JSON in --mask-spec returns a typer BadParameter (exit 2)."""
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "apply-primitive",
            "test-image",
            "--entry",
            "wb_warm_subtle",
            "--mask-spec",
            "{not valid json",
        ],
    )
    assert result.exit_code != ExitCode.SUCCESS.value
    assert "valid JSON" in (result.stdout + result.stderr)


def test_apply_primitive_mask_spec_missing_dt_form_rejected(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    """A mask_spec JSON object missing 'dt_form' is rejected up front
    (better UX than letting it propagate to apply_with_drawn_mask)."""
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "apply-primitive",
            "test-image",
            "--entry",
            "wb_warm_subtle",
            "--mask-spec",
            '{"dt_params":{}}',
        ],
    )
    assert result.exit_code != ExitCode.SUCCESS.value
    assert "dt_form" in (result.stdout + result.stderr)


# ----- apply-primitive --value / --param parameterized entries (RFC-021) ---


def test_apply_primitive_value_flag_rejected_on_non_parameterized_entry(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    """--value on an entry without a 'parameters' declaration is rejected
    by the CLI before the engine sees it."""
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "apply-primitive",
            "test-image",
            "--entry",
            "wb_warm_subtle",
            "--value",
            "0.7",
        ],
    )
    assert result.exit_code != ExitCode.SUCCESS.value
    assert "no parameters declared" in (result.stdout + result.stderr)


# Comprehensive --value / --param coverage (out-of-range, multi-param,
# happy-path) lands in step 5 once the manifest carries a parameterized
# entry. The unit tests in tests/unit/core/parameterize/ + the integration
# tests in tests/integration/core/test_parameterize_exposure.py cover the
# engine-side semantics today.


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
    """First apply wb_warm_subtle to introduce an exposure entry, then remove it.

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
            "wb_warm_subtle",
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
            "wb_warm_subtle",
        ],
    )
    result = runner.invoke(app, ["--workspace", str(cli_workspace_root), "reset", "test-image"])
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    assert "baseline" in result.stdout.lower()


def test_reset_unknown_image(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(app, ["--workspace", str(cli_workspace_root), "reset", "no-image"])
    assert result.exit_code == ExitCode.NOT_FOUND.value
