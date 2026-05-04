#!/usr/bin/env python3
"""Example agent loop driving Chemigram via the CLI.

Demonstrates the *programmatic* shape of CLI use, distinct from the
conversational MCP-session shape:

    - subprocess invocation with structured exit codes
    - NDJSON stream parsing on stdout
    - terminal-error event parsing on stderr
    - branching on exit code (recoverable vs. halt)
    - composing multiple verbs into one cohesive operation

Use this as a starting point for LangGraph pipelines, custom
Claude Code scripts, watch-folder daemons, CI/CD integrations,
or any context where the MCP session model is the wrong shape.

Run: ``python examples/cli-agent-loop.py /path/to/photo.NEF``
Requires: ``chemigram`` on PATH; ``CHEMIGRAM_DT_CONFIGDIR`` set if you
want renders to work.

Documentation:
    docs/guides/cli-output-schema.md  — NDJSON event format reference
    docs/guides/cli-reference.md      — every verb's flags
    docs/guides/cli-env-vars.md       — env var reference
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Exit codes that are typically recoverable in an agent loop.
# Codes 1/4/5/6/8/9/10 are halt-worthy (bug, env, infra issues).
_RECOVERABLE_EXIT_CODES = {2, 3, 7}  # INVALID_INPUT, NOT_FOUND, MASKING_ERROR


class CliResult:
    """Result of one ``chemigram --json <verb>`` invocation."""

    def __init__(
        self,
        *,
        ok: bool,
        exit_code: int,
        events: list[dict[str, Any]],
        result: dict[str, Any] | None,
        error: dict[str, Any] | None,
    ) -> None:
        self.ok = ok
        self.exit_code = exit_code
        self.events = events  # all stdout lines as parsed dicts (may include intermediate events)
        self.result = result  # the final ``event=result`` line on success, else None
        self.error = error  # the final ``event=error`` line on failure, else None

    def __repr__(self) -> str:
        if self.ok:
            return f"<CliResult ok={self.exit_code} {self.result!r}>"
        return f"<CliResult fail={self.exit_code} {self.error!r}>"


def call_chemigram(*args: str) -> CliResult:
    """Run ``chemigram --json <args>``; parse the NDJSON streams.

    Always emits ``--json`` so the output is machine-readable. The
    last stdout line is the ``result`` event on success; the last
    stderr line is the ``error`` event on failure.
    """
    # The example assumes chemigram is on $PATH (typical user setup).
    # Production agent-loops that want hardened invocation should resolve
    # via shutil.which("chemigram") and pass the absolute path.
    proc = subprocess.run(
        ["chemigram", "--json", *args],  # noqa: S607 — example: rely on $PATH
        capture_output=True,
        text=True,
        check=False,  # we handle exit codes explicitly
    )

    events: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            # Best effort: skip lines that aren't NDJSON (shouldn't happen
            # with --json, but defensive).
            continue

    result_event: dict[str, Any] | None = None
    if events and events[-1].get("event") == "result":
        result_event = events[-1]

    error_event: dict[str, Any] | None = None
    if proc.stderr:
        # stderr's last NDJSON line is the error event when --json mode + a
        # terminal failure. Earlier lines are unlikely (stderr is reserved
        # for terminal events) but parse defensively.
        for line in proc.stderr.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                error_event = json.loads(line)
            except json.JSONDecodeError:
                continue

    return CliResult(
        ok=(proc.returncode == 0),
        exit_code=proc.returncode,
        events=events,
        result=result_event,
        error=error_event,
    )


def edit_one_photo(raw_path: Path) -> int:
    """Drive Chemigram through a small edit on one raw.

    Demonstrates: ingest → apply two primitives → snapshot → render.
    Returns the final exit code (0 on success).
    """
    # 1) Ingest. The image_id derives from the raw's stem.
    print(f"[1/4] Ingesting {raw_path.name}…", file=sys.stderr)
    r = call_chemigram("ingest", str(raw_path))
    if not r.ok:
        return _handle_failure("ingest", r)

    image_id: str = r.result["image_id"]
    print(f"      → image_id={image_id}", file=sys.stderr)

    # 2) Apply a global exposure lift. expo_+0.3 is in expressive-baseline.
    print("[2/4] Applying expo_+0.3 (warmth nudge)…", file=sys.stderr)
    r = call_chemigram(
        "apply-primitive",
        image_id,
        "--entry",
        "expo_+0.3",
        "--pack",
        "starter",
        "--pack",
        "expressive-baseline",
    )
    if not r.ok:
        return _handle_failure("apply expo_+0.3", r)

    # 3) Apply a drawn-mask gradient (top dampen). One of the four shipped
    #    mask-bound entries; routes through apply_with_drawn_mask per ADR-076.
    print("[3/4] Applying gradient_top_dampen_highlights (mask-bound)…", file=sys.stderr)
    r = call_chemigram(
        "apply-primitive",
        image_id,
        "--entry",
        "gradient_top_dampen_highlights",
        "--pack",
        "expressive-baseline",
    )
    if not r.ok:
        # Mask-bound apply can fail with MASKING_ERROR (7) on malformed
        # mask_spec — which would be a vocabulary bug, not a runtime issue.
        return _handle_failure("apply mask-bound gradient", r)

    # 4) Render a preview. Requires CHEMIGRAM_DT_CONFIGDIR.
    print("[4/4] Rendering preview…", file=sys.stderr)
    r = call_chemigram("render-preview", image_id, "--size", "1024")
    if not r.ok:
        if r.exit_code == 6:  # DARKTABLE_ERROR
            print(
                "      → render failed (DARKTABLE_ERROR): is CHEMIGRAM_DT_CONFIGDIR "
                "set and pointing at a bootstrapped configdir?",
                file=sys.stderr,
            )
        return _handle_failure("render-preview", r)

    print("\nDone.", file=sys.stderr)
    print(f"Final state hash: {r.result['head_hash']}", file=sys.stderr)
    print(f"Preview JPEG:     {r.result.get('jpeg_path')}", file=sys.stderr)
    return 0


def _handle_failure(label: str, r: CliResult) -> int:
    """Print a structured error and return the exit code.

    A real agent loop would branch on ``r.error['exit_code']`` and either
    correct + retry (recoverable codes) or escalate (others). This example
    just reports.
    """
    err = r.error or {}
    code = err.get("exit_code", r.exit_code)
    name = err.get("exit_code_name", "UNKNOWN")
    msg = err.get("message", "(no message)")
    recoverable = code in _RECOVERABLE_EXIT_CODES
    tag = "recoverable" if recoverable else "halt"
    print(f"\n✗ {label} failed: {name} [{code}, {tag}]", file=sys.stderr)
    print(f"  {msg}", file=sys.stderr)
    return r.exit_code


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: cli-agent-loop.py <raw_path>", file=sys.stderr)
        return 2
    raw = Path(argv[1])
    if not raw.exists():
        print(f"raw not found: {raw}", file=sys.stderr)
        return 3
    return edit_one_photo(raw)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
