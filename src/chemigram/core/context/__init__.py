"""Context loaders for the agent's first turn.

Per **RFC-011** (closing in v0.5.0 via ADR-059): the loading order is
``tastes → brief → notes → recent_log → recent_gaps``. Tastes are global
(``~/.chemigram/tastes/`` per ADR-048) and merge ``_default.md`` with any
genre files declared in ``brief.md``. Brief, notes, log, and gaps are
per-image.

All loaders are tolerant of missing files: a missing or unreadable file
yields an empty structure rather than raising. The agent's first turn must
work on a fresh workspace with no prior context.

The :class:`Notes` loader implements RFC-011's line-truncation
summarization (first 10 + last 30 lines + ellision marker) so long notes
stay readable in the agent's prompt window. LLM-aware summarization is
deferred to Phase 2.

Public API:
    - :class:`Tastes`, :class:`Brief`, :class:`Notes`, :class:`RecentLog`,
      :class:`RecentGaps` — loaders
    - :class:`TastesContent`, :class:`BriefContent`, :class:`NotesContent`,
      :class:`LogEntry`, :class:`GapEntry` — return values
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chemigram.core.workspace import Workspace, tastes_dir

NOTES_HEAD_LINES = 10
NOTES_TAIL_LINES = 30
NOTES_TRUNCATION_THRESHOLD = NOTES_HEAD_LINES + NOTES_TAIL_LINES


@dataclass(frozen=True)
class TastesContent:
    """Loaded multi-scope taste content (per ADR-048)."""

    default: str = ""
    genres: dict[str, str] = field(default_factory=dict)
    conflicts: list[dict[str, Any]] = field(default_factory=list)


class Tastes:
    """Multi-scope taste loader."""

    @staticmethod
    def load(
        brief_genres: list[str] | None = None,
        *,
        tastes_root: Path | None = None,
    ) -> TastesContent:
        """Load ``_default.md`` plus declared genre files.

        Args:
            brief_genres: Genre filenames (without ``.md``) declared in
                ``brief.md``. ``None`` or ``[]`` → only ``_default.md``.
            tastes_root: Override the global ``~/.chemigram/tastes/``
                directory. Tests pass an isolated root.

        Missing files contribute empty content. Conflicts (same line in
        two genre files) are surfaced in :attr:`TastesContent.conflicts`
        for the agent to mediate.
        """
        root = tastes_root if tastes_root is not None else tastes_dir()
        default = _read_text_or_empty(root / "_default.md")

        genres: dict[str, str] = {}
        for name in brief_genres or []:
            content = _read_text_or_empty(root / f"{name}.md")
            if content:
                genres[name] = content

        conflicts = _detect_taste_conflicts(genres)
        return TastesContent(default=default, genres=genres, conflicts=conflicts)


@dataclass(frozen=True)
class BriefContent:
    """Parsed ``brief.md`` content."""

    raw: str = ""
    intent: str = ""
    tastes: list[str] = field(default_factory=list)


class Brief:
    """Reader for per-image ``brief.md``."""

    @staticmethod
    def load(workspace: Workspace) -> BriefContent:
        path = workspace.root / "brief.md"
        raw = _read_text_or_empty(path)
        if not raw:
            return BriefContent()
        intent, tastes = _parse_brief(raw)
        return BriefContent(raw=raw, intent=intent, tastes=tastes)


@dataclass(frozen=True)
class NotesContent:
    """Per-image notes content with optional summarization."""

    raw: str = ""
    summary: str = ""
    truncated: bool = False


class Notes:
    """Reader with line-truncation summarization per RFC-011."""

    @staticmethod
    def load(workspace: Workspace, *, summarize: bool = True) -> NotesContent:
        path = workspace.root / "notes.md"
        raw = _read_text_or_empty(path)
        if not raw:
            return NotesContent()
        if not summarize:
            return NotesContent(raw=raw, summary=raw, truncated=False)
        summary, truncated = _summarize_notes(raw)
        return NotesContent(raw=raw, summary=summary, truncated=truncated)


@dataclass(frozen=True)
class LogEntry:
    """One entry from the per-image log.jsonl."""

    timestamp: str
    op: str
    details: dict[str, Any] = field(default_factory=dict)


class RecentLog:
    """Reader for the tail of ``<workspace>/log.jsonl`` (newest first)."""

    @staticmethod
    def load(workspace: Workspace, *, limit: int = 10) -> list[LogEntry]:
        path = workspace.root / "log.jsonl"
        if not path.exists():
            return []
        entries: list[LogEntry] = []
        for raw_line in reversed(path.read_text(encoding="utf-8").splitlines()):
            if not raw_line.strip():
                continue
            try:
                obj = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            entries.append(
                LogEntry(
                    timestamp=str(obj.get("timestamp", "")),
                    op=str(obj.get("op", "")),
                    details={k: v for k, v in obj.items() if k not in ("timestamp", "op")},
                )
            )
            if len(entries) >= limit:
                break
        return entries


@dataclass(frozen=True)
class GapEntry:
    """One vocabulary-gap record. Optional fields default to None / empty
    for backwards-compat with v0.3.0's minimal 4-field schema."""

    timestamp: str
    image_id: str
    description: str
    workaround: str = ""
    session_id: str | None = None
    snapshot_hash: str | None = None
    intent: str | None = None
    intent_category: str = "uncategorized"
    missing_capability: str | None = None
    operations_involved: list[str] = field(default_factory=list)
    vocabulary_used: list[str] = field(default_factory=list)
    satisfaction: int | None = None
    notes: str = ""


class RecentGaps:
    """Reader for ``vocabulary_gaps.jsonl`` (newest first).

    Backwards-compat: handles both v0.3.0 minimal records (4 fields) and
    post-#24 RFC-013 records. Missing fields take the dataclass defaults.
    """

    @staticmethod
    def load(workspace: Workspace, *, limit: int = 10) -> list[GapEntry]:
        path = workspace.vocabulary_gaps_path
        if not path.exists():
            return []
        entries: list[GapEntry] = []
        for raw_line in reversed(path.read_text(encoding="utf-8").splitlines()):
            if not raw_line.strip():
                continue
            try:
                obj = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            entries.append(_gap_from_dict(obj))
            if len(entries) >= limit:
                break
        return entries


# --- helpers ------------------------------------------------------------


def _read_text_or_empty(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
        return ""


def _detect_taste_conflicts(genres: dict[str, str]) -> list[dict[str, Any]]:
    """Surface lines that appear in more than one genre file."""
    line_to_files: dict[str, list[str]] = {}
    for name, content in genres.items():
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            line_to_files.setdefault(stripped, []).append(name)
    return [
        {"point": line, "files": files} for line, files in line_to_files.items() if len(files) > 1
    ]


def _parse_brief(raw: str) -> tuple[str, list[str]]:
    """Parse a markdown brief. The ``Tastes:`` line declares genre files.

    Convention: a line of the form ``Tastes: [a, b, c]`` or
    ``Tastes: a, b, c``. Whitespace + brackets stripped. Other lines feed
    ``intent`` (everything except the Tastes line).
    """
    intent_lines: list[str] = []
    tastes: list[str] = []
    for line in raw.splitlines():
        if line.lower().startswith("tastes:"):
            payload = line.split(":", 1)[1].strip()
            payload = payload.strip("[]")
            tastes = [p.strip().strip('"').strip("'") for p in payload.split(",") if p.strip()]
        else:
            intent_lines.append(line)
    return ("\n".join(intent_lines).strip(), tastes)


def _summarize_notes(raw: str) -> tuple[str, bool]:
    """Apply line-truncation per RFC-011."""
    lines = raw.splitlines()
    if len(lines) <= NOTES_TRUNCATION_THRESHOLD:
        return raw, False
    head = lines[:NOTES_HEAD_LINES]
    tail = lines[-NOTES_TAIL_LINES:]
    elided = len(lines) - NOTES_HEAD_LINES - NOTES_TAIL_LINES
    summary = "\n".join(head) + f"\n\n... [{elided} lines elided] ...\n\n" + "\n".join(tail)
    return summary, True


def _gap_from_dict(obj: dict[str, Any]) -> GapEntry:
    return GapEntry(
        timestamp=str(obj.get("timestamp", "")),
        image_id=str(obj.get("image_id", "")),
        description=str(obj.get("description", "")),
        workaround=str(obj.get("workaround", "")),
        session_id=obj.get("session_id"),
        snapshot_hash=obj.get("snapshot_hash"),
        intent=obj.get("intent"),
        intent_category=str(obj.get("intent_category") or "uncategorized"),
        missing_capability=obj.get("missing_capability"),
        operations_involved=list(obj.get("operations_involved") or []),
        vocabulary_used=list(obj.get("vocabulary_used") or []),
        satisfaction=obj.get("satisfaction"),
        notes=str(obj.get("notes", "")),
    )


__all__ = [
    "Brief",
    "BriefContent",
    "GapEntry",
    "LogEntry",
    "Notes",
    "NotesContent",
    "RecentGaps",
    "RecentLog",
    "Tastes",
    "TastesContent",
]
