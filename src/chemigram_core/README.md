# chemigram_core

The engine. XMP composition, `.dtstyle` parsing, vocabulary loading, render orchestration, versioning, masking provider integration, EXIF auto-binding.

Pure Python, no agent awareness. Driven by `chemigram_mcp` (or other adapters). Spec lives in `docs/architecture.md`.

**Status:** not started. Phase 1 work.

## Modules (planned per `docs/architecture.md`)

```
chemigram_core/
  xmp.py              # parse + synthesize XMP sidecars
  dtstyle.py          # parse .dtstyle XML files
  vocab.py            # vocabulary loading + filtering
  render.py           # darktable-cli wrapper
  versioning.py       # content-addressed snapshot DAG
  workspace.py        # per-image directory management
  config.py           # config.toml resolution
  pipeline.py         # PipelineStage protocol + runner
  masking/
    __init__.py       # MaskingProvider protocol
    coarse_agent.py   # bundled default (BYOA fallback)
  context.py          # taste.md / brief.md / notes.md handling
  sessions.py         # session lifecycle + transcripts
  bind.py             # EXIF auto-binding for L1/L2
  stages/
    darktable_cli.py  # the v1 pipeline stage
```

See `docs/phase-0-notebook.md` for what to validate before writing any of this.
