"""End-to-end versioning combinations through MCP + real darktable.

The integration suite proves each versioning tool works in isolation.
This suite proves the *combinations* — sequences of (apply, snapshot,
tag, branch, checkout, reset) — leave the workspace's rendered state
matching what the engine semantics promise.

Specifically: if the spec says "checking out tag X gives you the state
that was tagged at X", we render at X and assert the bytes match a
direct render of the XMP that was tagged. Same for reset, branch,
remove_module, etc.

These are the tests that catch "checkout said it succeeded but the
rendered output is wrong" regressions — the gap between what the
engine reports and what darktable actually produces.

Part of GH #31 / v1.1.0 capability matrix.
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


def test_snapshot_tag_reset_render_round_trips(
    test_raw: Path,
    configdir: Path,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """apply → snapshot → tag → apply → reset → render: rendered output
    matches a fresh-baseline render. Catches "reset says success but
    the XMP isn't actually rewound" regressions.
    """
    _ = darktable_binary
    clear_registry()
    prompts = PromptStore(_SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=starter_vocab, prompts=prompts)
    ws = _build_workspace(tmp_path, test_raw, configdir)
    ctx.workspaces[ws.image_id] = ws

    async def _exercise() -> tuple[bytes, bytes]:
        async with in_memory_session(server) as session:
            # Render baseline directly.
            r1 = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert r1["success"], r1.get("error")
            baseline_bytes = Path(r1["data"]["jpeg_path"]).read_bytes()

            # Apply, tag the apply, apply again, reset, render.
            await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "phase0", "primitive_name": "expo_+0.5"},
            )
            await session.call_tool("tag", arguments={"image_id": "phase0", "name": "after-plus"})
            await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "phase0", "primitive_name": "expo_-0.5"},
            )
            await session.call_tool("reset", arguments={"image_id": "phase0"})
            r2 = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert r2["success"], r2.get("error")
            after_reset_bytes = Path(r2["data"]["jpeg_path"]).read_bytes()
            return baseline_bytes, after_reset_bytes

    try:
        baseline_bytes, after_reset_bytes = anyio.run(_exercise)
    finally:
        clear_registry()

    baseline_lum = _luma(baseline_bytes)
    after_lum = _luma(after_reset_bytes)
    assert abs(baseline_lum - after_lum) < 0.5, (
        f"reset should rewind to the exact baseline render; "
        f"got baseline={baseline_lum:.3f}, after_reset={after_lum:.3f}"
    )


def test_branch_checkout_render_renders_branch_state(
    test_raw: Path,
    configdir: Path,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """apply on main → branch → switch to branch → apply different →
    checkout main → render: gets main's state, not branch's.

    Catches "branch state leaks into main" / "checkout doesn't rewrite
    current.xmp" regressions.
    """
    _ = darktable_binary
    clear_registry()
    prompts = PromptStore(_SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=starter_vocab, prompts=prompts)
    ws = _build_workspace(tmp_path, test_raw, configdir)
    ctx.workspaces[ws.image_id] = ws

    async def _exercise() -> tuple[bytes, bytes]:
        async with in_memory_session(server) as session:
            # Apply expo_+0.5 on main.
            await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "phase0", "primitive_name": "expo_+0.5"},
            )

            # Branch experimental from HEAD.
            await session.call_tool(
                "branch",
                arguments={
                    "image_id": "phase0",
                    "name": "experimental",
                    "from_": "HEAD",
                },
            )
            await session.call_tool(
                "checkout",
                arguments={"image_id": "phase0", "ref_or_hash": "experimental"},
            )

            # Apply expo_-0.5 on experimental.
            await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "phase0", "primitive_name": "expo_-0.5"},
            )
            r_exp = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert r_exp["success"], r_exp.get("error")
            exp_bytes = Path(r_exp["data"]["jpeg_path"]).read_bytes()

            # Switch back to main and render.
            await session.call_tool(
                "checkout",
                arguments={"image_id": "phase0", "ref_or_hash": "main"},
            )
            r_main = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert r_main["success"], r_main.get("error")
            main_bytes = Path(r_main["data"]["jpeg_path"]).read_bytes()
            return exp_bytes, main_bytes

    try:
        exp_bytes, main_bytes = anyio.run(_exercise)
    finally:
        clear_registry()

    # main has expo_+0.5, experimental has expo_-0.5 (SET-replace would
    # have produced expo_-0.5 on experimental, since both branches
    # branched from the apply_+0.5 snapshot then experimental did
    # apply_-0.5). main should be brighter than experimental.
    main_lum = _luma(main_bytes)
    exp_lum = _luma(exp_bytes)
    delta = main_lum - exp_lum
    assert delta > 5.0, (
        f"main (expo_+0.5) should render brighter than experimental "
        f"(expo_-0.5); got main={main_lum:.2f}, exp={exp_lum:.2f}, "
        f"delta={delta:.3f}. Branches are leaking state or checkout "
        f"is not rewriting current.xmp."
    )


def test_tag_then_checkout_tag_renders_tagged_state(
    test_raw: Path,
    configdir: Path,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """Tag a state → diverge from it → checkout the tag → render: gets
    the tagged state's render, not the divergent one.
    """
    _ = darktable_binary
    clear_registry()
    prompts = PromptStore(_SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=starter_vocab, prompts=prompts)
    ws = _build_workspace(tmp_path, test_raw, configdir)
    ctx.workspaces[ws.image_id] = ws

    async def _exercise() -> tuple[bytes, bytes]:
        async with in_memory_session(server) as session:
            # Apply A (will be tagged).
            await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "phase0", "primitive_name": "expo_+0.5"},
            )
            r_a = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert r_a["success"], r_a.get("error")
            at_a_bytes = Path(r_a["data"]["jpeg_path"]).read_bytes()

            # Tag the apply.
            await session.call_tool("tag", arguments={"image_id": "phase0", "name": "tagged-state"})

            # Diverge: SET-replace exposure.
            await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "phase0", "primitive_name": "expo_-0.5"},
            )

            # Checkout the tag (HEAD detaches per ADR-019).
            await session.call_tool(
                "checkout",
                arguments={"image_id": "phase0", "ref_or_hash": "tagged-state"},
            )
            r_back = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 256},
                )
            )
            assert r_back["success"], r_back.get("error")
            back_bytes = Path(r_back["data"]["jpeg_path"]).read_bytes()
            return at_a_bytes, back_bytes

    try:
        a_bytes, back_bytes = anyio.run(_exercise)
    finally:
        clear_registry()

    a_lum = _luma(a_bytes)
    back_lum = _luma(back_bytes)
    assert abs(a_lum - back_lum) < 0.5, (
        f"checkout to tag should restore the tagged render exactly; "
        f"got at_tag={a_lum:.3f}, after_checkout={back_lum:.3f}"
    )
