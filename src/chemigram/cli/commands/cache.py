"""``chemigram cache`` sub-app — manage the per-image preview cache.

Each image's ``previews/`` directory accumulates JPEGs from
``render_preview`` calls (filename pattern: ``preview_<hash16>_<size>.jpg``).
These are regenerable from snapshots so removing them is safe; they're
useful for fast re-display of past states. Over time the cache grows.

Sister sub-app to ``gap-log`` and ``session-log``: read-side tooling
without mutating edit state.

Commands:
    list  — newest-first listing of cached previews across all images
    size  — aggregate disk usage (total + per-image)
    clear — opt-in removal of cached previews (with confirmation)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import typer

from chemigram.cli._context import CliContext
from chemigram.cli._workspace import default_workspace_root
from chemigram.cli.exit_codes import ExitCode

app = typer.Typer(no_args_is_help=True)


def _resolve_workspace_root(ctx: typer.Context) -> Path:
    obj = cast(CliContext, ctx.obj)
    return obj.get("workspace") or default_workspace_root()


def _iter_image_ids(workspace_root: Path) -> list[str]:
    """Image_ids in the workspace root (objects/ + raw/ signature)."""
    if not workspace_root.exists():
        return []
    out: list[str] = []
    for child in workspace_root.iterdir():
        if not child.is_dir():
            continue
        if (child / "objects").is_dir() and (child / "raw").is_dir():
            out.append(child.name)
    return sorted(out)


def _previews_dir(workspace_root: Path, image_id: str) -> Path:
    return workspace_root / image_id / "previews"


def _list_preview_files(previews_dir: Path) -> list[Path]:
    if not previews_dir.exists():
        return []
    return sorted(previews_dir.glob("*.jpg"))


def _human_bytes(n: int) -> str:
    """Render byte count as a human-friendly string (KB/MB/GB)."""
    for unit, denom in (("GB", 1024**3), ("MB", 1024**2), ("KB", 1024)):
        if n >= denom:
            return f"{n / denom:.1f} {unit}"
    return f"{n} B"


def _parse_since(spec: str) -> datetime:
    """Parse '7d', '24h', '30m' into a timestamp threshold."""
    spec = spec.strip().lower()
    if spec.endswith("d"):
        delta = timedelta(days=int(spec[:-1]))
    elif spec.endswith("h"):
        delta = timedelta(hours=int(spec[:-1]))
    elif spec.endswith("m"):
        delta = timedelta(minutes=int(spec[:-1]))
    else:
        raise ValueError(f"unknown duration {spec!r}; use Nd / Nh / Nm")
    return datetime.now(UTC) - delta


@app.command("list")
def list_(
    ctx: typer.Context,
    image: str | None = typer.Option(None, "--image", help="Restrict to one image_id."),
    since: str | None = typer.Option(
        None,
        "--since",
        help="Only show previews modified within this window (e.g. 7d, 24h, 30m).",
    ),
) -> None:
    """List cached preview JPEGs newest-first across the workspace.

    Each row reports image_id, filename, size (bytes + human-friendly),
    and modified time. Matches the gap-log / session-log row pattern.
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    workspace_root = _resolve_workspace_root(ctx)
    image_ids = [image] if image else _iter_image_ids(workspace_root)

    threshold: datetime | None = None
    if since is not None:
        try:
            threshold = _parse_since(since)
        except ValueError as exc:
            writer.error(str(exc), ExitCode.INVALID_INPUT, since=since)
            raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc

    rows: list[tuple[Path, str, int, datetime]] = []
    for img_id in image_ids:
        for path in _list_preview_files(_previews_dir(workspace_root, img_id)):
            stat = path.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
            if threshold is not None and mtime < threshold:
                continue
            rows.append((path, img_id, stat.st_size, mtime))
    rows.sort(key=lambda r: r[3], reverse=True)

    for path, img_id, size, mtime in rows:
        writer.event(
            "cache_entry",
            image_id=img_id,
            filename=path.name,
            path=str(path),
            size_bytes=size,
            size_human=_human_bytes(size),
            modified=mtime.isoformat(),
        )

    total_size = sum(r[2] for r in rows)
    writer.result(
        message=(
            f"{len(rows)} cached preview(s) across {len(image_ids)} image(s); "
            f"{_human_bytes(total_size)} total"
        ),
        count=len(rows),
        total_bytes=total_size,
        total_human=_human_bytes(total_size),
    )


@app.command("size")
def size(
    ctx: typer.Context,
    image: str | None = typer.Option(None, "--image", help="Restrict to one image_id."),
) -> None:
    """Aggregate cache size: total bytes + per-image breakdown."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    workspace_root = _resolve_workspace_root(ctx)
    image_ids = [image] if image else _iter_image_ids(workspace_root)

    per_image: list[tuple[str, int, int]] = []  # (image_id, file_count, bytes)
    for img_id in image_ids:
        files = _list_preview_files(_previews_dir(workspace_root, img_id))
        total = sum(p.stat().st_size for p in files)
        if files:
            per_image.append((img_id, len(files), total))
    per_image.sort(key=lambda r: r[2], reverse=True)

    for img_id, count, total in per_image:
        writer.event(
            "cache_size",
            image_id=img_id,
            file_count=count,
            size_bytes=total,
            size_human=_human_bytes(total),
        )

    total_size = sum(r[2] for r in per_image)
    total_files = sum(r[1] for r in per_image)
    writer.result(
        message=(
            f"{total_files} cached preview(s) across {len(per_image)} image(s); "
            f"{_human_bytes(total_size)} total"
        ),
        file_count=total_files,
        total_bytes=total_size,
        total_human=_human_bytes(total_size),
    )


@app.command("clear")
def clear(
    ctx: typer.Context,
    image: str | None = typer.Option(None, "--image", help="Restrict to one image_id."),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation; required for non-interactive use.",
    ),
) -> None:
    """Remove cached preview JPEGs.

    Previews are regenerable from snapshots, so this is a safe cleanup
    operation. Requires ``--yes`` to skip the interactive confirmation
    prompt; without ``--yes``, prints what would be removed and exits
    without modifying anything (matches the gap-log clear UX).

    Removes only ``previews/*.jpg`` files. The directory itself is
    preserved (other tools assume it exists).
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    workspace_root = _resolve_workspace_root(ctx)
    image_ids = [image] if image else _iter_image_ids(workspace_root)

    targets: list[Path] = []
    for img_id in image_ids:
        targets.extend(_list_preview_files(_previews_dir(workspace_root, img_id)))

    total_size = sum(p.stat().st_size for p in targets)

    if not yes:
        writer.event(
            "cache_clear_dry_run",
            file_count=len(targets),
            total_bytes=total_size,
            total_human=_human_bytes(total_size),
        )
        writer.result(
            message=(
                f"would remove {len(targets)} preview(s) "
                f"({_human_bytes(total_size)}); rerun with --yes to confirm"
            ),
            file_count=len(targets),
            total_bytes=total_size,
            removed=False,
        )
        return

    removed_count = 0
    for path in targets:
        try:
            path.unlink()
            removed_count += 1
        except OSError as exc:
            writer.event(
                "cache_clear_error",
                path=str(path),
                error=str(exc),
            )

    writer.result(
        message=f"removed {removed_count}/{len(targets)} preview(s) ({_human_bytes(total_size)})",
        file_count=removed_count,
        total_bytes=total_size,
        removed=True,
    )
