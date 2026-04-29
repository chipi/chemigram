"""End-to-end coverage for the `compare` MCP tool and workspace
persistence across registry clears.

Two distinct claims under test:

1. **compare** renders two states side-by-side as one stitched JPEG. The
   output must contain both renders' content — width is greater than
   either individual render and the stitched bytes differ from each
   side alone.
2. **Persistence:** after `clear_registry()` (or process restart), a
   workspace re-registered from the same on-disk path sees the same
   refs, the same objects, and the same baseline hash. Per ADR-018,
   the filesystem is the truth; the in-memory registry is just a cache.

Part of GH #30 (v1.1.0 capability matrix completion before tag).
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


def test_compare_stitches_two_states_into_one_jpeg(
    test_raw: Path,
    configdir: Path,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """Apply two different primitives → snapshot each → compare. The
    stitched output should be wider than either individual render
    (proving both halves are present).
    """
    _ = darktable_binary
    clear_registry()
    prompts = PromptStore(_SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=starter_vocab, prompts=prompts)
    ws = _build_workspace(tmp_path, test_raw, configdir)
    ctx.workspaces[ws.image_id] = ws

    async def _exercise() -> tuple[bytes, bytes, bytes]:
        async with in_memory_session(server) as session:
            apply_a = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={"image_id": "phase0", "primitive_name": "expo_+0.5"},
                )
            )
            assert apply_a["success"], apply_a.get("error")
            hash_a = apply_a["data"]["snapshot_hash"]

            r_a = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={
                        "image_id": "phase0",
                        "size": 256,
                        "ref_or_hash": hash_a,
                    },
                )
            )
            assert r_a["success"], r_a.get("error")
            a_bytes = Path(r_a["data"]["jpeg_path"]).read_bytes()

            apply_b = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={"image_id": "phase0", "primitive_name": "expo_-0.5"},
                )
            )
            hash_b = apply_b["data"]["snapshot_hash"]

            r_b = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={
                        "image_id": "phase0",
                        "size": 256,
                        "ref_or_hash": hash_b,
                    },
                )
            )
            b_bytes = Path(r_b["data"]["jpeg_path"]).read_bytes()

            cmp_r = _decode(
                await session.call_tool(
                    "compare",
                    arguments={
                        "image_id": "phase0",
                        "hash_a": hash_a,
                        "hash_b": hash_b,
                        "size": 256,
                    },
                )
            )
            assert cmp_r["success"], cmp_r.get("error")
            cmp_bytes = Path(cmp_r["data"]["jpeg_path"]).read_bytes()
            return a_bytes, b_bytes, cmp_bytes

    try:
        a_bytes, b_bytes, cmp_bytes = anyio.run(_exercise)
    finally:
        clear_registry()

    a_img = Image.open(io.BytesIO(a_bytes))
    b_img = Image.open(io.BytesIO(b_bytes))
    cmp_img = Image.open(io.BytesIO(cmp_bytes))

    # Stitched output is wider than either side alone (both halves +
    # gap). Don't demand exact width — pillow and JPEG both round.
    assert cmp_img.width > a_img.width, (
        f"compare output ({cmp_img.size}) should be wider than a single "
        f"render ({a_img.size}); the stitcher dropped a half."
    )
    assert cmp_img.width > b_img.width
    # Compare bytes differ from each side's bytes (it's a different
    # image — stitched + labeled).
    assert cmp_bytes != a_bytes
    assert cmp_bytes != b_bytes


def test_workspace_state_survives_registry_clear(
    test_raw: Path,
    configdir: Path,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """Per ADR-018, the filesystem is the truth. Clearing the in-memory
    workspace registry and re-registering the same on-disk path must
    see the same refs and the same render bytes.

    This is what makes ``chemigram`` agent sessions safe to interrupt
    and resume — state lives on disk, not in process memory.
    """
    _ = darktable_binary
    clear_registry()
    prompts = PromptStore(_SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=starter_vocab, prompts=prompts)
    ws = _build_workspace(tmp_path, test_raw, configdir)
    ctx.workspaces[ws.image_id] = ws

    async def _go_session_one() -> tuple[str, bytes]:
        async with in_memory_session(server) as session:
            applied = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={"image_id": "phase0", "primitive_name": "expo_+0.5"},
                )
            )
            assert applied["success"], applied.get("error")
            hash_after_apply = applied["data"]["snapshot_hash"]

            r = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert r["success"], r.get("error")
            return hash_after_apply, Path(r["data"]["jpeg_path"]).read_bytes()

    hash_one, render_one = anyio.run(_go_session_one)
    ws_root = ws.root

    # Simulate restart: drop registry, re-build server, re-register
    # workspace from the same root.
    clear_registry()
    prompts2 = PromptStore(_SHIPPED_PROMPTS)
    server2, ctx2 = build_server(vocabulary=starter_vocab, prompts=prompts2)
    repo2 = ImageRepo(ws_root)
    ws2 = Workspace(
        image_id="phase0",
        root=ws_root,
        repo=repo2,
        raw_path=ws_root / "raw" / test_raw.name,
        configdir=configdir,
    )
    ctx2.workspaces[ws2.image_id] = ws2

    async def _go_session_two() -> tuple[str, bytes]:
        async with in_memory_session(server2) as session:
            state = _decode(await session.call_tool("get_state", arguments={"image_id": "phase0"}))
            assert state["success"], state.get("error")
            r = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert r["success"], r.get("error")
            return state["data"]["head_hash"], Path(r["data"]["jpeg_path"]).read_bytes()

    try:
        hash_two, render_two = anyio.run(_go_session_two)
    finally:
        clear_registry()

    # On-disk truth is the same: same HEAD hash.
    assert hash_two == hash_one, (
        f"persisted HEAD hash should equal pre-restart hash; "
        f"got pre={hash_one[:12]}, post={hash_two[:12]}. "
        f"Either the on-disk state was mutated by clear_registry or "
        f"the second-session workspace isn't reading the same repo."
    )
    # Rendered luma should be identical — same XMP, same raw, same
    # configdir. Bytes-level equality is too strict because darktable
    # embeds a render timestamp in JPEG metadata that differs run to
    # run; the *image content* is what we actually care about.
    img_one = Image.open(io.BytesIO(render_one)).convert("RGB")
    img_two = Image.open(io.BytesIO(render_two)).convert("RGB")
    means_one = [
        sum(i * c for i, c in enumerate(b.histogram())) / max(sum(b.histogram()), 1)
        for b in img_one.split()
    ]
    means_two = [
        sum(i * c for i, c in enumerate(b.histogram())) / max(sum(b.histogram()), 1)
        for b in img_two.split()
    ]
    for ch, (a, b) in enumerate(zip(means_one, means_two, strict=True)):
        assert abs(a - b) < 0.5, (
            f"channel {ch} luma diverges across registry-clear; "
            f"pre={a:.3f}, post={b:.3f}. The workspace's rendered "
            f"output isn't reproducible from on-disk state alone."
        )
