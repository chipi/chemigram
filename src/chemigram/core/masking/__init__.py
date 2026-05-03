"""Masking subsystem.

After v1.4.x: drawn-mask only. Masks are encoded directly into darktable's
``masks_history`` XMP element via :mod:`chemigram.core.masking.dt_serialize`,
bound to modules through patched ``blendop_params``. The PNG-producing
``MaskingProvider`` Protocol and bundled providers (CoarseAgent, geometric)
were removed — darktable never read external PNGs (``src/develop/blend.c``
resolves raster masks from in-pipeline pointers, not the filesystem), so
that whole apply path was a silent no-op.

Public API: see :mod:`chemigram.core.masking.dt_serialize` for the
encoders, and :func:`chemigram.core.helpers.apply_with_drawn_mask` for the
high-level apply helper.
"""

from __future__ import annotations
