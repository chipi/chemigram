"""``chemigram session-log`` sub-app — read-side tooling for session transcripts.

The agent writes per-image session transcripts to
``<workspace>/<image_id>/sessions/<session_id>.jsonl`` per ADR-029 +
RFC-014 / ADR-061. Each transcript is a JSONL file: header line +
per-turn entries (tool_call / tool_result / proposal / confirmation /
note) + optional footer summary.

Until now there was no read-side tooling — sessions were written but
not queryable. This sub-app provides the analytics layer:

    chemigram session-log list   [--since 7d] [--image <id>]
    chemigram session-log show   <session_id>
    chemigram session-log find   --primitive <name> | --module <name> | --tool <name>
    chemigram session-log replay <session_id>

Closes #109. Sister to ``chemigram gap-log`` (#106 / commit b943e62).
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import typer

from chemigram.cli._context import CliContext
from chemigram.cli._workspace import default_workspace_root
from chemigram.cli.exit_codes import ExitCode

app = typer.Typer(no_args_is_help=True)


def _resolve_workspace_root(ctx: typer.Context) -> Path:
    obj = cast(CliContext, ctx.obj)
    return obj.get("workspace") or default_workspace_root()


def _iter_image_ids(workspace_root: Path) -> list[str]:
    """Return image_ids found in the workspace root (per-image-repo signature)."""
    if not workspace_root.exists():
        return []
    out: list[str] = []
    for child in workspace_root.iterdir():
        if not child.is_dir():
            continue
        if (child / "objects").is_dir() and (child / "raw").is_dir():
            out.append(child.name)
    return sorted(out)


def _sessions_dir(workspace_root: Path, image_id: str) -> Path:
    return workspace_root / image_id / "sessions"


def _read_transcript(path: Path) -> list[dict[str, Any]]:
    """Parse a session JSONL transcript. Tolerates malformed lines."""
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out


def _transcript_header(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the header entry (kind=header) in a transcript."""
    for entry in entries:
        if entry.get("kind") == "header":
            return entry
    return None


def _transcript_footer(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find the footer entry (kind=footer) in a transcript, if present."""
    for entry in reversed(entries):
        if entry.get("kind") == "footer":
            return entry
    return None


def _iter_transcripts(workspace_root: Path, image_id: str | None) -> list[tuple[str, Path]]:
    """Walk the workspace's sessions/ dirs; return (image_id, transcript_path) tuples."""
    image_ids = [image_id] if image_id else _iter_image_ids(workspace_root)
    out: list[tuple[str, Path]] = []
    for iid in image_ids:
        sd = _sessions_dir(workspace_root, iid)
        if not sd.exists():
            continue
        for path in sorted(sd.glob("*.jsonl")):
            out.append((iid, path))
    return out


_RELATIVE_RE = re.compile(r"^(\d+)([dwhm])$")


def _parse_since(value: str | None) -> datetime | None:
    """Accept ISO 8601 or relative (7d / 2w / 24h / 30m). Returns UTC datetime or None."""
    if not value:
        return None
    rel = _RELATIVE_RE.match(value.strip().lower())
    if rel:
        n = int(rel.group(1))
        unit = rel.group(2)
        delta = {
            "d": timedelta(days=n),
            "w": timedelta(weeks=n),
            "h": timedelta(hours=n),
            "m": timedelta(minutes=n),
        }[unit]
        return datetime.now(UTC) - delta
    iso = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError as exc:
        raise typer.BadParameter(
            f"--since must be ISO 8601 (2026-05-01) or relative (7d/2w/24h/30m); got {value!r}"
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _session_after(header: dict[str, Any] | None, since: datetime | None) -> bool:
    if since is None:
        return True
    if header is None:
        return False
    started = header.get("started_at")
    if not started:
        return False
    try:
        ts = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts >= since


# --- list ----------------------------------------------------------------


@app.command("list")
def list_(
    ctx: typer.Context,
    since: str | None = typer.Option(
        None,
        "--since",
        help="Only show sessions started after this point. "
        "ISO 8601 or relative (7d / 2w / 24h / 30m).",
    ),
    image: str | None = typer.Option(
        None,
        "--image",
        help="Filter to one image_id. Omit to scan all images.",
    ),
) -> None:
    """List session transcripts across the workspace, newest-first."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    try:
        since_dt = _parse_since(since)
    except typer.BadParameter as exc:
        writer.error(str(exc), ExitCode.INVALID_INPUT, value=since)
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc

    workspace_root = _resolve_workspace_root(ctx)
    transcripts = _iter_transcripts(workspace_root, image)

    rows: list[dict[str, Any]] = []
    for image_id, path in transcripts:
        entries = _read_transcript(path)
        header = _transcript_header(entries)
        footer = _transcript_footer(entries)
        if not _session_after(header, since_dt):
            continue
        rows.append(
            {
                "image_id": image_id,
                "session_id": header.get("session_id") if header else path.stem,
                "started_at": header.get("started_at") if header else None,
                "mode": header.get("mode") if header else None,
                "vocab_pack": header.get("vocab_pack") if header else None,
                "entry_count": len(entries),
                "summary": (footer or {}).get("summary"),
                "path": str(path),
            }
        )

    # Newest first by started_at (ISO 8601 sorts chronologically)
    rows.sort(key=lambda r: r.get("started_at") or "", reverse=True)
    for row in rows:
        writer.event("session_entry", **row)

    writer.result(
        message=f"{len(rows)} session(s) across {len({r['image_id'] for r in rows})} image(s)",
        count=len(rows),
        filter={"since": since, "image": image},
    )


# --- show ----------------------------------------------------------------


def _find_transcript(workspace_root: Path, session_id: str) -> tuple[str, Path] | None:
    """Locate a transcript by session_id; returns (image_id, path) or None."""
    for image_id, path in _iter_transcripts(workspace_root, image_id=None):
        if path.stem == session_id:
            return image_id, path
        # Also check the header's session_id field
        entries = _read_transcript(path)
        header = _transcript_header(entries)
        if header and header.get("session_id") == session_id:
            return image_id, path
    return None


@app.command("show")
def show(
    ctx: typer.Context,
    session_id: str = typer.Argument(
        ...,
        help="Session identifier (matches the JSONL filename or header's session_id).",
    ),
) -> None:
    """Show all entries from one session, chronological."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace_root = _resolve_workspace_root(ctx)
    found = _find_transcript(workspace_root, session_id)
    if found is None:
        writer.error(
            f"session not found: {session_id}",
            ExitCode.NOT_FOUND,
            session_id=session_id,
        )
        raise typer.Exit(code=ExitCode.NOT_FOUND.value)

    image_id, path = found
    entries = _read_transcript(path)
    for entry in entries:
        # The transcript entry's "kind" field would collide with
        # writer.event()'s 'kind' positional; rename it to 'turn_kind'
        # for the output event.
        out = dict(entry)
        out["turn_kind"] = out.pop("kind", None)
        writer.event("session_turn", **out)

    writer.result(
        message=f"{len(entries)} entries in session {session_id!r}",
        count=len(entries),
        session_id=session_id,
        image_id=image_id,
        path=str(path),
    )


# --- find ----------------------------------------------------------------


def _entry_matches_query(
    entry: dict[str, Any],
    primitive: str | None,
    module: str | None,
    tool: str | None,
) -> bool:
    """Match a transcript entry against the find query filters."""
    if primitive is not None:
        # Match against tool_call args.name (apply_primitive's name argument)
        if entry.get("kind") != "tool_call":
            return False
        args = entry.get("args") or {}
        if str(args.get("name", "")).lower() != primitive.lower():
            return False
    if tool is not None:
        if entry.get("tool", "").lower() != tool.lower():
            return False
    if module is not None:
        # Match anywhere in the entry's serialized JSON (covers
        # tool args, error messages, note text)
        needle = module.lower()
        return needle in json.dumps(entry).lower()
    return True


@app.command("find")
def find(
    ctx: typer.Context,
    primitive: str | None = typer.Option(
        None,
        "--primitive",
        help="Match tool_call entries where args.name == this primitive (e.g. 'exposure').",
    ),
    module: str | None = typer.Option(
        None,
        "--module",
        help="Match anywhere in the entry's serialized JSON "
        "(covers tool args, error messages, notes).",
    ),
    tool: str | None = typer.Option(
        None,
        "--tool",
        help="Match tool_call / tool_result entries with this tool name (e.g. 'apply_primitive').",
    ),
    image: str | None = typer.Option(None, "--image", help="Restrict to one image_id."),
) -> None:
    """Find entries across all session transcripts matching the query."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    if primitive is None and module is None and tool is None:
        writer.error(
            "session-log find requires at least one filter: --primitive, --module, or --tool",
            ExitCode.INVALID_INPUT,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)

    workspace_root = _resolve_workspace_root(ctx)
    transcripts = _iter_transcripts(workspace_root, image)

    matches: list[dict[str, Any]] = []
    for image_id, path in transcripts:
        for entry in _read_transcript(path):
            if not _entry_matches_query(entry, primitive, module, tool):
                continue
            matches.append({"image_id": image_id, "session_id": path.stem, **entry})

    matches.sort(key=lambda m: str(m.get("timestamp", "")), reverse=True)
    for match in matches:
        out = dict(match)
        out["turn_kind"] = out.pop("kind", None)
        writer.event("session_match", **out)

    writer.result(
        message=f"{len(matches)} match(es) across {len(transcripts)} session(s)",
        count=len(matches),
        sessions_scanned=len(transcripts),
        filter={"primitive": primitive, "module": module, "tool": tool, "image": image},
    )


# --- replay --------------------------------------------------------------


def _replay_command_for(entry: dict[str, Any]) -> str | None:
    """Render a transcript entry as a CLI invocation hint (best-effort)."""
    if entry.get("kind") != "tool_call":
        return None
    tool = entry.get("tool")
    args = entry.get("args") or {}
    if tool == "apply_primitive":
        name = args.get("name")
        image_id = args.get("image_id")
        bits = ["chemigram apply-primitive", name or "<name>"]
        if image_id:
            bits.append(f"--image {image_id}")
        if "value" in args:
            bits.append(f"--value {args['value']}")
        for k, v in args.items():
            if k.startswith("param_") or k in {"name", "image_id", "value"}:
                continue
            bits.append(f"--{k.replace('_', '-')} {v!r}")
        return " ".join(bits)
    if tool in {"snapshot", "tag", "branch", "checkout", "log", "diff", "reset"}:
        image_id = args.get("image_id", "<image_id>")
        return f"chemigram {tool} {image_id}"
    return f"# {tool}({json.dumps(args)})"


@app.command("replay")
def replay(
    ctx: typer.Context,
    session_id: str = typer.Argument(..., help="Session identifier."),
) -> None:
    """Re-emit a session's tool calls as CLI invocation hints.

    Best-effort rendering: each tool_call becomes a line you could
    re-run from the shell. Tool-specific argument shapes are mapped for
    the common cases (apply_primitive, versioning verbs); others fall
    through as a comment.
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace_root = _resolve_workspace_root(ctx)
    found = _find_transcript(workspace_root, session_id)
    if found is None:
        writer.error(
            f"session not found: {session_id}",
            ExitCode.NOT_FOUND,
            session_id=session_id,
        )
        raise typer.Exit(code=ExitCode.NOT_FOUND.value)

    image_id, path = found
    entries = _read_transcript(path)

    rendered: list[str] = []
    for entry in entries:
        cmd = _replay_command_for(entry)
        if cmd:
            rendered.append(cmd)
            writer.event("replay_command", command=cmd, turn_kind=entry.get("kind"))

    writer.result(
        message=f"{len(rendered)} command(s) for session {session_id!r}",
        count=len(rendered),
        session_id=session_id,
        image_id=image_id,
    )
