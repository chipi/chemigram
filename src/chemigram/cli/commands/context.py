"""Context-related CLI verbs.

- ``chemigram read-context <image_id>`` mirrors MCP ``read_context``.
- ``chemigram log-vocabulary-gap`` mirrors MCP ``log_vocabulary_gap``.
- ``chemigram apply-taste-update`` is a CLI-only direct verb. The
  conversational propose/confirm pair (``propose_taste_update`` +
  ``confirm_taste_update``) is MCP-only by design — it requires
  in-process state across two tool calls, which is the wrong model
  for the subprocess CLI (a parallel ``for f in *.NEF`` loop would
  race on a shared proposal store). RFC-020 amendment to follow.
- ``chemigram apply-notes-update`` is the equivalent for per-image notes.

Both ``apply-*`` verbs match what scripts and agent loops actually need:
the agent has already decided; the CLI just writes.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast

import typer

from chemigram.cli._context import CliContext
from chemigram.cli._workspace import default_workspace_root, load_workspace
from chemigram.cli.exit_codes import ExitCode
from chemigram.core.context import Brief, Notes, RecentGaps, RecentLog, Tastes
from chemigram.core.workspace import append_markdown, tastes_dir

_VALID_TASTE_CATEGORIES = ("appearance", "process", "value")
_VALID_SATISFACTION = (-1, 0, 1)


# ---------------------------------------------------------------------------
# read-context
# ---------------------------------------------------------------------------


def read_context(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID (workspace name)."),
) -> None:
    """Print the agent's first-turn context for ``image_id`` (RFC-011)."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    workspace_root = obj["workspace"] or default_workspace_root()

    workspace = load_workspace(workspace_root, image_id)
    if workspace is None:
        writer.error(
            f"workspace not found: {image_id}",
            ExitCode.NOT_FOUND,
            image_id=image_id,
            workspace_root=str(workspace_root),
        )
        raise typer.Exit(code=ExitCode.NOT_FOUND.value)

    brief = Brief.load(workspace)
    tastes = Tastes.load(brief_genres=brief.tastes)
    notes = Notes.load(workspace)
    # Same limits as the MCP read_context tool — without these a long-lived
    # workspace can dump thousands of records into the agent's first turn.
    recent_log = RecentLog.load(workspace, limit=10)
    recent_gaps = RecentGaps.load(workspace, limit=10)

    writer.result(
        message=f"context for {image_id}",
        image_id=image_id,
        tastes={
            "default": tastes.default,
            "genres": dict(tastes.genres),
            "conflicts": list(tastes.conflicts),
        },
        brief={"raw": brief.raw, "intent": brief.intent, "tastes": list(brief.tastes)},
        notes={"summary": notes.summary, "truncated": notes.truncated},
        recent_log=[
            {"timestamp": e.timestamp, "op": e.op, "details": dict(e.details)} for e in recent_log
        ],
        recent_gaps=[
            {
                "timestamp": g.timestamp,
                "description": g.description,
                "intent_category": g.intent_category,
            }
            for g in recent_gaps
        ],
    )


# ---------------------------------------------------------------------------
# log-vocabulary-gap
# ---------------------------------------------------------------------------


def log_vocabulary_gap(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    description: str = typer.Option(
        ..., "--description", help="What the agent reached for that didn't exist."
    ),
    workaround: str = typer.Option("", "--workaround", help="What was used instead, if anything."),
    intent: str | None = typer.Option(None, "--intent", help="The intent the agent was after."),
    intent_category: str = typer.Option(
        "uncategorized", "--intent-category", help="Tier of the missing primitive."
    ),
    missing_capability: str | None = typer.Option(
        None, "--missing-capability", help="The specific capability that's absent."
    ),
    operations_involved: list[str] = typer.Option(
        None,
        "--operation",
        help="darktable operation(s) involved in the workaround (repeatable).",
    ),
    vocabulary_used: list[str] = typer.Option(
        None,
        "--vocab-used",
        help="Vocabulary entries used in the workaround (repeatable).",
    ),
    satisfaction: int | None = typer.Option(
        None,
        "--satisfaction",
        help="Photographer's read on the workaround: -1 (poor), 0 (ok), +1 (good).",
    ),
    notes: str = typer.Option("", "--notes", help="Free-form."),
) -> None:
    """Append a vocabulary-gap record to the image's vocabulary_gaps.jsonl (ADR-060)."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    workspace_root = obj["workspace"] or default_workspace_root()

    workspace = load_workspace(workspace_root, image_id)
    if workspace is None:
        writer.error(
            f"workspace not found: {image_id}",
            ExitCode.NOT_FOUND,
            image_id=image_id,
        )
        raise typer.Exit(code=ExitCode.NOT_FOUND.value)
    if not description.strip():
        writer.error(
            "--description must be non-empty",
            ExitCode.INVALID_INPUT,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)
    if satisfaction is not None and satisfaction not in _VALID_SATISFACTION:
        writer.error(
            f"--satisfaction must be -1, 0, or 1; got {satisfaction}",
            ExitCode.INVALID_INPUT,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)

    snapshot_hash: str | None
    try:
        snapshot_hash = workspace.repo.resolve_ref("HEAD")
    except Exception:
        snapshot_hash = None

    record = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "image_id": image_id,
        "session_id": None,  # CLI doesn't have an MCP-session id
        "snapshot_hash": snapshot_hash,
        "description": description,
        "workaround": workaround,
        "intent": intent,
        "intent_category": intent_category,
        "missing_capability": missing_capability,
        "operations_involved": list(operations_involved or []),
        "vocabulary_used": list(vocabulary_used or []),
        "satisfaction": satisfaction,
        "notes": notes,
    }
    workspace.vocabulary_gaps_path.parent.mkdir(parents=True, exist_ok=True)
    with workspace.vocabulary_gaps_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    writer.result(
        message=f"gap logged for {image_id}",
        path=str(workspace.vocabulary_gaps_path),
        appended=True,
    )


# ---------------------------------------------------------------------------
# apply-taste-update / apply-notes-update (CLI-only direct verbs)
# ---------------------------------------------------------------------------


def apply_taste_update(
    ctx: typer.Context,
    content: str = typer.Option(..., "--content", help="Markdown to append (must be non-empty)."),
    category: str = typer.Option(
        ...,
        "--category",
        help="Taste category: appearance | process | value (per ADR-048).",
    ),
    file: str = typer.Option(
        "_default.md",
        "--file",
        help="Target taste file (auto-suffixed with .md). Defaults to _default.md.",
    ),
) -> None:
    """Append a taste line to ``~/.chemigram/tastes/<file>`` directly.

    CLI-only direct verb. The conversational propose/confirm pair lives in
    MCP only; the CLI does not maintain cross-invocation state.
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    if not content.strip():
        writer.error("--content must be non-empty", ExitCode.INVALID_INPUT)
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)
    if category not in _VALID_TASTE_CATEGORIES:
        writer.error(
            f"--category must be one of {_VALID_TASTE_CATEGORIES}; got {category!r}",
            ExitCode.INVALID_INPUT,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)

    target_file = file if file.endswith(".md") else f"{file}.md"
    target = tastes_dir() / target_file
    append_markdown(target, content)

    writer.result(
        message=f"taste appended to {target_file}",
        written_to=str(target),
        category=category,
    )


def apply_notes_update(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    content: str = typer.Option(..., "--content", help="Markdown to append (must be non-empty)."),
) -> None:
    """Append a notes line to ``<workspace>/notes.md`` directly.

    CLI-only direct verb (see ``apply-taste-update`` rationale).
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    workspace_root = obj["workspace"] or default_workspace_root()

    workspace = load_workspace(workspace_root, image_id)
    if workspace is None:
        writer.error(
            f"workspace not found: {image_id}",
            ExitCode.NOT_FOUND,
            image_id=image_id,
        )
        raise typer.Exit(code=ExitCode.NOT_FOUND.value)
    if not content.strip():
        writer.error("--content must be non-empty", ExitCode.INVALID_INPUT)
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)

    target = workspace.root / "notes.md"
    append_markdown(target, content)

    writer.result(
        message=f"notes appended for {image_id}",
        written_to=str(target),
        image_id=image_id,
    )
