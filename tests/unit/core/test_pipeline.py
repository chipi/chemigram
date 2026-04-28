"""Unit tests for chemigram.core.pipeline + DarktableCliStage construction.

These tests use a fake stage and don't invoke darktable. The integration
tier (tests/integration/core/test_darktable_cli.py) covers real subprocess.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chemigram.core.pipeline import (
    Pipeline,
    StageContext,
    StageResult,
)
from chemigram.core.stages.darktable_cli import DarktableCliStage


class _FakeStage:
    """Test double for PipelineStage."""

    def __init__(self, result: StageResult) -> None:
        self.result = result
        self.calls: list[StageContext] = []

    def run(self, context: StageContext) -> StageResult:
        self.calls.append(context)
        return self.result


def _make_context(tmp_path: Path) -> StageContext:
    return StageContext(
        raw_path=tmp_path / "raw.nef",
        xmp_path=tmp_path / "raw.xmp",
        output_path=tmp_path / "out.jpg",
        configdir=tmp_path / "configdir",
    )


def _success_result(tmp_path: Path) -> StageResult:
    return StageResult(
        success=True,
        output_path=tmp_path / "out.jpg",
        duration_seconds=0.0,
        stderr="",
    )


def test_pipeline_runs_single_stage(tmp_path: Path) -> None:
    fake = _FakeStage(_success_result(tmp_path))
    pipeline = Pipeline([fake])
    ctx = _make_context(tmp_path)
    result = pipeline.run(ctx)
    assert result is fake.result
    assert fake.calls == [ctx]


def test_pipeline_empty_stages_raises() -> None:
    with pytest.raises(ValueError, match="at least one stage"):
        Pipeline([])


def test_pipeline_short_circuits_on_failure(tmp_path: Path) -> None:
    """When a stage returns success=False, pipeline stops and returns it."""
    failing = _FakeStage(
        StageResult(
            success=False,
            output_path=tmp_path / "out.jpg",
            duration_seconds=0.0,
            stderr="boom",
            error_message="stage failed",
        )
    )
    later = _FakeStage(_success_result(tmp_path))
    pipeline = Pipeline([failing, later])
    ctx = _make_context(tmp_path)
    result = pipeline.run(ctx)
    assert result.success is False
    assert later.calls == []  # never reached


def test_stage_constructor_default_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DARKTABLE_CLI", raising=False)
    stage = DarktableCliStage()
    assert stage.binary == "darktable-cli"


def test_stage_reads_darktable_cli_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DARKTABLE_CLI", "/custom/path/darktable-cli")
    stage = DarktableCliStage()
    assert stage.binary == "/custom/path/darktable-cli"


def test_stage_explicit_binary_overrides_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DARKTABLE_CLI", "/from/env")
    stage = DarktableCliStage(binary="/from/argument")
    assert stage.binary == "/from/argument"


def test_stage_default_timeout() -> None:
    stage = DarktableCliStage()
    assert stage.timeout_seconds == DarktableCliStage.DEFAULT_TIMEOUT_SECONDS


def test_stage_custom_timeout() -> None:
    stage = DarktableCliStage(timeout_seconds=5.0)
    assert stage.timeout_seconds == 5.0


def test_invocation_form_locked(tmp_path: Path) -> None:
    """The argv shape is fixed per CLAUDE.md; verify it without spawning."""
    stage = DarktableCliStage(binary="/fake/darktable-cli")
    ctx = StageContext(
        raw_path=Path("/r.nef"),
        xmp_path=Path("/r.xmp"),
        output_path=Path("/o.jpg"),
        configdir=Path("/cfg"),
        width=512,
        height=512,
        high_quality=True,
    )
    argv = stage._build_argv(ctx)
    assert argv == [
        "/fake/darktable-cli",
        "/r.nef",
        "/r.xmp",
        "/o.jpg",
        "--width",
        "512",
        "--height",
        "512",
        "--hq",
        "true",
        "--apply-custom-presets",
        "false",
        "--core",
        "--configdir",
        "/cfg",
    ]


def test_invocation_form_hq_false_by_default(tmp_path: Path) -> None:
    stage = DarktableCliStage(binary="dt")
    ctx = _make_context(tmp_path)
    argv = stage._build_argv(ctx)
    assert "--hq" in argv
    assert argv[argv.index("--hq") + 1] == "false"
    assert "--apply-custom-presets" in argv
    assert argv[argv.index("--apply-custom-presets") + 1] == "false"


def test_lock_for_configdir_returns_same_lock(tmp_path: Path) -> None:
    """Same configdir → same lock instance (per ADR-005 serialization)."""
    a = DarktableCliStage._lock_for_configdir(tmp_path)
    b = DarktableCliStage._lock_for_configdir(tmp_path)
    assert a is b


def test_lock_for_configdir_different_dirs_different_locks(
    tmp_path: Path,
) -> None:
    a = DarktableCliStage._lock_for_configdir(tmp_path / "a")
    (tmp_path / "a").mkdir()
    b = DarktableCliStage._lock_for_configdir(tmp_path / "b")
    (tmp_path / "b").mkdir()
    assert a is not b


def test_render_uses_default_tempdir_when_no_configdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """render() with configdir=None creates a tempdir and runs the pipeline."""
    from chemigram.core import pipeline as pipeline_module

    captured: dict[str, StageContext] = {}

    class _CaptureStage:
        def run(self, context: StageContext) -> StageResult:
            captured["ctx"] = context
            return StageResult(
                success=True,
                output_path=context.output_path,
                duration_seconds=0.0,
                stderr="",
            )

    monkeypatch.setattr(
        "chemigram.core.stages.darktable_cli.DarktableCliStage",
        lambda *a, **kw: _CaptureStage(),
    )

    result = pipeline_module.render(
        raw_path=tmp_path / "r.nef",
        xmp_path=tmp_path / "r.xmp",
        output_path=tmp_path / "o.jpg",
    )
    assert result.success
    assert captured["ctx"].configdir is not None
    assert captured["ctx"].configdir.exists()
    assert captured["ctx"].configdir.is_dir()
