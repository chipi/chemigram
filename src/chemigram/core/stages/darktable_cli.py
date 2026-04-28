"""DarktableCliStage: invokes ``darktable-cli`` to render raw + XMP into JPEG.

Per ADR-005, only one ``darktable-cli`` runs per configdir at a time;
darktable holds an exclusive lock on ``library.db`` inside the
configdir. This stage uses a class-level lock dict keyed by configdir
to enforce single-process serialization. Cross-process coordination is
out of scope — a caller bug if violated.

Per CLAUDE.md "darktable-cli invocation form", every invocation uses::

    darktable-cli <raw> <xmp> <output> \\
      --width N --height N --hq <bool> \\
      --apply-custom-presets false \\
      --core --configdir <isolated>

**Binary path resolution:**

1. Explicit ``binary=`` constructor argument (highest precedence)
2. ``$DARKTABLE_CLI`` environment variable
3. ``"darktable-cli"`` resolved via ``$PATH``

The env-var override exists for the macOS .app-bundle install case:
``/Applications/darktable.app/Contents/MacOS/darktable-cli`` cannot be
naively symlinked onto PATH because macOS resolves bundle resources
from the binary's invocation path. Either install a thin exec wrapper
on PATH or set ``DARKTABLE_CLI`` to the absolute path.
"""

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import ClassVar

from chemigram.core.pipeline import StageContext, StageResult


class DarktableCliStage:
    """v1's only render stage: invoke ``darktable-cli``."""

    DEFAULT_TIMEOUT_SECONDS: ClassVar[float] = 60.0

    # Per-configdir locks; the dict is process-local. Resolved-path keys.
    _configdir_locks: ClassVar[dict[Path, threading.Lock]] = {}
    _locks_dict_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(
        self,
        binary: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.binary = binary or os.environ.get("DARKTABLE_CLI") or "darktable-cli"
        self.timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else self.DEFAULT_TIMEOUT_SECONDS
        )

    @classmethod
    def _lock_for_configdir(cls, configdir: Path) -> threading.Lock:
        key = configdir.resolve()
        with cls._locks_dict_lock:
            lock = cls._configdir_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                cls._configdir_locks[key] = lock
            return lock

    def _build_argv(self, context: StageContext) -> list[str]:
        return [
            self.binary,
            str(context.raw_path),
            str(context.xmp_path),
            str(context.output_path),
            "--width",
            str(context.width),
            "--height",
            str(context.height),
            "--hq",
            "true" if context.high_quality else "false",
            "--apply-custom-presets",
            "false",
            "--core",
            "--configdir",
            str(context.configdir),
        ]

    def run(self, context: StageContext) -> StageResult:
        """Invoke ``darktable-cli`` per the canonical CLAUDE.md form.

        Returns a :class:`StageResult` capturing success, the output
        path, wall-clock duration, and stderr (always; useful on
        failure for diagnosis).
        """
        lock = self._lock_for_configdir(context.configdir)
        with lock:
            return self._run_locked(context)

    def _run_locked(self, context: StageContext) -> StageResult:
        argv = self._build_argv(context)
        start = time.monotonic()

        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                errors="replace",
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - start
            stderr = self._coerce_str(exc.stderr)
            return StageResult(
                success=False,
                output_path=context.output_path,
                duration_seconds=duration,
                stderr=stderr,
                error_message=f"render timed out after {self.timeout_seconds}s",
            )
        except FileNotFoundError as exc:
            duration = time.monotonic() - start
            return StageResult(
                success=False,
                output_path=context.output_path,
                duration_seconds=duration,
                stderr="",
                error_message=f"darktable-cli binary not found: {exc}",
            )

        duration = time.monotonic() - start

        if completed.returncode != 0:
            return StageResult(
                success=False,
                output_path=context.output_path,
                duration_seconds=duration,
                stderr=completed.stderr or "",
                error_message=f"darktable-cli exited with code {completed.returncode}",
            )

        if not context.output_path.exists() or context.output_path.stat().st_size == 0:
            return StageResult(
                success=False,
                output_path=context.output_path,
                duration_seconds=duration,
                stderr=completed.stderr or "",
                error_message="output file not produced (or empty)",
            )

        return StageResult(
            success=True,
            output_path=context.output_path,
            duration_seconds=duration,
            stderr=completed.stderr or "",
            error_message=None,
        )

    @staticmethod
    def _coerce_str(value: bytes | str | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value
