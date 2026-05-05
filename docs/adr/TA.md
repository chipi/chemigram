# TA — Technical Architecture

> Reference document for the tech plane.
> Version · v0.1 · 2026-04-27
> Sources · `docs/concept/04-architecture.md`, `examples/phase-0-notebook.md`

The reference document for everything technical. Per-artifact docs (RFCs, ADRs) anchor into this with paths like `TA/components/synthesizer` or `TA/constraints`.

This document is **read by linking-into specific sections** — never end-to-end. It's amended whenever state changes (new component, new constraint, RFC closes into ADR).

If TA drifts toward narrative ("this is how we got here"), it has stopped being a reference. The narrative belongs in the concept package (the architecture doc).

---

## components

The five subsystems Chemigram's engine decomposes into. Boundaries are stable; per-component design lives in linked PRD/RFC/ADR.

### components/synthesizer

XMP composition engine. Reads `.dtstyle` files, parses XMPs, synthesizes new XMPs by composing vocabulary entries onto a baseline. Pure file operations — no rendering, no AI.

**Files (shipped):** `src/chemigram/core/xmp.py`, `src/chemigram/core/dtstyle.py` (Slice 1)

**Public API:**
- `parse_dtstyle(path) → list[PluginEntry]`
- `parse_xmp(path) → XMP`
- `synthesize_xmp(baseline_xmp, vocabulary_entries) → XMP`
- `write_xmp(xmp, path) → None`

**Anchored from:** RFC-001, ADR-002, ADR-008, ADR-009, ADR-010

### components/render-pipeline

Sequence of stages producing a JPEG from an XMP. v1 has one stage; the abstraction admits N.

**Files (shipped):** `src/chemigram/core/pipeline.py`, `src/chemigram/core/stages/__init__.py`, `src/chemigram/core/stages/darktable_cli.py` (Slice 1)

**Public API:**
- `class PipelineStage(Protocol)` — inputs/outputs/run contract
- `class DarktableCliStage(PipelineStage)` — the v1 stage
- `Pipeline(stages: list[PipelineStage]).run(context) → StageResult`

**Anchored from:** RFC-005, ADR-004, ADR-005, ADR-013

### components/versioning

Per-image content-addressed DAG of XMP snapshots. "Mini git for photos."

**Files (shipped):** `src/chemigram/core/versioning/{canonical,repo,ops,masks}.py` (v0.2.0)

**Public API:**
- `canonical_bytes(xmp) → bytes`, `xmp_hash(xmp) → str` — content-address primitive
- `ImageRepo.init(root)`, `write_object`, `read_object`, `write_ref`, `resolve_ref`, `list_refs`, `delete_ref`, `append_log`, `read_log`
- `snapshot(repo, xmp, *, label?, parent="HEAD", metadata?) → hash`
- `checkout(repo, ref_or_hash) → Xmp`
- `branch(repo, name, from_="HEAD") → ref_name`
- `log(repo, *, ref?, limit?) → list[LogEntry]`
- `diff(repo, hash_a, hash_b) → list[PrimitiveDiff]`
- `tag(repo, name, hash_?) → ref_name`


**Anchored from:** RFC-002 (→ ADR-054), ADR-017, ADR-018, ADR-019, ADR-020. (Mask-registry surface — RFC-003 / ADR-055 / ADR-021 / ADR-022 — removed in v1.5.0 per ADR-076; the PNG path was a silent no-op.)

### components/masking

Drawn-mask serialization for vocabulary entries that shape only part of the frame. Encodes geometric forms (gradient / ellipse / rectangle) directly into darktable's `<darktable:masks_history>` XMP element, and patches each plugin's `blendop_params` to bind the form via `mask_id`.

**Files (shipped v1.4.0, simplified v1.5.0):** `src/chemigram/core/masking/dt_serialize.py` — encoders for `dt_masks_point_gradient_t`, `dt_masks_point_ellipse_t`, 4-corner `dt_masks_point_path_t`, plus the 420-byte `dt_develop_blend_params_t` patch. High-level apply helper at `chemigram.core.helpers.apply_with_drawn_mask`.

**Public API:**
- `apply_with_drawn_mask(baseline, dtstyle, mask_spec, *, opacity=100.0) → Xmp` — apply a vocabulary entry's dtstyle bound to a drawn form. Routed by `apply_primitive` either from the entry's manifest `mask_spec` (the v1.5.0 path) or from a caller-supplied `mask_spec` parameter (the v1.6.0 path; CLI: `--mask-spec '<json>'`, MCP: `mask_spec` arg). Caller override wins when both present.

**Schema:** `mask_spec: {"dt_form": "gradient"|"ellipse"|"rectangle", "dt_params": {...}}` on the vocabulary entry. No PNG, no provider, no registry — see ADR-076.

**Anchored from:** ADR-076 (closes the prior PNG-mask path retroactively; supersedes ADR-021/022/055/057/058/074)

### components/mcp-server

Adapts subsystems 1–4 as agent-callable tools. Thin layer.

**Files:** `src/chemigram/mcp/server.py` (bootstrap + stdio), `src/chemigram/mcp/registry.py` (tool registry + `ToolContext`), `src/chemigram/mcp/errors.py` (`ToolResult` / `ToolError` / `ErrorCode`), `src/chemigram/mcp/_test_harness.py` (in-memory client/server harness), `src/chemigram/mcp/tools/*` — 22 tools as of v1.5.0 across vocab/edit (5), versioning (6), rendering (3), ingest (3), context (5). The 5 mask tools (`generate_mask`/`regenerate_mask`/`list_masks`/`tag_mask`/`invalidate_mask`) shipped in v0.3.0–v0.4.0 and were removed in v1.5.0 per ADR-076 — see CHANGELOG.

**Tool surface:** see TA/contracts/mcp-tools.

**Anchored from:** ADR-006, ADR-033, ADR-056 (closes RFC-010)

### components/cli

Subprocess-callable adapter over the same core that the MCP server adapts. Mirrors the MCP tool surface verb-for-verb (with `_` → `-` for shell ergonomics). Ships in v1.3.0 (RFC-020 closure). Two adapters, one core; no domain logic in either adapter layer (lint-enforced).

**Files (planned v1.3.0):** `src/chemigram/cli/main.py` (Typer root app + global-options callback), `src/chemigram/cli/commands/*` (one file per verb group), `src/chemigram/cli/output.py` (`HumanWriter` + `JsonWriter` behind `OutputWriter` Protocol), `src/chemigram/cli/exit_codes.py` (`ExitCode` IntEnum), `src/chemigram/cli/error_mapping.py` (maps `chemigram.mcp.errors.ErrorCode` to `ExitCode`).

**Entry point:** `chemigram` binary via `pyproject.toml` `[project.scripts]`, alongside `chemigram-mcp`.

**Verb surface:** see RFC-020 §F. Each verb maps 1:1 to an MCP tool from ADR-033/056 plus a diagnostic `chemigram status` (not a tool wrapper).

**Output:** human-readable text by default; NDJSON via `--json`. Schema mirrors `chemigram.mcp.errors.ToolResult` shape; versioned independently of package SemVer (same pattern as ADR-045 for prompts); surfaced in `chemigram status`.

**Exit codes:** `ExitCode` IntEnum mapped from `ErrorCode`; the two enums move in lockstep, audit-tested.

**Constraint (ADR-071):** No XML, subprocess, or raw filesystem imports in this layer or in `chemigram.mcp/`. All domain operations come from `chemigram.core`. CI lints for forbidden imports.

**Anchored from:** PRD-005, RFC-020, ADR-069, ADR-070, ADR-071, ADR-072

### components/prompts

Versioned prompt templates loaded by the MCP server at session start (and by the eval harness for autonomous Mode B runs). Append-only, MANIFEST-driven, Jinja2-templated.

**Files (shipped v0.3.0):** `src/chemigram/mcp/prompts/store.py` (PromptStore), `src/chemigram/mcp/prompts/MANIFEST.toml` (active-version registry), `src/chemigram/mcp/prompts/mode_a/system_v1.j2` (Mode A v1; migrated from `docs/agent-prompt.md`). Mode B + helpers ship in later phases per their RFC closures.

**Public API:**
- `PromptStore.render(path, context, version=None, provider=None) → str`
- `PromptStore.active_version(path) → str`
- `PromptStore.context_schema(path) → dict`
- `PromptStore.list_templates() → list[str]`

**Anchored from:** RFC-016, ADR-043, ADR-044, ADR-045

### components/context

Per-image and per-photographer context loaders. Reads tastes (multi-scope per ADR-048: `~/.chemigram/tastes/_default.md` plus brief-declared genre files), `brief.md` (with `Tastes:` declaration), `notes.md` (with line-truncation summarization for long files), recent log entries, recent vocabulary gaps. Tolerates missing files (returns empty structures so the agent's first turn works on a fresh workspace).

**Files (shipped v0.5.0):** `src/chemigram/core/context/__init__.py` — `Tastes`, `Brief`, `Notes`, `RecentLog`, `RecentGaps` loaders + their content dataclasses. MCP wiring in `src/chemigram/mcp/tools/context.py` (read_context + propose/confirm tools).

**Public API:** loaders' `.load(workspace, ...)` classmethods; `read_context(image_id)` MCP tool.

**Anchored from:** RFC-011 (→ ADR-059), ADR-031, ADR-048

### components/session

JSONL session transcripts per ADR-029. Header line, per-turn entries (`tool_call`, `tool_result`, `proposal`, `confirmation`, `note`), footer on close. Append-only, flushed per write.

**Files (shipped v0.5.0):** `src/chemigram/core/session/__init__.py` — `SessionTranscript`, `SessionHeader`, `start_session`. MCP server's tool dispatch (`build_server(transcript=...)`) auto-records every tool call.

**Public API:** `start_session(workspace, *, mode, session_id, ...) -> SessionTranscript`; `transcript.append_*` helpers; `transcript.close(summary?)`.

**Anchored from:** ADR-029, ADR-031, RFC-014 (→ ADR-061)

### components/eval

Headless eval harness for autonomous Mode B. Runs the agent against versioned golden datasets, computes mechanical and semantic metrics, writes run manifests for cross-run comparison. Phase 5 build; design locked in Phase 1.

**Files (planned):** `src/chemigram/eval/runner.py`, `src/chemigram/eval/scenarios.py`, `src/chemigram/eval/metrics/{mechanical,semantic}.py`, `src/chemigram/eval/reports.py`, `src/chemigram/eval/manifest.py`

**Public API (sketched):**
- `EvalRunner(golden_version, prompt_versions, model_config).run_all() → EvalRunResult`
- `EvalRunner.run_scenario(id) → EvalScenarioResult`
- `EvalRunResult.save(path) → None`
- `EvalRunResult.append_history(path) → None`

**Anchored from:** RFC-017, ADR-046, ADR-047

---

## contracts

Data shapes between components. The boundaries that survive across implementation iterations.

### contracts/dtstyle-schema

`.dtstyle` files are XML conforming to darktable's style format. Calibrated to darktable 5.4.1; per `04/3.1` and verified against Phase 0 fixtures:

```xml
<darktable_style version="1.0">
  <info>
    <name>NAME</name>
    <description>...</description>
    <iop_list>...</iop_list>      <!-- optional; absent in single-module exports -->
  </info>
  <style>
    <plugin>
      <num>N</num>
      <module>MODVERSION</module>
      <operation>OPERATION_NAME</operation>
      <op_params>HEX_BLOB</op_params>
      <enabled>1</enabled>
      <blendop_params>GZIP_BASE64_BLOB</blendop_params>
      <blendop_version>14</blendop_version>
      <multi_priority>0</multi_priority>
      <multi_name>STRING</multi_name>
      <multi_name_hand_edited>0</multi_name_hand_edited>
    </plugin>
    <!-- additional plugins... -->
  </style>
</darktable_style>
```

User-authored entries have `<multi_name>` empty (`""`). darktable's auto-applied entries have `<multi_name>` starting with `_builtin_` (e.g., `_builtin_scene-referred default`, `_builtin_auto`).

**Note (Phase 0 finding):** darktable 5.4.1 GUI exports do **not** include `<iop_order>` inside `<plugin>`. Pipeline ordering is reconstructed by darktable from the parent XMP's `darktable:iop_order_version` and a global iop_list, not from per-plugin metadata. Earlier drafts of this schema listed `<iop_order>FLOAT</iop_order>` as a sibling of `<multi_name_hand_edited>`; that was aspirational and has been removed.

### contracts/vocabulary-manifest

Per-pack `manifest.json`. Per `03/Vocabulary primitives`:

```json
{
  "name": "tone_lifted_shadows_subject",
  "layer": "L3",
  "subtype": "look",
  "path": "layers/L3/local/tone_lifted_shadows_subject.dtstyle",
  "touches": ["toneequalizer"],
  "tags": ["tone", "shadows", "local", "subject"],
  "description": "Lift shadow zones, restricted to the subject mask.",
  "mask_kind": "raster",
  "mask_ref": "current_subject_mask",
  "global_variant": "tone_lifted_shadows",
  "modversions": {"toneequalizer": 4},
  "darktable_version": "5.4",
  "source": "starter",
  "license": "MIT"
}
```

### contracts/xmp-darktable-history

darktable's history is an RDF Seq of `<rdf:li>` elements. Calibrated to darktable 5.4.1; per `04/3` and verified against the v3 Phase 0 reference XMP:

```xml
<rdf:li
  darktable:num="N"
  darktable:operation="OPERATION_NAME"
  darktable:enabled="1"
  darktable:modversion="MODVERSION"
  darktable:params="HEX"
  darktable:multi_name="STRING"
  darktable:multi_name_hand_edited="0"
  darktable:multi_priority="0"
  darktable:blendop_version="14"
  darktable:blendop_params="GZIP_BASE64_BLOB"/>
```

Per-entry execution ordering comes from the parent `<rdf:Description>`'s `darktable:iop_order_version="N"` attribute and an internal iop_list, not from per-`<rdf:li>` metadata. `<darktable:history_end>` at the parent controls how many entries are applied.

**Note (Phase 0 finding):** darktable 5.4.1 does not write a `darktable:iop_order` attribute on `<rdf:li>` history entries. Earlier drafts of this schema listed it as required-for-new-instances and inherited-for-replacements; that was aspirational. SET-replace under Path A inherits position implicitly because the entry stays at its baseline index. Path B (new-instance addition at a previously-unused `multi_priority`) currently has no source for `iop_order` from either dtstyle or XMP — implementations should defer Path B to a follow-up.

### contracts/per-image-repo

Per-image directory layout. Per `02/4`:

```
~/Pictures/Chemigram/<image_id>/
  raw/                    symlink to original
  brief.md
  notes.md
  metadata.json           EXIF cache, layer bindings
  current.xmp             synthesized from current snapshot
  objects/                content-addressed snapshot store
    NN/HHHHH...xmp        SHA-256 sharded
  refs/
    heads/<branch>        text file containing snapshot hash
    tags/<tag>            text file containing snapshot hash
    HEAD                  text file: "ref: refs/heads/main" or hash
  log.jsonl               append-only operation log
  sessions/               session transcripts (JSONL per session)
  previews/               render cache (regenerable)
  exports/                final outputs
  masks/                  registered masks + registry.json
  vocabulary_gaps.jsonl   gaps surfaced this image
```

### contracts/mcp-tools

The agent-visible MCP tool surface. Grouped by subsystem.

**Vocabulary and edit operations**
- `list_vocabulary(layer?, tags?)` → entries
- `get_state(image_id)` → entries + head hash
- `apply_primitive(image_id, primitive_name, mask_spec?)` → state_after, snapshot_hash
- `remove_module(image_id, module_name)` → state_after, snapshot_hash
- `reset(image_id)` → state_after (resets to baseline_end, not empty)

**Rendering**
- `render_preview(image_id, size=1024, ref_or_hash?)` → jpeg_path
- `compare(image_id, hash_a, hash_b, size=1024)` → jpeg_path
- `export_final(image_id, ref_or_hash?, size=None, format="jpeg")` → output_path

**Versioning**
- `snapshot(image_id, label?)` → hash
- `checkout(image_id, ref_or_hash)` → state
- `branch(image_id, name, from?)` → ref
- `log(image_id, ref?, limit=20)` → entries
- `diff(image_id, hash_a, hash_b)` → primitive diffs
- `tag(image_id, name, hash?)` → ref

**Masking**
- `generate_mask(image_id, target, prompt?, name?)` → mask_id, name
- `list_masks(image_id)` → entries
- `regenerate_mask(image_id, name, target?, prompt?)` → mask_id
- `invalidate_mask(image_id, name)` → ok
- `tag_mask(image_id, source, new_name)` → mask_id

**Ingestion and binding**
- `ingest(raw_path, image_id?)` → image_id, exif_summary, suggested_bindings
- `bind_layers(image_id, l1_template?, l2_template?)` → state_after

**Context**
- `read_context(image_id)` → taste_md + brief_md + notes_md + recent_log
- `propose_taste_update(content, category)` → proposal_id
- `confirm_taste_update(proposal_id)` → ok
- `propose_notes_update(image_id, content)` → proposal_id
- `confirm_notes_update(proposal_id)` → ok
- `log_vocabulary_gap(image_id, description, workaround)` → ok

---

## constraints

The non-negotiables. Things that hold across all implementation choices.

### constraints/single-process

Engine is a single Python process. No daemon, no IPC between subsystems. Each render spawns a `darktable-cli` subprocess. State is the filesystem.

Anchored from: ADR-006

### constraints/serial-renders

Only one `darktable-cli` instance per configdir at a time. darktable holds an exclusive lock on `library.db`. The render pipeline must serialize subprocess calls.

Anchored from: ADR-005

### constraints/byoa

No AI capabilities bundled with the engine. No PyTorch dependency in `chemigram.core`. No model weights. AI is provided via MCP-configured providers.

Anchored from: ADR-007

### constraints/agent-only-writes

Edit state mutations happen only through the engine's API, called by the agent. The photographer reads previews. The engine never silently mutates state outside an agent-initiated tool call.

Anchored from: ADR-024

### constraints/dt-orchestration-only

Chemigram does not implement image-processing capabilities. All color science, lens correction, denoise, tone, mask logic comes from darktable. Chemigram's responsibility is orchestration: vocabulary, composition, versioning, sessions.

Anchored from: ADR-025

### constraints/opaque-hex-blobs

`op_params` and `blendop_params` are treated as opaque hex/base64 blobs in v1. The synthesizer copies them verbatim from `.dtstyle` to XMP. Programmatic generation (decoding/encoding the C structs) is reserved for Path C — limited to a small set of high-value modules, only when a clear bottleneck appears.

Anchored from: ADR-008, RFC-016

### constraints/modversion-pinning

Vocabulary `.dtstyle` files are calibrated to a specific darktable version. The manifest's `darktable_version` field declares this. When darktable updates a module's `modversion`, captured `.dtstyle` files become invalid for that module.

Anchored from: ADR-026, RFC-007

### constraints/agent-only-mcp

The agent never accesses the engine directly. All operations go through the MCP server. The engine has no agent-aware code.

Anchored from: ADR-006

### constraints/local-only-data

Session transcripts, taste evolution, masks, vocabulary gaps — all stay on the photographer's machine. No telemetry. No phone-home. No cloud dependency.

Anchored from: ADR-027

---

## stack

Locked technology choices. Each entry has a corresponding ADR.

| Layer | Choice | ADR |
|-|-|-|
| Image processor | darktable 5.x (CLI for rendering) | ADR-014 |
| Language | Python 3.11+ | ADR-013 |
| Agent protocol | MCP (Model Context Protocol) | ADR-006 |
| Vocabulary format | darktable `.dtstyle` XML | ADR-008 |
| Edit state | darktable XMP RDF/XML | ADR-008 |
| Versioning storage | Filesystem, content-addressed by SHA-256 | ADR-018 |
| Configuration | TOML (`config.toml`) | ADR-028 |
| Manifest format | JSON (`manifest.json`) | ADR-028 |
| Mask format | Drawn forms encoded into XMP `masks_history` (gradient/ellipse/rectangle) | ADR-076 |
| Prompt template engine | Jinja2 | ADR-043 |
| Active prompt version registry | TOML (`MANIFEST.toml`) | ADR-044 |
| Eval run manifests | JSON + JSONL history | ADR-047 |
| Golden eval datasets | Versioned directories (`golden_v1`, `golden_v2`, ...) | ADR-046 |
| Session transcripts | JSONL | ADR-029 |
| Default mask path | Drawn-form geometry only (no PNG, no provider) | ADR-076 |
| Lens correction | Lensfun (via darktable) + embedded EXIF metadata | ADR-014 |
| Noise model | darktable profiled denoise | ADR-014 |
| Color science | darktable scene-referred pipeline | ADR-014 |
| Subject masking (production) | `chemigram-masker-sam` sibling project | RFC-004 |
| Build backend | hatchling (via `pyproject.toml`) | ADR-034 |
| Package layout | `src/`-style, single distribution, two modules (`chemigram.core`, `chemigram.mcp`) | ADR-034 |
| Dev environment | uv (lockfile: `uv.lock`) | ADR-035 |
| Test framework | pytest, three tiers (unit / integration / e2e) | ADR-036 |
| Linter and formatter | ruff (`ruff check` + `ruff format`) | ADR-037 |
| Type checker | mypy (strict on `chemigram.core`) | ADR-038 |
| Pre-commit hooks | `pre-commit` framework (ruff + mypy + unit tests on push) | ADR-039 |
| CI | GitHub Actions, Python 3.11/3.12/3.13, macOS-only for v1 | ADR-040 |
| Versioning | SemVer (0.x during Phase 1, 1.0.0 at Phase 1 done) | ADR-041 |
| Distribution | PyPI primary; GitHub releases supplement; TestPyPI for early validation | ADR-042 |

---

## map — RFC and ADR state board

The canonical state board for the tech plane. When an RFC closes into an ADR, both tables update; the corresponding stack/component sections update too if affected.

### RFCs

| RFC | Title | Status | Closes into |
|-|-|-|-|
| RFC-001 | XMP synthesizer architecture | Decided | ADR-050 (closes Path A); ADR-063 closes the Path B / iop_order question |
| RFC-002 | Canonical XMP serialization for stable hashing | Decided | ADR-054 (closes) |
| RFC-003 | Mask storage in versioning | Decided | ADR-055 (closes); superseded by ADR-076 (path retired) |
| RFC-004 | Default masking provider — coarse vs SAM | Decided | ADR-058 (closes); superseded by ADR-076 (path retired) |
| RFC-005 | Pipeline stage protocol — abstract now or YAGNI | Decided | ADR-052 (closes) |
| RFC-006 | Same-module collision behavior | Decided | ADR-051 (closes) |
| RFC-007 | modversion drift handling | Draft v0.1 | ADR (pending) |
| RFC-008 | Vocabulary discovery at scale | Draft v0.1 (speculative) | — |
| RFC-009 | Mask provider protocol shape | Decided | ADR-057 (closes); superseded by ADR-076 (path retired) |
| RFC-010 | MCP tool surface — parameter shapes and error contracts | Decided | ADR-056 (closes) |
| RFC-011 | Agent context loading order and format | Decided | ADR-059 (closes) |
| RFC-012 | Programmatic vocabulary generation (Path C) | Decided | ADR-073 (closes) |
| RFC-013 | Vocabulary gap surfacing format | Decided | ADR-060 (closes) |
| RFC-014 | End-of-session synthesis flow | Decided | ADR-061 (closes) |
| RFC-015 | EXIF auto-binding rules | Decided | ADR-053 (closes) |
| RFC-016 | Versioned prompt system | Decided | ADR-043, ADR-044, ADR-045 |
| RFC-018 | Vocabulary expansion for expressive taste articulation | Decided | ADR-063, ADR-064, ADR-073 |
| RFC-019 | Reference-image validation baseline | Decided | ADR-066, ADR-067, ADR-068 |
| RFC-020 | Command-line interface for Chemigram | Decided | ADR-069, ADR-070, ADR-071, ADR-072 (closes) |
| RFC-021 | Parameterized vocabulary magnitudes (Path C default for continuous-magnitude modules) | Draft v0.1 | ADR (pending) ×5 — apply path / manifest schema / CLI/MCP arg / test-coverage policy / migration |

### ADRs

| ADR | Title | Status |
|-|-|-|
| ADR-001 | Vocabulary approach (Architecture B) | Accepted |
| ADR-002 | SET semantics: replace by (operation, multi_priority) | Accepted |
| ADR-003 | Three foundational disciplines (writer, dt-photography, BYOA) | Accepted |
| ADR-004 | `darktable-cli` invocation form | Accepted |
| ADR-005 | Subprocess serialization per configdir | Accepted |
| ADR-006 | Single Python process, MCP server, no daemon | Accepted |
| ADR-007 | BYOA — no bundled AI capabilities | Accepted |
| ADR-008 | XMP and `.dtstyle` as opaque-blob carriers | Accepted |
| ADR-009 | Path A vs Path B for synthesis | Accepted |
| ADR-010 | Vocabulary parser identifies user entries by empty `<multi_name>` | Accepted |
| ADR-011 | Reject `darktable-cli --style NAME` for vocabulary application | Accepted |
| ADR-012 | `--apply-custom-presets false` always | Accepted |
| ADR-013 | Python 3.11+ | Accepted |
| ADR-014 | All image-processing via darktable | Accepted |
| ADR-015 | Three-layer model (L0/L1/L2/L3) | Accepted |
| ADR-016 | L1 empty by default; opt-in per camera+lens | Accepted |
| ADR-017 | L2 has two flavors (neutralizing, look-committed) | Accepted |
| ADR-018 | Per-image content-addressed DAG | Accepted |
| ADR-019 | Git-like ref structure (objects/, refs/heads, refs/tags, HEAD) | Accepted |
| ADR-020 | No remote, no three-way merge, no reflog | Accepted |
| ADR-021 | Three-layer mask pattern (pre-baked, AI-raster, agent-described) | Superseded by ADR-076 |
| ADR-022 | Mask registry per image with symbolic refs | Superseded by ADR-076 |
| ADR-023 | Vocabulary primitives are `.dtstyle` + manifest entries | Accepted |
| ADR-024 | Authoring discipline: uncheck non-target modules in dialog | Accepted |
| ADR-025 | WB and color calibration coupling — author with both or decouple | Accepted |
| ADR-026 | Vocabulary modversion-pinned to darktable version | Accepted |
| ADR-027 | Local-only session data — no telemetry, no cloud | Accepted |
| ADR-028 | Configuration formats: TOML for config, JSON for manifests | Accepted |
| ADR-029 | Session transcripts as JSONL with header metadata | Accepted |
| ADR-030 | Three-tier context model (taste/brief/notes) | Accepted |
| ADR-031 | Propose-and-confirm for context updates | Accepted |
| ADR-032 | Distribution split (OSS engine, OSS starter, OSS packs, private personal) | Accepted |
| ADR-033 | MCP tool surface (initial) | Accepted |
| ADR-034 | Build system and package layout | Accepted |
| ADR-035 | Dev environment with uv | Accepted |
| ADR-036 | Testing strategy: pytest with three tiers | Accepted |
| ADR-037 | Linting and formatting with ruff | Accepted |
| ADR-038 | Type checking with mypy strict for core | Accepted |
| ADR-039 | Pre-commit hooks for local quality gates | Accepted |
| ADR-040 | CI on GitHub Actions, macOS-only for v1 | Accepted |
| ADR-041 | SemVer with 0.x for Phase 1 development | Accepted |
| ADR-042 | Distribution via PyPI, GitHub releases as supplement | Accepted |
| ADR-043 | Jinja2 + filename-versioned templates as prompt format | Accepted |
| ADR-044 | PromptStore API and MANIFEST.toml as active-version registry | Accepted |
| ADR-045 | Prompt versioning is independent of package SemVer | Accepted |
| ADR-046 | Golden dataset versioning (immutable, append-only) | Accepted |
| ADR-047 | Run manifests for eval reproducibility | Accepted |
| ADR-048 | Multi-scope taste structure (extends ADR-030) | Accepted |
| ADR-049 | Vocabulary-starter ships within chemigram (clarifies ADR-032) | Accepted |
| ADR-050 | Parser API and synthesizer error contract (closes RFC-001) | Accepted |
| ADR-051 | Same-module SET-replace; last-writer-wins; Path B deferred (closes RFC-006) | Accepted |
| ADR-052 | PipelineStage Protocol with single v1 stage / DarktableCliStage (closes RFC-005) | Accepted |
| ADR-053 | EXIF auto-binding by exact-match identity (closes RFC-015) | Accepted |
| ADR-054 | Canonical XMP serialization for stable content hashing (closes RFC-002) | Accepted |
| ADR-055 | Raster masks share objects/ store; masks/registry.json maps names (closes RFC-003) | Superseded by ADR-076 |
| ADR-056 | MCP tool surface: parameter shapes + error contract (closes RFC-010) | Accepted |
| ADR-057 | MaskingProvider Protocol shape (closes RFC-009) | Superseded by ADR-076 |
| ADR-058 | Default masking provider: CoarseAgentProvider (closes RFC-004) | Superseded by ADR-076 |
| ADR-059 | Agent context loading order and format (closes RFC-011) | Accepted |
| ADR-060 | Vocabulary gap JSONL schema (closes RFC-013) | Accepted |
| ADR-061 | End-of-session synthesis is agent-orchestrated (closes RFC-014) | Accepted |
| ADR-062 | Reset rewinds the current branch to baseline | Accepted |
| ADR-063 | Path B unblocking; iop_order resolved as None (closes RFC-001, RFC-018) | Accepted |
| ADR-064 | Vocabulary authoring workflow (post-v0.2) (closes RFC-018) | Accepted |
| ADR-066 | Reference fixture policy (synthetic-only) (closes RFC-019) | Accepted |
| ADR-067 | Pixel-level assertion protocol (closes RFC-019) | Accepted |
| ADR-068 | darktable version gate (deferred) (closes RFC-019) | Accepted (deferred) |
| ADR-069 | CLI alongside MCP, won't replace it (closes RFC-020) | Accepted |
| ADR-070 | CLI framework: Typer (closes RFC-020) | Accepted |
| ADR-071 | CLI–MCP–core thin-wrapper discipline (closes RFC-020) | Accepted |
| ADR-072 | CLI output format: human default, NDJSON via `--json` (closes RFC-020) | Accepted |
| ADR-073 | Programmatic vocabulary authoring via reverse-engineered structs (closes RFC-012) | Accepted |
| ADR-074 | Built-in geometric mask providers (gradient/radial/rectangle) | Superseded by ADR-076 |
| ADR-075 | CI matrix expands to Ubuntu alongside macOS (amends ADR-040) | Accepted |
| ADR-076 | Drawn-mask-only mask architecture (supersedes 021/022/055/057/058/074) | Accepted |

---

## Changelog

- **v0.1** · 2026-04-27 · Initial population from 04 + Phase 0 findings + concept package work. RFCs and ADRs draft-numbered to match TA/map.

---

*TA · v0.1 · This is a reference document. Read by linking-into specific sections.*
