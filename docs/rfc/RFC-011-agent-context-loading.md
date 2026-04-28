# RFC-011 — Agent context loading order and format

> Status · Draft v0.1
> TA anchor ·/components/mcp-server
> Related · ADR-030, ADR-031
> Closes into · ADR-031 (already partly), additional ADRs for loading format (pending)
> Why this is an RFC · ADR-030 commits to three-tier context (taste/brief/notes). ADR-031 commits to propose-and-confirm updates. But the run-time loading question — what the agent sees at session start, in what order, how it's formatted — is open. The agent's effectiveness depends critically on this. Different formats produce dramatically different agent behaviors.

## The question

When the agent starts a session on an image, it calls `read_context(image_id)`. What does the response look like? In what order are the three tiers presented? How is recent log integrated? What's the format — concatenated markdown, structured JSON, mixed?

The wrong answer wastes context window or buries critical information. The right answer makes the agent feel like it's been on the project for months.

## Use cases

- New session on image A — agent reads `taste.md`, `brief.md`, `notes.md`, recent log → understands "this is the iguana image, photographer wants subtle structure, last session we tagged v1_export, the WB still feels too cool."
- Long-running image (30 sessions) — `notes.md` is hundreds of lines. Agent needs the whole file or a summary?
- New image, no prior sessions — `notes.md` is empty. Agent's reading order should still work.
- Mid-session, agent re-reads context — does this happen? Probably rarely; once at start is the dominant case.

## Goals

- Agent has bearings within the first turn
- Context is readable as prose by the agent (not parse-required JSON)
- Recent activity is surfaced (not just static taste/brief/notes)
- Format scales to long histories without exploding context window

## Constraints

- TA/components/mcp-server — `read_context` is a tool the agent calls
- ADR-030 — three-tier model is fixed
- ADR-031 — propose-and-confirm for updates
- Agent context windows are bounded — the response can't be unbounded

## Proposed approach

**Response shape: structured top, prose bodies.**

```python
{
    "success": True,
    "data": {
        "image_id": "abc123",
        "session_id": "...",  # current session
        "loaded_at": "2026-04-27T15:30:00Z",
        "starting_snapshot_hash": "a3f2...",

        "taste": {
            "path": "~/.chemigram/taste.md",
            "version": 47,
            "last_modified": "2026-04-20T10:15:00Z",
            "content": "..."   # raw markdown of taste.md
        },
        "brief": {
            "path": "<image_id>/brief.md",
            "content": "..."   # raw markdown
        },
        "notes": {
            "path": "<image_id>/notes.md",
            "content": "...",  # raw markdown; possibly summarized for long histories
            "summarized": False,
            "full_length_lines": 120
        },
        "recent_log": [
            {
                "timestamp": "...",
                "session_id": "...",
                "summary": "applied tone_lifted_shadows_subject; tagged v1_export"
            },
            # last 5-10 entries
        ],
        "vocabulary_gaps": [
            # last 3-5 unresolved gaps from this image
        ]
    }
}
```

**Reading order convention:**

The agent's prompt template (02/9) instructs the agent to read the context in a specific order:
1. `taste` (global enduring preferences)
2. `brief` (this image's intent)
3. `notes` (this image's working observations)
4. `recent_log` (what happened recently)
5. `vocabulary_gaps` (what we don't have a good word for)

This order surfaces "the photographer's craft" first, then "this image's specifics," then "what's recent."

**Long-notes summarization:**

For `notes.md` longer than ~50 lines, the engine summarizes by:
- Keeping the first 10 lines (typically context-setting)
- Keeping the last 30 lines (recent observations)
- Replacing the middle with `[... N lines elided; full notes at <path> ...]`

The summarized field flags this. The agent can call `read_full_notes(image_id)` if it needs the full text (proposed as an extension to `read_context`).

**Recent log format:**

Each log entry is one operation summary. The engine emits these from `log.jsonl` by extracting structured highlights ("applied X primitive," "tagged Y," "branched to Z"). Verbose tool-call traces stay in `log.jsonl` itself; the recent_log gives the agent the high-level pattern.

## Alternatives considered

- **Concatenate all three files into one markdown blob:** rejected — loses the boundary structure that helps the agent reason about "this is global vs this is per-image."
- **Pure markdown (no JSON wrapper):** rejected — the agent needs to know which file is which (paths), when they were last modified, etc. Pure markdown buries this.
- **No summarization (always send full files):** rejected — for long-running images, this would dominate the context window. Mitigation needed.
- **More aggressive summarization (e.g., LLM-based summary of all three files):** rejected for v1 — adds an LLM call before every session, which feels heavy for a `read_context`. Defer until evidence shows simple line-truncation isn't adequate.
- **Skip the structured wrapper, return Markdown with section headers:** considered. Loses metadata fields. The structured shape is more flexible.

## Trade-offs

- The structured top + prose body design is a JSON object — slightly verbose. Acceptable: each field is small, and the prose bodies are markdown which agents read well.
- The line-based summarization is heuristic; might cut a critical observation. Mitigated: full notes are accessible via `read_full_notes`.
- Pre-assembling `recent_log` from `log.jsonl` is engine work. Cheap; happens once per session start.

## Open questions

- **What constitutes "recent"?** Last 24 hours? Last 5 sessions? Last 10 operations? Proposed: last 5 sessions OR last 24 hours, whichever is larger. Tunable in `~/.chemigram/config.toml`.
- **Should `taste.md` be summarized at length?** It's the longest file in mature use. Proposed: same line-truncation rule as notes; full-version access via separate tool.
- **What's the right summarization for long taste.md?** "Recent" doesn't quite apply — the file accumulates across all images. Proposed: keep the file's section structure; truncate within each section if it's long.
- **Cross-image taste extraction.** Could the engine show "5 most-used vocabulary entries this month"? Probably useful; defer to a future tool.

## How this closes

This RFC closes into:
- **An ADR locking the response shape** for `read_context`.
- **An ADR for the summarization rules** if line-truncation is wrong.

## Links

- TA/components/mcp-server
- ADR-030 (three-tier context model)
- ADR-031 (propose-and-confirm)
- ADR-033 (MCP tool surface)
- 02/9 (agent prompt template)
