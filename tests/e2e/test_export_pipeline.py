"""End-to-end export pipeline through real darktable.

Covers what the integration tier can't:

- Full-resolution export produces an image at the raw's native
  rendered dimensions (not capped to 256/1024).
- Exported JPEG preserves EXIF tags from the source raw — at
  minimum Make / Model / DateTimeOriginal.
- ``--hq true`` (export) vs ``--hq false`` (preview) produces
  measurably different bytes at matching dimensions.
- PNG format works.

Part of GH #35 / v1.1.0 capability matrix.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import anyio
from PIL import Image
from PIL.ExifTags import TAGS

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


def _exif_tags(jpeg_bytes: bytes) -> dict[str, Any]:
    """Decode EXIF tags from a JPEG into a {tag-name: value} dict."""
    img = Image.open(io.BytesIO(jpeg_bytes))
    raw_exif = img.getexif()
    if not raw_exif:
        return {}
    return {TAGS.get(tag_id, str(tag_id)): value for tag_id, value in raw_exif.items()}


def test_export_full_resolution_produces_native_dimensions(
    test_raw: Path,
    configdir: Path,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """size omitted → full-resolution export. Image dimensions match
    the raw's rendered size (not capped to a preview default).
    """
    _ = darktable_binary
    clear_registry()
    prompts = PromptStore(_SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=starter_vocab, prompts=prompts)
    ws = _build_workspace(tmp_path, test_raw, configdir)
    ctx.workspaces[ws.image_id] = ws

    async def _go() -> bytes:
        async with in_memory_session(server) as session:
            r = _decode(
                await session.call_tool(
                    "export_final",
                    arguments={"image_id": "phase0", "format": "jpeg"},
                )
            )
            assert r["success"], r.get("error")
            return Path(r["data"]["output_path"]).read_bytes()

    try:
        jpeg_bytes = anyio.run(_go)
    finally:
        clear_registry()

    img = Image.open(io.BytesIO(jpeg_bytes))
    w, h = img.size
    # Phase 0 NEF is from a Nikon — sensor renders to a few-thousand-px
    # dimension. Don't hard-code the exact value (camera-dependent);
    # assert it's well above preview sizes.
    assert max(w, h) > 1500, (
        f"full-resolution export should be > 1500 px on the long edge; "
        f"got {w}x{h}. The size=None → full-res path is failing."
    )


def test_export_preserves_exif_from_source_raw(
    test_raw: Path,
    configdir: Path,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """Exported JPEG carries EXIF tags from the source raw.

    Asserts on Make + Model + DateTimeOriginal — the minimum set a
    photographer expects when handing the export to a downstream tool
    (Lightroom, archival workflow). The raw's native EXIF should round
    -trip; we don't assert exact equality because darktable normalizes
    some fields.
    """
    _ = darktable_binary
    clear_registry()
    prompts = PromptStore(_SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=starter_vocab, prompts=prompts)
    ws = _build_workspace(tmp_path, test_raw, configdir)
    ctx.workspaces[ws.image_id] = ws

    async def _go() -> bytes:
        async with in_memory_session(server) as session:
            r = _decode(
                await session.call_tool(
                    "export_final",
                    arguments={"image_id": "phase0", "format": "jpeg"},
                )
            )
            assert r["success"], r.get("error")
            return Path(r["data"]["output_path"]).read_bytes()

    try:
        jpeg_bytes = anyio.run(_go)
    finally:
        clear_registry()

    tags = _exif_tags(jpeg_bytes)
    # Make + Model are camera identity tags; should always be present
    # in a darktable-rendered JPEG from a NEF.
    assert tags.get("Make"), f"exported JPEG missing Make tag; available: {sorted(tags.keys())}"
    assert tags.get("Model"), f"exported JPEG missing Model tag; available: {sorted(tags.keys())}"
    assert "DateTimeOriginal" in tags or "DateTime" in tags, (
        f"exported JPEG missing DateTime/DateTimeOriginal; available: {sorted(tags.keys())}"
    )


def test_export_png_format_works(
    test_raw: Path,
    configdir: Path,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    _ = darktable_binary
    clear_registry()
    prompts = PromptStore(_SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=starter_vocab, prompts=prompts)
    ws = _build_workspace(tmp_path, test_raw, configdir)
    ctx.workspaces[ws.image_id] = ws

    async def _go() -> tuple[str, bytes]:
        async with in_memory_session(server) as session:
            r = _decode(
                await session.call_tool(
                    "export_final",
                    arguments={"image_id": "phase0", "format": "png", "size": 512},
                )
            )
            assert r["success"], r.get("error")
            path = r["data"]["output_path"]
            return path, Path(path).read_bytes()

    try:
        path, png_bytes = anyio.run(_go)
    finally:
        clear_registry()

    assert path.endswith(".png")
    # PNG signature: 89 50 4E 47 0D 0A 1A 0A
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    img = Image.open(io.BytesIO(png_bytes))
    assert img.format == "PNG"


def test_export_hq_differs_from_preview_at_same_size(
    test_raw: Path,
    configdir: Path,
    starter_vocab: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
) -> None:
    """At matching dimensions, --hq true (export) and --hq false
    (preview) render different bytes. ADR-004's invocation form
    documents --hq as a quality switch; this test proves it actually
    affects output.
    """
    _ = darktable_binary
    clear_registry()
    prompts = PromptStore(_SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=starter_vocab, prompts=prompts)
    ws = _build_workspace(tmp_path, test_raw, configdir)
    ctx.workspaces[ws.image_id] = ws

    async def _go() -> tuple[bytes, bytes]:
        async with in_memory_session(server) as session:
            r_prev = _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "phase0", "size": 512},
                )
            )
            assert r_prev["success"], r_prev.get("error")
            preview_bytes = Path(r_prev["data"]["jpeg_path"]).read_bytes()
            r_exp = _decode(
                await session.call_tool(
                    "export_final",
                    arguments={
                        "image_id": "phase0",
                        "format": "jpeg",
                        "size": 512,
                    },
                )
            )
            assert r_exp["success"], r_exp.get("error")
            export_bytes = Path(r_exp["data"]["output_path"]).read_bytes()
            return preview_bytes, export_bytes

    try:
        preview_bytes, export_bytes = anyio.run(_go)
    finally:
        clear_registry()

    # The bytes must differ — if they're identical, --hq is a no-op
    # and ADR-004's quality split is broken.
    assert preview_bytes != export_bytes, (
        "preview (--hq false) and export (--hq true) produced identical "
        "bytes at the same size — the --hq flag isn't affecting output."
    )
