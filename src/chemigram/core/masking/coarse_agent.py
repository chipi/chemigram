"""``CoarseAgentProvider`` — bundled default masker.

Uses MCP sampling to ask the calling agent (e.g., Claude with vision) for
a region descriptor against the rendered preview, then rasterizes that
descriptor to a grayscale PNG via Pillow. No PyTorch, no model weights —
satisfies ADR-007 (BYOA) for the bundled default.

The provider is intentionally split into two concerns:

1. **Asking the agent.** Encapsulated in the ``ask_agent`` callable
   passed to the constructor. The callable takes a structured request and
   returns a structured descriptor. Tests inject a fake; the production
   wiring (MCP sampling round-trip) lives in
   :mod:`chemigram.mcp.tools.masks` (#18) where the server's sampling
   callback is in scope.

2. **Rasterizing the descriptor.** Pure Pillow — turns a ``{bbox, polygon_hint?}``
   shape into a PNG matching the render's dimensions.

The split keeps the rasterizer trivially testable and keeps
``chemigram.core.masking`` free of any ``mcp`` SDK import (matching the
"core has no transport-specific deps" pattern from v0.3.0).
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol

from PIL import Image, ImageDraw

from chemigram.core.masking import (
    MaskGenerationError,
    MaskResult,
)


@dataclass(frozen=True)
class AgentRequest:
    """Inputs to the agent-ask callable. Frozen for thread safety."""

    target: str
    render_path: Path
    prompt: str | None
    prior_mask: bytes | None


class AskAgent(Protocol):
    """Callable that asks the agent for a region descriptor.

    Returns: ``{"bbox": [x, y, w, h], "polygon_hint": [[x, y], ...] | None,
    "confidence": float}``. Raises :class:`MaskGenerationError` on any
    failure (sampling declined, malformed JSON, schema mismatch).
    """

    def __call__(self, request: AgentRequest) -> dict[str, Any]: ...


class CoarseAgentProvider:
    """MCP-sampling-based bundled default masker."""

    def __init__(self, ask_agent: AskAgent) -> None:
        self._ask = ask_agent

    def generate(
        self,
        *,
        target: str,
        render_path: Path,
        prompt: str | None = None,
    ) -> MaskResult:
        descriptor = self._ask(
            AgentRequest(
                target=target,
                render_path=render_path,
                prompt=prompt,
                prior_mask=None,
            )
        )
        png = _rasterize(descriptor, render_path)
        return MaskResult(
            png_bytes=png,
            generator="coarse_agent",
            prompt=prompt,
            target=target,
        )

    def regenerate(
        self,
        *,
        target: str,
        render_path: Path,
        prior_mask: bytes,
        prompt: str | None = None,
    ) -> MaskResult:
        descriptor = self._ask(
            AgentRequest(
                target=target,
                render_path=render_path,
                prompt=prompt,
                prior_mask=prior_mask,
            )
        )
        png = _rasterize(descriptor, render_path)
        return MaskResult(
            png_bytes=png,
            generator="coarse_agent",
            prompt=prompt,
            target=target,
        )


def _rasterize(descriptor: dict[str, Any], render_path: Path) -> bytes:
    """Convert a descriptor to a grayscale PNG matching ``render_path``'s
    dimensions. ``polygon_hint`` (≥3 points) takes precedence over
    ``bbox``. Raises :class:`MaskGenerationError` on neither-present.
    """
    with Image.open(render_path) as ref:
        width, height = ref.size

    canvas = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(canvas)

    polygon_hint = descriptor.get("polygon_hint")
    bbox = descriptor.get("bbox")

    if polygon_hint and len(polygon_hint) >= 3:
        points = [(int(p[0]), int(p[1])) for p in polygon_hint]
        draw.polygon(points, fill=255)
    elif bbox is not None:
        if len(bbox) != 4:
            raise MaskGenerationError(f"bbox must be [x, y, w, h] (4 ints), got {bbox!r}")
        x, y, bw, bh = (int(v) for v in bbox)
        draw.rectangle([x, y, x + bw, y + bh], fill=255)
    else:
        raise MaskGenerationError(
            f"descriptor missing both bbox and usable polygon_hint: {descriptor!r}"
        )

    buf = BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


__all__ = [
    "AgentRequest",
    "AskAgent",
    "CoarseAgentProvider",
]
