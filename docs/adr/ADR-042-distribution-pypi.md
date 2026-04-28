# ADR-042 — Distribution via PyPI, GitHub releases as supplement

> Status · Accepted
> Date · 2026-04-27
> TA anchor · /stack
> Related RFC · None (engineering choice)

## Context

Chemigram is a Python package intended for local install on contributors' and end users' machines. The distribution channel affects discoverability, install ergonomics, dependency resolution, and auditability. Sibling projects (`chemigram-vocabulary-starter`, `chemigram-masker-sam`) ideally use the same channel for consistency.

Two reasonable channels:

1. **PyPI** — `pip install chemigram`, `uv pip install chemigram`. Standard Python package distribution. Indexed, searchable, integrated with all Python tooling.
2. **GitHub releases** — tarballs and wheels attached to git tags. Useful for direct download, version pinning to a specific git ref, or air-gapped environments.

Each has its place; they complement rather than compete.

## Decision

**PyPI is the primary distribution channel.** GitHub releases supplement PyPI by providing the same artifacts (sdist + wheel) attached to each git tag.

Release flow:

1. Bump version in `pyproject.toml`, update CHANGELOG.md
2. Tag (`git tag v0.x.y`)
3. Run `uv build` to produce sdist + wheel in `dist/`
4. Run pre-release E2E check (`scripts/pre-release-check.sh`)
5. `uv publish` (or `twine upload`) to PyPI
6. Push tag to GitHub, attach `dist/*` to the GitHub release

For pre-1.0 releases, also publish to TestPyPI first when uncertainty about packaging is real (large refactors, dependency changes).

## Rationale

- **PyPI is canonical for Python packages.** `pip install chemigram` is the path of least resistance for users; tooling assumes PyPI.
- **GitHub releases as a mirror** provides redundancy, supports version-pinning to git refs (`pip install git+https://github.com/.../chemigram@v0.1.0`), and offers a recovery path if PyPI has issues.
- **TestPyPI for early releases** lets us validate packaging without polluting the main index. Particularly useful during 0.x development.
- **Same artifacts in both channels** (built once, uploaded to both) avoids the "GitHub has a different version" confusion.

## Alternatives considered

- **GitHub-only:** loses pip discoverability, breaks `uv add chemigram` ergonomics, requires explicit URL pins for users. Acceptable for a private project but not for a public OSS package.
- **PyPI-only (no GitHub releases):** simpler but loses the audit/recovery story. GitHub release entries cost almost nothing to add.
- **Conda-forge:** considered as supplementary but adds release-management overhead; not justified for v1. Could add later if conda users emerge.
- **Custom wheel hosting:** unnecessary complexity for a public OSS package.

## Consequences

Positive:
- Standard Python install ergonomics (`pip install`, `uv add`)
- Discoverable on PyPI search
- GitHub releases provide redundancy
- TestPyPI lets us validate packaging on early releases

Negative:
- PyPI account + 2FA setup required for the maintainer (one-time cost)
- Two upload steps per release (mitigation: scripted in `scripts/release.sh`)
- Name reservation on PyPI matters — `chemigram` and sibling-project names should be claimed early to avoid squatting

## Implementation notes

`pyproject.toml` declares standard PyPI metadata: `[project]` block with name, version, description, authors, license, classifiers, keywords, urls. Trusted publishing (OIDC) configured between GitHub and PyPI to avoid storing API tokens in CI. `scripts/release.sh` wraps the release flow. `CHANGELOG.md` follows the "Keep a Changelog" format. PyPI names claimed during Slice 1 of Phase 1: `chemigram`, `chemigram-vocabulary-starter`, `chemigram-masker-sam` (placeholder uploads if needed to reserve).
