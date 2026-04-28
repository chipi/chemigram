"""Integration tests for DarktableCliStage.

These tests invoke real ``darktable-cli`` and require:

- ``darktable-cli`` on PATH (or ``$DARKTABLE_CLI`` set)
- a pre-bootstrapped darktable configdir (Phase 0's
  ``~/chemigram-phase0/dt-config`` is the default; override with
  ``$CHEMIGRAM_DT_CONFIGDIR``)
- the test raw at ``~/chemigram-phase0/raws/raw-test.NEF`` (override
  with ``$CHEMIGRAM_TEST_RAW``)

Tests skip cleanly when any of the three is missing.
"""

from __future__ import annotations

import os
import shutil
import threading
from pathlib import Path

import pytest

from chemigram.core.pipeline import StageContext
from chemigram.core.stages.darktable_cli import DarktableCliStage

_FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures"
_DEFAULT_CONFIGDIR = Path.home() / "chemigram-phase0" / "dt-config"
_DEFAULT_RAW = Path.home() / "chemigram-phase0" / "raws" / "raw-test.NEF"


def _darktable_available() -> bool:
    if "DARKTABLE_CLI" in os.environ:
        return True
    return shutil.which("darktable-cli") is not None


def _resolve_configdir() -> Path | None:
    env = os.environ.get("CHEMIGRAM_DT_CONFIGDIR")
    if env:
        path = Path(env).expanduser()
        return path if path.exists() else None
    return _DEFAULT_CONFIGDIR if _DEFAULT_CONFIGDIR.exists() else None


def _resolve_raw() -> Path | None:
    env = os.environ.get("CHEMIGRAM_TEST_RAW")
    if env:
        path = Path(env).expanduser()
        return path if path.exists() else None
    return _DEFAULT_RAW if _DEFAULT_RAW.exists() else None


@pytest.fixture(scope="module")
def darktable_binary() -> str:
    if not _darktable_available():
        pytest.skip("darktable-cli not on PATH and DARKTABLE_CLI env var not set")
    return os.environ.get("DARKTABLE_CLI", "darktable-cli")


@pytest.fixture(scope="module")
def configdir() -> Path:
    cd = _resolve_configdir()
    if cd is None:
        pytest.skip(
            "no usable darktable configdir "
            f"($CHEMIGRAM_DT_CONFIGDIR unset and {_DEFAULT_CONFIGDIR} absent)"
        )
    return cd


@pytest.fixture(scope="module")
def test_raw() -> Path:
    raw = _resolve_raw()
    if raw is None:
        pytest.skip(f"no usable test raw ($CHEMIGRAM_TEST_RAW unset and {_DEFAULT_RAW} absent)")
    return raw


@pytest.fixture(scope="module")
def reference_xmp() -> Path:
    return _FIXTURES / "xmps" / "synthesized_v3_reference.xmp"


def _ctx(
    raw: Path,
    xmp: Path,
    out: Path,
    configdir: Path,
    *,
    width: int = 256,
    height: int = 256,
) -> StageContext:
    return StageContext(
        raw_path=raw,
        xmp_path=xmp,
        output_path=out,
        configdir=configdir,
        width=width,
        height=height,
        high_quality=False,
    )


def test_render_v3_reference(
    darktable_binary: str,
    configdir: Path,
    test_raw: Path,
    reference_xmp: Path,
    tmp_path: Path,
) -> None:
    out = tmp_path / "out.jpg"
    stage = DarktableCliStage(binary=darktable_binary)
    result = stage.run(_ctx(test_raw, reference_xmp, out, configdir))

    assert result.success, f"render failed: {result.error_message}\n{result.stderr}"
    assert out.is_file()
    assert out.stat().st_size > 0
    assert result.duration_seconds > 0


def test_render_failure_captures_stderr(
    darktable_binary: str,
    configdir: Path,
    test_raw: Path,
    tmp_path: Path,
) -> None:
    bogus_xmp = tmp_path / "does_not_exist.xmp"
    out = tmp_path / "out.jpg"
    stage = DarktableCliStage(binary=darktable_binary)
    result = stage.run(_ctx(test_raw, bogus_xmp, out, configdir))

    assert result.success is False
    assert result.error_message is not None


def test_render_timeout(
    darktable_binary: str,
    configdir: Path,
    test_raw: Path,
    reference_xmp: Path,
    tmp_path: Path,
) -> None:
    out = tmp_path / "out.jpg"
    stage = DarktableCliStage(binary=darktable_binary, timeout_seconds=0.001)
    result = stage.run(_ctx(test_raw, reference_xmp, out, configdir))

    assert result.success is False
    assert result.error_message is not None
    assert "timed out" in result.error_message


def test_concurrent_renders_serialize(
    darktable_binary: str,
    configdir: Path,
    test_raw: Path,
    reference_xmp: Path,
    tmp_path: Path,
) -> None:
    """Per ADR-005, a single configdir serializes its renders.

    The lock is per-configdir at class level; two stage instances
    sharing a configdir must serialize. We start two threads and
    verify wall-clock >= 1.5x a single render's duration (with a
    margin for noise).
    """
    out_solo = tmp_path / "solo.jpg"
    stage = DarktableCliStage(binary=darktable_binary)
    solo = stage.run(_ctx(test_raw, reference_xmp, out_solo, configdir))
    assert solo.success
    solo_duration = solo.duration_seconds

    out_a = tmp_path / "a.jpg"
    out_b = tmp_path / "b.jpg"
    results: list[float] = []
    barrier = threading.Barrier(2)

    def _run(ctx: StageContext) -> None:
        barrier.wait()
        local_stage = DarktableCliStage(binary=darktable_binary)
        result = local_stage.run(ctx)
        assert result.success
        results.append(result.duration_seconds)

    threads = [
        threading.Thread(
            target=_run,
            args=(_ctx(test_raw, reference_xmp, out_a, configdir),),
        ),
        threading.Thread(
            target=_run,
            args=(_ctx(test_raw, reference_xmp, out_b, configdir),),
        ),
    ]
    import time

    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total = time.monotonic() - start

    # Two serialized renders should take roughly 2x a single render.
    # Allow generous slack (1.5x) for warm-cache effects on render #2.
    assert total >= solo_duration * 1.5, (
        f"expected serialized renders to take ≥{solo_duration * 1.5:.2f}s, "
        f"got {total:.2f}s (solo={solo_duration:.2f}s)"
    )
    assert out_a.is_file() and out_b.is_file()
