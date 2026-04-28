# Chemigram Makefile — convenience wrappers for common dev commands.
# Most targets just shell out to `uv run ...`; the value is discoverability
# and keeping commands consistent across contributors.
#
# Run `make` or `make help` to see all targets.

.PHONY: help setup hooks test test-unit test-integration test-e2e \
        lint format typecheck check ci clean build

# Default target: print available commands
help:
	@echo "Chemigram development targets:"
	@echo ""
	@echo "  make setup           First-time setup after clone (calls scripts/setup.sh)"
	@echo "  make hooks           Install pre-commit hooks"
	@echo ""
	@echo "  make test            Fast unit tests (default test target)"
	@echo "  make test-unit       Unit tests only"
	@echo "  make test-integration  Integration tests (no darktable needed)"
	@echo "  make test-e2e        End-to-end tests (requires darktable)"
	@echo ""
	@echo "  make lint            Ruff lint check"
	@echo "  make format          Ruff format (rewrites files)"
	@echo "  make typecheck       Mypy type check on src/chemigram"
	@echo "  make check           lint + typecheck + unit (fast, run before commit)"
	@echo "  make ci              Full CI parity: same steps as .github/workflows/ci.yml"
	@echo ""
	@echo "  make build           Build sdist + wheel into dist/"
	@echo "  make clean           Remove caches and build artifacts"

setup:
	@./scripts/setup.sh

hooks:
	uv run pre-commit install
	uv run pre-commit install --hook-type pre-push

# --- tests ---

test: test-unit

test-unit:
	uv run pytest tests/unit

test-integration:
	uv run pytest tests/integration

test-e2e:
	uv run pytest tests/e2e

# --- code quality ---

lint:
	uv run ruff check

format:
	uv run ruff format

typecheck:
	uv run mypy src/chemigram

# Run before committing: catches what CI catches in the fast path.
check: lint typecheck test-unit
	@echo ""
	@echo "✅ All checks passed."

# Full CI parity. Mirrors .github/workflows/ci.yml step-for-step so a
# clean `make ci` locally implies a clean GitHub Actions run.
# Per ADR-040: unit + integration tests, no E2E (E2E gated to releases
# via scripts/pre-release-check.sh).
ci:
	@echo "==> [1/6] uv sync --all-extras --dev"
	uv sync --all-extras --dev
	@echo "==> [2/6] ruff check --no-fix"
	uv run ruff check --no-fix
	@echo "==> [3/6] ruff format --check"
	uv run ruff format --check
	@echo "==> [4/6] mypy src/chemigram"
	uv run mypy src/chemigram
	@echo "==> [5/6] pytest tests/unit"
	uv run pytest tests/unit
	@echo "==> [6/6] pytest tests/integration"
	uv run pytest tests/integration
	@echo ""
	@echo "✅ CI parity check passed (matches ADR-040 / ci.yml)."

# --- build / cleanup ---

build:
	uv build

clean:
	rm -rf dist/ build/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned caches and build artifacts"
