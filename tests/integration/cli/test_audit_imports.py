"""Test that ``scripts/audit-cli-imports.py`` rejects the right things.

Runs the audit via subprocess (this test file is *testing* the audit
script, so it's allowed to use subprocess). Confirms that:

1. The current adapter tree is clean (exit 0)
2. A planted forbidden import in a temp file is flagged (exit 1)
3. The script is executable

This test is allowlisted in the audit itself (lives outside the
adapter dirs).
"""

from __future__ import annotations

import shutil
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


def test_audit_catches_planted_forbidden_import(tmp_path: Path) -> None:
    """Negative case: copy the repo into tmp_path, plant a forbidden
    ``import subprocess`` in a CLI module, and confirm the audit fails.

    This is the only test that proves the audit actually does its job —
    without it, a regression in the audit script (e.g., the AST walk
    skipping a node type) would leave forbidden imports undetected.
    """
    fake_repo = tmp_path / "repo"
    (fake_repo / "scripts").mkdir(parents=True)
    (fake_repo / "src" / "chemigram" / "cli" / "commands").mkdir(parents=True)
    (fake_repo / "src" / "chemigram" / "mcp").mkdir(parents=True)

    # Copy the audit script into the fake repo (it walks ADAPTER_DIRS
    # relative to its own parent, so it must live in the fake tree).
    shutil.copy(AUDIT, fake_repo / "scripts" / "audit-cli-imports.py")

    # Plant a violation: a CLI commands module with a top-level
    # `import subprocess`. This is exactly what ADR-071 forbids.
    bad_module = fake_repo / "src" / "chemigram" / "cli" / "commands" / "evil.py"
    bad_module.write_text(
        '"""Test fixture: should be flagged by the audit."""\n'
        "from __future__ import annotations\n\n"
        "import subprocess  # forbidden\n\n"
        "_ = subprocess\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, str(fake_repo / "scripts" / "audit-cli-imports.py")],
        capture_output=True,
        text=True,
        cwd=fake_repo,
        check=False,
    )
    assert proc.returncode == 1, (
        "Audit failed to flag a planted `import subprocess` in a CLI module.\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert "evil.py" in proc.stderr
    assert "subprocess" in proc.stderr


def test_audit_catches_planted_xml_import(tmp_path: Path) -> None:
    """Same shape as the subprocess case, for ``xml.*`` imports."""
    fake_repo = tmp_path / "repo"
    (fake_repo / "scripts").mkdir(parents=True)
    (fake_repo / "src" / "chemigram" / "cli").mkdir(parents=True)
    (fake_repo / "src" / "chemigram" / "mcp").mkdir(parents=True)

    shutil.copy(AUDIT, fake_repo / "scripts" / "audit-cli-imports.py")

    bad_module = fake_repo / "src" / "chemigram" / "cli" / "evil.py"
    bad_module.write_text(
        "from __future__ import annotations\nfrom xml.etree import ElementTree as _ET\n\n_ = _ET\n",
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, str(fake_repo / "scripts" / "audit-cli-imports.py")],
        capture_output=True,
        text=True,
        cwd=fake_repo,
        check=False,
    )
    assert proc.returncode == 1
    assert "xml" in proc.stderr
