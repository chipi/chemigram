"""Audit: per-verb param alignment between CLI Typer args and MCP input_schema.

For every (CLI verb, MCP tool) mirror pair, this test asserts that every
parameter the CLI exposes maps to a known counterpart on the MCP side
(or is documented as a CLI-only legitimate extra), and vice versa. The
canonical mapping is captured in :data:`CANONICAL_NAME_MAPPING`,
:data:`CLI_ONLY_PARAMS`, and :data:`MCP_ONLY_PARAMS` below.

Failure modes the test catches:

- A new CLI flag added without updating MCP → CLI surface grows past MCP.
- A new MCP arg added without updating CLI → MCP grows past CLI.
- A CLI flag renamed without updating MCP (and vice versa) → name drift.
- A documented mapping entry pointing at a CLI param that no longer
  exists → stale mapping.

Closes the v1.10.0 audit follow-up where we found that the
``cli-reference`` generator's allowlist had drifted past v1.3.0 without
catching new verbs (apply-spot, apply-per-region, propagate-state,
wb-from-gray-card). Sister to ``test_verb_parity.py`` which audits
verb-level mirror; this audits per-verb param-level mirror.
"""

from __future__ import annotations

import typer
from typer.main import get_command

from chemigram.cli.main import app
from chemigram.mcp.registry import list_registered
from chemigram.mcp.tools import register_all

# ---------------------------------------------------------------------------
# Canonical CLI ↔ MCP name mapping
# ---------------------------------------------------------------------------
# Each entry: (cli_verb, cli_param_name) → mcp_param_name. Only pairs where
# the names *differ* are listed; same-name pairs are auto-accepted.
#
# When adding a new entry: the mapping must be a deliberate ergonomic
# choice with a defensible reason (Python keyword collision, conversational
# vs API naming, repeatable-flag-vs-array shape). If you're adding because
# "they happen to be different," consider whether they SHOULD be the same.
CANONICAL_NAME_MAPPING: dict[tuple[str, str], str] = {
    # `entry` is photographer-vocabulary; `primitive_name` is engine-API
    ("apply-primitive", "entry"): "primitive_name",
    ("apply-per-region", "entry"): "primitive_name",
    # `operation` reads cleaner on the CLI; `module_name` is the field's
    # actual darktable role
    ("remove-module", "operation"): "module_name",
    # Short flag forms for L1/L2 binding templates
    ("bind-layers", "l1"): "l1_template",
    ("bind-layers", "l2"): "l2_template",
    # Python-keyword-collision avoidance (Typer adds the trailing _)
    ("branch", "from_ref"): "from_",
    ("tag", "hash_"): "hash",
    ("export-final", "format_"): "format",
    # Repeatable singular flag (CLI) vs array (MCP) — same intent
    ("propagate-state", "target"): "target_image_ids",
    ("propagate-state", "exclude_op"): "exclude_ops",
    ("vocab list", "tag"): "tags",
    ("vocab list-masks", "tag"): "tags",
}

# CLI params with NO MCP equivalent. Each MUST have a documented reason
# in the comment block above — these aren't accidental gaps but
# deliberate adapter-specific affordances.
CLI_ONLY_PARAMS: set[tuple[str, str]] = {
    # --stdin: batch shape over multiple invocations; doesn't fit MCP's
    # single-call-per-tool surface
    ("apply-primitive", "stdin"),
    ("get-state", "stdin"),
    ("export-final", "stdin"),
    ("render-preview", "stdin"),
    # --param NAME=VALUE: shorthand for the MCP `value` dict shape;
    # CLI offers both --value (scalar) and --param (dict-like via repeated flags)
    ("apply-primitive", "param"),
    # --label: snapshot label override (CLI exposes; MCP synthesizes from kind)
    ("apply-spot", "label"),
    # --pack -p: per-invocation pack loading (CLI loads packs per call;
    # MCP loads packs at server startup, can't reload mid-session)
    ("apply-primitive", "pack"),
    ("ingest", "pack"),
    ("vocab list", "pack"),
    ("vocab list-masks", "pack"),
    ("bind-layers", "pack"),
    # apply-per-region accepts a JSON string on the CLI; MCP accepts the
    # native parsed array. Different wire, same semantic.
    ("apply-per-region", "regions_json"),
    ("apply-per-region", "entry"),  # also mapped above; CLI top-level entry vs MCP primitive_name
    ("apply-per-region", "pack"),
}

# MCP params with NO CLI equivalent. CLI uses globals or different shapes.
MCP_ONLY_PARAMS: set[tuple[str, str]] = {
    # workspace_root: CLI uses the global --workspace flag instead
    ("ingest", "workspace_root"),
    # regions array vs CLI's regions_json string (same semantic; different wire)
    ("apply-per-region", "regions"),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _walk_cli(t: typer.Typer, prefix: str = "") -> dict[str, object]:
    """Return ``{verb_path: click_command}`` for every leaf verb."""
    out: dict[str, object] = {}
    cmd = get_command(t)
    if not hasattr(cmd, "commands"):
        return out
    for name, sub in cmd.commands.items():  # type: ignore[attr-defined]
        full = f"{prefix} {name}".strip()
        if hasattr(sub, "commands") and sub.commands:  # type: ignore[attr-defined]
            for sub_name, sub_cmd in sub.commands.items():  # type: ignore[attr-defined]
                out[f"{full} {sub_name}"] = sub_cmd
        else:
            out[full] = sub
    return out


def _cli_param_names(click_cmd: object) -> set[str]:
    return {p.name for p in click_cmd.params}  # type: ignore[attr-defined]


def _mcp_for_cli(verb: str) -> str | None:
    """Return the MCP tool name mirrored by ``verb``, or ``None`` if
    no MCP mirror (CLI-only verbs like ``status``, ``vocab show``,
    ``gap-log list``, etc)."""
    if verb == "vocab list":
        return "list_vocabulary"
    if verb == "vocab list-masks":
        return "list_masks_vocabulary"
    if " " in verb:
        return None
    return verb.replace("-", "_")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_per_verb_param_alignment_against_canonical_mapping() -> None:
    """Every CLI verb's params either match the MCP tool's
    input_schema names (modulo `_` ↔ `-`), or appear in the
    documented mapping/exception dicts above."""
    cli_commands = _walk_cli(app)
    register_all()
    mcp_specs = {s.name: s for s in list_registered()}

    failures: list[str] = []

    for verb in sorted(cli_commands):
        mcp_name = _mcp_for_cli(verb)
        if mcp_name is None or mcp_name not in mcp_specs:
            continue

        cli_params = _cli_param_names(cli_commands[verb])
        mcp_props = set(mcp_specs[mcp_name].input_schema.get("properties", {}).keys())

        # Apply the canonical mapping: rewrite CLI param names to their MCP-side
        # counterparts where documented.
        mapped_cli = {CANONICAL_NAME_MAPPING.get((verb, p), p) for p in cli_params}

        cli_extra = {p for p in mapped_cli if p not in mcp_props}
        mcp_extra = mcp_props - mapped_cli

        # Filter out documented CLI-only and MCP-only entries
        cli_extra_unaccounted = {
            p
            for p in cli_extra
            # The CLI_ONLY_PARAMS entries are keyed by the ORIGINAL CLI param
            # name (pre-mapping), since that's what an author writes.
            if not any(
                (verb, original) in CLI_ONLY_PARAMS
                for original in cli_params
                if CANONICAL_NAME_MAPPING.get((verb, original), original) == p
            )
            and (verb, p) not in CLI_ONLY_PARAMS
        }
        mcp_extra_unaccounted = {p for p in mcp_extra if (verb, p) not in MCP_ONLY_PARAMS}

        if cli_extra_unaccounted:
            failures.append(
                f"{verb} ←→ {mcp_name}: CLI params with no MCP counterpart "
                f"(and not in CLI_ONLY_PARAMS): {sorted(cli_extra_unaccounted)}. "
                "Add to CANONICAL_NAME_MAPPING with a documented MCP name, "
                "or to CLI_ONLY_PARAMS with a reason."
            )
        if mcp_extra_unaccounted:
            failures.append(
                f"{verb} ←→ {mcp_name}: MCP props with no CLI counterpart "
                f"(and not in MCP_ONLY_PARAMS): {sorted(mcp_extra_unaccounted)}. "
                "Add the flag to the CLI verb so the surface stays aligned, or "
                "add to MCP_ONLY_PARAMS with a reason."
            )

    assert not failures, "Per-verb param alignment audit failed:\n\n" + "\n\n".join(failures)


def test_canonical_mapping_has_no_stale_entries() -> None:
    """Every (verb, cli_param) tuple in CANONICAL_NAME_MAPPING must
    point at a verb + param that actually exists on the live CLI."""
    cli_commands = _walk_cli(app)
    stale: list[tuple[str, str]] = []
    for (verb, cli_param), _mcp_param in CANONICAL_NAME_MAPPING.items():
        if verb not in cli_commands:
            stale.append((verb, cli_param))
            continue
        if cli_param not in _cli_param_names(cli_commands[verb]):
            stale.append((verb, cli_param))

    assert not stale, (
        f"CANONICAL_NAME_MAPPING references CLI verb/param tuples that no "
        f"longer exist on the live CLI: {sorted(stale)}. Remove them from "
        "the mapping."
    )


def test_cli_only_params_has_no_stale_entries() -> None:
    """Every (verb, param) tuple in CLI_ONLY_PARAMS must actually exist."""
    cli_commands = _walk_cli(app)
    stale: list[tuple[str, str]] = []
    for verb, param in CLI_ONLY_PARAMS:
        if verb not in cli_commands:
            stale.append((verb, param))
            continue
        if param not in _cli_param_names(cli_commands[verb]):
            stale.append((verb, param))

    assert not stale, (
        f"CLI_ONLY_PARAMS references CLI verb/param tuples that no longer "
        f"exist on the live CLI: {sorted(stale)}. Remove them."
    )


def test_mcp_only_params_has_no_stale_entries() -> None:
    """Every (verb, param) tuple in MCP_ONLY_PARAMS must actually exist
    on the MCP side."""
    register_all()
    mcp_specs = {s.name: s for s in list_registered()}
    cli_commands = _walk_cli(app)

    stale: list[tuple[str, str]] = []
    for verb, param in MCP_ONLY_PARAMS:
        mcp_name = _mcp_for_cli(verb)
        if mcp_name is None or mcp_name not in mcp_specs:
            stale.append((verb, param))
            continue
        if verb not in cli_commands:
            stale.append((verb, param))
            continue
        props = mcp_specs[mcp_name].input_schema.get("properties", {})
        if param not in props:
            stale.append((verb, param))

    assert not stale, (
        f"MCP_ONLY_PARAMS references MCP tool/param tuples that no longer "
        f"exist: {sorted(stale)}. Remove them."
    )
