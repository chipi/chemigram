"""End-to-end test of a CLI-driven session against real darktable.

Drives ``chemigram ingest → apply-primitive → get-state`` via subprocess
(matching the real agent-loop pattern). Skips cleanly when prereqs are
missing per ADR-040.

The render path lives in #57 (a separate verb group); when that lands,
this test extends with ``render-preview`` + a luma direction-of-change
assertion.
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


def test_cli_status_runs_as_subprocess() -> None:
    """``chemigram status`` exits 0 in a real subprocess (proves the entry point
    works post-install — the integration-level ``CliRunner`` test doesn't
    catch entry-point regressions).
    """
    proc = _run_cli("status")
    # Exit 0 if darktable-cli is available; exit 6 if not (DARKTABLE_ERROR).
    # Both are valid here — we're testing the entry point, not the
    # darktable presence.
    assert proc.returncode in (0, 6), (
        f"status returned unexpected code {proc.returncode}\n"
        f"stdout={proc.stdout}\nstderr={proc.stderr}"
    )
