# chemigram.core

The engine. XMP composition, `.dtstyle` parsing, vocabulary loading, render orchestration, versioning, drawn-mask serialization, EXIF auto-binding.

Pure Python, no agent awareness. Driven by `chemigram.mcp` (or other adapters). Spec lives in `docs/concept/04-architecture.md` and `docs/adr/TA.md`.

**Status:** Shipped. Phase 1 closed at v1.0.0; current state v1.5.0 — drawn-mask-only architecture per ADR-076. See `docs/IMPLEMENTATION.md` for the canonical phase plan.

## Modules (current shape, v1.5.0)

```
src/chemigram/core/
  dtstyle.py            # parse .dtstyle XML files
  xmp.py                # parse / synthesize / write XMP sidecars
  vocab/                # vocabulary index + manifest loading
  pipeline.py           # PipelineStage Protocol + render() runner
  stages/
    darktable_cli.py    # the v1 pipeline stage
  versioning/           # content-addressed snapshot DAG (canonical, repo, ops)
  workspace.py          # per-image directory orchestrator
  config.py             # config.toml resolution
  masking/
    __init__.py         # subsystem docstring
    dt_serialize.py     # darktable drawn-form XMP encoders (gradient / ellipse / rectangle)
  helpers.py            # shared MCP+CLI helpers (apply_with_drawn_mask, summarize_state, …)
  context/              # taste.md / brief.md / notes.md / recent log + gaps
  session/              # JSONL session transcripts
  binding.py            # EXIF auto-binding for L1
  exif.py               # EXIF read for binding lookup
```

See `docs/concept/04-architecture.md` § 6 for the masking architecture and `docs/adr/ADR-076-drawn-mask-only-mask-architecture.md` for the v1.5.0 cleanup rationale.
