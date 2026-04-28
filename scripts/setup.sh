#!/usr/bin/env bash
# scripts/setup.sh — first-time setup after `git clone`.
#
# Idempotent: safe to re-run after pulling new code or switching branches.
# Checks prereqs, creates a venv, installs dependencies, and (optionally)
# installs pre-commit hooks.
#
# Usage:  ./scripts/setup.sh [--no-hooks] [--no-pip-fallback]
#
# Flags:
#   --no-hooks        Skip the pre-commit hook installation prompt
#   --no-pip-fallback Hard-fail if uv isn't installed (default: fall back to pip)

set -euo pipefail

cd "$(dirname "$0")/.."

# ---- argument parsing -----------------------------------------------------

INSTALL_HOOKS_PROMPT=1
ALLOW_PIP_FALLBACK=1

for arg in "$@"; do
    case "$arg" in
        --no-hooks)         INSTALL_HOOKS_PROMPT=0 ;;
        --no-pip-fallback)  ALLOW_PIP_FALLBACK=0 ;;
        -h|--help)
            grep '^#' "$0" | sed 's/^# \{0,1\}//' | head -15
            exit 0 ;;
        *)
            echo "ERROR: unknown argument: $arg" >&2
            exit 2 ;;
    esac
done

# ---- helpers --------------------------------------------------------------

# Color codes — only emit if stdout is a terminal
if [[ -t 1 ]]; then
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    RED='\033[0;31m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    GREEN=''; YELLOW=''; RED=''; BOLD=''; RESET=''
fi

ok()    { printf "${GREEN}✓${RESET} %s\n" "$1"; }
warn()  { printf "${YELLOW}⚠${RESET} %s\n" "$1"; }
fail()  { printf "${RED}✗${RESET} %s\n" "$1" >&2; exit 1; }
info()  { printf "${BOLD}==>${RESET} %s\n" "$1"; }

has() { command -v "$1" >/dev/null 2>&1; }

# ---- prereq checks --------------------------------------------------------

info "Checking prerequisites"

# Python 3.11+
if ! has python3; then
    fail "python3 not found in PATH. Install Python 3.11 or newer."
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    fail "Python 3.11+ required (found ${PY_VER}). Install a newer Python."
fi
ok "Python ${PY_VER}"

# uv (preferred). Fall back to pip+venv unless --no-pip-fallback was given.
USE_UV=0
if has uv; then
    UV_VER=$(uv --version 2>&1 | awk '{print $2}')
    ok "uv ${UV_VER}"
    USE_UV=1
elif [[ "${ALLOW_PIP_FALLBACK}" == "1" ]]; then
    warn "uv not found; will fall back to plain venv + pip"
    warn "(install with: brew install uv  OR  pipx install uv  OR  pip install uv)"
else
    fail "uv not found and --no-pip-fallback was given"
fi

# darktable (required for E2E tests; warn but don't fail)
if has darktable-cli; then
    DT_LINE=$(darktable-cli --version 2>&1 | head -1)
    ok "darktable: ${DT_LINE}"
else
    warn "darktable-cli not found; E2E tests will be skipped"
    warn "(install with: brew install darktable)"
fi

echo

# ---- environment setup ----------------------------------------------------

if [[ "${USE_UV}" == "1" ]]; then
    info "Creating venv and syncing dependencies (via uv)"
    uv venv
    uv sync --all-extras --dev
else
    info "Creating venv and installing dependencies (via pip)"
    if [[ ! -d ".venv" ]]; then
        python3 -m venv .venv
    fi
    # shellcheck source=/dev/null
    source .venv/bin/activate
    python -m pip install --upgrade pip setuptools wheel
    python -m pip install -e ".[dev]"
fi

ok "Dependencies installed"
echo

# ---- pre-commit hooks (opt-in) -------------------------------------------

if [[ "${INSTALL_HOOKS_PROMPT}" == "1" ]]; then
    if [[ -t 0 ]]; then
        read -r -p "Install pre-commit hooks (recommended)? [Y/n] " REPLY
        REPLY="${REPLY:-Y}"
    else
        # Non-interactive: skip silently
        REPLY="n"
    fi

    if [[ "${REPLY}" =~ ^[Yy]$ ]]; then
        info "Installing pre-commit hooks"
        if [[ "${USE_UV}" == "1" ]]; then
            uv run pre-commit install
            uv run pre-commit install --hook-type pre-push
        else
            pre-commit install
            pre-commit install --hook-type pre-push
        fi
        ok "Pre-commit hooks installed"
    else
        info "Skipping pre-commit hook install (you can run 'make hooks' later)"
    fi
fi

echo

# ---- final report --------------------------------------------------------

printf "${GREEN}${BOLD}✅ Setup complete.${RESET}\n\n"

if [[ "${USE_UV}" == "1" ]]; then
    cat <<EOF
Common commands (uv prefix handles venv automatically):
  ${BOLD}uv run pytest tests/unit${RESET}            fast unit tests
  ${BOLD}uv run pytest tests/integration${RESET}     integration tests (no darktable needed)
  ${BOLD}uv run pytest tests/e2e${RESET}             end-to-end tests (requires darktable)
  ${BOLD}uv run ruff check${RESET}                   lint
  ${BOLD}uv run ruff format${RESET}                  format
  ${BOLD}uv run mypy src/chemigram${RESET}           type check

Or use the Makefile shortcuts:
  ${BOLD}make test${RESET}        unit tests
  ${BOLD}make check${RESET}       lint + typecheck + unit (run before committing)
  ${BOLD}make help${RESET}        list all targets
EOF
else
    cat <<EOF
Activate the venv:
  ${BOLD}source .venv/bin/activate${RESET}

Then common commands:
  ${BOLD}pytest tests/unit${RESET}                fast unit tests
  ${BOLD}ruff check${RESET}                       lint
  ${BOLD}mypy src/chemigram${RESET}               type check

Or use the Makefile shortcuts:
  ${BOLD}make test${RESET}        unit tests
  ${BOLD}make check${RESET}       lint + typecheck + unit (run before committing)
  ${BOLD}make help${RESET}        list all targets
EOF
fi
