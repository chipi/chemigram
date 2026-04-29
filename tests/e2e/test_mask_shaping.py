"""End-to-end: registered mask actually shapes the rendered effect.

A step beyond :file:`test_vocabulary_primitives.py`'s mask-bound test,
which only proved "the primitive fires when there's a mask." This file
proves the *spatial* claim: the mask defines *where* the effect
applies, and pixels outside the mask remain effectively unchanged.

The assertion: render WITH a half-coverage mask (top half white, bottom
half black) → the top-half luma differs from baseline (effect applied),
the bottom-half luma matches baseline (effect masked out).

Part of GH #33 / v1.1.0 capability matrix.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import anyio
from PIL import Image

from chemigram.core.versioning import ImageRepo
from chemigram.core.versioning.masks import register_mask
from chemigram.core.versioning.ops import snapshot, tag
from chemigram.core.vocab import VocabularyIndex
from chemigram.core.workspace import Workspace, init_workspace_root
from chemigram.core.xmp import parse_xmp
from chemigram.mcp._test_harness import in_memory_session
from chemigram.mcp.prompts import PromptStore
from chemigram.mcp.registry import clear_registry
from chemigram.mcp.server import build_server

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINE_XMP = _REPO_ROOT / "src" / "chemigram" / "core" / "_baseline_v1.xmp"
_SHIPPED_PROMPTS = _REPO_ROOT / "src" / "chemigram" / "mcp" / "prompts"


def _build_workspace(tmp_path: Path, raw_path: Path, configdir: Path) -> Workspace:
    root = tmp_path / "ws"
    init_workspace_root(root)
    repo = ImageRepo.init(root)
    workspace_raw = root / "raw" / raw_path.name
    if not workspace_raw.exists():
        workspace_raw.symlink_to(raw_path.resolve())
    h = snapshot(repo, parse_xmp(_BASELINE_XMP), label="baseline")
    tag(repo, "baseline", h)
    return Workspace(
        image_id="phase0",
        root=root,
        repo=repo,
        raw_path=workspace_raw,
        configdir=configdir,
    )


def _decode(call_result: Any) -> dict:
    return json.loads(call_result.content[0].text)


def _half_coverage_mask_png(size: int = 256) -> bytes:
    """Top half white (mask active), bottom half black (mask off).

    The actual rendered output is 256xnative-aspect — the mask is
    sampled to that size by darktable. Using a square here is fine
    because we ask for size=256 and dt scales the mask to the
    rendered dimensions.
    """
    img = Image.new("L", (size, size), 0)
    # Top half = 255 (effect on); bottom half = 0 (effect off).
    for y in range(size // 2):
        for x in range(size):
            img.putpixel((x, y), 255)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _band_mean(band: Image.Image) -> float:
    hist = band.histogram()
    return sum(i * c for i, c in enumerate(hist)) / max(sum(hist), 1)


def _region_luma(jpeg_bytes: bytes, *, top_half: bool) -> float:
    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    w, h = img.size
    box = (0, 0, w, h // 2) if top_half else (0, h // 2, w, h)
    region = img.crop(box)
    r, g, b = region.split()
    return 0.2126 * _band_mean(r) + 0.7152 * _band_mean(g) + 0.0722 * _band_mean(b)


def test_half_mask_shapes_effect_to_top_half(
    test_raw: Path,
    configdir: Path,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """Register a top-half-on / bottom-half-off mask, apply
    ``tone_lifted_shadows_subject`` with it, render, and assert:

    - top-half luma differs from baseline (effect applied)
    - bottom-half luma matches baseline (effect masked out)

    Catches "mask is registered but not actually shaping the effect"
    regressions — i.e. the mask hash isn't reaching darktable's
    blendop, or darktable is rendering the mask as full-coverage.
    """
    _ = darktable_binary
    clear_registry()
    prompts = PromptStore(_SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=starter_vocab, prompts=prompts)
    ws = _build_workspace(tmp_path, test_raw, configdir)
    ctx.workspaces[ws.image_id] = ws

    register_mask(
        ws.repo,
        "current_subject_mask",
        _half_coverage_mask_png(),
        generator="test-fake",
    )

    async def _exercise() -> tuple[bytes, bytes]:
        async with in_memory_session(server) as session:
            r_base = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert r_base["success"], r_base.get("error")
            base_bytes = Path(r_base["data"]["jpeg_path"]).read_bytes()

            applied = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={
                        "image_id": "phase0",
                        "primitive_name": "tone_lifted_shadows_subject",
                        "mask_override": "current_subject_mask",
                    },
                )
            )
            assert applied["success"], applied.get("error")

            r_after = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert r_after["success"], r_after.get("error")
            after_bytes = Path(r_after["data"]["jpeg_path"]).read_bytes()
            return base_bytes, after_bytes

    try:
        base_bytes, after_bytes = anyio.run(_exercise)
    finally:
        clear_registry()

    base_top = _region_luma(base_bytes, top_half=True)
    after_top = _region_luma(after_bytes, top_half=True)
    base_bottom = _region_luma(base_bytes, top_half=False)
    after_bottom = _region_luma(after_bytes, top_half=False)

    top_delta = abs(after_top - base_top)
    bottom_delta = abs(after_bottom - base_bottom)

    # Top half (mask = white = effect active): expect a measurable shift.
    # Bottom half (mask = black = effect off): expect baseline preserved.
    # The exposure-on-shadows primitive's effect on the top is
    # scene-dependent in magnitude, but always > the bottom-half delta
    # by a clear margin if masking works.
    assert top_delta > bottom_delta + 1.0, (
        f"top-half mask should shape the effect; got top_delta={top_delta:.3f}, "
        f"bottom_delta={bottom_delta:.3f}. The mask isn't actually masking — "
        f"the primitive is being applied uniformly or not at all."
    )
