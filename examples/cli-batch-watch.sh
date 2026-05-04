#!/usr/bin/env bash
# Watch-folder script: ingest + auto-edit any new RAW that lands in $WATCH_DIR.
#
# Demonstrates the *substrate* shape of CLI use — Chemigram as a piece of
# infrastructure rather than as a session host. Drop a raw into the watched
# folder, get back a snapshotted workspace + preview JPEG with a small
# default edit applied. Useful for tethered shoots, scripted pipelines, or
# any context where the agent has already decided what move to apply.
#
# Pairs with: examples/cli-agent-loop.py (the Python equivalent).
# Documentation:
#   docs/guides/cli-output-schema.md  — NDJSON event format
#   docs/guides/cli-reference.md      — verb / flag reference
#   docs/guides/cli-env-vars.md       — env var reference
#
# Usage:
#   export CHEMIGRAM_DT_CONFIGDIR=/path/to/bootstrapped/configdir
#   ./cli-batch-watch.sh /path/to/incoming/folder
#
# Requires: chemigram on PATH; fswatch (macOS) or inotifywait (Linux);
# jq for parsing the NDJSON output.

set -euo pipefail

WATCH_DIR="${1:-}"
if [[ -z "$WATCH_DIR" || ! -d "$WATCH_DIR" ]]; then
  echo "usage: $0 <directory-to-watch>" >&2
  exit 2
fi

if [[ -z "${CHEMIGRAM_DT_CONFIGDIR:-}" ]]; then
  echo "warning: CHEMIGRAM_DT_CONFIGDIR not set; renders will fail" >&2
fi

# Detect the platform's file-watch tool.
if command -v fswatch >/dev/null 2>&1; then
  WATCH_CMD=(fswatch -0 --event Created "$WATCH_DIR")
elif command -v inotifywait >/dev/null 2>&1; then
  WATCH_CMD=(inotifywait -m -e create --format '%w%f%0' --no-newline "$WATCH_DIR")
else
  echo "error: install fswatch (macOS: brew install fswatch) or inotify-tools (Linux)" >&2
  exit 6
fi

echo "Watching $WATCH_DIR for new RAW files…" >&2
echo "Drop a .NEF, .RAF, .ARW, .CR2, .CR3, .ORF, .RW2, etc. into the folder." >&2
echo "Press Ctrl+C to stop." >&2
echo

# fswatch -0 / inotifywait %0 separate events with NUL bytes; read with -d ''.
"${WATCH_CMD[@]}" | while IFS= read -r -d '' file; do
  # Only react to RAW files; ignore xmp sidecars, dotfiles, etc.
  case "${file,,}" in
    *.nef|*.raf|*.arw|*.cr2|*.cr3|*.orf|*.rw2|*.dng|*.raw)
      ;;
    *)
      continue
      ;;
  esac

  echo "──── $(basename "$file")" >&2
  process_one "$file" || echo "  (failed; continuing)" >&2
  echo >&2
done

# ---------------------------------------------------------------------------
# process_one: ingest + apply a small default edit + render preview.
# ---------------------------------------------------------------------------
process_one() {
  local raw="$1"

  # 1) ingest
  local ingest
  if ! ingest=$(chemigram --json ingest "$raw" 2>&1 | tail -1); then
    echo "  ingest failed:" "$ingest" >&2
    return 1
  fi

  if [[ "$(jq -r .status <<<"$ingest")" != "ok" ]]; then
    echo "  ingest error:" "$(jq -r .message <<<"$ingest")" >&2
    return 1
  fi

  local image_id
  image_id=$(jq -r .image_id <<<"$ingest")
  echo "  ingested → image_id=$image_id" >&2

  # 2) apply a small default edit (swap for whatever your script needs).
  #    Here: top-dampen gradient on the highlights.
  local apply
  if ! apply=$(chemigram --json apply-primitive "$image_id" \
      --entry gradient_top_dampen_highlights \
      --pack expressive-baseline 2>&1 | tail -1); then
    echo "  apply failed:" "$apply" >&2
    return 1
  fi

  if [[ "$(jq -r .status <<<"$apply")" != "ok" ]]; then
    local code
    code=$(jq -r .exit_code_name <<<"$apply")
    case "$code" in
      MASKING_ERROR)
        echo "  apply: malformed mask_spec on entry (vocab bug)" >&2
        ;;
      NOT_FOUND)
        echo "  apply: entry not found in expressive-baseline pack" >&2
        ;;
      *)
        echo "  apply: $code →" "$(jq -r .message <<<"$apply")" >&2
        ;;
    esac
    return 1
  fi

  echo "  applied gradient_top_dampen_highlights → snapshot $(jq -r .snapshot_hash <<<"$apply" | cut -c1-12)…" >&2

  # 3) render a preview.
  local render
  if ! render=$(chemigram --json render-preview "$image_id" --size 1024 2>&1 | tail -1); then
    echo "  render failed:" "$render" >&2
    return 1
  fi

  if [[ "$(jq -r .status <<<"$render")" != "ok" ]]; then
    echo "  render: $(jq -r .message <<<"$render")" >&2
    if [[ "$(jq -r .exit_code_name <<<"$render")" == "DARKTABLE_ERROR" ]]; then
      echo "  hint: check CHEMIGRAM_DT_CONFIGDIR is set + bootstrapped" >&2
    fi
    return 1
  fi

  echo "  preview → $(jq -r .jpeg_path <<<"$render")" >&2
}
