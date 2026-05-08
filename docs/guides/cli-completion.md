# Shell completion for `chemigram`

The CLI supports shell completion for command and option names via Typer's built-in mechanism. Wire it up once per shell; the completion script auto-discovers when new commands ship.

## Install

```sh
# zsh
chemigram --install-completion

# bash / fish — same flag, the shell auto-detects
chemigram --install-completion
```

The flag detects your current shell via [shellingham](https://github.com/sarugaku/shellingham) and writes the completion script to the standard location for that shell. Restart your shell (or `source` the file the install path prints) to activate.

If detection fails (`Shell None is not supported.`), set `$SHELL` explicitly in the parent shell before invoking, or use `--show-completion` to dump the script and add it to your shell rc manually:

```sh
chemigram --show-completion >> ~/.zshrc
# or whatever your shell's rc file is
```

## What's completed

- **Top-level commands** — every verb and sub-app shows up after `chemigram <TAB>`.
- **Sub-app commands** — `chemigram vocab <TAB>` lists `list` / `show`; `chemigram gap-log <TAB>` lists `list` / `rank` / `show` / `clear`; etc.
- **Option names** — `chemigram vocab list --<TAB>` surfaces `--pack`, `--layer`, etc.

## What's NOT completed (yet)

- **Vocabulary entry names** as values to `chemigram vocab show <name>`. Loading the full vocabulary index at completion time is too slow for an interactive shell. If you frequently need this, pipe `chemigram vocab list` through grep instead.
- **Image_id values** for commands that take one. Same reason — workspace enumeration is filesystem-bound and would slow completion. Use `chemigram status --json | jq` or your shell's path-completion against `~/Pictures/Chemigram/<TAB>` instead.

## Trade-offs vs. the alternatives

- **vs. building a custom click-completion shim**: typer's built-in is good enough for command + option names, which is 90% of the value. Hand-rolling completion for value-spaces (vocab names, image_ids) trades implementation complexity for speed gains we don't currently need.
- **vs. shipping completion scripts in the package**: the typer-generated script per shell is identical for every install; the install-completion flow is the standard upstream path.

## See also

- [Typer documentation on completion](https://typer.tiangolo.com/tutorial/options/help/#shell-completion)
- The CLI's design RFC (RFC-020 / ADR-069..072)
