"""Chemigram core engine.

Pure-Python orchestration of darktable: XMP composition, ``.dtstyle``
parsing, render pipeline, EXIF auto-binding. No agent awareness; the
agent surface lives in :mod:`chemigram.mcp`.

Slice 1 modules (shipped):
    - :mod:`chemigram.core.dtstyle` — parse darktable style files
    - :mod:`chemigram.core.xmp` — parse, synthesize, write XMP sidecars
    - :mod:`chemigram.core.pipeline` — render pipeline + ``render()``
    - :mod:`chemigram.core.stages.darktable_cli` — the v1 render stage
    - :mod:`chemigram.core.exif` — EXIF read for L1 binding
    - :mod:`chemigram.core.binding` — exact-match L1 vocabulary lookup

Slices 2+ add: ``versioning``, ``masking``, ``context``, ``sessions``,
``vocab``. See ``docs/IMPLEMENTATION.md`` for the phase plan and
``docs/adr/TA.md`` for component anchors.

Three foundational disciplines (see ADR-003):
    1. **Agent is the only writer.** This package never silently
       mutates state; every change is a tool call.
    2. **darktable does the photography, Chemigram does the loop.**
       No image-processing capabilities live here — only orchestration.
    3. **BYOA — Bring Your Own AI.** No AI dependencies in this
       package's runtime; AI capabilities arrive via MCP-configured
       providers.
"""
