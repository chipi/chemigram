# Tests

`pytest`-driven test suite for `chemigram.core` and `chemigram.mcp`. Three tiers per ADR-036.

**Status:** populated as Phase 1 slices land. Slice 1 seeds `unit/` and `integration/` for the synthesizer and pipeline.

## Tiers

- `tests/unit/` — pure-logic tests. No I/O beyond `tmp_path`, no subprocess, no darktable. Fast (<1s typical). Run by default.
- `tests/integration/` — tests using real `.dtstyle` and XMP fixtures in temp filesystems. No darktable required. Validates parser + synthesizer composition.
- `tests/e2e/` — end-to-end tests that invoke `darktable-cli`. Require darktable installed and a real raw fixture. Skipped automatically when prerequisites are absent.

## Fixtures

Real `.dtstyle` files captured during Phase 0 live at `tests/fixtures/dtstyles/`. The reference baseline XMP and the validated composed XMP live at `tests/fixtures/xmps/`. The reference raw file is **not** committed (51 MB Nikon NEF); `tests/e2e/` discovers it via the `CHEMIGRAM_TEST_RAW` environment variable, defaulting to `~/chemigram-phase0/raws/raw-test.NEF`. See `tests/fixtures/README.md`.

## Running

```bash
make test              # unit only (fast)
make test-integration  # unit + integration (no darktable needed)
make test-e2e          # full suite (requires darktable + test raw)
```
