"""Canonical registry of framing-bound darktable operations.

A *framing-bound* op produces results tied to a specific image's
coordinates, framing, or per-image content. Such ops don't propagate
cleanly across different images and are auto-excluded from
:func:`chemigram.core.propagate.propagate_state` by default.

The bug class this prevents: a future op with per-image-framing
characteristics gets added (e.g., a perspective sub-mode of ashift, a
depth-aware op) and the propagate-state callsite forgets to flag it as
framing-bound. The single-source-of-truth registry here means the only
edit needed to teach propagate (and any future cross-image tool) about
the new op is adding it to :data:`FRAMING_BOUND_OPS`.

Closes Gap D from the RFC-035/036/037 retro.

The detection has two layers:

1. **Op-level** — ops in :data:`FRAMING_BOUND_OPS` are framing-bound
   regardless of their parameters or which entry uses them. ``ashift``
   is always per-camera-angle; ``crop`` is always per-composition;
   ``retouch`` is always location-specific; ``lens`` is always
   per-camera. This list is the canonical registry.

2. **Mask-level** — runtime check on ``blendop_params``. An entry that
   uses a drawn-form mask (gradient / ellipse / rectangle / path) has
   image-coordinate-specific geometry and is framing-bound. Detected by
   :func:`chemigram.core.propagate._is_drawn_mask_bound`. Parametric
   range masks (color-range / luminance-range) are content-relative and
   DO propagate.
"""

from __future__ import annotations

# The canonical op-level framing-bound registry.
#
# When adding a new entry: include it here AND verify any test that
# exercises propagate_state's exclusion semantics covers the new op.
FRAMING_BOUND_OPS: frozenset[str] = frozenset(
    {
        # Compositional crop — per-image framing.
        "crop",
        # Perspective correction — per-camera-angle.
        "ashift",
        # Retouch heal/clone — location-specific spots (RFC-025 / ADR-087).
        "retouch",
        # Lens correction — per-camera; EXIF-bound. Usually consistent
        # within a batch from one body+lens, but mixed-camera sets
        # produce wrong color science. Auto-excluded; opt-in via
        # ``include_per_image=True`` for single-camera workflows.
        "lens",
    }
)


def is_framing_bound_op(operation: str) -> bool:
    """Return True if ``operation`` is in the canonical framing-bound
    registry. Mirror of ``operation in FRAMING_BOUND_OPS`` exposed as a
    function for callers that prefer not to import the constant."""
    return operation in FRAMING_BOUND_OPS
