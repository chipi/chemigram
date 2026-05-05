"""Path C runtime: decode/edit/re-encode darktable module ``op_params`` blobs.

Per RFC-021 / ADR-077, modules with a manifest ``parameters`` block route
through this package at apply time so a caller can supply continuous
magnitude values (e.g., ``exposure --value 0.7``) without enumerating
discrete vocabulary entries. Each supported module provides a
``patch(op_params: str, **values) -> str`` function that decodes the
opaque hex blob, edits the named fields, re-encodes, and returns the
new hex string.

ADR-008's opacity policy still applies to non-parameterized modules and
to ``blendop_params`` universally (mask binding has its own byte-level
codec at :mod:`chemigram.core.masking.dt_serialize`).

Public surface:
    - :func:`patch_op_params` — registry-routed entry point keyed by
      module name + modversion. The apply path in
      :mod:`chemigram.core.helpers` calls this when a vocabulary entry
      with a ``parameters`` block is applied with caller-supplied values.
    - :class:`PatchError` — raised on modversion mismatch, blob-size
      mismatch, or unknown module.
"""

from __future__ import annotations

from collections.abc import Callable

from chemigram.core.parameterize import exposure, vignette


class PatchError(Exception):
    """Raised when a Path C decoder cannot produce a valid output."""


# Registry: (module_name, modversion) -> callable(op_params, **values) -> patched op_params hex.
# Keys are pinned so a darktable modversion bump fails loud rather than
# silently corrupting bytes.
_PATCH_REGISTRY: dict[tuple[str, int], Callable[..., str]] = {
    ("exposure", 7): exposure.patch,
    ("vignette", 4): vignette.patch,
}


def patch_op_params(
    op_params: str,
    *,
    module: str,
    modversion: int,
    values: dict[str, float],
) -> str:
    """Apply caller-supplied parameter ``values`` to a module's ``op_params``.

    Args:
        op_params: hex-encoded ``op_params`` from the source ``.dtstyle``.
        module: darktable iop module name (e.g. ``"exposure"``).
        modversion: pinned struct version. Must match the registry's
            registered version for ``module``; mismatch raises
            :class:`PatchError`.
        values: parameter name → value, scoped to this module.

    Returns:
        New hex-encoded ``op_params`` with the named fields patched.

    Raises:
        PatchError: ``(module, modversion)`` not in the registry, or the
            decoder rejects the input blob (size mismatch, etc.).
    """
    key = (module, modversion)
    if key not in _PATCH_REGISTRY:
        raise PatchError(
            f"no Path C decoder registered for {module}@{modversion}; "
            f"known: {sorted(_PATCH_REGISTRY.keys())}"
        )
    fn = _PATCH_REGISTRY[key]
    return fn(op_params, **values)


__all__ = ["PatchError", "exposure", "patch_op_params", "vignette"]
