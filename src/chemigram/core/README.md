# chemigram.core

The engine. XMP composition, `.dtstyle` parsing, vocabulary loading, render orchestration, versioning, masking provider integration, EXIF auto-binding.

Pure Python, no agent awareness. Driven by `chemigram.mcp` (or other adapters). Spec lives in `docs/concept/04-architecture.md` and `docs/adr/TA.md`.

**Status:** not started. Phase 1 work; see `docs/IMPLEMENTATION.md`.

## Modules (planned per TA/components)

```
src/chemigram/core/
  xmp.py              # parse + synthesize XMP sidecars
  dtstyle.py          # parse .dtstyle XML files
  vocab.py            # vocabulary loading + filtering
  pipeline.py         # PipelineStage protocol + runner
  stages/
    darktable_cli.py  # the v1 pipeline stage
  versioning.py       # content-addressed snapshot DAG
  workspace.py        # per-image directory management
  config.py           # config.toml resolution
  masking/
    __init__.py       # MaskingProvider protocol
    coarse_agent.py   # bundled default (BYOA fallback)
  context.py          # taste.md / brief.md / notes.md handling
  sessions.py         # session lifecycle + transcripts
  bind.py             # EXIF auto-binding for L1/L2
```

See `examples/phase-0-notebook-working.md` for the validation that grounds this design.
