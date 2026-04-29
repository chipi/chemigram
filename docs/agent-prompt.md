# Agent Prompt — Mode A v1

> **Redirect.** As of v0.3.0 (Slice 3), the canonical Mode A system prompt
> lives in the source tree at:
>
> `src/chemigram/mcp/prompts/mode_a/system_v1.j2`
>
> with version registration in `src/chemigram/mcp/prompts/MANIFEST.toml`
> and a per-version changelog at
> `src/chemigram/mcp/prompts/mode_a/system_v1.changelog.md`.
>
> This file is preserved as a redirect because RFC-016 (now closed) and
> several other docs reference it by URL. The original v0.1 draft is
> recoverable via `git log --follow` on this path; the runtime artifact
> took precedence once Slice 3 shipped.

The prompt system follows ADR-043 (Jinja2 + filename-versioned templates),
ADR-044 (PromptStore API + MANIFEST.toml), and ADR-045 (prompt versions
independent of package SemVer). To view the active prompt, open the `.j2`
file above. To render it against sample context, use:

```python
from pathlib import Path
from chemigram.mcp.prompts import PromptStore

store = PromptStore(Path("src/chemigram/mcp/prompts"))
print(
    store.render(
        "mode_a/system",
        {"image_id": "abc123", "vocabulary_size": 30, "masker_available": False},
    )
)
```

New iterations (v2, v3, …) land as new files alongside `system_v1.j2`; the
active version is bumped in `MANIFEST.toml`. Old versions stay on disk for
eval reproducibility (per ADR-045).
