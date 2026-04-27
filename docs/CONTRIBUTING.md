# Contributing to Chemigram

*Two contribution flows: code and vocabulary. Different review processes, different timelines, different criteria.*

This project is a research-flavored OSS project. We're happy to accept contributions, but we ask contributors to read this doc first because the review process for **vocabulary** is meaningfully different from the review process for **code**, and that difference is intentional.

## Before you start

**Read the project's framing.** `chemigram.md` and `architecture.md` explain what this project is and (importantly) what it isn't. Contributions that pull the project toward DAM features, bulk processing, or "make it more like Lightroom" will be politely declined — see "What this is not" in `chemigram.md` and the deferred-items in `TODO.md`.

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
- New `PipelineStage` implementations (per the contract in `architecture.md`)
- Improvements to error messages and diagnostics
- Build/CI/packaging improvements

Code contributions that need prior discussion in an issue:

- New MCP tools (the surface is deliberately small)
- New engine subsystems
- Changes to the layer model (L0–L3)
- Changes to versioning / snapshot format (compatibility-sensitive)
- Anything touching the SET-semantics or replace-not-accumulate behavior

### Process

Standard GitHub flow:

1. Fork, create a branch with a descriptive name.
2. Make your changes. Keep PRs focused on one concern.
3. Add or update tests. New code paths need test coverage.
4. Run the test suite locally. CI must pass.
5. Open a PR with a clear description of *what* changed and *why*.
6. Address review comments. Be patient — most reviewers are doing this in their evenings.
7. Merge happens after at least one approving review.

### Standards

- Python 3.11+. Type hints expected on public functions.
- Formatter: `ruff format`. Linter: `ruff check`. CI enforces both.
- Tests: `pytest`. Aim for ~80% coverage on new code; integration tests welcome.
- Commit messages: clear and present-tense. We don't enforce conventional commits but appreciate readable history.
- No CLA required at this stage. By submitting a PR you agree your contribution is licensed under MIT (see `LICENSING.md`).

### What CI checks

- Tests pass on macOS Apple Silicon (primary target) and Linux (best-effort)
- Linting and formatting clean
- Type checks (`mypy --strict` on the core package)
- Documentation builds (any `*.md` referenced from code as docstrings)

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
