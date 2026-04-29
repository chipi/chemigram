"""Unit tests for CoarseAgentProvider — descriptor → PNG rasterizer."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from chemigram.core.masking import MaskGenerationError, MaskResult
from chemigram.core.masking.coarse_agent import (
    AgentRequest,
    CoarseAgentProvider,
)


@pytest.fixture
def render_jpeg(tmp_path: Path) -> Path:
    """A 64x32 placeholder render the rasterizer can size against."""
    p = tmp_path / "render.jpg"
    Image.new("RGB", (64, 32), "gray").save(p, "JPEG")
    return p


def _const_ask(descriptor: dict[str, Any]):
    """Factory returning an ask_agent that always responds with `descriptor`."""

    def ask(_request: AgentRequest) -> dict[str, Any]:
        return descriptor

    return ask


def test_rasterizes_bbox(render_jpeg: Path) -> None:
    provider = CoarseAgentProvider(_const_ask({"bbox": [4, 4, 16, 8]}))
    result = provider.generate(target="t", render_path=render_jpeg)
    assert isinstance(result, MaskResult)
    img = Image.open(io.BytesIO(result.png_bytes))
    assert img.mode == "L"
    assert img.size == (64, 32)
    # pixel inside the bbox is set
    assert img.getpixel((10, 6)) == 255
    # pixel outside is zero
    assert img.getpixel((40, 20)) == 0


def test_rasterizes_polygon(render_jpeg: Path) -> None:
    provider = CoarseAgentProvider(_const_ask({"polygon_hint": [[0, 0], [10, 0], [5, 10]]}))
    result = provider.generate(target="t", render_path=render_jpeg)
    img = Image.open(io.BytesIO(result.png_bytes))
    assert img.size == (64, 32)
    # apex of the triangle is filled
    assert img.getpixel((5, 5)) == 255


def test_polygon_takes_precedence_over_bbox(render_jpeg: Path) -> None:
    """≥3 polygon points wins over bbox."""
    provider = CoarseAgentProvider(
        _const_ask(
            {
                "bbox": [40, 0, 10, 10],
                "polygon_hint": [[0, 0], [10, 0], [5, 10]],
            }
        )
    )
    result = provider.generate(target="t", render_path=render_jpeg)
    img = Image.open(io.BytesIO(result.png_bytes))
    # bbox region should be empty (polygon won)
    assert img.getpixel((45, 5)) == 0
    # polygon region filled
    assert img.getpixel((5, 5)) == 255


def test_polygon_under_three_points_falls_back_to_bbox(render_jpeg: Path) -> None:
    provider = CoarseAgentProvider(
        _const_ask(
            {
                "bbox": [0, 0, 10, 10],
                "polygon_hint": [[0, 0], [5, 5]],
            }
        )
    )
    result = provider.generate(target="t", render_path=render_jpeg)
    img = Image.open(io.BytesIO(result.png_bytes))
    assert img.getpixel((5, 5)) == 255


def test_dimensions_match_render(render_jpeg: Path) -> None:
    provider = CoarseAgentProvider(_const_ask({"bbox": [0, 0, 1, 1]}))
    result = provider.generate(target="t", render_path=render_jpeg)
    img = Image.open(io.BytesIO(result.png_bytes))
    assert img.size == (64, 32)


def test_invalid_descriptor_raises(render_jpeg: Path) -> None:
    provider = CoarseAgentProvider(_const_ask({}))
    with pytest.raises(MaskGenerationError, match="missing both"):
        provider.generate(target="t", render_path=render_jpeg)


def test_bbox_wrong_arity_raises(render_jpeg: Path) -> None:
    provider = CoarseAgentProvider(_const_ask({"bbox": [1, 2, 3]}))
    with pytest.raises(MaskGenerationError, match="bbox must be"):
        provider.generate(target="t", render_path=render_jpeg)


def test_ask_agent_failure_propagates(render_jpeg: Path) -> None:
    def boom(_req: AgentRequest) -> dict[str, Any]:
        raise MaskGenerationError("agent declined")

    provider = CoarseAgentProvider(boom)
    with pytest.raises(MaskGenerationError, match="agent declined"):
        provider.generate(target="t", render_path=render_jpeg)


def test_regenerate_passes_prior_mask(render_jpeg: Path) -> None:
    captured: dict[str, Any] = {}

    def ask(req: AgentRequest) -> dict[str, Any]:
        captured["prior"] = req.prior_mask
        captured["prompt"] = req.prompt
        return {"bbox": [0, 0, 10, 10]}

    provider = CoarseAgentProvider(ask)
    provider.regenerate(
        target="t",
        render_path=render_jpeg,
        prior_mask=b"prior-png-bytes",
        prompt="tighter edges",
    )
    assert captured["prior"] == b"prior-png-bytes"
    assert captured["prompt"] == "tighter edges"


def test_mask_bytes_are_valid_png(render_jpeg: Path) -> None:
    provider = CoarseAgentProvider(_const_ask({"bbox": [0, 0, 5, 5]}))
    result = provider.generate(target="t", render_path=render_jpeg)
    assert result.png_bytes.startswith(b"\x89PNG\r\n\x1a\n")


def test_target_propagates_to_result(render_jpeg: Path) -> None:
    provider = CoarseAgentProvider(_const_ask({"bbox": [0, 0, 5, 5]}))
    result = provider.generate(target="manta", render_path=render_jpeg)
    assert result.target == "manta"
    assert result.generator == "coarse_agent"


def test_prompt_propagates_to_result(render_jpeg: Path) -> None:
    provider = CoarseAgentProvider(_const_ask({"bbox": [0, 0, 5, 5]}))
    result = provider.generate(target="t", render_path=render_jpeg, prompt="centered subject")
    assert result.prompt == "centered subject"
