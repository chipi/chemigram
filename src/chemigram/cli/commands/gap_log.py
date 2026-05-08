"""``chemigram gap-log`` sub-app — read-side tooling for vocabulary_gaps.jsonl.

The agent calls ``log_vocabulary_gap`` (MCP) / ``chemigram log-vocabulary-gap``
(CLI) when reaching for a missing primitive, appending one record per
gap to the per-image ``vocabulary_gaps.jsonl``. This sub-app provides
the read side: aggregate gaps across images, rank by frequency, surface
patterns. Closes #106.

Workflow context: per CLAUDE.md, Phase 2 (vocabulary maturation) is
use-driven — real sessions log gaps; the photographer (or maintainer)
periodically reads the log and authors missing primitives. Without
analytics, the loop is read-once-per-image and hard to aggregate. This
sub-app is the analytics layer.

Per ADR-081, the eventual Tier 3 → Tier 2 promotion threshold
(deferred to multi-photographer review phase) will read this surface
to decide which Tier 3 modules clear the cost/benefit bar.

Commands:
    list  — flat list of gap entries across all images, filterable
    rank  — frequency-ranked summary aggregated by description + module
    show  — full text of one image's gap log (chronological)
    clear — opt-in cleanup of gaps for one image (with confirmation)
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import typer

from chemigram.cli._context import CliContext
from chemigram.cli._workspace import default_workspace_root
from chemigram.cli.exit_codes import ExitCode
from chemigram.core.context import GapEntry

app = typer.Typer(no_args_is_help=True)


def _resolve_workspace_root(ctx: typer.Context) -> Path:
    obj = cast(CliContext, ctx.obj)
    return obj.get("workspace") or default_workspace_root()


def _iter_image_ids(workspace_root: Path) -> list[str]:
    """Return image_ids found in the workspace root.

    A directory is considered an image_id if it contains both
    ``objects/`` and ``raw/`` (the per-image-repo signature, matching
    :func:`chemigram.cli._workspace.discover_workspace_from_cwd`).
    """
    if not workspace_root.exists():
        return []
    out: list[str] = []
    for child in workspace_root.iterdir():
        if not child.is_dir():
            continue
        if (child / "objects").is_dir() and (child / "raw").is_dir():
            out.append(child.name)
    return sorted(out)


def _gap_path(workspace_root: Path, image_id: str) -> Path:
    return workspace_root / image_id / "vocabulary_gaps.jsonl"


def _read_gaps(path: Path) -> list[GapEntry]:
    """Parse a vocabulary_gaps.jsonl file. Tolerates malformed lines
    (skips them silently, matching :class:`RecentGaps.load` behavior)."""
    if not path.exists():
        return []
    out: list[GapEntry] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        out.append(
            GapEntry(
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
        )
    return out


_RELATIVE_RE = re.compile(r"^(\d+)([dwhm])$")


def _parse_since(value: str | None) -> datetime | None:
    """Accept ISO 8601 (``2026-05-01T00:00:00Z`` or date) or relative
    (``7d``, ``2w``, ``24h``, ``30m``). Returns a UTC ``datetime`` or
    ``None`` if no filter requested."""
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
    # ISO 8601 — handle trailing Z (Python's fromisoformat doesn't pre-3.11)
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


def _gap_after(gap: GapEntry, since: datetime | None) -> bool:
    if since is None:
        return True
    if not gap.timestamp:
        return False
    try:
        ts = datetime.fromisoformat(gap.timestamp.replace("Z", "+00:00"))
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts >= since


def _gap_matches_module(gap: GapEntry, module: str | None) -> bool:
    if not module:
        return True
    needle = module.lower()
    if gap.missing_capability and needle in gap.missing_capability.lower():
        return True
    if any(needle in op.lower() for op in gap.operations_involved):
        return True
    return needle in gap.description.lower()


# --- list ----------------------------------------------------------------


@app.command("list")
def list_(
    ctx: typer.Context,
    since: str | None = typer.Option(
        None,
        "--since",
        help="Only show gaps logged after this point. ISO 8601 (2026-05-01) "
        "or relative (7d / 2w / 24h / 30m).",
    ),
    image: str | None = typer.Option(
        None,
        "--image",
        help="Filter to one image_id. Omit to scan all images in the workspace.",
    ),
    module: str | None = typer.Option(
        None,
        "--module",
        help="Filter to gaps mentioning a darktable module name "
        "(matches missing_capability, operations_involved, or description).",
    ),
) -> None:
    """List vocabulary-gap entries across the workspace, filterable.

    Each row is one ``vocabulary_entry``-equivalent event. The result
    summary reports the total count + the filter scope.
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    try:
        since_dt = _parse_since(since)
    except typer.BadParameter as exc:
        writer.error(str(exc), ExitCode.INVALID_INPUT, value=since)
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc

    workspace_root = _resolve_workspace_root(ctx)
    image_ids = [image] if image else _iter_image_ids(workspace_root)

    matched: list[GapEntry] = []
    for image_id in image_ids:
        for gap in _read_gaps(_gap_path(workspace_root, image_id)):
            if not _gap_after(gap, since_dt):
                continue
            if not _gap_matches_module(gap, module):
                continue
            matched.append(gap)

    # Sort newest-first by timestamp string (ISO 8601 sorts chronologically)
    matched.sort(key=lambda g: g.timestamp, reverse=True)

    for gap in matched:
        writer.event(
            "gap_entry",
            timestamp=gap.timestamp,
            image_id=gap.image_id,
            description=gap.description,
            workaround=gap.workaround,
            intent_category=gap.intent_category,
            missing_capability=gap.missing_capability,
            operations_involved=gap.operations_involved,
            vocabulary_used=gap.vocabulary_used,
            satisfaction=gap.satisfaction,
        )

    writer.result(
        message=f"{len(matched)} gap(s) across {len(image_ids)} image(s)",
        count=len(matched),
        images_scanned=len(image_ids),
        filter={"since": since, "image": image, "module": module},
    )


# --- rank ----------------------------------------------------------------


def _aggregation_key(gap: GapEntry) -> tuple[str, str]:
    """Aggregate by (description-trimmed-lowercased, missing_capability or '')."""
    return (gap.description.strip().lower(), (gap.missing_capability or "").lower())


@app.command("rank")
def rank(
    ctx: typer.Context,
    since: str | None = typer.Option(
        None,
        "--since",
        help="Only count gaps logged after this point. ISO 8601 or relative.",
    ),
    image: str | None = typer.Option(
        None,
        "--image",
        help="Filter to one image_id. Omit to scan all images.",
    ),
    top: int = typer.Option(
        20,
        "--top",
        help="Show the top N most frequent gaps (default 20). 0 = no limit.",
        min=0,
    ),
) -> None:
    """Rank vocabulary gaps by frequency.

    Aggregation key: ``(description, missing_capability)``. Each unique
    key is one row; ``count`` is the occurrence frequency; ``examples``
    surfaces a sample image_id + timestamp for the row.
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    try:
        since_dt = _parse_since(since)
    except typer.BadParameter as exc:
        writer.error(str(exc), ExitCode.INVALID_INPUT, value=since)
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc

    workspace_root = _resolve_workspace_root(ctx)
    image_ids = [image] if image else _iter_image_ids(workspace_root)

    counter: Counter[tuple[str, str]] = Counter()
    examples: dict[tuple[str, str], GapEntry] = {}

    for image_id in image_ids:
        for gap in _read_gaps(_gap_path(workspace_root, image_id)):
            if not _gap_after(gap, since_dt):
                continue
            key = _aggregation_key(gap)
            counter[key] += 1
            if key not in examples:
                examples[key] = gap

    rows = counter.most_common(None if top == 0 else top)

    for (description, capability), count in rows:
        sample = examples[(description, capability)]
        writer.event(
            "gap_rank",
            count=count,
            description=sample.description,
            missing_capability=sample.missing_capability,
            example_image_id=sample.image_id,
            example_timestamp=sample.timestamp,
        )

    writer.result(
        message=f"{len(rows)} unique gap pattern(s) (top {top or 'unbounded'})",
        unique_patterns=len(rows),
        total_gaps=sum(counter.values()),
        images_scanned=len(image_ids),
        filter={"since": since, "image": image, "top": top},
    )


# --- show ----------------------------------------------------------------


@app.command("show")
def show(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image identifier."),
) -> None:
    """Show all gap entries for one image, chronological (oldest first)."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace_root = _resolve_workspace_root(ctx)
    path = _gap_path(workspace_root, image_id)

    if not path.exists():
        writer.event(
            "warning",
            message=f"no vocabulary_gaps.jsonl for image_id {image_id!r}",
            path=str(path),
        )
        writer.result(message="0 gaps", count=0, image_id=image_id)
        return

    gaps = _read_gaps(path)
    gaps.sort(key=lambda g: g.timestamp)  # oldest first

    for gap in gaps:
        writer.event(
            "gap_entry",
            timestamp=gap.timestamp,
            description=gap.description,
            workaround=gap.workaround,
            intent_category=gap.intent_category,
            missing_capability=gap.missing_capability,
            operations_involved=gap.operations_involved,
            vocabulary_used=gap.vocabulary_used,
            satisfaction=gap.satisfaction,
            notes=gap.notes,
        )

    writer.result(
        message=f"{len(gaps)} gap(s) for image {image_id!r}",
        count=len(gaps),
        image_id=image_id,
        path=str(path),
    )


# --- clear ---------------------------------------------------------------


@app.command("clear")
def clear(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image identifier."),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the confirmation prompt. Use after you've reviewed and "
        "addressed the gaps for this image.",
    ),
) -> None:
    """Delete the vocabulary_gaps.jsonl for one image (opt-in cleanup).

    Intended for use after the photographer / maintainer has reviewed
    the image's gaps and either authored missing primitives or decided
    they don't need addressing. The file is deleted, not truncated, so
    a fresh empty file is created when the agent next logs a gap.
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace_root = _resolve_workspace_root(ctx)
    path = _gap_path(workspace_root, image_id)

    if not path.exists():
        writer.event(
            "warning",
            message=f"no vocabulary_gaps.jsonl for image_id {image_id!r}",
            path=str(path),
        )
        writer.result(message="nothing to clear", cleared=False, image_id=image_id)
        return

    count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

    if not yes:
        confirm = typer.confirm(
            f"Delete {count} gap entr{'y' if count == 1 else 'ies'} for image {image_id!r}?"
        )
        if not confirm:
            writer.event("info", message="cancelled by user")
            writer.result(message="cancelled", cleared=False, image_id=image_id)
            return

    path.unlink()
    writer.result(
        message=f"cleared {count} gap(s) for image {image_id!r}",
        cleared=True,
        deleted_count=count,
        image_id=image_id,
        path=str(path),
    )


_PUBLIC_HELPERS: dict[str, Any] = {
    "_iter_image_ids": _iter_image_ids,
    "_parse_since": _parse_since,
    "_aggregation_key": _aggregation_key,
}
