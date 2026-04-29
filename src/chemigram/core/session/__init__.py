"""Session transcript writer per ADR-029.

Each Mode A session writes a JSONL transcript to
``<workspace>/sessions/<session_id>.jsonl``. The format:

- **Header line** (first line): session metadata.
- **Per-turn entries**: ``{kind: "tool_call" | "tool_result" |
  "proposal" | "confirmation" | "note", timestamp, ...kind-specific-fields}``.
- **Footer line** (on :meth:`SessionTranscript.close`): summary stats.

Append-only; no buffering — a crashed session loses ≤1 entry. Entries
that fail to serialize (rare) are caught and replaced with a
``write_failure`` marker line so the rest of the transcript stays intact.

Public API:
    - :func:`start_session` — factory
    - :class:`SessionTranscript` — handle
    - :class:`SessionHeader` — metadata dataclass
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from chemigram.core.workspace import Workspace

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SessionHeader:
    """First-line session metadata."""

    session_id: str
    started_at: str
    image_id: str
    mode: str
    prompt_versions: dict[str, str] = field(default_factory=dict)
    vocab_pack: str = "starter"


class SessionTranscript:
    """Open transcript handle. Construct via :func:`start_session`.

    All :meth:`append_*` methods are sync + flushed; in production the
    cost is <1 ms per call. Errors are caught and logged so transcript
    failures never abort the calling tool.
    """

    def __init__(self, path: Path, header: SessionHeader) -> None:
        self._path = path
        self._header = header
        self._entry_count = 0
        self._closed = False
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("w", encoding="utf-8")
        self._write({"kind": "header", **asdict(header)})

    @property
    def session_id(self) -> str:
        return self._header.session_id

    @property
    def path(self) -> Path:
        return self._path

    def append(self, entry: dict[str, Any]) -> None:
        """Write one JSONL line. Caller supplies ``kind`` + fields."""
        if self._closed:
            raise RuntimeError("transcript is closed")
        full: dict[str, Any] = {"timestamp": _now_iso()}
        full.update(entry)
        self._write(full)
        self._entry_count += 1

    def append_tool_call(self, tool_name: str, args: dict[str, Any]) -> None:
        self.append({"kind": "tool_call", "tool": tool_name, "args": args})

    def append_tool_result(
        self,
        tool_name: str,
        success: bool,
        *,
        error_code: str | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "kind": "tool_result",
            "tool": tool_name,
            "success": success,
        }
        if error_code is not None:
            entry["error_code"] = error_code
        self.append(entry)

    def append_proposal(self, proposal_kind: str, proposal_id: str, summary: str) -> None:
        self.append(
            {
                "kind": "proposal",
                "proposal_kind": proposal_kind,
                "proposal_id": proposal_id,
                "summary": summary,
            }
        )

    def append_confirmation(self, proposal_id: str, accepted: bool) -> None:
        self.append(
            {
                "kind": "confirmation",
                "proposal_id": proposal_id,
                "accepted": accepted,
            }
        )

    def close(self, *, summary: dict[str, Any] | None = None) -> None:
        """Write footer and close. Idempotent — second call is no-op."""
        if self._closed:
            return
        footer: dict[str, Any] = {
            "kind": "footer",
            "ended_at": _now_iso(),
            "entry_count": self._entry_count,
        }
        if summary is not None:
            footer.update(summary)
        try:
            self._write(footer)
        finally:
            self._fh.close()
            self._closed = True

    # --- internal -------------------------------------------------------

    def _write(self, obj: dict[str, Any]) -> None:
        try:
            line = json.dumps(obj, default=str)
        except (TypeError, ValueError) as exc:
            logger.warning("session transcript: serialize failed (%s); skipping", exc)
            line = json.dumps({"kind": "write_failure", "error": str(exc)})
        try:
            self._fh.write(line + "\n")
            self._fh.flush()
        except OSError as exc:
            logger.warning("session transcript: write failed (%s)", exc)


def start_session(
    workspace: Workspace,
    *,
    mode: str = "A",
    session_id: str | None = None,
    prompt_versions: dict[str, str] | None = None,
    vocab_pack: str = "starter",
) -> SessionTranscript:
    """Open a new session transcript at
    ``<workspace>/sessions/<session_id>.jsonl``.

    ``session_id`` defaults to a uuid4 hex; pass an explicit value for
    deterministic test paths or replay scenarios.
    """
    sid = session_id if session_id is not None else uuid4().hex
    header = SessionHeader(
        session_id=sid,
        started_at=_now_iso(),
        image_id=workspace.image_id,
        mode=mode,
        prompt_versions=prompt_versions or {},
        vocab_pack=vocab_pack,
    )
    path = workspace.sessions_dir / f"{sid}.jsonl"
    return SessionTranscript(path, header)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


__all__ = [
    "SessionHeader",
    "SessionTranscript",
    "start_session",
]
