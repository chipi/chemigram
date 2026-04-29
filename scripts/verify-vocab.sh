#!/usr/bin/env bash
# Verify the bundled starter vocabulary pack loads cleanly.
#
# Same shape as scripts/verify-prompts.sh, but this one imports
# chemigram, so it needs the project's venv on PYTHONPATH. We prefer
# `uv run python` if available; fall back to bare `python3` otherwise
# (which works inside an already-activated venv).

set -euo pipefail

PACK_ROOT="${1:-vocabulary/starter}"

if command -v uv >/dev/null 2>&1; then
    PY="uv run python"
else
    PY="python3"
fi

$PY - "${PACK_ROOT}" <<'PY'
import sys
from pathlib import Path

from chemigram.core.vocab import ManifestError, VocabularyIndex

pack = Path(sys.argv[1])
if not (pack / "manifest.json").exists():
    print(
        f"verify-vocab: no manifest at {pack}/manifest.json — skipping "
        "(dev or test workspace)",
        file=sys.stderr,
    )
    sys.exit(0)

try:
    index = VocabularyIndex(pack)
except ManifestError as exc:
    print(f"verify-vocab: FAILED — {exc}", file=sys.stderr)
    sys.exit(2)

count = len(index.list_all())
print(f"verify-vocab: OK ({count} entries)")
PY
