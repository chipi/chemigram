#!/usr/bin/env bash
# Release Chemigram (ADR-042).
# Tags the version, publishes to PyPI, and pushes the tag to GitHub.
# Run scripts/pre-release-check.sh FIRST.
#
# Usage:  ./scripts/release.sh <version>
# Example: ./scripts/release.sh 0.1.0

set -euo pipefail

cd "$(dirname "$0")/.."

VERSION="${1:-}"
if [[ -z "${VERSION}" ]]; then
    echo "Usage: $0 <version>" >&2
    echo "Example: $0 0.1.0" >&2
    exit 1
fi

# Verify pyproject.toml version matches
PYPROJECT_VERSION="$(grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')"
if [[ "${PYPROJECT_VERSION}" != "${VERSION}" ]]; then
    echo "ERROR: pyproject.toml version (${PYPROJECT_VERSION}) does not match argument (${VERSION})" >&2
    echo "       Update [project] version in pyproject.toml first." >&2
    exit 1
fi

# Verify CHANGELOG.md mentions this version
if ! grep -q "## \[${VERSION}\]" CHANGELOG.md; then
    echo "ERROR: CHANGELOG.md does not have an entry for [${VERSION}]" >&2
    echo "       Add a section before releasing." >&2
    exit 1
fi

# Verify clean working tree
if ! git diff-index --quiet HEAD --; then
    echo "ERROR: working tree has uncommitted changes" >&2
    exit 1
fi

# Verify pre-release checks have been run (build artifacts present)
if [[ ! -d dist ]] || [[ -z "$(ls -A dist 2>/dev/null)" ]]; then
    echo "ERROR: no dist/ artifacts found" >&2
    echo "       Run scripts/pre-release-check.sh first." >&2
    exit 1
fi

echo "==> About to release version ${VERSION}"
echo "    Will: tag v${VERSION}, publish to PyPI, push tag"
read -p "    Continue? [y/N] " -n 1 -r CONFIRM
echo
if [[ ! "${CONFIRM}" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo "==> Tagging v${VERSION}"
git tag -a "v${VERSION}" -m "Release v${VERSION}"

echo "==> Publishing to PyPI"
# Trusted publishing (OIDC) preferred; fall back to twine + token if configured
uv publish

echo "==> Pushing tag to GitHub"
git push origin "v${VERSION}"

echo ""
echo "✅ Released v${VERSION}"
echo "   Next: attach dist/ artifacts to the GitHub release at"
echo "         https://github.com/chipi/chemigram/releases/tag/v${VERSION}"
