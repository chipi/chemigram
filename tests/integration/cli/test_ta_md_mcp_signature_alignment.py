"""Audit: TA.md's `contracts/mcp-tools` section signatures match the
actual MCP input_schemas. The TA reference doc is meant to be the
canonical contract surface; if it drifts from runtime registry, agents
and humans reading TA.md get the wrong picture.

Catches the bug class found during the v1.10.0 round-2 audit where
`apply_primitive` was documented with `parameter_values` (older name)
but the schema has `value`, and `log_vocabulary_gap` was documented
with 3 args but the schema accepts 10. Without this test, the drift
slips past every release.

The match is approximate (we don't enforce the exact arg-name spelling
for Python-keyword-collision cases like `from_` — those are noted as
documented exceptions). Required-vs-optional markers are not enforced
yet either.
"""

from __future__ import annotations

import re
from pathlib import Path

from chemigram.mcp.registry import list_registered
from chemigram.mcp.tools import register_all

TA_PATH = Path(__file__).resolve().parents[3] / "docs" / "adr" / "TA.md"

# (tool, schema_prop, doc_spelling) — TA.md documents these with a
# different spelling than the schema field for documented reasons
# (Python keyword collision). Both names refer to the same parameter.
DOCUMENTED_NAME_EXCEPTIONS: set[tuple[str, str, str]] = {
    ("branch", "from_", "from"),  # Python keyword collision
}


def _parse_ta_signatures() -> dict[str, set[str]]:
    """Return {tool_name: {arg_names_documented}}."""
    text = TA_PATH.read_text()
    # Locate the contracts/mcp-tools section
    m = re.search(
        r"### contracts/mcp-tools(.*?)(?:### constraints|## constraints|---\n\n## )",
        text,
        re.S,
    )
    section = m.group(1) if m else text

    # Match `tool_name(args)` patterns
    tool_re = re.compile(r"`([a-z_]+)\(([^)]*)\)`")
    parsed: dict[str, set[str]] = {}
    for match in tool_re.finditer(section):
        name = match.group(1)
        args_str = match.group(2)
        args = re.split(r"[,\s]+", args_str)
        arg_names: set[str] = set()
        for a in args:
            a = a.strip().rstrip("?").rstrip(",").rstrip("*")
            if not a or a == "*":
                continue
            # Strip default value: name=value
            a = a.split("=")[0].strip()
            if a and not a.startswith("*"):
                arg_names.add(a)
        if name in parsed:
            # First occurrence (the contract listing) wins; helper-fn refs
            # higher up in TA.md are signature-only references.
            continue
        parsed[name] = arg_names
    return parsed


def test_ta_md_mcp_signatures_match_runtime_schemas() -> None:
    """For every tool documented in TA.md `contracts/mcp-tools`, the
    documented arg names must match the live MCP schema properties
    (modulo the documented Python-keyword exceptions)."""
    register_all()
    mcp_specs = {s.name: s for s in list_registered()}

    ta_signatures = _parse_ta_signatures()

    failures: list[str] = []
    for tool_name, documented in ta_signatures.items():
        if tool_name not in mcp_specs:
            # Could be a non-tool reference (e.g. helper fn signature
            # earlier in TA.md). Skip silently — the parser is approximate.
            continue
        actual_props = set(mcp_specs[tool_name].input_schema.get("properties", {}).keys())

        # Apply exceptions: rewrite documented spellings to schema spellings
        normalized_documented = set()
        for arg in documented:
            mapped = arg
            for excp_tool, schema_name, doc_spelling in DOCUMENTED_NAME_EXCEPTIONS:
                if excp_tool == tool_name and arg == doc_spelling:
                    mapped = schema_name
                    break
            normalized_documented.add(mapped)

        documented_extras = normalized_documented - actual_props
        missing_documentation = actual_props - normalized_documented

        if documented_extras:
            failures.append(
                f"{tool_name}: TA.md documents args {sorted(documented_extras)} "
                f"that don't exist in the schema. Remove them from TA.md or "
                "add them to DOCUMENTED_NAME_EXCEPTIONS if it's a known spelling diff."
            )
        if missing_documentation:
            failures.append(
                f"{tool_name}: schema has props {sorted(missing_documentation)} "
                f"that TA.md doesn't document. Update TA.md to include them, "
                "or add to DOCUMENTED_NAME_EXCEPTIONS if it's a known spelling diff."
            )

    assert not failures, "TA.md MCP signature audit failed:\n\n" + "\n\n".join(failures)


def test_documented_name_exceptions_are_actually_used() -> None:
    """Every entry in DOCUMENTED_NAME_EXCEPTIONS must apply — the
    documented spelling must appear in TA.md, AND the schema spelling
    must exist in the actual schema. Catches stale exceptions when a
    tool's name resolution changes."""
    register_all()
    mcp_specs = {s.name: s for s in list_registered()}
    ta_sigs = _parse_ta_signatures()

    stale: list[tuple[str, str, str]] = []
    for tool_name, schema_name, doc_spelling in DOCUMENTED_NAME_EXCEPTIONS:
        if tool_name not in mcp_specs:
            stale.append((tool_name, schema_name, doc_spelling))
            continue
        actual_props = set(mcp_specs[tool_name].input_schema.get("properties", {}).keys())
        if schema_name not in actual_props:
            stale.append((tool_name, schema_name, doc_spelling))
            continue
        if tool_name not in ta_sigs or doc_spelling not in ta_sigs[tool_name]:
            stale.append((tool_name, schema_name, doc_spelling))

    assert not stale, (
        f"DOCUMENTED_NAME_EXCEPTIONS entries that no longer apply: "
        f"{sorted(stale)}. Remove them — neither the tool, schema name, "
        "or doc spelling exists anymore."
    )
