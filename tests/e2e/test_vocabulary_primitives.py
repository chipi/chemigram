"""End-to-end pixel validation for the remaining starter primitives.

Sister to :file:`test_render_validation.py`, which covers the L3
direction-of-change cases (expo, wb). This file covers:

- ``look_neutral`` (L2) — composite primitive touching both exposure
  and temperature; assert the rendered output differs measurably from
  the unprimed baseline.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import anyio
from PIL import Image

from chemigram.core.versioning import ImageRepo
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


def _luma(jpeg_bytes: bytes) -> float:
    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    r, g, b = img.split()
    means = []
    for band in (r, g, b):
        hist = band.histogram()
        means.append(sum(i * c for i, c in enumerate(hist)) / max(sum(hist), 1))
    return 0.2126 * means[0] + 0.7152 * means[1] + 0.0722 * means[2]


def test_look_neutral_changes_baseline_render(
    test_raw: Path,
    configdir: Path,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """L2 composite primitive: applying ``look_neutral`` produces a
    measurably different render from the unprimed baseline. Catches
    L2 entries that fail to compose (synthesizer drops them) or that
    have stale modversions.
    """
    _ = darktable_binary
    clear_registry()
    prompts = PromptStore(_SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=starter_vocab, prompts=prompts)
    ws = _build_workspace(tmp_path, test_raw, configdir)
    ctx.workspaces[ws.image_id] = ws

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
                    arguments={"image_id": "phase0", "primitive_name": "look_neutral"},
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

    base_lum = _luma(base_bytes)
    after_lum = _luma(after_bytes)
    delta = abs(base_lum - after_lum)
    assert delta > 5.0, (
        f"look_neutral should produce a measurable luma delta from baseline; "
        f"got base={base_lum:.2f}, after={after_lum:.2f}, |delta|={delta:.3f}. "
        f"L2 composite is failing to apply or being dropped by the synthesizer."
    )
