"""Parse darktable .dtstyle files.

A .dtstyle is darktable's style export format: XML containing one or more
single-module configurations. Calibrated to darktable 5.4.1 (see
``tests/fixtures/README.md`` and ``docs/adr/TA.md`` ``contracts/dtstyle-schema``).

Binary parameters (``op_params``, ``blendop_params``) are opaque blobs
(ADR-008). They are never decoded — they pass through verbatim as strings.

XML parsing uses ``defusedxml`` for safety against malicious or malformed
input. (Adopted as a defensive default; not pinned to an ADR.)

Public API:
    - :func:`parse_dtstyle` — parse a file from disk
    - :class:`DtstyleEntry`, :class:`PluginEntry` — frozen dataclasses
    - :class:`DtstyleParseError` — raised on malformed input
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from defusedxml import ElementTree


class DtstyleParseError(Exception):
    """Raised when a .dtstyle file cannot be parsed."""


@dataclass(frozen=True)
class PluginEntry:
    """One ``<plugin>`` element from a .dtstyle file.

    Calibrated to darktable 5.4.1. Binary blobs (``op_params``,
    ``blendop_params``) are kept as strings and NEVER decoded (ADR-008).
    """

    operation: str
    num: int
    module: int
    op_params: str
    blendop_params: str
    blendop_version: int
    multi_priority: int
    multi_name: str
    enabled: bool


@dataclass(frozen=True)
class DtstyleEntry:
    """A parsed .dtstyle file."""

    name: str
    description: str
    iop_list: str | None
    plugins: tuple[PluginEntry, ...]


def _require_text(elem: Any, tag: str, path: Path) -> str:
    child = elem.find(tag)
    if child is None or child.text is None:
        raise DtstyleParseError(f"{path}: missing required element <{tag}>")
    return str(child.text).strip()


def _optional_text(elem: Any, tag: str) -> str | None:
    child = elem.find(tag)
    if child is None or child.text is None:
        return None
    return str(child.text).strip()


def _parse_int(s: str, field: str, path: Path) -> int:
    try:
        return int(s)
    except ValueError as exc:
        raise DtstyleParseError(f"{path}: <{field}> not an integer: {s!r}") from exc


def _parse_enabled(s: str, path: Path) -> bool:
    if s == "1":
        return True
    if s == "0":
        return False
    raise DtstyleParseError(f"{path}: <enabled> must be '0' or '1', got {s!r}")


def _opaque_blob(elem: Any, tag: str, path: Path) -> str:
    """Extract opaque hex/base64 blob without stripping or decoding (ADR-008)."""
    child = elem.find(tag)
    if child is None or child.text is None:
        raise DtstyleParseError(f"{path}: missing required element <{tag}>")
    text = str(child.text)
    if not text.strip():
        raise DtstyleParseError(f"{path}: <{tag}> is empty or whitespace-only")
    return text


def _parse_plugin(plugin: Any, path: Path) -> PluginEntry:
    operation = _require_text(plugin, "operation", path)
    num = _parse_int(_require_text(plugin, "num", path), "num", path)
    module = _parse_int(_require_text(plugin, "module", path), "module", path)
    op_params = _opaque_blob(plugin, "op_params", path)
    blendop_params = _opaque_blob(plugin, "blendop_params", path)
    blendop_version = _parse_int(
        _require_text(plugin, "blendop_version", path),
        "blendop_version",
        path,
    )
    multi_priority = _parse_int(
        _require_text(plugin, "multi_priority", path),
        "multi_priority",
        path,
    )

    # multi_name is the special case: per ADR-010, user-authored entries
    # have <multi_name></multi_name> (empty text) — that's the identity
    # marker. ElementTree returns text=None for elements with no content,
    # so the `or ""` is required and semantically correct (empty user
    # entry vs. absent element). All other plugin fields use
    # `_require_text` and raise on absence; this field requires the
    # element but allows empty text.
    multi_name_elem = plugin.find("multi_name")
    if multi_name_elem is None:
        raise DtstyleParseError(f"{path}: missing required element <multi_name>")
    multi_name = multi_name_elem.text or ""

    enabled = _parse_enabled(
        _require_text(plugin, "enabled", path),
        path,
    )

    return PluginEntry(
        operation=operation,
        num=num,
        module=module,
        op_params=op_params,
        blendop_params=blendop_params,
        blendop_version=blendop_version,
        multi_priority=multi_priority,
        multi_name=multi_name,
        enabled=enabled,
    )


def parse_dtstyle(path: Path) -> DtstyleEntry:
    """Parse a .dtstyle file from disk.

    Args:
        path: Path to a .dtstyle file.

    Returns:
        A :class:`DtstyleEntry` capturing the file's contents. Plugins
        are returned as a tuple in document order.

    Raises:
        DtstyleParseError: malformed XML; missing required elements
            (e.g., no ``<plugin>`` inside ``<style>``); missing required
            child elements within a ``<plugin>``; ``<enabled>`` not 0/1.
        FileNotFoundError: ``path`` does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(path)

    try:
        tree = ElementTree.parse(path)
    except ElementTree.ParseError as exc:
        raise DtstyleParseError(f"{path}: malformed XML: {exc}") from exc

    root = tree.getroot()
    if root.tag != "darktable_style":
        raise DtstyleParseError(f"{path}: root element must be <darktable_style>, got <{root.tag}>")

    info = root.find("info")
    if info is None:
        raise DtstyleParseError(f"{path}: missing <info>")

    name = _require_text(info, "name", path)
    description = _optional_text(info, "description") or ""
    iop_list = _optional_text(info, "iop_list")

    style = root.find("style")
    if style is None:
        raise DtstyleParseError(f"{path}: missing <style>")

    plugin_elems = style.findall("plugin")
    if not plugin_elems:
        raise DtstyleParseError(f"{path}: <style> must contain at least one <plugin>")

    # Parse all plugins, then filter out darktable's auto-applied entries
    # (multi_name prefixed "_builtin_") per ADR-010. Phase 0 working
    # notebook recommends this safety-net filter to protect against
    # contributor authoring errors (the "first attempt" failure mode where
    # a contaminated dtstyle exports the full default pipeline).
    plugins_all = tuple(_parse_plugin(p, path) for p in plugin_elems)
    plugins = tuple(p for p in plugins_all if not p.multi_name.startswith("_builtin_"))

    if not plugins:
        filtered = len(plugins_all)
        raise DtstyleParseError(
            f"{path}: no user-authored <plugin> entries "
            f"(filtered {filtered} _builtin_* entries; per ADR-010, user "
            "entries are identified by empty <multi_name>)"
        )

    return DtstyleEntry(
        name=name,
        description=description,
        iop_list=iop_list,
        plugins=plugins,
    )
