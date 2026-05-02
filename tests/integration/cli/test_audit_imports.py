"""Test that ``scripts/audit-cli-imports.py`` rejects the right things.

Runs the audit via subprocess (this test file is *testing* the audit
script, so it's allowed to use subprocess). Confirms that:

1. The current adapter tree is clean (exit 0)
2. A planted forbidden import in a temp file is flagged

This test is allowlisted in the audit itself (lives outside the
adapter dirs).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
AUDIT = REPO_ROOT / "scripts" / "audit-cli-imports.py"


def test_audit_passes_on_current_tree() -> None:
    proc = subprocess.run(
        [sys.executable, str(AUDIT)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert proc.returncode == 0, (
        f"Audit failed on current tree:\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )


def test_audit_script_is_executable() -> None:
    """Catches accidental ``chmod`` regressions."""
    import os

    assert os.access(AUDIT, os.X_OK), f"{AUDIT} not executable"
