# `~/.chemigram/config.toml` reference

> The user's static configuration file. TOML format. Read by both the CLI and MCP server at startup.
>
> Optional — if `~/.chemigram/config.toml` doesn't exist, defaults apply. Most photographers can run Chemigram without ever creating this file.

## Where it lives

Default path: `~/.chemigram/config.toml` (created by hand; no `chemigram init` command). The directory `~/.chemigram/` also holds `tastes/` and (for users who maintain a personal pack) `vocabulary/personal/`.

## What it controls

Three concerns live in `config.toml` today:

1. **Vocabulary sources** — which packs to load on session start
2. **L1 bindings** — camera+lens → vocabulary template lookups (per ADR-053)
3. **Per-darktable-version overrides** — rare; only needed when running multiple dt versions

Everything else (workspace location, configdir, taste-dir) is env-var-overridable; see [`cli-env-vars.md`](cli-env-vars.md).

---

## Schema

### `[vocabulary]`

```toml
[vocabulary]
sources = [
    "$CHEMIGRAM_INSTALL/vocabulary/starter",
    "$CHEMIGRAM_INSTALL/vocabulary/packs/expressive-baseline",
    "~/.chemigram/vocabulary/personal",
    "~/private/chemigram-vocabulary-marko",
]
```

| Field | Type | Default | Description |
|-|-|-|-|
| `sources` | `list[str]` | `["$CHEMIGRAM_INSTALL/vocabulary/starter"]` | Pack roots to load, in order. Later packs override earlier on name collisions (collisions still raise — there's no silent shadowing per `chemigram.core.vocab.VocabularyIndex`). |

Path expansion:
- `~` expands to `$HOME`
- `$CHEMIGRAM_INSTALL` expands to the install root of the chemigram package (where `vocabulary/starter/` ships)
- Absolute paths are used as-is

If `sources` is omitted entirely, only the bundled starter pack loads.

### `[[layers.L1.bindings]]`

```toml
[[layers.L1.bindings]]
make = "Canon"
model = "EOS R5"
lens_model = "RF24-105mm F4 L IS USM"
template = "lens_correct_full + denoise_auto"

[[layers.L1.bindings]]
make = "NIKON CORPORATION"
model = "NIKON D850"
lens_model = "AF-S Fisheye Nikkor 8-15mm f/3.5-4.5E ED"
template = "denoise_auto"   # NO lens correction; preserve fisheye character
```

L1 is the *technical correction* layer (lens correction, profiled denoise) — empty by default per ADR-016. Photographers who want auto-applied L1 bindings keyed to their actual gear add entries here.

| Field | Type | Description |
|-|-|-|
| `make` | string | EXIF `Make`, exact match (case-sensitive per ADR-053). |
| `model` | string | EXIF `Model`, exact match. |
| `lens_model` | string | EXIF `LensModel`, exact match. (Not all cameras populate this; entries without a known lens require the photographer to set `lens_model = ""` and accept the binding fires for any lens on that body.) |
| `template` | string | A vocabulary entry name (or whitespace-separated list combined via `+`). Resolved against the loaded packs. |

Match is exact-tuple. If a photographer has two D850s shot with the same lens but they want different L1 templates, that's not currently expressible — file an issue.

### `[layers.L2]`

L2 (look establishment, e.g., `underwater_pelagic_blue`) is selected per-image via the brief's `Tastes:` declaration, not via `config.toml`. There's no `[layers.L2]` section.

### `[layers.L3]`

L3 (the agent's vocabulary) is mutable in the loop, not pre-bound. There's no `[layers.L3]` section.

### Per-darktable-version overrides

If you run multiple darktable versions (typical when comparing 4.x against 5.x for vocabulary calibration), you can shadow a pack per-version:

```toml
[[vocabulary.darktable_overrides]]
darktable_version = "4.6"
sources = ["$CHEMIGRAM_INSTALL/vocabulary/starter-dt46"]
```

This is rare. Most users don't need it.

---

## Minimal config (typical photographer)

```toml
[vocabulary]
sources = [
    "$CHEMIGRAM_INSTALL/vocabulary/starter",
    "$CHEMIGRAM_INSTALL/vocabulary/packs/expressive-baseline",
    "~/.chemigram/vocabulary/personal",
]
```

## L1-binding example (Canon shooter who wants auto-correction)

```toml
[vocabulary]
sources = [
    "$CHEMIGRAM_INSTALL/vocabulary/starter",
    "$CHEMIGRAM_INSTALL/vocabulary/packs/expressive-baseline",
    "~/.chemigram/vocabulary/personal",
]

[[layers.L1.bindings]]
make = "Canon"
model = "EOS R5"
lens_model = "RF24-105mm F4 L IS USM"
template = "lens_correct_full + denoise_auto"

[[layers.L1.bindings]]
make = "Canon"
model = "EOS R5"
lens_model = "RF15-35mm F2.8 L IS USM"
template = "lens_correct_full + denoise_auto"
```

Note: the `lens_correct_full` and `denoise_auto` primitives don't ship in the starter or expressive-baseline packs — they're examples of what *would* live in your personal pack once you author them. L1 is opt-in evidence-driven per ADR-016.

---

## Validation

There's no `chemigram config validate` verb (yet). To check that your config loads cleanly, run `chemigram status`:

```bash
chemigram status
# Pack sources are listed; if a path doesn't exist, the loader raises.
```

Or use the CLI's `--json` mode and inspect the loaded packs:

```bash
chemigram --json status | jq .vocabulary_packs
```

---

## See also

- [`cli-env-vars.md`](cli-env-vars.md) — env vars that override config-file paths
- [`docs/concept/03-data-catalog.md`](../concept/03-data-catalog.md) — the broader data catalog
- [`docs/adr/ADR-016-l1-empty-by-default.md`](../adr/ADR-016-l1-empty-by-default.md) — why L1 ships empty
- [`docs/adr/ADR-053-l1-binding-exact-match.md`](../adr/ADR-053-l1-binding-exact-match.md) — L1 lookup semantics
