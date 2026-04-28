# Tests

`pytest`-driven test suite for `chemigram.core` and `chemigram.mcp`. Three tiers per ADR-036.

**Status:** populated as Phase 1 slices land. Slice 1 seeds `unit/` and `integration/` for the synthesizer and pipeline.

## Tiers

- `tests/unit/` — fast tests of pure logic. May read committed fixture files from `tests/fixtures/` and use `tmp_path` for ephemeral writes. **No subprocess, no network, no installed-binary dependencies.** Sub-second per test. Run by `make test` and on every commit (pre-push hook) and CI.
- `tests/integration/` — tests where multiple components meet against committed real-world artifacts. No darktable subprocess. Validates parser + synthesizer + fixture wiring; covers EXIF reads from real raws via `CHEMIGRAM_TEST_RAW`. Run by `make test-integration` and CI.
- `tests/e2e/` — full-pipeline tests that invoke `darktable-cli`. Require darktable installed and a real raw fixture. Skipped automatically when prerequisites are absent. **Not run in CI** per ADR-040 — gated to `make test-e2e` locally and `scripts/pre-release-check.sh`.

## Fixtures

Real `.dtstyle` files captured during Phase 0 live at `tests/fixtures/dtstyles/`. The reference baseline XMP and the validated composed XMP live at `tests/fixtures/xmps/`. The reference raw file is **not** committed (51 MB Nikon NEF); `tests/e2e/` discovers it via the `CHEMIGRAM_TEST_RAW` environment variable, defaulting to `~/chemigram-phase0/raws/raw-test.NEF`. See `tests/fixtures/README.md`.

## Running

```bash
make test              # unit only (fast)
make test-integration  # unit + integration (no darktable needed)
make test-e2e          # full suite (requires darktable + test raw)
```
