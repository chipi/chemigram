# Chemigram stack diagram

> Source: `docs/diagrams/stack.md`. GitHub + MkDocs render Mermaid blocks
> natively. Edit this file when the stack shape changes.

The stack: an AI client drives `chemigram-mcp` over stdio (or any other
MCP transport), `chemigram-mcp` and the `chemigram` CLI both dispatch
through `chemigram.core`, and `chemigram.core` invokes `darktable-cli`
as a subprocess to render. State lives on the filesystem at
`~/Pictures/Chemigram/<image_id>/`. Every pixel decision is made by
darktable; chemigram contributes orchestration only.

```mermaid
flowchart LR
    subgraph CLIENT["AI client (one of)"]
        direction TB
        CC[Claude Code]
        CD[Claude Desktop]
        CR[Cursor / Continue / Cline / Zed / Codex]
    end

    subgraph ADAPTERS["chemigram adapters"]
        direction TB
        MCP[chemigram-mcp<br/>27 tools]
        CLI[chemigram CLI<br/>28 verbs]
    end

    subgraph CORE["chemigram.core (engine — single Python process)"]
        direction TB
        VOCAB[vocab<br/>114 entries + 9 maskdefs]
        SYNTH[synthesizer<br/>SET-replace + Path B]
        VERS[versioning<br/>content-addressed DAG]
        MASK[masking<br/>drawn + parametric + LLM-vision + retouch]
        CTX[context<br/>tastes / brief / notes / session]
        PARAM[parameterize<br/>Path C decoders × 18 modules]
    end

    DT[darktable-cli<br/>v5.x — every pixel decision]

    subgraph FS["Filesystem state (no daemon)"]
        direction TB
        WS["~/Pictures/Chemigram/&lt;image_id&gt;/<br/>snapshots/ exports/ sessions/ previews/"]
        TASTES["~/.chemigram/<br/>tastes/ vocabulary/personal/ config.toml"]
    end

    CC -.stdio.-> MCP
    CD -.stdio.-> MCP
    CR -.stdio.-> MCP
    CLI -.subprocess.-> CORE
    MCP --> CORE
    CORE -- "synthesize XMP" --> SYNTH
    CORE --> VOCAB
    CORE --> VERS
    CORE --> MASK
    CORE --> CTX
    CORE --> PARAM
    SYNTH -- "writes" --> WS
    CORE -- "spawns" --> DT
    DT -- "reads RAW + XMP, writes JPEG" --> WS
    CTX -- "reads / proposes updates" --> TASTES

    classDef adapter fill:#e8f3ff,stroke:#0366d6,stroke-width:2px
    classDef core fill:#fff5e6,stroke:#d97706,stroke-width:2px
    classDef external fill:#f0fdf4,stroke:#16a34a,stroke-width:2px
    classDef state fill:#fef3c7,stroke:#a16207,stroke-width:1px,stroke-dasharray:4 2
    class MCP,CLI adapter
    class VOCAB,SYNTH,VERS,MASK,CTX,PARAM core
    class DT external
    class WS,TASTES state
```

## Reading the diagram

- **Solid arrows** = in-process function calls.
- **Dotted arrows** = subprocess / IPC (stdio for MCP, fork+exec for CLI ↔ core, fork+exec for darktable-cli).
- **Blue nodes** (`MCP`, `CLI`) — adapter layers; thin wrappers over `chemigram.core` (lint-enforced per ADR-071).
- **Orange nodes** — `chemigram.core` subsystems.
- **Green node** — external dependency. The architectural commitment ("darktable does the photography, Chemigram does the loop"; CLAUDE.md § "The three foundational disciplines") means this box is the entire pixel-processing surface.
- **Yellow dashed nodes** — filesystem state (the project explicitly has no daemon / no in-memory persistence; the filesystem IS the state).

See also: `docs/diagrams/mask-trilogy.md`, `docs/diagrams/vocabulary-layers.md`, `docs/diagrams/phase-1-timeline.md`.
