# Environment variables

> Centralized reference for every `CHEMIGRAM_*` env var the CLI and engine respect.
>
> All env vars are optional. Each has a sensible default; the env var is the override.

| Variable | Defaults to | What it controls | Where used |
|-|-|-|-|
| `CHEMIGRAM_WORKSPACE` | `~/Pictures/Chemigram` | Per-image workspace root. The CLI's `--workspace <path>` flag overrides this. | Resolves the per-image workspace directory in `chemigram.cli._workspace`. |
| `CHEMIGRAM_DT_CONFIGDIR` | (none — must be set or passed via `--configdir` for any verb that renders) | darktable-cli configdir (must be pre-bootstrapped per ADR-005). The CLI's `--configdir <path>` flag overrides this. | Passed to `darktable-cli --configdir` for every render. |
| `CHEMIGRAM_DT_CLI` | `darktable-cli` (resolved on `$PATH`) | Path to the `darktable-cli` binary. Set this if `darktable-cli` isn't on `$PATH` (e.g., on macOS where it's inside the `.app` bundle). | Read by the render pipeline before subprocess invocation. |
| `CHEMIGRAM_TASTES_DIR` | `~/.chemigram/tastes/` | Where multi-scope taste files live (`_default.md`, genre-specific files). | Read by the context loader and `apply-taste-update` verb. |

## Suggested setup

For interactive use, drop these into your shell profile (`~/.zshrc`, `~/.bashrc`):

```bash
# darktable-cli — only if not already on PATH
# macOS:
export CHEMIGRAM_DT_CLI=/Applications/darktable.app/Contents/MacOS/darktable-cli

# Pre-bootstrapped configdir (do this once: open darktable, quit; that bootstraps it)
export CHEMIGRAM_DT_CONFIGDIR="$HOME/chemigram-phase0/dt-config"
```

The other two (`CHEMIGRAM_WORKSPACE` and `CHEMIGRAM_TASTES_DIR`) almost always work with their defaults.

## In agent loops / batch scripts

Pass env vars per-invocation when scripting against multiple workspaces:

```bash
# Process several photo projects in turn
for ws in "$HOME/Pictures/Chemigram-Wedding" "$HOME/Pictures/Chemigram-Travel"; do
  CHEMIGRAM_WORKSPACE="$ws" chemigram apply-primitive img-001 --entry wb_warm_subtle
done
```

Or set once at the top of a script and let every subprocess inherit:

```bash
export CHEMIGRAM_WORKSPACE="$HOME/Pictures/Chemigram-Project"
export CHEMIGRAM_DT_CONFIGDIR="$HOME/chemigram-phase0/dt-config"
chemigram ingest /path/to/raw.NEF
chemigram apply-primitive raw --entry expo_+0.5
```

## Test-only env vars (not user-facing)

These are read by the test suite to inject paths or override defaults during CI / local test runs. **Don't set them in your shell profile.**

- `CHEMIGRAM_TEST_RAW` — path to a real raw file the e2e test suite uses if present (otherwise tests skip with a "no usable test raw" message).

## Where each var is referenced in code

For maintainers / debuggers:

| Variable | Source |
|-|-|
| `CHEMIGRAM_WORKSPACE` | `src/chemigram/cli/main.py` (typer `envvar=` on `--workspace`) |
| `CHEMIGRAM_DT_CONFIGDIR` | `src/chemigram/cli/main.py` (typer `envvar=` on `--configdir`) |
| `CHEMIGRAM_DT_CLI` | `src/chemigram/core/stages/darktable_cli.py` |
| `CHEMIGRAM_TASTES_DIR` | `src/chemigram/core/workspace.py` (`tastes_dir()`) |
| `CHEMIGRAM_TEST_RAW` | `tests/e2e/conftest.py` (test-only) |

## See also

- [`cli-reference.md`](cli-reference.md) — every verb / flag / global option
- [`docs/getting-started.md`](../getting-started.md) — full setup walkthrough including env-var configuration
- [`config-toml.md`](config-toml.md) — `~/.chemigram/config.toml` reference (covers vocabulary sources, L1 bindings, etc. that aren't env-var-overridable)
