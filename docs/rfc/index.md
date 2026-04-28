# RFCs — Request for Comments

RFCs explore open technical questions with deliberation. Each RFC names a question, frames the alternatives honestly, and proposes a path forward. RFCs close into ADRs once a decision is made.

RFCs are not implementation specs and not justifications-after-the-fact. They're real deliberation captured.

## Reference

- `../adr/TA.md` — technical architecture. Every RFC anchors here via `TA/components/...` or `TA/constraints`.
- `RFC_TEMPLATE.md` — the format every RFC follows.

## Index

| RFC | Title | Status | Closes into |
|-|-|-|-|
| RFC-001 | XMP synthesizer architecture | Draft v0.1 | ADR-009, ADR-010, ADR-011 (pending) |
| RFC-002 | Canonical XMP serialization for stable hashing | Draft v0.1 | ADR-018-amendment (pending) |
| RFC-003 | Mask storage in versioning | Draft v0.1 | ADR-022-amendment (pending) |
| RFC-004 | Default masking provider — coarse vs SAM | Draft v0.1 | ADR (pending) |
| RFC-005 | Pipeline stage protocol — abstract now or YAGNI | Draft v0.1 | ADR (pending) |
| RFC-006 | Same-module collision behavior | Draft v0.1 | ADR (pending) |
| RFC-007 | modversion drift handling | Draft v0.1 | ADR (pending) |
| RFC-008 | Vocabulary discovery at scale | Draft v0.1 (speculative) | — |
| RFC-009 | Mask provider protocol shape | Draft v0.1 | ADR (pending) |
| RFC-010 | MCP tool surface — parameter shapes and errors | Draft v0.1 | ADR (pending) |
| RFC-011 | Agent context loading order and format | Draft v0.1 | ADR-031 (pending) |
| RFC-012 | Programmatic vocabulary generation (Path C) | Draft v0.1 (deferred) | — |
| RFC-013 | Vocabulary gap surfacing format | Draft v0.1 | ADR (pending) |
| RFC-014 | End-of-session synthesis flow | Draft v0.1 | ADR (pending) |
| RFC-015 | EXIF auto-binding rules | Draft v0.1 | ADR (pending) |

## Maturity legend

- **Draft v0.1** — written; deliberation captured; awaiting implementation evidence to close
- **Draft v0.1 (speculative)** — question identified but problem isn't real yet (e.g. vocabulary too small to need discovery tooling); placeholder until it becomes pressing
- **Draft v0.1 (deferred)** — question identified, deliberately not being argued in this round; revisit later
- **Decided** — closed into one or more ADRs; remains as historical record

## Conventions

- Numbered sequentially (`RFC-NNN-slug.md`)
- Every RFC has a "Why this is an RFC" gating sentence in the header
- "Alternatives considered" must list real alternatives with honest reasons for rejection
- An RFC that argues for something already-decided is an ADR; close and start over
