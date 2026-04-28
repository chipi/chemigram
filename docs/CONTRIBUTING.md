# Contributing to Chemigram

*Two contribution flows: code and vocabulary. Different review processes, different timelines, different criteria.*

This project is a research-flavored OSS project. We're happy to accept contributions, but we ask contributors to read this doc first because the review process for **vocabulary** is meaningfully different from the review process for **code**, and that difference is intentional.

## Before you start

**Read the project's framing.** `docs/concept/00-introduction.md` and `docs/concept/04-architecture.md` explain what this project is and (importantly) what it isn't. Contributions that pull the project toward DAM features, bulk processing, or "make it more like Lightroom" will be politely declined — see "What this is not" in `docs/concept/01-vision.md` and the deferred-items in `docs/TODO.md`.

**Open an issue before a large PR.** For non-trivial changes (new modules, new MCP tools, architectural changes, new vocabulary subsystems), please open an issue first to discuss the approach. Avoids the situation where you've built something we have to ask you to redesign.

**Be patient with vocabulary review.** It takes longer than code review, by design. See below.

---

## Code contributions

### Scope

Code contributions are welcome for:

- Bug fixes in the engine, MCP server, or supporting tooling
- Performance improvements
- Tests (especially edge cases the existing tests miss)
- Documentation corrections and clarifications
- New `PipelineStage` implementations (per the contract in `docs/concept/04-architecture.md`)
- Improvements to error messages and diagnostics
- Build/CI/packaging improvements

Code contributions that need prior discussion in an issue:

- New MCP tools (the surface is deliberately small)
- New engine subsystems
- Changes to the layer model (L0–L3)
- Changes to versioning / snapshot format (compatibility-sensitive)
- Anything touching the SET-semantics or replace-not-accumulate behavior

### Dev setup

The fast path:

```bash
git clone https://github.com/chipi/chemigram.git
cd chemigram
./scripts/setup.sh
```

`setup.sh` checks prerequisites (Python 3.11+, uv if installed, darktable for E2E tests), creates a venv, installs all dependencies, and optionally installs pre-commit hooks. It's idempotent — safe to re-run after pulling new code or switching branches.

If you don't have `uv` installed, the script falls back to plain `python -m venv` + `pip install -e ".[dev]"`. Install uv for faster dependency resolution: `brew install uv`, `pipx install uv`, or `pip install uv`.

Day-to-day commands via the Makefile:

```bash
make test            # fast unit tests
make test-integration  # integration tests (no darktable needed)
make test-e2e        # E2E tests (requires darktable)
make lint            # ruff check
make format          # ruff format
make typecheck       # mypy on src/chemigram
make check           # lint + typecheck + unit (run before committing)
make help            # list all targets
```

Or invoke the underlying tools directly:

```bash
uv run pytest tests/unit
uv run ruff check
uv run mypy src/chemigram
```

Optional but recommended — install pre-commit hooks (ADR-039), if you didn't during setup:

```bash
make hooks
```

### Process

Standard GitHub flow:

1. Fork, create a branch with a descriptive name.
2. Make your changes. Keep PRs focused on one concern.
3. Add or update tests. New code paths need test coverage in the appropriate tier (unit / integration / e2e — see ADR-036).
4. Run the test suite locally. CI must pass.
5. Open a PR with a clear description of *what* changed and *why*.
6. Address review comments. Be patient — most reviewers are doing this in their evenings.
7. Merge happens after at least one approving review.

### Test fixtures (raw files, .dtstyle samples)

Tests in different tiers need different fixtures:

**Unit tier** — pure logic, no fixtures needed. If a test wants a small `.dtstyle` blob to parse, it's defined inline in the test file.

**Integration tier** — needs real `.dtstyle` files but does *not* need raws. A small set of canonical `.dtstyle` files lives at `tests/fixtures/dtstyles/` and is committed to the repo (these are tiny — a few KB each).

**E2E tier** — needs real raw files, which are too large to commit. Two-part strategy:

1. **A tiny synthetic raw** (`tests/fixtures/raws/synthetic.NEF` or similar, if technically feasible) committed to the repo for smoke-test E2E coverage. Goal: confirm the pipeline runs end-to-end without depending on photographer-supplied data.
2. **Photographer-supplied raws** for substantive E2E tests. The contributor places real raws at `tests/fixtures/raws/local/` (gitignored). E2E tests parametrized on whatever's present skip cleanly when the directory is empty.

The pre-release script (`scripts/pre-release-check.sh`) requires the `local/` directory to be populated with at least three real raws — this is the gate that prevents shipping without real-world validation.

**Rationale.** Committing a full raw library to git is infeasible (file sizes, redistribution rights). Git-LFS adds infrastructure cost without clear benefit at v1 size. Auto-download from a public bucket adds an external dependency. Photographer-supplied raws keep the repo light and validate against real data the photographer cares about.

---

### Standards

- **Python 3.11+** (ADR-013). Type hints expected on public functions.
- **Formatter and linter:** `ruff format` and `ruff check` (ADR-037). CI enforces both.
- **Tests:** `pytest` (ADR-036), three tiers. New code paths get tests in the appropriate tier. Coverage targets are pragmatic — high on the synthesizer (pure logic), reasonable elsewhere. No "must hit X%" gate.
- **Type checking:** `mypy` strict on `chemigram.core` (ADR-038); looser elsewhere.
- **Pre-commit hooks** are recommended (ADR-039). They run ruff + mypy on every commit and unit tests on push. CI catches the same things if you skip them.
- **Commit messages:** clear and present-tense. We don't enforce conventional commits but appreciate readable history.
- **No CLA required** at this stage. By submitting a PR you agree your contribution is licensed under MIT (see `LICENSING.md`).

### What CI checks

GitHub Actions runs on every PR (ADR-040):

- Tests pass on macOS Apple Silicon (Python 3.11, 3.12, 3.13)
- Lint and format checks clean (`ruff check --no-fix` and `ruff format --check`)
- Type checks pass (`mypy src/chemigram`)
- Unit and integration tests pass

What CI **doesn't** check (run these locally before releases):

- E2E tests (require darktable installed; not in CI runners)
- Linux compatibility (deferred to Phase 2)
- Cross-Python forward compat beyond the matrix

The pre-release script `scripts/pre-release-check.sh` runs the full suite including E2E.

---

## Vocabulary contributions

This is the contribution path that's different from typical OSS projects.

### Why vocabulary review is different

A `.dtstyle` file is **opaque** to mechanical inspection. Its `op_params` and `blendop_params` are hex-encoded C structs that we deliberately don't decode. So:

- We can't write a unit test that says "this entry produces +0.5 EV exposure."
- We can't lint the contents to confirm the entry "feels subtle enough."
- We can't grep for problematic values.

The only way to assess a vocabulary contribution is to **render an image with it and look at the result**. The reviewer's eye is the test. This is irreducibly slower than code review.

We're honest about this, and we ask contributors to make the manual review as efficient as possible by submitting *complete, self-contained* PRs (see template below).

### What we accept

**For the starter vocabulary** (`vocabulary/starter/`):

- Generic, broadly-applicable primitives (exposure increments, basic WB moves, common tone moves)
- Single-module entries where possible (composition is more legible)
- Conventional naming following existing patterns
- Clear `description` and accurate `touches` declaration in the manifest

**For community packs** (`vocabulary/packs/`):

- Genre-specific or look-specific collections (Fuji sims, Nikon picture-control emulations, etc.)
- Borrowed content with proper `ATTRIBUTION.md` credit and preserved upstream license
- Coherent themes — a "1970s film" pack should feel internally consistent

**What we do not accept into the OSS repo:**

- Highly idiosyncratic personal-taste vocabularies (those belong in private repos)
- Vocabularies that depend on specific paid plugins or non-OSS components
- Re-uploads of existing community work without proper attribution

### Authoring procedure (read this before your first vocabulary PR)

Phase 0 testing surfaced several authoring caveats specific to darktable's GUI behavior. Following this procedure produces clean single-module dtstyles that pass CI mechanical checks and match the architectural assumptions in `docs/concept/04-architecture.md`.

**1. Use an isolated configdir for vocabulary work.**

Don't author vocabulary against your everyday darktable library — auto-applied presets and prior history can contaminate captures. Set up a clean configdir:

```bash
mkdir -p ~/chemigram-vocab/dt-config ~/chemigram-vocab/raws ~/chemigram-vocab/styles
/Applications/darktable.app/Contents/MacOS/darktable \
  --configdir ~/chemigram-vocab/dt-config
```

Import a representative raw, develop, save styles, export. The configdir is disposable.

**2. Discard history before each style.**

In darkroom view, right-click in the history stack panel → "discard history" (or "compress history stack"). This removes any prior moves so you start clean. Skipping this captures whatever was on the previous edit.

**3. Make exactly the move the primitive should encode.**

For `expo_+0.5`: enable the exposure module, set value to `0.5` (type into the value field, press tab). For nothing else. Don't enable other modules.

For WB primitives, note the coupling: in darktable's modern scene-referred pipeline, **adjusting WB while color calibration is enabled auto-updates color calibration**. Two approaches:

- **Decoupled** (cleaner single-module captures): disable color calibration first, then adjust WB. The resulting style touches only `temperature`. Simpler to compose.
- **Coupled** (truer to darktable's modern pipeline): leave color calibration enabled, adjust WB. The resulting style touches both `temperature` and `channelmixerrgb`. The manifest's `touches: [temperature, channelmixerrgb]` declaration honors this, and the synthesizer handles multi-module entries fine.

Either is acceptable for vocabulary; declare the coupling in the manifest so the synthesizer knows what's being modified.

**4. In the create-style dialog, uncheck non-target modules.**

This is the critical step. The dialog presents a checklist of every module in the active pipeline. The default is "all checked" — accepting the default produces a 12-14 module dtstyle that includes all of darktable's `_builtin_*` defaults plus the L0 always-on stack.

**Explicitly uncheck every module except the target operation(s)** before clicking create. The export will then contain just the user-authored entries.

For verification: after exporting, `cat the.dtstyle` and count `<plugin>` elements. A clean single-module primitive has exactly one. A multi-module primitive (like a WB entry that captures the WB/color-calibration coupling) has just the declared `touches` count. If you see 12-14 entries, you didn't uncheck — re-do.

**5. Note the darktable version.**

Vocabulary is calibrated to specific module versions (`modversion` per module). If darktable bumps a module's modversion, the captured dtstyle becomes invalid for that module. Always note the darktable version you authored against in the PR template (and in the manifest's `darktable_version` field).

**6. Note about literal-zero values.**

Some sliders have minimum granularity that prevents authoring exact zero values. Exposure for instance: the GUI's smallest representable value is ~0.009 EV, not 0.0. For true no-op vocabulary entries, programmatic generation will eventually be needed (see `docs/TODO.md` Path C). For now, accept ~0.009 EV as the practical neutral and document it in the entry's description.

### Vocabulary PR template

When you open a vocabulary PR, the PR description must include:

```
## Vocabulary entry/entries

- Name(s):
- Layer(s) (L1, L2, L3):
- Pack target (starter / packs/<pack_name>):

## What this does

A short description of the visual effect. What kind of image is it for?
What does it do to that image? Why is this useful in the vocabulary?

## Modules touched

List the darktable modules each entry touches, matching the manifest entry's
`touches` field.

## Renders

Attach (as PR images or links to a public image host):

1. A "before" render: the reference image with no styles applied.
2. An "after" render: the reference image with this entry applied.
3. (For multi-entry PRs) An "after" render for each entry, individually.

The reference image should be:
- A representative example for the vocabulary's genre
- Available raw (we may want to re-render to verify)
- Yours or freely-licensed (don't use copyrighted photos)

## Attribution (if applicable)

If this is borrowed from an existing community project, include the
upstream source URL, commit hash, and license. Update `ATTRIBUTION.md`
in the relevant pack directory.

## darktable version tested

Which darktable version did you author this against? (modversions are tied
to darktable releases)
```

### Automated checks (CI)

CI runs the following on every vocabulary PR:

- **Manifest schema validation** — required fields present, layer/subtype valid, modules_touched non-empty
- **`.dtstyle` schema validation** — parses as XML, contains expected `<plugin>` count, has all required fields
- **Touches consistency** — the manifest's `touches` declaration matches the actual `<operation>` tags in the dtstyle
- **Modversion consistency** — the manifest's `modversions` match `<module>` values in the dtstyle
- **Render test** — apply each entry to a sample raw, confirm darktable-cli exits 0 (catches gross XML errors)
- **Attribution check** — if the entry lists a `source`, that source is in `ATTRIBUTION.md`

These catch mechanical problems but say nothing about whether the entry is *good*. That's the human reviewer's job.

### Manual review (the reviewer's eye)

A maintainer will:

1. Pull the PR, render the contributor's reference image with the entry applied.
2. Render the same image *without* the entry.
3. Look at both. Does the rendered effect match the description? Is the named entry doing what its name claims?
4. For starter pack: is this entry generic enough, or is it idiosyncratic to the contributor's taste? (Idiosyncratic is fine for community packs, not for starter.)
5. Check naming: does it follow the patterns in the existing vocabulary?
6. Check for duplication: does this duplicate an existing entry?

Manual review is fast in absolute terms (a few minutes per entry) but slow in calendar terms because reviewers look at vocabulary PRs in batches when they have darktable running.

**Expect 1-2 weeks turnaround on vocabulary PRs.** This is by design — we'd rather review carefully than fast.

### Why the starter pack is conservative

The starter vocabulary is a teaching artifact. Its purpose is to give new users enough to get the system working, demonstrate the conventions, and motivate them to author their own vocabulary.

If the starter pack grew unboundedly, it would start encoding particular tastes, which contradicts its purpose. So we're conservative about expanding it — new entries should fill clear gaps, not add stylistic choices.

For stylistic choices, contribute a community pack instead. The bar is lower: a coherent, well-described pack with attribution can land in `vocabulary/packs/` even if the individual entries reflect a particular aesthetic.

---

## Documentation contributions

Documentation contributions follow the code flow (regular PR, CI runs spell-check and link validation, reviewer assesses clarity). The bar:

- Accurate (don't drift from how the system actually works)
- Honest (caveats and known limitations stay in)
- Clear (prefer prose over excessive lists)
- Aligned with project framing (don't reframe the project's research-orientation as a product)

If you find a doc that's wrong or unclear, please fix it. Documentation drift is one of the easier ways for an OSS project to decay.

---

## What we won't accept

A short list, to save everyone time:

- **DAM features.** No catalog, no smart collections, no bulk tagging UI. See `TODO.md` "DAM, taxonomy, classification — out of scope."
- **Bulk batch processing.** Chemigram is per-image research. Bulk workflows belong in the (hypothetical) sibling project.
- **Generic `set_module_param`-style tools.** The vocabulary discipline is core to the project; bypassing it is bypassing the research question.
- **Non-darktable backends in v1.** The pipeline-stages abstraction admits other backends *eventually*; we won't accept the second backend until the first is rock-solid.
- **Telemetry, analytics, or anything that uploads data.** Session data is local-only. Period.
- **Closed dependencies.** OSS components must work entirely with OSS dependencies.

If your contribution falls into one of these categories, please open an issue first to discuss alternatives or whether the deferred-projects framing in `TODO.md` is the right home.

---

## Code of conduct

Be kind. Assume good faith. Keep technical discussions technical and craft discussions humble. Photography is taste, taste is personal, and we're all here to learn — not to enforce one aesthetic over another.

If a discussion gets heated, take a walk and come back. The project will still be here.

---

## Questions

For technical questions about contributing, open a GitHub issue with the `question` label.

For licensing-specific questions, see `LICENSING.md`.

For anything else, open an issue or start a discussion.

Thank you for considering a contribution. The project is better for it.
