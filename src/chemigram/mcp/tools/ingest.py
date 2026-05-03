"""Ingest + workspace orchestration tools (batch 3 of Slice 3).

- ``ingest`` — bootstraps a workspace from a raw path; registers it with
  the server's workspace registry so subsequent tools can find it by id.
- ``bind_layers`` — applies L1 + L2 templates onto the current state and
  snapshots; if both are omitted, returns the existing baseline state.
- ``log_vocabulary_gap`` — appends to ``vocabulary_gaps.jsonl`` (real, no
  stub — pure logging).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chemigram.core.helpers import current_xmp, summarize_state
from chemigram.core.versioning.ops import VersioningError, snapshot
from chemigram.core.workspace import (
    ingest_workspace,
    workspace_id_for,
)
from chemigram.core.xmp import synthesize_xmp
from chemigram.mcp._state import resolve_workspace
from chemigram.mcp.errors import (
    ErrorCode,
    ToolError,
    ToolResult,
    error_invalid_input,
    error_not_found,
)
from chemigram.mcp.registry import ToolContext, register_tool


def _serialize_exif(exif: Any) -> dict[str, Any] | None:
    if exif is None:
        return None
    return {
        "make": exif.make,
        "model": exif.model,
        "lens_model": exif.lens_model,
        "focal_length_mm": exif.focal_length_mm,
    }


# --- ingest -------------------------------------------------------------


async def _ingest(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    raw_path_str = args["raw_path"]
    image_id = args.get("image_id")
    workspace_root = args.get("workspace_root")

    raw_path = Path(raw_path_str).expanduser().resolve()
    if not raw_path.exists():
        return ToolResult.fail(error_not_found(f"raw file {raw_path}"))

    if workspace_root is None:
        # Default per `contracts/per-image-repo`: ~/Pictures/Chemigram
        ws_root = Path.home() / "Pictures" / "Chemigram"
    else:
        ws_root = Path(workspace_root).expanduser().resolve()
    ws_root.mkdir(parents=True, exist_ok=True)

    if image_id is None:
        image_id = workspace_id_for(raw_path)
    if image_id in ctx.workspaces:
        return ToolResult.fail(
            ToolError(
                code=ErrorCode.STATE_ERROR,
                message=f"image_id {image_id!r} already in use; pass a different id",
            )
        )

    try:
        ws = ingest_workspace(
            raw_path,
            workspace_root=ws_root,
            image_id=image_id,
            vocabulary=ctx.vocabulary,
        )
    except FileExistsError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.STATE_ERROR, message=str(exc)))

    ctx.workspaces[ws.image_id] = ws

    return ToolResult.ok(
        {
            "image_id": ws.image_id,
            "root": str(ws.root),
            "exif_summary": _serialize_exif(ws.exif),
            "suggested_bindings": [
                {"name": e.name, "description": e.description} for e in ws.suggested_bindings
            ],
        }
    )


register_tool(
    name="ingest",
    description=(
        "Bootstrap a per-image workspace for a raw file. Creates the directory "
        "layout, reads EXIF, suggests L1 bindings, snapshots a baseline XMP."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "raw_path": {"type": "string"},
            "image_id": {"type": "string"},
            "workspace_root": {"type": "string"},
        },
        "required": ["raw_path"],
        "additionalProperties": False,
    },
    handler=_ingest,
)


# --- bind_layers --------------------------------------------------------


async def _bind_layers(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    l1_template = args.get("l1_template")
    l2_template = args.get("l2_template")
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))

    baseline = current_xmp(workspace)
    if baseline is None:
        return ToolResult.fail(
            ToolError(
                code=ErrorCode.STATE_ERROR,
                message="cannot bind_layers: workspace has no current XMP",
            )
        )

    entries = []
    for name, layer_label in ((l1_template, "L1"), (l2_template, "L2")):
        if name is None:
            continue
        entry = ctx.vocabulary.lookup_by_name(name)
        if entry is None:
            return ToolResult.fail(error_not_found(f"vocabulary entry {name!r} for {layer_label}"))
        if entry.layer != layer_label:
            return ToolResult.fail(
                error_invalid_input(f"{name!r} is layer {entry.layer}, expected {layer_label}")
            )
        entries.append(entry.dtstyle)

    if not entries:
        return ToolResult.ok({"state_after": summarize_state(baseline), "applied": []})

    new_xmp = synthesize_xmp(baseline, entries)
    try:
        h = snapshot(workspace.repo, new_xmp, label="bind_layers")
    except VersioningError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.VERSIONING_ERROR, message=str(exc)))

    return ToolResult.ok(
        {
            "state_after": summarize_state(new_xmp),
            "snapshot_hash": h,
            "applied": [n for n in (l1_template, l2_template) if n is not None],
        }
    )


register_tool(
    name="bind_layers",
    description=(
        "Apply optional L1 and L2 vocabulary templates onto the current XMP "
        "and snapshot the result. With both omitted, returns the current state."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "l1_template": {"type": "string"},
            "l2_template": {"type": "string"},
        },
        "required": ["image_id"],
        "additionalProperties": False,
    },
    handler=_bind_layers,
)


# --- log_vocabulary_gap -------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


_VALID_SATISFACTION = (-1, 0, 1)


def _read_head_hash(repo: Any) -> str | None:
    """Resolve current HEAD hash; returns None if no snapshot exists yet."""
    try:
        return repo.resolve_ref("HEAD")
    except Exception:
        return None


async def _log_vocabulary_gap(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    description = args["description"]

    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))

    if not description.strip():
        return ToolResult.fail(error_invalid_input("description must be non-empty"))

    satisfaction = args.get("satisfaction")
    if satisfaction is not None and satisfaction not in _VALID_SATISFACTION:
        return ToolResult.fail(
            error_invalid_input(f"satisfaction must be -1|0|1, got {satisfaction!r}")
        )

    session_id = ctx.transcript.session_id if ctx.transcript is not None else None
    snapshot_hash = _read_head_hash(workspace.repo)

    record = {
        "timestamp": _now_iso(),
        "image_id": image_id,
        "session_id": session_id,
        "snapshot_hash": snapshot_hash,
        "description": description,
        "workaround": args.get("workaround", ""),
        "intent": args.get("intent"),
        "intent_category": args.get("intent_category", "uncategorized"),
        "missing_capability": args.get("missing_capability"),
        "operations_involved": list(args.get("operations_involved", [])),
        "vocabulary_used": list(args.get("vocabulary_used", [])),
        "satisfaction": satisfaction,
        "notes": args.get("notes", ""),
    }
    workspace.vocabulary_gaps_path.parent.mkdir(parents=True, exist_ok=True)
    with workspace.vocabulary_gaps_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    return ToolResult.ok(
        {
            "path": str(workspace.vocabulary_gaps_path),
            "appended": True,
            "session_id": session_id,
        }
    )


register_tool(
    name="log_vocabulary_gap",
    description=(
        "Append a vocabulary-gap record to the image's vocabulary_gaps.jsonl. "
        "RFC-013 schema. The agent calls this when no primitive matches the "
        "photographer's request. session_id and snapshot_hash auto-populate "
        "from the active session/HEAD when available."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "description": {"type": "string"},
            "workaround": {"type": "string"},
            "intent": {"type": "string"},
            "intent_category": {"type": "string"},
            "missing_capability": {"type": "string"},
            "operations_involved": {"type": "array", "items": {"type": "string"}},
            "vocabulary_used": {"type": "array", "items": {"type": "string"}},
            "satisfaction": {"type": "integer", "enum": [-1, 0, 1]},
            "notes": {"type": "string"},
        },
        "required": ["image_id", "description"],
        "additionalProperties": False,
    },
    handler=_log_vocabulary_gap,
)
