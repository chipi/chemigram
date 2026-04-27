# Tests

`pytest`-driven test suite for `chemigram_core` and `chemigram_mcp`.

**Status:** empty. Populated as Phase 1 modules land.

## Planned coverage

- **Unit tests:** XMP synthesis correctness, SET semantics, hash determinism, dtstyle parsing edge cases, vocabulary manifest validation
- **Integration tests:** `darktable-cli` invocation with synthesized XMPs (real darktable in CI on macOS), versioning round-trips
- **Snapshot tests:** XMP outputs for known input vocabulary entries (catches drift)
- **Provider tests:** `MaskingProvider` protocol conformance for the bundled coarse default

CI runs on macOS Apple Silicon (primary target) and Linux (best-effort).

## Running

Once Phase 1 lands:

```bash
pip install -e ".[dev]"
pytest
```
