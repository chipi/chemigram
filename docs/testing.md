# Testing strategy

> *Software shall work 100% as speced. Humans validate from a different perspective — taste, judgment, vocabulary fit, image-by-image craft. They are not test subjects for correctness.*

This document is the operational handbook for testing Chemigram. It states the philosophy, the tiers, the coverage standards, and the capability matrix that drives ongoing test work.

If you're contributing code, the **Coverage standards** section is the bar. If you're contributing tests, the **Capability matrix** is what we're tracking. If you're trying to understand *why* the test suite is shaped the way it is, start at the top.

---

## Why this exists

Three kinds of confidence get confused with each other. Naming them matters:

1. **Correctness** — "the code does what the spec says, on every reachable path, against real inputs." This is what automated tests prove.
2. **Quality of judgment** — "the vocabulary entries and prompts produce edits that feel right on real photos." This is what a photographer using the tool reveals.
3. **Robustness under load** — "the system handles weird raw files, big sessions, slow disks." This is what soak testing reveals.

(1) is the engine's responsibility. We do not delegate (1) to humans. A human stumbling onto a stack trace is a *failure of testing*, not a feature. Photographers belong on (2) and (3) — perspective, taste, durability under real use — and they should reach those without having to debug us first.

That's the bar: every shipped capability has automated proof it works as the spec says, before the photographer ever sees it.

---

## First principles

These five rules govern every test we write.

### 1. Test through the agent boundary

The agent talks to Chemigram exclusively through MCP tools (per ADR-006, ADR-033, ADR-056). That is the contract. If a tool returns the wrong shape, silently caches stale bytes, or omits an error code, the agent gets misled — even if the engine internals are correct.

So: **every shipped MCP tool has at least one test that drives it through the in-memory MCP harness.** Calling the underlying engine function directly is not enough. The harness round-trips the JSON envelope, the schema validation, and the error contract — that's the contract the agent depends on.

### 2. Test against real bytes

The "is darktable producing the right pixels for this XMP?" question can only be answered by darktable. Stubbed renders catch type errors and coordinate logic, but not the thing that actually matters: did the photographer's intent reach the photons?

So: **every primitive that ships, every render code path, every export path has at least one e2e test that invokes real `darktable-cli` against a real raw and asserts on the pixel statistics of the output.** The Phase 0 test raw + configdir (ADR-005) is the standard fixture.

### 3. Direction-of-change, not magnitudes

darktable is deterministic for a given (raw, configdir, XMP) tuple, but the rendered pixel statistics depend on scene content. The same exposure shift will move luma by a different amount on a midday landscape than on a dim interior.

So: **assertions are direction-of-change with generous noise floors, not exact magnitudes.** Exposure-up should brighten by *more than* a noise threshold. White-balance-warm should increase the warmth ratio. We never assert "luma equals 142.3" — that's a brittle test that fails for the wrong reasons.

### 4. Skip cleanly when prereqs absent

E2e tests need darktable, the Phase 0 raw, and a darktable configdir. CI doesn't have those (per ADR-040 — e2e isn't in CI). Local contributors might not have them either.

So: **e2e tests skip with a clear reason when prereqs are missing.** They never fail. `make test-e2e` either runs the suite or prints what's missing — both are acceptable; failing because the environment is shaped differently is not.

### 5. Cover the full surface

Coverage is not a percentage. It's a list. The list has rows for every MCP tool, every vocabulary primitive, every error code, every versioning operation, every export path, every context loader, every session lifecycle event. A capability without a row is a capability we don't know works.

So: **the [Capability matrix](#capability-matrix) is the source of truth for what's covered.** Every PR that adds capability adds a row. Every PR that adds a test ticks a column.

---

## The three tiers

Tests live in three directories, codified in ADR-036, refined here with concrete "what belongs where" rules.

### `tests/unit/` — the engine in isolation

**Scope:** one module, one function, one behavior at a time. Pure-Python logic, dataclasses, parsers, hash semantics, error taxonomies, JSON-shape validators. No subprocesses, no network, no filesystem beyond `tmp_path`. Run in milliseconds.

**Lives here:**
- XMP parser / serializer behavior on canned inputs and adversarial fixtures.
- `synthesize_xmp` SET semantics on synthetic vocabulary entries.
- Versioning ops on a fake repo (`ImageRepo.init(tmp_path)` is fine).
- Mask-registry filesystem layout.
- `ToolResult` / `ToolError` shape contracts.
- Each MCP tool's input-schema validation paths.

**Doesn't belong:**
- darktable invocation (e2e tier).
- Round-tripping through the MCP transport layer (integration tier).

### `tests/integration/` — the wiring works

**Scope:** real Python objects collaborating across module boundaries, but without external processes. The MCP in-memory harness, real `Workspace` objects on real `tmp_path` directories, real `VocabularyIndex` loaded from the test pack, real prompts from `PromptStore`. Subprocess calls (darktable, git) are stubbed; everything else is real.

**Lives here:**
- Each MCP tool's full round-trip through `in_memory_session`: build server, call tool, assert on the decoded `ToolResult`.
- Workspace lifecycle: ingest → snapshot → tag → checkout → rebind layers.
- Mask materialization for darktable (filesystem layout, registry shape).
- Context loaders against fixture workspaces with hand-crafted tastes/brief/notes.
- Session transcript JSONL contents after a multi-tool sequence.
- Error-path coverage: every recoverable `ErrorCode` should be reachable through at least one integration test.

**Doesn't belong:**
- Real darktable rendering (e2e tier).
- Pure-Python algorithm tests on a single function (unit tier).

### `tests/e2e/` — the photons

**Scope:** the full chain, end to end. Real `darktable-cli`, real Phase 0 raw, real configdir, real bytes back. Real synthesizer driving real XMP, real render, real pixel statistics. Asserts on direction-of-change in luminance, warmth, contrast, etc.

**Lives here:**
- Every shipped vocabulary primitive: real render, assert on the appropriate channel statistic.
- Every render code path: preview, export, with/without masks, different sizes.
- Full MCP session shapes: ingest → bind → apply → render → export → snapshot.
- Reset / branch / checkout semantics: each followed by a render to confirm the workspace state is intact.
- Mask-bound primitives: real mask materialization → real render → assert the masked region differs from the unmasked region.

**Doesn't belong:**
- Anything that doesn't ultimately validate pixels or filesystem state from a real darktable invocation.

---

## Coverage standards

These are the rules a PR must satisfy before it lands.

### When you add an MCP tool

- One unit test per input-validation path (schema rejects malformed input).
- One integration test per error code the tool can return (`recoverable=True` errors all need at least one test).
- One integration test for the happy path through `in_memory_session`.
- If the tool produces side-effects on the filesystem (snapshot, mask, transcript): one integration test that asserts the post-state.
- If the tool drives a render: one e2e test that asserts on the rendered pixels.

### When you add a vocabulary primitive

- A `.dtstyle` file in the test pack (or the starter pack, if it ships).
- A unit test asserting the primitive parses and serializes round-trip-clean.
- An integration test applying the primitive through `apply_primitive` and asserting the snapshot's history shape.
- An e2e test rendering the primitive and asserting on the appropriate pixel statistic (luma for exposure, warmth ratio for WB, contrast variance for tone curves, etc.).

### When you add an error code

- A unit test that the `ErrorCode` enum entry exists and has the documented `code` string.
- An integration test that drives at least one tool to return it through the MCP boundary.
- If the error is recoverable, the test asserts the agent gets the structured shape (not a stack trace).

### When you add a versioning operation

- Unit tests for: happy path, idempotency (where applicable), failure modes, log-entry contents.
- An integration test through the MCP tool that wraps it (if any).
- An e2e test that proves the operation followed by `apply_primitive + render_preview` works (no detached-HEAD-style traps — see ADR-062).

### When you add a render code path

- Unit tests for the path's argv construction.
- An integration test for the error path (binary missing, configdir bad).
- An e2e test for the happy path against the Phase 0 raw, asserting on bytes.

---

## Capability matrix

The matrix is the central tracker. Each row is a capability. Each column tracks coverage at a specific tier (unit / integration / e2e) plus a happy-path / error-paths split. Status: `✓` covered, `~` partial, ` ` missing.

The canonical version lives in the GH tracking issue (link in the repo's milestone). What follows here is a snapshot of the categories the matrix organizes — the tracking issue is the source of truth for current status.

### Vocabulary primitives

Every shipped primitive needs end-to-end pixel validation. The 5 starter entries:

| Primitive | Layer | Render assertion |
|-|-|-|
| `expo_+0.5` | L3 | luma > baseline (with caveat — see e2e module docstring on baseline EV) |
| `expo_-0.5` | L3 | luma < `expo_+0.5` (relative ordering) |
| `wb_warm_subtle` | L3 | warmth ratio (R+G)/(2B) increases |
| `look_neutral` | L2 | composite renders without errors; specific channel asserts TBD |
| `tone_lifted_shadows_subject` | L3 raster-mask-bound | masked region's shadow tones lifted vs unmasked baseline |

### MCP tool surface

All 27 shipped tools need:
- Unit input-validation coverage
- Integration round-trip coverage through `in_memory_session`
- E2e coverage for any tool that drives a render or mutates filesystem state

Categories:
- **Vocabulary edit:** `apply_primitive`, `remove_module`, `reset` (post-ADR-062), `get_state`, `list_vocabulary`
- **Versioning:** `branch`, `tag`, `checkout`, `log`, `diff`
- **Layer binding:** `bind_layers`, `unbind_layers`
- **Rendering:** `render_preview`, `compare`
- **Export:** `export`
- **Masks:** `generate_mask`, `regenerate_mask`, `list_masks`, `tag_mask`, `apply_primitive(mask_override=...)`
- **Context:** `read_context`, `propose_taste_update`, `confirm_taste_update`, `propose_notes_update`, `confirm_notes_update`, `log_vocabulary_gap`
- **Lifecycle:** `ingest_workspace`

### Error path coverage

Every `ErrorCode` enum value (`invalid_input`, `not_found`, `state_error`, `versioning_error`, `darktable_error`, `masking_error`, `prompt_error`, `not_implemented`, `internal`) needs at least one integration test exercising the path.

### Versioning operations

Beyond per-tool coverage, the *combinations* matter:
- snapshot → tag → reset → snapshot (the ADR-062 case)
- branch → checkout → snapshot → checkout main → diff
- tag (immutable) → re-tag (must fail)
- snapshot → invalidate-mask → snapshot (mask reachability)

### Render paths

- Preview at multiple sizes (256, 1024, 4096)
- Export at full resolution (`--hq true`)
- Render with `apply_primitive(mask_override)` — masked region differs from unmasked
- Render after corrupt XMP — surfaced as `darktable_error`, not stack trace

### Context + session

- Loading order: tastes → brief → notes → recent_log → recent_gaps (per ADR-059)
- Multi-scope tastes: `_default.md` always; genre files declared in brief.md
- Notes summarization (10 head + 30 tail) for long files
- Vocabulary gap log RFC-013 schema (round-trip read after write)
- Session transcript JSONL contains every tool call + result in order

### Lifecycle

- `ingest_workspace` from a raw + photographer's XMP produces the right baseline tag, layer binding, EXIF cache.
- Workspace persistence across `clear_registry()` — the on-disk state is the truth.

---

## Fixtures and reproducibility

E2e tests use a standardized Phase 0 setup, discoverable via env vars or default paths.

| What | Default path | Override env var |
|-|-|-|
| Test raw (NEF) | `~/chemigram-phase0/raws/raw-test.NEF` | `CHEMIGRAM_TEST_RAW` |
| darktable configdir | `~/chemigram-phase0/dt-config` | `CHEMIGRAM_DT_CONFIGDIR` |
| `darktable-cli` binary | `darktable-cli` on PATH | `DARKTABLE_CLI` |

The configdir is **pre-bootstrapped** — a fresh empty directory makes `darktable-cli` fail with "can't init develop system." Real renders need a configdir that's been initialized at least once by the darktable GUI.

Bootstrapping: open darktable.app once, point it at any image, quit. The `~/.config/darktable` it creates can be copied to the Phase 0 location.

---

## Tolerances

How tight are pixel assertions?

- **Luma direction-of-change:** delta > 5 units (out of 255). Generous floor; well above JPEG quantization noise but well below typical primitive deltas.
- **Warmth ratio direction:** strictly positive delta for warming primitives. Magnitude is scene-dependent.
- **Determinism:** same inputs → luma within 0.5 units. JPEG q-noise is sub-unit on small renders.
- **Plausibility:** baseline render falls in [20, 230] luma — not pure black, not blown out.

These tolerances are deliberately loose. The point of e2e tests is to catch *categorical* regressions (synthesizer dropping ops, render returning cached previews, MCP tools silently failing), not to micromeasure darktable's behavior.

If a tolerance ever fails, **investigate the cause before tightening or loosening.** Loosening to make tests pass papers over real regressions; that's worse than a failing test.

---

## When tests find a bug

This will happen. Software has bugs; tests find them. Three rules:

1. **No easy overrides, no cheating.** Don't `xfail` a real failure to make CI green. Don't loosen a tolerance below "well above noise" to dodge a regression.
2. **Root-cause first, fix second.** Understand *why* the test is failing before changing the code. The test might be wrong; the code might be wrong; the spec might be wrong. Each leads to a different fix.
3. **Doc the finding.** If the bug surfaces a real engine issue, write or update an ADR. If it surfaces a test-design issue, update this document. The first ADR-062 bug — reset detaching HEAD — was a 5-month-old behavior never caught because no test exercised reset+apply.

If you're stuck on a failing test and can't tell whether it's the test or the code, ask. Don't guess.

---

## Running tests

```bash
make test              # all tests (unit + integration; e2e excluded)
make test-unit         # unit tier only — milliseconds
make test-integration  # integration tier — seconds
make test-e2e          # e2e tier — needs Phase 0 setup, tens of seconds
make ci                # the full set CI runs (unit + integration + lint + types)
```

E2e is **not in CI** (per ADR-040). It's gated to local `make test-e2e` and the pre-release check script. The expectation is that maintainers run e2e before tagging a release; CI handles the cheap tiers on every commit across the Python 3.11/3.12/3.13 matrix.

---

## What this document is not

- It is not the test suite — that's in `tests/`.
- It is not the bug tracker — that's GH issues.
- It is not the milestone plan — that's `IMPLEMENTATION.md` and the GH milestones.

This document is the *philosophy* and the *standards*. When in doubt about whether to add a test, what tier it belongs in, or what tolerance to use, this is where to look.
