# RFCs — Request for Comments

RFCs explore open technical questions with deliberation. Each RFC names a question, frames the alternatives honestly, and proposes a path forward. RFCs close into ADRs once a decision is made.

RFCs are not implementation specs and not justifications-after-the-fact. They're real deliberation captured.

## Reference

- `../adr/TA.md` — technical architecture. Every RFC anchors here via `TA/components/...` or `TA/constraints`.
- `RFC_TEMPLATE.md` — the format every RFC follows.

## Index

| RFC | Title | Status | Closes into |
|-|-|-|-|
| RFC-001 | XMP synthesizer architecture | Decided | ADR-050 (closes); Path B / iop_order question remains open |
| RFC-002 | Canonical XMP serialization for stable hashing | Decided | ADR-054 (closes) |
| RFC-003 | Mask storage in versioning | Decided | ADR-055 (closes) |
| RFC-004 | Default masking provider — coarse vs SAM | Decided | ADR-058 (closes) |
| RFC-005 | Pipeline stage protocol — abstract now or YAGNI | Decided | ADR-052 (closes) |
| RFC-006 | Same-module collision behavior | Decided | ADR-051 (closes); deviated from in-call-collision proposal — see ADR rationale |
| RFC-007 | modversion drift handling | Draft v0.1 | ADR (pending) |
| RFC-008 | Vocabulary discovery at scale | Draft v0.1 (speculative) | — |
| RFC-009 | Mask provider protocol shape | Decided | ADR-057 (closes) |
| RFC-010 | MCP tool surface — parameter shapes and errors | Decided | ADR-056 (closes) |
| RFC-011 | Agent context loading order and format | Decided | ADR-059 (closes) |
| RFC-012 | Programmatic vocabulary generation (Path C) | Draft v0.1 (deferred) | — |
| RFC-013 | Vocabulary gap surfacing format | Decided | ADR-060 (closes) |
| RFC-014 | End-of-session synthesis flow | Decided | ADR-061 (closes) |
| RFC-015 | EXIF auto-binding rules | Decided | ADR-053 (closes) |
| RFC-016 | Versioned prompt system | Decided | ADR-043, ADR-044, ADR-045 |
| RFC-017 | Evaluation harness and auto-research workflow | Accepted (design); built Phase 5 | ADR-046, ADR-047 |
| RFC-018 | Vocabulary expansion for expressive taste articulation | Draft v0.1 | ADR-063, ADR-064 |

## Maturity legend

- **Draft v0.1** — written; deliberation captured; awaiting implementation evidence to close
- **Draft v0.1 (speculative)** — question identified but problem isn't real yet (e.g. vocabulary too small to need discovery tooling); placeholder until it becomes pressing
- **Draft v0.1 (deferred)** — question identified, deliberately not being argued in this round; revisit later
- **Accepted** — design decision settled; closing ADRs lock the structural pieces. Distinct from "Decided" because the RFC remains a living reference for the rationale.
- **Accepted (design); built Phase X** — design accepted now, implementation deferred to a named phase
- **Decided** — closed into one or more ADRs; remains as historical record

## Conventions

- Numbered sequentially (`RFC-NNN-slug.md`)
- Every RFC has a "Why this is an RFC" gating sentence in the header
- "Alternatives considered" must list real alternatives with honest reasons for rejection
- An RFC that argues for something already-decided is an ADR; close and start over
