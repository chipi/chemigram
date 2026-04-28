#!/usr/bin/env bash
# Pre-release validation for Chemigram (ADR-036, ADR-042).
# Runs the full test suite including E2E tests that require darktable installed locally.
# CI does NOT run E2E (no darktable in GitHub Actions runners). This script is the
# gate before publishing to PyPI.
#
# Usage:  ./scripts/pre-release-check.sh

set -euo pipefail

cd "$(dirname "$0")/.."

# Verify darktable is installed
if ! command -v darktable-cli >/dev/null 2>&1; then
    echo "ERROR: darktable-cli not found in PATH" >&2
    echo "       Install darktable 5.x (Apple Silicon native build recommended)" >&2
    exit 1
fi

DT_VERSION="$(darktable-cli --version 2>&1 | head -1)"
echo "==> Using ${DT_VERSION}"

echo "==> Lint check"
uv run ruff check --no-fix

echo "==> Format check"
uv run ruff format --check

echo "==> Type check (chemigram.core strict)"
uv run mypy src/chemigram

echo "==> Unit tests"
uv run pytest tests/unit -q

echo "==> Integration tests"
uv run pytest tests/integration -q

echo "==> E2E tests (this is the slow tier)"
uv run pytest tests/e2e -q

echo "==> Build wheel + sdist"
uv build

echo ""
echo "✅ Pre-release checks passed. Artifacts in dist/"
echo "   Next: scripts/release.sh <version>"
