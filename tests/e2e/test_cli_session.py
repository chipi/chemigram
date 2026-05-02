"""End-to-end test of a CLI-driven session against real darktable.

Drives ``chemigram ingest → apply-primitive → get-state → render-preview
→ export-final`` via subprocess (matching the real agent-loop pattern).
Skips cleanly when prereqs are missing per ADR-040.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    return tmp_path / "ws"


def _run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run the chemigram CLI as a subprocess (matches PRD-005's agent-loop pattern)."""
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "chemigram.cli.main", *args],
        capture_output=True,
        text=True,
        env=full_env,
        check=False,
    )


def test_cli_session_ingest_apply_get_state(test_raw: Path, workspace_root: Path) -> None:
    """A real subprocess-driven mini session: ingest → apply → get-state.

    Mirrors the agent-loop pattern from PRD-005 — subprocess + NDJSON,
    no MCP. Validates that:

    1. ``chemigram ingest`` creates the workspace from a real raw
    2. ``chemigram apply-primitive`` advances HEAD to a new snapshot
    3. ``chemigram get-state`` reflects the post-apply state
    4. NDJSON event shapes match the documented schema
    """
    # 1. ingest
    ingest = _run_cli(
        "--json",
        "--workspace",
        str(workspace_root),
        "ingest",
        str(test_raw),
        "--image-id",
        "session-test",
    )
    assert ingest.returncode == 0, f"ingest failed:\nstdout={ingest.stdout}\nstderr={ingest.stderr}"
    ingest_payload = json.loads(ingest.stdout.strip().splitlines()[-1])
    assert ingest_payload["status"] == "ok"
    assert ingest_payload["image_id"] == "session-test"

    # 2. apply-primitive
    apply_proc = _run_cli(
        "--json",
        "--workspace",
        str(workspace_root),
        "apply-primitive",
        "session-test",
        "--entry",
        "expo_+0.5",
    )
    assert apply_proc.returncode == 0, (
        f"apply-primitive failed:\nstdout={apply_proc.stdout}\nstderr={apply_proc.stderr}"
    )
    apply_payload = json.loads(apply_proc.stdout.strip().splitlines()[-1])
    assert apply_payload["status"] == "ok"
    apply_hash = apply_payload["snapshot_hash"]
    assert apply_hash, "snapshot_hash should be a non-empty content hash"

    # 3. get-state
    state = _run_cli(
        "--json",
        "--workspace",
        str(workspace_root),
        "get-state",
        "session-test",
    )
    assert state.returncode == 0
    state_payload = json.loads(state.stdout.strip().splitlines()[-1])
    assert state_payload["status"] == "ok"
    # The state's head_hash should match the post-apply snapshot hash
    assert state_payload["head_hash"] == apply_hash

    # 4. reset, then get-state should land on a different (baseline) hash
    reset_proc = _run_cli(
        "--workspace",
        str(workspace_root),
        "reset",
        "session-test",
    )
    assert reset_proc.returncode == 0

    state_after_reset = _run_cli(
        "--json",
        "--workspace",
        str(workspace_root),
        "get-state",
        "session-test",
    )
    state_reset_payload = json.loads(state_after_reset.stdout.strip().splitlines()[-1])
    assert state_reset_payload["head_hash"] != apply_hash


def test_cli_session_render_and_export(
    test_raw: Path, configdir: Path, workspace_root: Path
) -> None:
    """Real subprocess pipeline through render-preview + export-final.

    Uses the Phase 0 raw + bootstrapped configdir. Asserts on the output
    JPEG bytes existing on disk (direction-of-change pixel assertions
    live in the e2e expressive/ tests; this test only verifies the CLI
    actually drove darktable end-to-end).
    """
    env = {"CHEMIGRAM_DT_CONFIGDIR": str(configdir)}
    image_id = "render-test"

    ingest = _run_cli(
        "--workspace",
        str(workspace_root),
        "ingest",
        str(test_raw),
        "--image-id",
        image_id,
        env=env,
    )
    assert ingest.returncode == 0, f"ingest failed:\n{ingest.stderr}"

    # Apply a small move so render reflects the workspace state, not just baseline.
    apply_proc = _run_cli(
        "--workspace",
        str(workspace_root),
        "apply-primitive",
        image_id,
        "--entry",
        "expo_+0.5",
        env=env,
    )
    assert apply_proc.returncode == 0, f"apply failed:\n{apply_proc.stderr}"

    # render-preview
    render_proc = _run_cli(
        "--json",
        "--workspace",
        str(workspace_root),
        "render-preview",
        image_id,
        "--size",
        "512",
        env=env,
    )
    assert render_proc.returncode == 0, (
        f"render-preview failed:\nstdout={render_proc.stdout}\nstderr={render_proc.stderr}"
    )
    render_payload = json.loads(render_proc.stdout.strip().splitlines()[-1])
    preview_path = Path(render_payload["jpeg_path"])
    assert preview_path.is_file()
    assert preview_path.stat().st_size > 0

    # export-final
    export_proc = _run_cli(
        "--json",
        "--workspace",
        str(workspace_root),
        "export-final",
        image_id,
        "--format",
        "jpeg",
        "--size",
        "512",
        env=env,
    )
    assert export_proc.returncode == 0, (
        f"export-final failed:\nstdout={export_proc.stdout}\nstderr={export_proc.stderr}"
    )
    export_payload = json.loads(export_proc.stdout.strip().splitlines()[-1])
    out = Path(export_payload["output_path"])
    assert out.is_file()
    assert out.stat().st_size > 0
    assert export_payload["format"] == "jpeg"


def test_cli_session_compare(test_raw: Path, configdir: Path, workspace_root: Path) -> None:
    """Real subprocess pipeline through `compare` against two snapshots.

    Captures baseline hash, applies a primitive, captures the post-apply
    hash, then compares the two via `chemigram compare` and asserts the
    stitched output JPEG was written.
    """
    env = {"CHEMIGRAM_DT_CONFIGDIR": str(configdir)}
    image_id = "compare-test"

    ingest = _run_cli(
        "--workspace",
        str(workspace_root),
        "ingest",
        str(test_raw),
        "--image-id",
        image_id,
        env=env,
    )
    assert ingest.returncode == 0, f"ingest:\n{ingest.stderr}"

    state_before = _run_cli(
        "--json",
        "--workspace",
        str(workspace_root),
        "get-state",
        image_id,
        env=env,
    )
    assert state_before.returncode == 0
    baseline_hash = json.loads(state_before.stdout.strip().splitlines()[-1])["head_hash"]

    apply_proc = _run_cli(
        "--workspace",
        str(workspace_root),
        "apply-primitive",
        image_id,
        "--entry",
        "expo_+0.5",
        env=env,
    )
    assert apply_proc.returncode == 0

    state_after = _run_cli(
        "--json",
        "--workspace",
        str(workspace_root),
        "get-state",
        image_id,
        env=env,
    )
    after_hash = json.loads(state_after.stdout.strip().splitlines()[-1])["head_hash"]
    assert baseline_hash != after_hash

    compare_proc = _run_cli(
        "--json",
        "--workspace",
        str(workspace_root),
        "compare",
        image_id,
        baseline_hash,
        after_hash,
        "--size",
        "512",
        env=env,
    )
    assert compare_proc.returncode == 0, (
        f"compare failed:\nstdout={compare_proc.stdout}\nstderr={compare_proc.stderr}"
    )
    payload = json.loads(compare_proc.stdout.strip().splitlines()[-1])
    out = Path(payload["jpeg_path"])
    assert out.is_file()
    assert out.stat().st_size > 0


def test_cli_status_runs_as_subprocess() -> None:
    """``chemigram status`` always exits 0 — it's a diagnostic that reports
    missing components in fields/warnings rather than failing on them.
    Proves the entry point works post-install (the integration-level
    ``CliRunner`` test doesn't catch entry-point regressions).
    """
    proc = _run_cli("status")
    assert proc.returncode == 0, (
        f"status returned unexpected code {proc.returncode}\n"
        f"stdout={proc.stdout}\nstderr={proc.stderr}"
    )
