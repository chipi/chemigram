"""Modversion drift detection at vocabulary-load time.

Closes RFC-007 (the long-pending Draft v0.1) into ADR-082. The policy:

1. **Parameterized modules (Tier 1+2 per ADR-081)** — every module with
   a registered Path C decoder has a pinned ``SUPPORTED_MODVERSION``.
   When a manifest entry declares ``modversions: {<module>: N}`` and N
   does NOT match the decoder's pin, this is *certain* drift between
   manifest annotation and engine.

   - **Default behavior**: emit a Python warning (UserWarning) at vocab
     load time naming each affected entry. The vocab still loads — the
     photographer can render and judge whether the binary format
     actually changed meaningfully (modversion bumps sometimes don't
     affect the relevant fields).
   - **Strict mode**: set the env var ``CHEMIGRAM_VOCAB_STRICT_MODVERSION=1``
     to upgrade these warnings to ``ManifestError`` (load fails). For
     CI / production scenarios where silent drift would mask bugs.
   - **Apply-time backstop**: regardless of load-time policy, the
     parameterize registry's ``patch_op_params`` already raises
     ``PatchError`` on mismatch — the load-time warning is an early
     signal, not the only line of defence.

2. **Non-parameterized modules** — ADR-008's opacity policy applies; the
   synthesizer copies bytes verbatim. Drift detection isn't possible
   without darktable-cli introspection (which would cost a subprocess
   call per vocab load), and even when detected the only response is
   "trust darktable to reject if the bytes don't fit". The project
   doesn't intercept here. RFC-007's strict-block alternative was
   rejected in the closing ADR — it'd over-block on benign modversion
   bumps where the binary format is wire-compatible.

The check is fast (registry lookup + dict comparison; no I/O), runs
once per ``VocabularyIndex`` construction, and does not slow render
or apply paths.
"""

from __future__ import annotations

import os
import warnings
from typing import Any

# Build the {module_name: pinned_modversion} map from the parameterize
# registry. Importing locally (function-scoped) to avoid circular import
# at module-load time — vocab loads before parameterize is needed.


def _build_known_pinned_modversions() -> dict[str, int]:
    """Return ``{module_name: SUPPORTED_MODVERSION}`` for every Path C
    decoder registered in :mod:`chemigram.core.parameterize`.

    Functions called at vocab-load time, not at import; safe to call
    repeatedly (cheap)."""
    from chemigram.core.parameterize import (
        bilat,
        colorbalancergb,
        colorequal,
        crop,
        denoiseprofile,
        diffuse,
        exposure,
        filmicrgb,
        grain,
        hazeremoval,
        highlights,
        lens,
        sharpen,
        sigmoid,
        temperature,
        toneequalizer,
        vignette,
    )

    return {
        "bilat": bilat.SUPPORTED_MODVERSION,
        "colorbalancergb": colorbalancergb.SUPPORTED_MODVERSION,
        "colorequal": colorequal.SUPPORTED_MODVERSION,
        "crop": crop.SUPPORTED_MODVERSION,
        "denoiseprofile": denoiseprofile.SUPPORTED_MODVERSION,
        "diffuse": diffuse.SUPPORTED_MODVERSION,
        "exposure": exposure.SUPPORTED_MODVERSION,
        "filmicrgb": filmicrgb.SUPPORTED_MODVERSION,
        "grain": grain.SUPPORTED_MODVERSION,
        "hazeremoval": hazeremoval.SUPPORTED_MODVERSION,
        "highlights": highlights.SUPPORTED_MODVERSION,
        "lens": lens.SUPPORTED_MODVERSION,
        "sharpen": sharpen.SUPPORTED_MODVERSION,
        "sigmoid": sigmoid.SUPPORTED_MODVERSION,
        "temperature": temperature.SUPPORTED_MODVERSION,
        "toneequal": toneequalizer.SUPPORTED_MODVERSION,
        "vignette": vignette.SUPPORTED_MODVERSION,
    }


def _is_strict_mode() -> bool:
    """``CHEMIGRAM_VOCAB_STRICT_MODVERSION`` set to a truthy value
    upgrades drift warnings to errors. Useful for CI or production."""
    val = os.environ.get("CHEMIGRAM_VOCAB_STRICT_MODVERSION", "").strip().lower()
    return val in {"1", "true", "yes", "on"}


def check_entry_modversion_drift(
    entry: Any,  # VocabEntry, unannotated to avoid circular import
    pinned: dict[str, int] | None = None,
) -> list[str]:
    """Return a list of human-readable mismatch messages for one entry.

    Empty list when the entry's declared modversions agree with the
    parameterize registry's pinned modversions for every module that's
    in the registry. Modules without a registered decoder are skipped
    (we don't know the "correct" modversion for them).

    The caller decides whether to warn or raise — see
    :func:`emit_drift_signals` for the standard policy.
    """
    if pinned is None:
        pinned = _build_known_pinned_modversions()
    mismatches: list[str] = []
    declared = getattr(entry, "modversions", None) or {}
    for module, declared_mv in declared.items():
        if module not in pinned:
            continue
        engine_mv = pinned[module]
        if declared_mv != engine_mv:
            mismatches.append(
                f"entry {entry.name!r} declares "
                f"modversions[{module!r}]={declared_mv} but the engine's Path C "
                f"decoder is pinned to mv{engine_mv}. PatchError will fire on "
                f"any apply through this entry; re-author against the current "
                f"darktable version or update the manifest's modversion field."
            )
    return mismatches


def emit_drift_signals(entries: list[Any]) -> None:
    """Walk the loaded entries; emit warnings for every modversion
    mismatch against the parameterize registry. In strict mode (env
    var ``CHEMIGRAM_VOCAB_STRICT_MODVERSION``), aggregate mismatches
    and raise :class:`chemigram.core.vocab.ManifestError` instead.

    Closes RFC-007 / ADR-082 — the warn-loud-configurable-to-block
    policy."""
    pinned = _build_known_pinned_modversions()
    all_mismatches: list[str] = []
    for entry in entries:
        all_mismatches.extend(check_entry_modversion_drift(entry, pinned))

    if not all_mismatches:
        return

    if _is_strict_mode():
        from chemigram.core.vocab import ManifestError

        joined = "\n  - ".join(all_mismatches)
        raise ManifestError(
            f"vocabulary load failed: {len(all_mismatches)} modversion "
            f"mismatch(es) detected and CHEMIGRAM_VOCAB_STRICT_MODVERSION is set:\n  - "
            f"{joined}"
        )

    # Default: warn-loud, vocab still loads.
    for msg in all_mismatches:
        warnings.warn(
            f"modversion drift: {msg}",
            UserWarning,
            stacklevel=3,
        )
