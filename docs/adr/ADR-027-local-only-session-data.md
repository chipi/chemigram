# ADR-027 — Local-only session data; no telemetry, no cloud

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/constraints/local-only-data
> Related RFC · None (foundational privacy commitment)

## Context

Chemigram's session transcripts, taste evolution, vocabulary gaps, masks, and per-image notes are intimate research artifacts — they capture the photographer's craft as it forms. Each is also data that, in another product context, might be collected for analytics, model training, or "improvement of the service."

The project is run by a hobbyist photographer for hobbyist photographers, and the research thesis depends on photographers trusting the system enough to be honest in their notes. Any whisper of telemetry or cloud sync poisons that.

## Decision

All Chemigram artifacts stay on the photographer's machine. No telemetry. No "anonymized analytics." No phone-home. No cloud dependency. The engine never makes outbound network requests except through MCP-configured providers that the photographer explicitly chose (e.g., a hosted masking service, the photo agent itself).

This applies to:
- Session transcripts (`<image_id>/sessions/*.jsonl`)
- Per-image notes (`<image_id>/notes.md`)
- Per-image briefs (`<image_id>/brief.md`)
- Global taste (`~/.chemigram/taste.md`)
- Vocabulary gaps (`<image_id>/vocabulary_gaps.jsonl`)
- Snapshots (`<image_id>/objects/`, `refs/`, `log.jsonl`)
- Masks (`<image_id>/masks/`)
- Configuration (`~/.chemigram/config.toml`)

## Rationale

- **Trust.** Photographers must feel safe being honest in `taste.md` and `notes.md` for those files to do their job. Any extraction risk poisons the artifact.
- **Research integrity.** The research thesis (taste transmission via vocabulary + context) depends on photographers actually using the system as designed. Telemetry concerns block that.
- **Simplicity.** No telemetry pipeline to build, no analytics infrastructure to maintain, no privacy review process for what gets collected.
- **Sets a clear principle for future features.** "Could we add X" gets a fast answer when X involves data exfiltration: no.

## Alternatives considered

- **Opt-in anonymized telemetry for "product improvement":** rejected — even with opt-in, the existence of the pipeline shapes user behavior (people self-censor knowing telemetry exists). Better to commit absolutely.
- **Local-first with optional cloud sync (e.g., for cross-machine work):** out of scope for v1. If photographers want sync, they can use rsync, git, Dropbox, or any other generic tool to sync their `~/Pictures/Chemigram/` directory. We don't build sync into the engine.
- **Voluntary anonymized data sharing for research:** could be added later as an explicit, photographer-initiated export action with full visibility into what gets shared. Not v1 scope.

## Consequences

Positive:
- Strong, simple privacy commitment that's easy to communicate
- No data pipeline infrastructure to build or maintain
- Photographers can trust their artifacts won't leak
- Research integrity: photographers behave naturally in their notes

Negative:
- We learn nothing about how Chemigram is used aggregate-wise (mitigated: voluntary feedback, sample case studies from consenting users, in-person conversations at events)
- "Sync across machines" is the photographer's problem, not Chemigram's (mitigated: their data is plain files; standard sync tools work)

## Implementation notes

The engine has no HTTP client in `chemigram_core`. Network access happens only through MCP server / client communication with explicitly-configured providers. The MCP server itself does not make outbound calls to any Chemigram-controlled service. CI includes a check that `chemigram_core` has no `requests`, `httpx`, `urllib`, etc. imports.
