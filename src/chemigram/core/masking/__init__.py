"""Masking provider abstraction.

Per **RFC-009** (closing in v0.4.0 via ADR-057): a :class:`MaskingProvider`
produces grayscale-PNG masks for a target on a rendered image. Per ADR-007
(BYOA), no PyTorch in core; the bundled default
:class:`~chemigram.core.masking.coarse_agent.CoarseAgentProvider` uses MCP
sampling — the calling agent (e.g., Claude with vision) is the masker.
Production-quality masking lives in the sibling ``chemigram-masker-sam``
project (Phase 4) and implements the same Protocol.

The Protocol is sync; if asynchronous providers become necessary,
``MaskingProvider.generate_async`` is reserved for a follow-up RFC.

Public API:
    - :class:`MaskingProvider` — the contract
    - :class:`MaskResult` — return value
    - :class:`MaskingError`, :class:`MaskGenerationError`,
      :class:`MaskFormatError` — exception hierarchy
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class MaskingError(Exception):
    """Base class for masking errors."""


class MaskGenerationError(MaskingError):
    """Raised when the provider cannot produce a mask.

    Common causes: sampling declined by the calling client, descriptor
    invalid (missing both ``bbox`` and ``polygon_hint``), prior-mask path
    unreadable.
    """


class MaskFormatError(MaskingError):
    """Raised when produced bytes don't form a valid PNG."""


@dataclass(frozen=True)
class MaskResult:
    """One mask production result.

    Attributes:
        png_bytes: Grayscale PNG (8-bit, target=255 / outside=0 per
            ADR-021). Caller's responsibility to register via
            :func:`chemigram.core.versioning.masks.register_mask`.
        generator: Provider id (``"coarse_agent"``, ``"sam_provider"``…).
        prompt: Refinement prompt used (``None`` on first generation).
        target: The target descriptor that produced this mask.
    """

    png_bytes: bytes
    generator: str
    prompt: str | None
    target: str


class MaskingProvider(Protocol):
    """Sync provider contract.

    Concrete implementations: :class:`CoarseAgentProvider` (bundled),
    ``chemigram-masker-sam``'s ``SamProvider`` (sibling project, Phase 4).
    """

    def generate(
        self,
        *,
        target: str,
        render_path: Path,
        prompt: str | None = None,
    ) -> MaskResult:
        """Produce a mask for ``target`` against the image at ``render_path``."""
        ...

    def regenerate(
        self,
        *,
        target: str,
        render_path: Path,
        prior_mask: bytes,
        prompt: str | None = None,
    ) -> MaskResult:
        """Refine an existing mask. Implementations may delegate to
        :meth:`generate` if they don't make use of the prior mask."""
        ...


__all__ = [
    "MaskFormatError",
    "MaskGenerationError",
    "MaskResult",
    "MaskingError",
    "MaskingProvider",
]
