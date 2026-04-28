---
name: Slice task
about: An atomic implementation task as part of a Phase/Slice
title: "[Slice X] "
labels: ""
assignees: ""
---

# [Slice X] <task title>

## Why this issue

(One paragraph: why now, what unblocks, what depends on this. Be specific.)

## Context (background reading)

- (ADR/RFC references with one-line descriptions of relevance)
- (Related conceptual docs in `docs/concept/`)

## Scope (what's in)

(Bulleted list of concrete deliverables. Be precise. Aim for one PR's worth of work.)

## Out of scope (don't drift)

- ❌ (things that look related but belong in another issue)
- ❌ (things this issue might naturally grow into; resist)

## API to implement

**File:** `src/chemigram/...`

```python
# Skeleton showing the public API: dataclass shapes, function signatures,
# docstring conventions. Implementation details left to the author.
```

Implementation notes:

- (Specific gotchas, dependency choices, ADR rules to follow)

## Tests

**File:** `tests/unit/...` (or integration / e2e as appropriate)

Required test cases:

- [ ] (specific scenarios with the property being verified)

## Acceptance criteria

- [ ] All test cases listed above pass
- [ ] `uv run mypy <module>` passes (per ADR-038's strictness for the relevant subpackage)
- [ ] `uv run ruff check <module>` clean
- [ ] `uv run ruff format --check <module>` clean
- [ ] Docstrings on all public symbols
- [ ] CHANGELOG.md gets an entry under `## [Unreleased]`
- [ ] (Module-specific criteria — e.g., "no decoding of opaque blobs")

## What lands after this

- (Names the follow-up issues that this unblocks)

## References

- ADR-NNN — (relevance)
- RFC-NNN — (relevance)
- `docs/concept/...` — (relevance)

---

**Suggested labels:** `phase-N`, `slice-M`, `module:NAME`
**Suggested milestone:** `0.x.y`
**Estimated effort:** N sittings (~X–Y hours)
