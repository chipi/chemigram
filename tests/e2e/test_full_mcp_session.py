"""End-to-end MCP-level test against real darktable.

The big one: drives a real Mode A session through the in-memory MCP
client/server harness, with REAL ``pipeline.render`` (not stubbed) hitting
the real ``darktable-cli`` against the Phase 0 test raw. Validates that
the rendered preview's pixel statistics moved as expected after applying
a vocabulary primitive — proving the *whole* chain works end-to-end:
agent intent → MCP tool dispatch → workspace state → synthesizer →
render pipeline → darktable-cli → produced bytes back to the agent.

This is the layer of evidence between the Slice 3/4/5 in-memory gate
tests (which stub the render) and the user's manual sessions (which
have no automated assertion).

Skipped automatically when prerequisites are absent.
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


def _build_workspace_with_phase_0_raw(
    tmp_path: Path,
    raw_path: Path,
    configdir: Path,
) -> Workspace:
    """Create a workspace using the real Phase 0 raw + configdir."""
    root = tmp_path / "ws"
    init_workspace_root(root)
    repo = ImageRepo.init(root)

    # Symlink the real raw into the workspace.
    workspace_raw = root / "raw" / raw_path.name
    if not workspace_raw.exists():
        workspace_raw.symlink_to(raw_path.resolve())

    # Snapshot the bundled baseline XMP + tag it as 'baseline' (mirrors
    # what ingest_workspace does internally).
    baseline = parse_xmp(_BASELINE_XMP)
    h = snapshot(repo, baseline, label="baseline")
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


def _read_jpeg_mean_luma_bytes(jpeg_bytes: bytes) -> float:
    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    r_band, g_band, b_band = img.split()

    def _band_mean(band):
        hist = band.histogram()
        return sum(i * c for i, c in enumerate(hist)) / max(sum(hist), 1)

    r, g, b = _band_mean(r_band), _band_mean(g_band), _band_mean(b_band)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def test_mcp_session_with_real_render_full_circle(
    test_raw: Path,
    configdir: Path,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """The big test.

    Through the real MCP harness, with the real darktable-cli rendering:

    1. Apply expo_+0.5 → render_preview (real render, not stubbed)
    2. Apply expo_-0.5 → render_preview (real render again)
       — SET semantics (ADR-002) replace the prior exposure entry, so the
       second snapshot is "exposure = -0.5 EV" not "exposure = +0.5 then
       +(-0.5)". One whole EV of difference between the two renders.
    3. Verify the two renders have measurably different luma — proving
       the agent's tool call actually drove the synthesizer + render
       pipeline + darktable + produced different pixels back.

    If anything in the chain breaks (synthesizer drops the op, render
    returns the cached preview, MCP tool dispatch silently fails), this
    test catches it.
    """
    _ = darktable_binary  # implicitly used via PATH by pipeline.render
    clear_registry()
    prompts = PromptStore(_SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=starter_vocab, prompts=prompts)
    ws = _build_workspace_with_phase_0_raw(tmp_path, test_raw, configdir)
    ctx.workspaces[ws.image_id] = ws

    async def _exercise() -> tuple[bytes, bytes, str, str]:
        async with in_memory_session(server) as session:
            apply_plus = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={"image_id": "phase0", "primitive_name": "expo_+0.5"},
                )
            )
            assert apply_plus["success"], apply_plus.get("error")
            plus_hash = apply_plus["data"]["snapshot_hash"]

            render_plus = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert render_plus["success"], render_plus.get("error")
            # render_preview writes to a deterministic path keyed on
            # ref_or_hash[:16], so the next render will overwrite. Capture
            # the JPEG bytes immediately.
            plus_bytes = Path(render_plus["data"]["jpeg_path"]).read_bytes()

            apply_minus = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={"image_id": "phase0", "primitive_name": "expo_-0.5"},
                )
            )
            assert apply_minus["success"], apply_minus.get("error")
            minus_hash = apply_minus["data"]["snapshot_hash"]

            render_minus = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert render_minus["success"], render_minus.get("error")
            minus_bytes = Path(render_minus["data"]["jpeg_path"]).read_bytes()

            return plus_bytes, minus_bytes, plus_hash, minus_hash

    try:
        plus_bytes, minus_bytes, plus_hash, minus_hash = anyio.run(_exercise)
    finally:
        clear_registry()

    # Sanity: the two applies produced different snapshot hashes (XMPs
    # differ structurally). If equal, the synthesizer or SET semantics
    # are broken upstream of darktable.
    assert plus_hash != minus_hash, (
        f"applying expo_+0.5 then expo_-0.5 produced the same snapshot hash "
        f"({plus_hash[:12]}); SET-replace or synthesize_xmp regressed."
    )

    plus_lum = _read_jpeg_mean_luma_bytes(plus_bytes)
    minus_lum = _read_jpeg_mean_luma_bytes(minus_bytes)
    delta = plus_lum - minus_lum

    # Same threshold as the engine-level relative test (1.0 EV difference
    # in the dtstyles' exposure floats → many luma units on a typical
    # scene; demand >5 to be well above noise).
    assert delta > 5.0, (
        f"MCP-driven session: expo_+0.5 should render brighter than expo_-0.5; "
        f"got plus={plus_lum:.2f}, minus={minus_lum:.2f}, delta={delta:.3f}. "
        f"If this fails, the chain (MCP → synthesizer → render → darktable) "
        f"has a regression somewhere."
    )


def test_mcp_session_render_then_no_change(
    test_raw: Path,
    configdir: Path,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """Render the same workspace state twice via MCP → identical luma.

    Validates that the render cache (or absence of it) doesn't introduce
    spurious differences. Two render_preview calls back-to-back without
    any state change should produce the same image.
    """
    _ = darktable_binary
    clear_registry()
    prompts = PromptStore(_SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=starter_vocab, prompts=prompts)
    ws = _build_workspace_with_phase_0_raw(tmp_path, test_raw, configdir)
    ctx.workspaces[ws.image_id] = ws

    async def _exercise() -> tuple[bytes, bytes]:
        async with in_memory_session(server) as session:
            r1 = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert r1["success"], r1.get("error")
            a_bytes = Path(r1["data"]["jpeg_path"]).read_bytes()
            r2 = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert r2["success"], r2.get("error")
            b_bytes = Path(r2["data"]["jpeg_path"]).read_bytes()
            return a_bytes, b_bytes

    try:
        a, b = anyio.run(_exercise)
    finally:
        clear_registry()

    a_lum = _read_jpeg_mean_luma_bytes(a)
    b_lum = _read_jpeg_mean_luma_bytes(b)
    assert abs(a_lum - b_lum) < 0.5, (
        f"two consecutive render_preview calls should produce the same image; "
        f"got a={a_lum:.3f}, b={b_lum:.3f}"
    )
