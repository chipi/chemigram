"""Per-plugin modversion drift detection at vocabulary-load time.

Sister to :mod:`_modversion_drift`, which checks the manifest's declared
``modversions: {<module>: N}`` against the engine's pinned ``SUPPORTED_MODVERSION``.
This module checks each plugin's actual ``<module>N</module>`` byte in the
parsed dtstyle file against the same pin.

The two checks catch different bug classes:

- **Manifest drift** — the manifest annotation lies about the modversion.
  The annotation is for humans + tooling; the actual bytes don't change.
  Caught by ``_modversion_drift``.
- **Dtstyle drift** — the dtstyle file's binary bytes encode the wrong
  modversion. Symptom: darktable silently hangs at render (60s timeout)
  because it tries to migrate obsolete bytes for the wrong module
  configuration. Caught here.

The dtstyle-drift bug class surfaced during the v1.10.0 photographer-
survey vocabulary expansion: 25 newly authored entries shipped with
``<module>8</module>`` for ``colorequal`` (correct: ``4``) and similar
mismatches for ``bilat``, ``sharpen``, ``temperature``, ``denoiseprofile``,
``hazeremoval``. Each entry hung darktable for 60s before timing out.
This check would have caught the bug at vocab load time instead.

Policy mirrors RFC-007 / ADR-082:

- **Default**: emit a Python ``UserWarning`` per affected plugin. Vocab
  still loads.
- **Strict mode**: ``CHEMIGRAM_VOCAB_STRICT_MODVERSION=1`` upgrades to
  ``ManifestError``. (Same env var as the manifest-drift check — both
  are "modversion strictness" facets.)
- **Apply-time backstop**: parameterize registry's
  :func:`patch_op_params` already raises ``PatchError`` on mismatch; the
  load-time warning is the early signal.

Only modules with a registered Path C decoder are checked — for opaque
ops the project follows ADR-008 and accepts whatever modversion the
dtstyle declares.
"""

from __future__ import annotations

import warnings
from typing import Any

from chemigram.core.vocab._modversion_drift import (
    _build_known_pinned_modversions,
    _is_strict_mode,
)


def check_entry_dtstyle_modversion_drift(
    entry: Any,
    pinned: dict[str, int] | None = None,
) -> list[str]:
    """Return mismatch messages for plugins whose ``<module>`` byte
    disagrees with the engine's pinned modversion. Empty list when the
    dtstyle's plugin modversions match the parameterize registry.

    Plugins for ops without a registered decoder are skipped — for those
    we have no pinned reference and ADR-008's opaque-bytes policy applies.
    """
    if pinned is None:
        pinned = _build_known_pinned_modversions()
    mismatches: list[str] = []
    dtstyle = getattr(entry, "dtstyle", None)
    if dtstyle is None:
        return mismatches
    for plugin in getattr(dtstyle, "plugins", ()):
        op = plugin.operation
        if op not in pinned:
            continue
        engine_mv = pinned[op]
        plugin_mv = plugin.module
        if plugin_mv != engine_mv:
            mismatches.append(
                f"entry {entry.name!r} plugin {op!r} (multi_priority={plugin.multi_priority}) "
                f"has dtstyle ``<module>{plugin_mv}</module>`` but the engine's Path C "
                f"decoder is pinned to mv{engine_mv}. This is the dtstyle-drift bug "
                f"class: darktable will silently hang at render trying to migrate "
                f"obsolete bytes. Re-author the dtstyle against the current darktable "
                f"version (export from a darktable-GUI session) or fix the generator "
                f"that produced it."
            )
    return mismatches


def emit_dtstyle_drift_signals(entries: list[Any]) -> None:
    """Walk loaded entries; emit warnings for every plugin whose
    ``<module>`` byte disagrees with the engine pin. In strict mode
    (env var ``CHEMIGRAM_VOCAB_STRICT_MODVERSION``), aggregate all
    mismatches and raise :class:`chemigram.core.vocab.ManifestError`."""
    pinned = _build_known_pinned_modversions()
    all_mismatches: list[str] = []
    for entry in entries:
        all_mismatches.extend(check_entry_dtstyle_modversion_drift(entry, pinned))

    if not all_mismatches:
        return

    if _is_strict_mode():
        from chemigram.core.vocab import ManifestError

        joined = "\n  - ".join(all_mismatches)
        raise ManifestError(
            f"vocabulary load failed: {len(all_mismatches)} dtstyle-modversion "
            f"mismatch(es) detected and CHEMIGRAM_VOCAB_STRICT_MODVERSION is set:\n  - "
            f"{joined}"
        )

    for msg in all_mismatches:
        warnings.warn(
            f"dtstyle modversion drift: {msg}",
            UserWarning,
            stacklevel=3,
        )
