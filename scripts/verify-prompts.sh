#!/usr/bin/env bash
# Verify MANIFEST.toml entries match the .j2 files on disk.
#
# Per ADR-044: MANIFEST is the single source of truth for active prompt
# versions. CI runs this script to catch drift between the registry and
# the template tree.

set -euo pipefail

PROMPTS_ROOT="${1:-src/chemigram/mcp/prompts}"
MANIFEST="${PROMPTS_ROOT}/MANIFEST.toml"

if [[ ! -f "${MANIFEST}" ]]; then
  echo "verify-prompts: ${MANIFEST} not found" >&2
  exit 1
fi

python3 - "${PROMPTS_ROOT}" "${MANIFEST}" <<'PY'
import sys
import tomllib
from pathlib import Path

prompts_root = Path(sys.argv[1])
manifest_path = Path(sys.argv[2])

data = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
prompts = data.get("prompts", {})

failures: list[str] = []
checked = 0
for path, entry in prompts.items():
    active = entry.get("active")
    if not active:
        failures.append(f"{path}: missing 'active' key")
        continue
    template = prompts_root / f"{path}_{active}.j2"
    if not template.exists():
        failures.append(f"{path}: active version {active} not on disk ({template})")
        continue
    checked += 1

if failures:
    print("verify-prompts: FAILED", file=sys.stderr)
    for f in failures:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(2)

print(f"verify-prompts: OK ({checked} active prompt(s) match files)")
PY
