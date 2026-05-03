# Getting started with Chemigram

This is the user guide. If you've heard about Chemigram and want to actually run it, you're in the right place. The README has the project pitch; this guide takes you from a fresh machine to a working Mode A session with a real raw photo.

The guide grows as the project does. If something here is wrong or unclear, please [open an issue](https://github.com/chipi/chemigram/issues).

---

## What you need

- **macOS Apple Silicon** (Linux is best-effort in v1.x; Windows untested)
- **Python 3.11 or newer**
- **darktable 5.x** — install from [darktable.org](https://www.darktable.org/install/) or `brew install --cask darktable`
- **An MCP-capable AI client** — one of:
  - [Claude Code](https://docs.claude.com/en/docs/claude-code) (CLI)
  - [Claude Desktop](https://claude.ai/download) (macOS/Windows/Linux app)
  - [Cursor](https://cursor.com/) (IDE)
  - [Continue](https://continue.dev/) (VS Code / JetBrains extension)
  - [Cline](https://cline.bot/) (VS Code extension)
  - [Zed](https://zed.dev/) (editor)
  - OpenAI Codex CLI / ChatGPT (see notes in the [client matrix](#connecting-your-mcp-client) below)
- **One raw photo** to work with — anything darktable supports (NEF, ARW, RAF, CR2, DNG, …)

---

## Install

```bash
pip install chemigram
```

That's it for the engine. The package ships with a small starter vocabulary built in (5 entries, deliberately small per the project's Phase 2 design — see [Growing your vocabulary](#growing-your-vocabulary) below).

Verify the install:

```bash
chemigram-mcp --help 2>&1 | head -1   # should not error
python -c "from chemigram.core.vocab import load_starter; print(len(load_starter().list_all()), 'entries')"
# → 5 entries
```

### Setting up darktable on macOS

Chemigram drives darktable headlessly via `darktable-cli`. On macOS the `.app` bundle hides the binary in a way that breaks direct symlinks (the bundle resolves resources from the *invocation path*, so a bare symlink fails with "can't init develop system"). The fix is a thin wrapper script:

```bash
sudo tee /opt/homebrew/bin/darktable-cli > /dev/null <<'EOF'
#!/bin/bash
exec /Applications/darktable.app/Contents/MacOS/darktable-cli "$@"
EOF
sudo chmod +x /opt/homebrew/bin/darktable-cli
```

Adjust the path if your `darktable.app` lives elsewhere. Verify:

```bash
darktable-cli --version 2>&1 | head -1
# → this is darktable 5.4.1
```

If you need to point Chemigram at a non-standard `darktable-cli` location, set the `CHEMIGRAM_DT_CLI` environment variable to the absolute path.

### Initialize a darktable configdir (one-time)

darktable-cli needs a configdir that's been bootstrapped at least once by the GUI. The simplest way: launch the darktable GUI and quit it. That creates `~/.config/darktable/` (or `~/Library/Application Support/darktable/` on macOS) with the schemas and library that `darktable-cli` expects.

If you skip this step, the first render in a Chemigram session will fail with "can't init develop system."

---

## First-time configuration

### Create the chemigram directory

```bash
mkdir -p ~/.chemigram/tastes
mkdir -p ~/Pictures/Chemigram
```

`~/.chemigram/` holds your *cross-image* configuration: tastes, personal vocabulary (Phase 2), config files. `~/Pictures/Chemigram/` is where per-image workspaces live.

### Seed your taste

Write a starter `~/.chemigram/tastes/_default.md` — your global preferences. The agent reads this on every session's first turn. Keep it short and honest; you'll grow it through use.

```markdown
# My default photographic taste

- I prefer natural-feeling tone curves over heavy contrast
- For shadows, I'd rather lift a stop than crush them
- Subtle white balance shifts are fine; I don't want neutral-at-all-costs
- I dislike haloing around high-contrast edges
- Colors should feel restrained, not muted
```

That's enough to start. The agent will propose additions over time via `propose_taste_update`; you confirm each one.

Optionally, create per-genre files for situations where your taste shifts:

```bash
echo "# Underwater taste\n\n- Slate-blue water beats cyan-pop\n- Subjects want warmth on their belly\n" > ~/.chemigram/tastes/underwater.md
```

Per-image briefs (in each workspace's `brief.md`) declare which genre files apply for that image:

```markdown
# This image
Tastes: [underwater]

A manta ray at 18m off La Ventana, late afternoon, bottom-up angle.
```

---

## Connecting your MCP client

Chemigram exposes itself as an MCP (Model Context Protocol) stdio server: `chemigram-mcp`. Every modern AI coding/conversation tool that supports MCP can talk to it. The configuration shape is similar across clients but the file location differs.

### Claude Code (CLI)

Project-local (recommended): create `.mcp.json` in your project root, or any directory you'll be working from:

```json
{
  "mcpServers": {
    "chemigram": {
      "command": "chemigram-mcp"
    }
  }
}
```

User-global: same content at `~/.claude/mcp.json`.

Restart `claude` (the Claude Code CLI). On first connection it'll prompt you to approve the MCP server.

### Claude Desktop (macOS/Windows/Linux app)

Edit your Claude Desktop config (locations vary by OS):

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "chemigram": {
      "command": "chemigram-mcp"
    }
  }
}
```

Quit and reopen Claude Desktop. The MCP server appears in the connectors UI.

### Cursor

Cursor reads MCP config from `.cursor/mcp.json` in your project, or globally via Settings → Features → MCP. Same shape:

```json
{
  "mcpServers": {
    "chemigram": {
      "command": "chemigram-mcp"
    }
  }
}
```

### Continue (VS Code / JetBrains)

Continue reads MCP config from `~/.continue/config.yaml` (yaml, not json):

```yaml
mcpServers:
  - name: chemigram
    command: chemigram-mcp
```

Or via the Continue UI: Settings → Tools → MCP Servers → Add.

### Cline (VS Code)

Open Cline's settings panel in VS Code → MCP Servers → Edit Configuration. Same JSON shape as Claude Code/Desktop.

### Zed

Edit `~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "chemigram": {
      "command": {
        "path": "chemigram-mcp",
        "args": []
      }
    }
  }
}
```

Restart Zed.

### OpenAI Codex CLI / ChatGPT

OpenAI added MCP support to their stack in late 2025 — the configuration is evolving. Check the [OpenAI Codex CLI MCP docs](https://github.com/openai/codex) for the latest format. The general pattern (a `command: chemigram-mcp` registration) maps cleanly; only the file location and JSON envelope differ.

For ChatGPT (web/desktop), MCP integration goes through the Connectors panel rather than a config file. Add `chemigram-mcp` as a custom connector per the in-app instructions.

### Pointing at a custom Python (uv, conda, etc.)

If you installed `chemigram` into a virtualenv that isn't on your shell PATH, point the MCP config at the absolute path:

```json
{
  "mcpServers": {
    "chemigram": {
      "command": "/Users/you/.venv/chemigram/bin/chemigram-mcp"
    }
  }
}
```

Or invoke via `uv run` if you're working from a checkout:

```json
{
  "mcpServers": {
    "chemigram": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/chemigram-checkout", "chemigram-mcp"]
    }
  }
}
```

---

## Your first session

Once your MCP client sees `chemigram-mcp`, start a conversation. The agent's first move is always `read_context` — it reads your tastes, the brief, any prior notes, and recent operations.

Drop a raw photo somewhere accessible (e.g., `/tmp/manta.NEF`) and say:

> Ingest /tmp/manta.NEF. Read context. Tell me what you see.

A typical exchange (paraphrased — the actual agent will be wordier):

```
You:    Ingest /tmp/manta.NEF. Read context.

Agent:  [calls ingest → image_id "manta"; reads context]
        I've ingested manta.NEF as image_id "manta". Tastes loaded:
        natural tone curves, lifted shadows over crushed blacks, restrained
        colors. No genre file declared in brief.md yet. Notes empty.

        Looking at the metadata: Canon EOS R5, f/8, 1/250s, ISO 400, 24mm.
        No L1 templates for this camera/lens combination yet.

You:    Render a preview at 1024px so we can see what we're working with.

Agent:  [calls render_preview]
        Saved to ~/Pictures/Chemigram/manta/previews/preview_*.jpg. The
        baseline is darktable's default — flat tone curve, slightly cool
        WB. The water reads cyan-blue.

You:    The water feels too cyan. Try wb_warm_subtle, then let me see.

Agent:  [calls apply_primitive("wb_warm_subtle"), then render_preview]
        Applied wb_warm_subtle (snapshot abc123). Render here. The blue
        is closer to slate now, less pure cyan.

You:    Better. The sky's blown out at the top. Dampen it.

Agent:  [calls apply_primitive("gradient_top_dampen_highlights"),
         then render_preview]
        Applied gradient_top_dampen_highlights (snapshot def456). The
        entry binds a -0.5 EV exposure through a top-bright gradient
        directly into the XMP — darktable does the masking. Top 40%
        is dampened; the rest is untouched.

You:    Good. Lift the bottom of the frame a touch where the manta sits.

Agent:  [calls apply_primitive("gradient_bottom_lift_shadows"),
         then render_preview]
        Applied. The bottom half lifted +0.4 EV. The manta reads with
        more presence now without affecting the water column above.

[... session continues with radial_subject_lift, snapshots, branches ...]

You:    OK, this is good. Save it as v1-export. Take a final snapshot.

Agent:  [calls tag("v1-export"), snapshot]
        Tagged. Final snapshot ghi789. Want me to export at full res?

You:    Yes, JPEG. Then wrap up.

Agent:  [calls export_final, then proposes a notes update + a taste
         addition + confirms vocabulary gaps if any]
        Exported to ~/Pictures/Chemigram/manta/exports/.

        I noticed you preferred slate-blue water over cyan-pop and
        leaned on the gradient pair (top dampen + bottom lift) for
        the wide shape. Two propose-and-confirms:

        1. Add to underwater.md: "For pelagic shots, slate-blue water
           reads better than cyan-pop." Confirm?
        2. Notes for this image: "Top-dampen + bottom-lift gradient
           pair carried the wide composition; subject lift added
           presence without going local." Confirm?

You:    Confirm 1. Skip 2.

Agent:  [calls confirm_taste_update]
        Done. Underwater.md updated. Session wrap.
```

That's the loop. The agent can branch (`branch experimental`), checkout earlier states, diff snapshots, log gaps when the vocabulary doesn't have what you want — the 22 tools are available; you don't need to know them by name, the agent reaches for what it needs.

> **Note on local adjustments.** v1.5.0 ships drawn-form geometric masks (gradient / ellipse / rectangle) baked into vocabulary entries' `mask_spec`. Subject-precise content-aware masking ("lift the shadows on the manta's belly") arrives in Phase 4 via a sibling project. Per ADR-076, the earlier PNG-based masker path was retired — darktable doesn't read external PNG masks at all.

---

## Driving Chemigram from a script or agent loop (CLI)

The CLI (v1.3.0+) exposes the same operations as the MCP server as subprocess-callable verbs. Same engine, same vocabulary, same workspace state on disk — just a different invocation surface. PRD-005 / RFC-020 cover the design.

This shape is for:

- **Batch processing** — `for f in *.NEF; do chemigram apply-primitive ... ; done`
- **Agent-loop builders** — LangGraph pipelines, Claude Code scripts, custom Python loops that shell out to subprocesses rather than maintain an MCP session
- **Watch-folder daemons and CI scripts**

It's *not* for interactive editing — that's MCP's job.

### Setup

The `chemigram` binary lands on your `$PATH` after `pip install chemigram` (alongside `chemigram-mcp`). Point at a pre-bootstrapped darktable configdir for any verb that renders:

```bash
export CHEMIGRAM_DT_CONFIGDIR=~/chemigram-phase0/dt-config
chemigram status   # confirms versions, packs, prompt store, output schema
```

### A minimal session

```bash
# 1. ingest a raw — creates ~/Pictures/Chemigram/iguana/ with baseline snapshot
chemigram ingest ~/Pictures/raw/iguana.NEF

# 2. apply primitives — each call snapshots the new state
chemigram apply-primitive iguana --entry expo_+0.5
chemigram apply-primitive iguana --entry wb_warm_subtle

# 3. branch + iterate
chemigram branch iguana --name aggressive
chemigram apply-primitive iguana --entry expo_+0.5   # second EV bump on the branch

# 4. compare
chemigram --json get-state iguana       # capture the current hash
chemigram checkout iguana baseline      # back to the ingest state for diff
chemigram compare iguana baseline aggressive --size 1024

# 5. final export
chemigram checkout iguana aggressive
chemigram export-final iguana --format jpeg
```

Every verb takes `--json` for newline-delimited JSON output suitable for scripting.

### Agent-loop pattern

The intended Python integration:

```python
import json
import subprocess

def chemigram(*args: str) -> dict:
    """Call chemigram with --json; return the final summary event."""
    result = subprocess.run(
        ["chemigram", "--json", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        # stderr is NDJSON in --json mode; the last line is the error event
        err = json.loads(result.stderr.strip().splitlines()[-1])
        raise RuntimeError(f"{err['exit_code_name']}: {err['message']}")
    # stdout's last line is always the final result event
    return json.loads(result.stdout.strip().splitlines()[-1])

# Use it in a loop
for raw in glob("/path/to/raws/*.NEF"):
    chemigram("ingest", raw)
    image_id = Path(raw).stem
    chemigram("apply-primitive", image_id, "--entry", "expo_+0.5")
    summary = chemigram("export-final", image_id, "--format", "jpeg")
    print(f"exported {image_id} → {summary['output_path']}")
```

No MCP session lifecycle. No transport. Just subprocesses + structured exit codes + NDJSON. The CLI's exit codes (`SUCCESS=0`, `INVALID_INPUT=2`, `NOT_FOUND=3`, `STATE_ERROR=4`, `VERSIONING_ERROR=5`, `DARKTABLE_ERROR=6`, `MASKING_ERROR=7`, `SYNTHESIZER_ERROR=8`, `PERMISSION_ERROR=9`, `NOT_IMPLEMENTED=10`) are documented and stable; agents can branch on them without parsing stderr text.

### What CLI doesn't do

- **No `propose-taste-update` / `confirm-taste-update`.** Those are conversational by design — the propose/confirm dance lives between an agent and a human inside an MCP session. The CLI offers `apply-taste-update` / `apply-notes-update` as direct verbs for the agent-loop case (the agent has already decided; the CLI just writes).
- **No interactive REPL.** Stateless per-invocation. If you want a conversation, MCP is the surface.

For the full verb surface — every command, every flag, every exit code — see [`docs/guides/cli-reference.md`](guides/cli-reference.md).

---

## Where things live

```
~/.chemigram/
  tastes/
    _default.md          ← always loaded
    underwater.md        ← genre-specific; loaded when brief declares it
    wildlife.md
  vocabulary/
    personal/            ← your private pack (Phase 2)
      manifest.json
      layers/L3/...

~/Pictures/Chemigram/<image_id>/
  raw/<basename>         ← symlink to your original
  brief.md               ← intent + Tastes: [...] declaration
  notes.md               ← accumulated session notes
  current.xmp            ← synthesized current state
  objects/               ← content-addressed snapshot store (sha256 sharded)
  refs/heads/<branch>    ← branch refs (text files: hash)
  refs/tags/<tag>        ← tag refs
  refs/HEAD              ← current head
  log.jsonl              ← append-only operation log
  sessions/<id>.jsonl    ← per-session transcripts
  previews/              ← render cache
  exports/               ← final outputs
  vocabulary_gaps.jsonl  ← gaps surfaced this image
```

The shipped starter vocabulary lives inside the package install — it's not a directory you edit. Your *personal* vocabulary at `~/.chemigram/vocabulary/personal/` is where you grow your craft.

---

## Growing your vocabulary

This is Phase 2. The agent flags gaps via `log_vocabulary_gap` when you reach for a move it doesn't have. Periodically — a vocabulary-authoring evening per month is the rhythm — you turn those gaps into real entries.

The flow:

1. **Run sessions.** The agent logs gaps when it can't find what you want.
2. **Read your gaps.** `cat ~/Pictures/Chemigram/*/vocabulary_gaps.jsonl | jq` shows what came up across images.
3. **Open darktable's GUI.** For each gap that recurred (e.g., "subtle gradient warm tone"), recreate the move on a sample image; export the style as a `.dtstyle` file. Keep moves single-module where possible — composition is more legible than chunky multi-module styles.
4. **Drop into your personal pack.** Place the `.dtstyle` under `~/.chemigram/vocabulary/personal/layers/L3/<module>/` and add a manifest entry.
5. **Validate.** `./scripts/verify-vocab.sh ~/.chemigram/vocabulary/personal` (works in the chemigram checkout; for `pip install`, use the equivalent Python one-liner shown by the script).
6. **Run again.** The agent now has the new primitive in its action space.

Markers of growth: ~30–60 personal entries after 3 months of regular use; ~80–120 after 6 months. The vocabulary becomes an articulation of *your* craft — moves you reach for, named in language that's natural to you. See `docs/CONTRIBUTING.md` § Vocabulary contributions for the full authoring procedure (including darktable export caveats).

---

## Where to go next

- **The concept package** (`docs/concept/`) — the project's intellectual frame. Read `00-introduction.md` if you want to engage with the why.
- **`docs/IMPLEMENTATION.md`** — phase plan; what's shipped, what's next.
- **`vocabulary/starter/README.md`** — what the bundled pack covers; what's intentionally absent.
- **`docs/CONTRIBUTING.md`** — code and vocabulary contribution flows.
- **`examples/iguana-galapagos.md`** — a worked Mode A session, prose form.

---

## Troubleshooting

**`chemigram-mcp` command not found** — the package didn't install its console script. Reinstall: `pip install --force-reinstall chemigram`. If you're in a venv, activate it before running the MCP client, or point the client config at the absolute path: `/path/to/venv/bin/chemigram-mcp`.

**"can't init develop system" from darktable** — your configdir isn't initialized. Open the darktable GUI once and quit. If the error persists, set `CHEMIGRAM_DT_CONFIGDIR` to a writable directory you've initialized.

**`MASKING_ERROR` from `apply_primitive`** — the entry's `mask_spec` is malformed (unknown `dt_form`, missing/wrong `dt_params`). Inspect the entry with `chemigram vocab show <name>`; valid forms are `gradient`, `ellipse`, `rectangle` per ADR-076. (Subject-precise content-aware masking is Phase 4 work; v1.5.0 has no AI-driven masker — the earlier PNG path was retired because darktable doesn't read external PNGs for raster masks.)

**`STATE_ERROR: workspace has no current XMP`** — the workspace's HEAD doesn't resolve to a snapshot. This usually means the `ingest` step didn't complete cleanly. Try ingesting under a different `image_id` or delete the half-built workspace and start over.

**Render taking forever** — first renders against a fresh configdir are slower. Subsequent ones hit darktable's caches. If renders consistently exceed 10s on Apple Silicon, you may have a slow disk or a large raw — neither is a Chemigram bug. Profile with `darktable-cli --quiet` separately.

**Agent says "no primitive matches"** — the starter pack is deliberately small. The agent will log this as a vocabulary gap; over time, you turn gaps into entries (see [Growing your vocabulary](#growing-your-vocabulary)). For now, ask the agent to improvise with what's there.

**Tastes don't seem to load** — `read_context` returns an empty `tastes.default` if `~/.chemigram/tastes/_default.md` doesn't exist. Create the file; the agent's next `read_context` will pick it up. Set `CHEMIGRAM_TASTES_DIR` if you want a non-standard location.

**Anything else** — [open an issue](https://github.com/chipi/chemigram/issues) with the symptom, the MCP client you're using, and the relevant lines from `~/Pictures/Chemigram/<image_id>/sessions/<id>.jsonl` (the session transcript).
