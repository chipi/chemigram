"""Cross-image state propagation (RFC-037).

The architectural primitive missing from chemigram surfaced by the
photographer-workflows survey (Wedding/Event genre, 4/6 photographers
ship anchor-and-sync as load-bearing). Same mental model as Lightroom's
Sync function: edit one anchor image, propagate the resulting state to
N similar-light targets in one atomic call.

Default behavior: inherit EVERYTHING from the source's edit history,
auto-excluding ops that depend on per-image content / coordinates
(drawn masks, retouch, crop, L1 baselines). Optional caller-supplied
``exclude_ops`` for the rare "everything except <X>" case.

Atomic semantics: validation phase walks all targets first; only after
all validations pass does any apply happen. Either all targets receive
the propagated state or none do.
"""

from __future__ import annotations

from dataclasses import dataclass

from chemigram.core.workspace import Workspace
from chemigram.core.xmp import HistoryEntry, Xmp

# Soft cap on targets per call. Wedding lighting groups typically max out
# at ~80-100 images; bird bursts at ~30. 200 is generous-but-finite.
MAX_TARGETS_PER_CALL = 200

# Operations that depend on per-image content / coordinates and don't
# propagate cleanly across different images. Matches Lightroom's Sync
# discipline — settings tied to framing don't sync.
FRAMING_BOUND_OPS: frozenset[str] = frozenset(
    {
        # Compositional crop is per-image
        "ashift",
        "crop",
        # Retouch (heal/clone) is location-specific (RFC-025 / ADR-087)
        "retouch",
        # Lens correction is per-camera but EXIF-bound; usually consistent
        # within a batch, but not across mixed-camera sets. Auto-excluded
        # to match "no propagation across cameras" wedding discipline;
        # opt-in via include_per_image=True for single-camera workflows.
        "lens",
    }
)


class PropagateError(Exception):
    """Raised when propagate_state validation fails."""


@dataclass(frozen=True)
class PropagateResult:
    """Per-target result of a successful propagation."""

    image_id: str
    snapshot_hash: str
    applied_ops: tuple[str, ...]


@dataclass(frozen=True)
class PropagateBatchResult:
    """Aggregate result of a propagate_state batch."""

    results: tuple[PropagateResult, ...]
    n_succeeded: int
    n_failed: int  # always 0 for atomic-success batches; reserved for future


def filter_history_for_propagation(
    history: tuple[HistoryEntry, ...],
    *,
    exclude_ops: list[str] | None = None,
    include_per_image: bool = False,
) -> tuple[HistoryEntry, ...]:
    """Filter the source history to the subset that propagates cleanly.

    By default excludes:
    - All ops in :data:`FRAMING_BOUND_OPS` (drawn masks, retouch, crop,
      lens) unless ``include_per_image=True``.
    - History entries with drawn-mask bindings (mask_mode flag set) —
      coordinate-specific and don't apply to other images.
    - Any op explicitly listed in ``exclude_ops``.

    Returns the surviving entries in source order. The caller applies them
    sequentially against each target's baseline.
    """
    if exclude_ops is None:
        exclude_ops = []
    excluded = set(exclude_ops)
    result = []
    for entry in history:
        if entry.operation in excluded:
            continue
        if not include_per_image and entry.operation in FRAMING_BOUND_OPS:
            continue
        if not include_per_image and _is_drawn_mask_bound(entry):
            continue
        result.append(entry)
    return tuple(result)


def _is_drawn_mask_bound(entry: HistoryEntry) -> bool:
    """Return True if the history entry's blendop_params indicates a drawn-
    mask binding (mask_mode flag with the ENABLED|MASK bit set per ADR-085).

    Drawn masks are coordinate-specific (eye-region ellipse, retouch
    spot) and don't propagate cleanly to images with different framing.
    Detected via the blendop blob's mask_mode field — value 3 (ENABLED|
    DRAWN) or 7 (DRAWN+CONDITIONAL) indicate a drawn-form binding.
    """
    from chemigram.core.masking.dt_serialize import _decode_default_blendop_blob

    blendop_str = entry.blendop_params
    if not blendop_str:
        return False
    try:
        if blendop_str.startswith("gz"):
            raw = _decode_default_blendop_blob(blendop_str)
        else:
            raw = bytes.fromhex(blendop_str)
    except (ValueError, OSError):
        return False
    # mask_mode is the second 4-byte int in the blendop struct (offset 4..7)
    if len(raw) < 8:
        return False
    import struct

    mask_mode = struct.unpack("<I", raw[4:8])[0]
    # DT_DEV_PIXELPIPE_DISPLAY_MASK = 3; DRAWN+CONDITIONAL = 7
    return mask_mode in (3, 7)


def propagate_state(
    source_workspace: Workspace,
    target_workspaces: list[Workspace],
    *,
    exclude_ops: list[str] | None = None,
    include_per_image: bool = False,
    label: str | None = None,
) -> PropagateBatchResult:
    """Propagate the source workspace's current edit state to N targets
    atomically (RFC-037).

    Args:
        source_workspace: The anchor workspace (edits propagate FROM).
        target_workspaces: List of workspaces (edits propagate TO).
            Soft cap at MAX_TARGETS_PER_CALL.
        exclude_ops: Optional list of operations to skip. Defaults to None
            (= empty list = inherit everything except the framing-bound
            auto-exclusion set).
        include_per_image: If True, also propagate framing-bound ops (drawn
            masks, retouch, crop, lens). Default False matches Lightroom's
            Sync discipline.
        label: Optional snapshot label per target. Default:
            "propagated from <source_image_id> [<n_ops> ops]".

    Returns:
        :class:`PropagateBatchResult` with per-target snapshot hashes.

    Raises:
        PropagateError: validation fails — atomic, no targets receive
            partial state.
    """
    from chemigram.core.dtstyle import DtstyleEntry, PluginEntry
    from chemigram.core.helpers import current_xmp
    from chemigram.core.versioning.ops import snapshot
    from chemigram.core.xmp import synthesize_xmp

    _validate_batch_shape(source_workspace, target_workspaces)

    source_xmp = current_xmp(source_workspace)
    if source_xmp is None:
        raise PropagateError(
            f"source workspace {source_workspace.image_id!r} has no current XMP "
            f"(no anchor edit to propagate from)"
        )

    filtered = filter_history_for_propagation(
        source_xmp.history,
        exclude_ops=exclude_ops,
        include_per_image=include_per_image,
    )
    if not filtered:
        raise PropagateError(
            "filter produced empty op set — nothing to propagate. "
            "Source has no eligible history; check exclude_ops + include_per_image."
        )

    # Validation phase: walk every target, ensure baseline exists.
    # No mutation yet (atomic discipline).
    target_baselines: list[tuple[Workspace, Xmp]] = []
    for target_ws in target_workspaces:
        target_xmp = current_xmp(target_ws)
        if target_xmp is None:
            raise PropagateError(
                f"target workspace {target_ws.image_id!r} has no current XMP "
                f"(no baseline to apply propagation onto)"
            )
        target_baselines.append((target_ws, target_xmp))

    # Round-trip filtered history → DtstyleEntry → reuse synthesize_xmp's
    # SET-replace + Path B logic. The XMP HistoryEntry shape and the
    # PluginEntry shape carry the same data with different field names
    # (params → op_params, modversion → module).
    propagated_plugins = tuple(
        PluginEntry(
            operation=h.operation,
            num=h.num,
            module=h.modversion,
            op_params=h.params,
            blendop_params=h.blendop_params,
            blendop_version=h.blendop_version,
            multi_priority=h.multi_priority,
            multi_name=h.multi_name,
            enabled=h.enabled,
        )
        for h in filtered
    )
    propagated_dtstyle = DtstyleEntry(
        name=f"_propagated_from_{source_workspace.image_id}",
        description=f"Propagated state from {source_workspace.image_id} ({len(filtered)} ops)",
        iop_list=None,
        plugins=propagated_plugins,
    )

    n_ops = len(filtered)
    label_default = f"propagated from {source_workspace.image_id} [{n_ops} ops]"
    snapshot_label = label if label else label_default

    # Apply phase. Per-target snapshot.
    results: list[PropagateResult] = []
    applied_op_names = tuple(e.operation for e in filtered)
    for target_ws, target_baseline in target_baselines:
        new_xmp = synthesize_xmp(target_baseline, [propagated_dtstyle])
        new_hash = snapshot(target_ws.repo, new_xmp, label=snapshot_label)
        results.append(
            PropagateResult(
                image_id=target_ws.image_id,
                snapshot_hash=new_hash,
                applied_ops=applied_op_names,
            )
        )

    return PropagateBatchResult(
        results=tuple(results),
        n_succeeded=len(results),
        n_failed=0,
    )


def _validate_batch_shape(
    source_workspace: Workspace,
    target_workspaces: list[Workspace],
) -> None:
    """Hard-reject batches that fail shape requirements before any work."""
    if not target_workspaces:
        raise PropagateError(
            "target_workspaces is empty; propagate_state requires at least one target"
        )
    if len(target_workspaces) > MAX_TARGETS_PER_CALL:
        raise PropagateError(
            f"target count ({len(target_workspaces)}) exceeds soft cap "
            f"({MAX_TARGETS_PER_CALL}); split the batch"
        )
    source_id = source_workspace.image_id
    for target in target_workspaces:
        if target.image_id == source_id:
            raise PropagateError(
                f"source and target both refer to {source_id!r}; "
                f"propagating to oneself is a no-op and almost always a bug"
            )
    seen: set[str] = set()
    for target in target_workspaces:
        if target.image_id in seen:
            raise PropagateError(
                f"duplicate target image_id {target.image_id!r}; "
                f"each target must appear at most once"
            )
        seen.add(target.image_id)
