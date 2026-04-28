# ADRs — Architecture Decision Records

ADRs lock single decisions with rationale. Short. Append-only. Never edited after acceptance — superseded by new ADRs if circumstances change.

ADRs come from two streams:
- **Direct ADRs** — small decisions that don't need an RFC's deliberation
- **RFC-closure ADRs** — written when an RFC closes; one RFC may close into multiple ADRs

## Reference

- `TA.md` — technical architecture. Every ADR anchors here via `TA/components/...` or `TA/constraints`.
- `ADR_TEMPLATE.md` — the format every ADR follows.

## Index

| ADR | Title | Status |
|-|-|-|
| ADR-001 | Vocabulary approach (Architecture B) | Accepted |
| ADR-002 | SET semantics: replace by (operation, multi_priority) | Accepted |
| ADR-003 | Three foundational disciplines | Accepted |
| ADR-004 | `darktable-cli` invocation form | Accepted |
| ADR-005 | Subprocess serialization per configdir | Accepted |
| ADR-006 | Single Python process, MCP server, no daemon | Accepted |
| ADR-007 | BYOA — no bundled AI capabilities | Accepted |
| ADR-008 | XMP and `.dtstyle` as opaque-blob carriers | Accepted |
| ADR-009 | Path A vs Path B for synthesis | Accepted |
| ADR-010 | Vocabulary parser identifies user entries by empty `<multi_name>` | Accepted |
| ADR-011 | Reject `darktable-cli --style NAME` for vocabulary application | Accepted |
| ADR-012 | `--apply-custom-presets false` always | Accepted |
| ADR-013 | Python 3.11+ | Accepted |
| ADR-014 | All image-processing via darktable | Accepted |
| ADR-015 | Three-layer model (L0/L1/L2/L3) | Accepted |
| ADR-016 | L1 empty by default; opt-in per camera+lens | Accepted |
| ADR-017 | L2 has two flavors (neutralizing, look-committed) | Accepted |
| ADR-018 | Per-image content-addressed DAG | Accepted |
| ADR-019 | Git-like ref structure | Accepted |
| ADR-020 | No remote, no three-way merge, no reflog | Accepted |
| ADR-021 | Three-layer mask pattern | Accepted |
| ADR-022 | Mask registry per image with symbolic refs | Accepted |
| ADR-023 | Vocabulary primitives are `.dtstyle` + manifest entries | Accepted |
| ADR-024 | Authoring discipline: uncheck non-target modules | Accepted |
| ADR-025 | WB and color calibration coupling | Accepted |
| ADR-026 | Vocabulary modversion-pinned to darktable version | Accepted |
| ADR-027 | Local-only session data | Accepted |
| ADR-028 | Configuration formats: TOML and JSON | Accepted |
| ADR-029 | Session transcripts as JSONL | Accepted |
| ADR-030 | Three-tier context model | Accepted |
| ADR-031 | Propose-and-confirm for context updates | Accepted |
| ADR-032 | Distribution split | Accepted |
| ADR-033 | MCP tool surface (initial) | Accepted |
| ADR-034 | Build system and package layout (pyproject.toml + hatchling, src/-layout) | Accepted |
| ADR-035 | Dev environment with uv | Accepted |
| ADR-036 | Testing strategy: pytest with three tiers | Accepted |
| ADR-037 | Linting and formatting with ruff | Accepted |
| ADR-038 | Type checking with mypy strict for core | Accepted |
| ADR-039 | Pre-commit hooks for local quality gates | Accepted |
| ADR-040 | CI on GitHub Actions, macOS-only for v1 | Accepted |
| ADR-041 | SemVer with 0.x for Phase 1 development | Accepted |
| ADR-042 | Distribution via PyPI, GitHub releases as supplement | Accepted |
| ADR-043 | Jinja2 + filename-versioned templates as prompt format | Accepted |
| ADR-044 | PromptStore API and MANIFEST.toml as active-version registry | Accepted |
| ADR-045 | Prompt versioning is independent of package SemVer | Accepted |
| ADR-046 | Golden dataset versioning (immutable, append-only) | Accepted |
| ADR-047 | Run manifests for eval reproducibility | Accepted |
| ADR-048 | Multi-scope taste structure (extends ADR-030) | Accepted |
| ADR-049 | Vocabulary-starter ships within chemigram (clarifies ADR-032) | Accepted |

## Conventions

- Numbered sequentially (`ADR-NNN-slug.md`)
- Append-only — once Accepted, never edited
- Superseded ADRs stay in the record with `Status · Superseded by ADR-NNN`
- Every ADR references its TA anchor
- Short by design — full deliberation lives in the related RFC if there was one
