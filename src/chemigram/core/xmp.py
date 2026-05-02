"""Parse and write darktable XMP sidecar files.

XMP is darktable's per-image edit state format: RDF/XML with a
``<rdf:Seq>`` of history entries (per-module configurations).
Calibrated to darktable 5.4.1 (see ``tests/fixtures/README.md`` and
``docs/adr/TA.md`` ``contracts/xmp-darktable-history``).

Binary blobs (``params``, ``blendop_params``) are opaque (ADR-008) and
are never decoded. ``defusedxml`` is used for parsing untrusted input;
output uses the standard library's ElementTree (which we control).

Round-trip property: ``parse_xmp(write_xmp(x, p)) == x`` for any
well-formed Xmp ``x`` (semantic equality of the dataclass, not byte
identity of the file).

Public API:
    - :func:`parse_xmp`, :func:`write_xmp`
    - :class:`Xmp`, :class:`HistoryEntry` — frozen dataclasses
    - :class:`XmpParseError` — exception raised on malformed input
"""

import dataclasses
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from defusedxml.ElementTree import (
    ParseError as _DefusedParseError,
)
from defusedxml.ElementTree import (
    fromstring as _defused_fromstring,
)
from defusedxml.ElementTree import (
    parse as _defused_parse,
)

from chemigram.core.dtstyle import DtstyleEntry, PluginEntry

# Conventional namespace prefixes and their URIs. darktable XMP files
# declare them on <rdf:Description>; we use the same set on write so
# the output is recognizable to humans reading diffs.
_NS: dict[str, str] = {
    "x": "adobe:ns:meta/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "exif": "http://ns.adobe.com/exif/1.0/",
    "xmp": "http://ns.adobe.com/xap/1.0/",
    "xmpMM": "http://ns.adobe.com/xap/1.0/mm/",
    "darktable": "http://darktable.sf.net/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "lr": "http://ns.adobe.com/lightroom/1.0/",
}
_URI_TO_PREFIX: dict[str, str] = {uri: prefix for prefix, uri in _NS.items()}

# Register namespaces with ElementTree so output uses our prefixes.
for _prefix, _uri in _NS.items():
    ET.register_namespace(_prefix, _uri)


class XmpParseError(Exception):
    """Raised when an XMP file cannot be parsed."""


@dataclass(frozen=True)
class HistoryEntry:
    """One ``<rdf:li>`` entry in a darktable XMP ``<rdf:Seq>``.

    Calibrated to darktable 5.4.1. ``params`` and ``blendop_params``
    are opaque blobs (ADR-008) and are never decoded.

    ``iop_order`` is ``None`` in 5.4.1 ``.dtstyle`` files and is unnecessary
    for Path B (per RFC-018 v0.2 empirical evidence). darktable resolves
    pipeline order from the parent's ``darktable:iop_order_version`` + an
    internal iop_list. The field stays Optional + ``float`` because rendered
    XMP sidecars *can* carry per-entry iop_order as a float (e.g.
    ``47.4747``); the parser must round-trip those.
    """

    num: int
    operation: str
    enabled: bool
    modversion: int
    params: str
    multi_name: str
    multi_name_hand_edited: bool
    multi_priority: int
    blendop_version: int
    blendop_params: str
    iop_order: float | None = None


@dataclass(frozen=True)
class Xmp:
    """A parsed darktable XMP file.

    First-class fields are those the synthesizer (Issue #3) reads or
    writes. Everything else on ``<rdf:Description>`` (timestamps, hashes,
    creator metadata, ``masks_history``, etc.) is preserved opaquely in
    ``raw_extra_fields`` for round-trip fidelity.

    ``raw_extra_fields`` entries are 3-tuples ``(kind, qname, value)``:

    - ``kind == "attr"``: an attribute on ``<rdf:Description>``. ``qname``
      is the prefixed name (e.g. ``"darktable:xmp_version"``); ``value``
      is the raw attribute string.
    - ``kind == "elem"``: a child element of ``<rdf:Description>``.
      ``qname`` is the prefixed element name; ``value`` is the entire
      subtree serialized as XML text.
    """

    rating: int
    label: str
    auto_presets_applied: bool
    history_end: int
    iop_order_version: int
    history: tuple[HistoryEntry, ...]
    raw_extra_fields: tuple[tuple[str, str, str], ...] = ()


def _clark(prefix: str, name: str) -> str:
    return f"{{{_NS[prefix]}}}{name}"


def _split_clark(clark_or_name: str) -> tuple[str | None, str]:
    if clark_or_name.startswith("{"):
        uri, name = clark_or_name[1:].split("}", 1)
        return _URI_TO_PREFIX.get(uri), name
    return None, clark_or_name


def _qname_str(clark_or_name: str) -> str:
    prefix, name = _split_clark(clark_or_name)
    return f"{prefix}:{name}" if prefix else name


def _qname_to_clark(qname: str) -> str:
    if ":" in qname:
        prefix, name = qname.split(":", 1)
        if prefix in _NS:
            return _clark(prefix, name)
    return qname


def _bool_attr(s: str, qname: str, path: Path) -> bool:
    if s == "1":
        return True
    if s == "0":
        return False
    raise XmpParseError(f"{path}: {qname} must be '0' or '1', got {s!r}")


def _int_attr(s: str, qname: str, path: Path) -> int:
    try:
        return int(s)
    except ValueError as exc:
        raise XmpParseError(f"{path}: {qname} not an integer: {s!r}") from exc


def _float_attr(s: str, qname: str, path: Path) -> float:
    try:
        return float(s)
    except ValueError as exc:
        raise XmpParseError(f"{path}: {qname} not a float: {s!r}") from exc


def _parse_history_entry(li: Any, path: Path) -> HistoryEntry:
    attrs: dict[str, str] = {}
    for clark_key, value in li.attrib.items():
        prefix, name = _split_clark(clark_key)
        if prefix == "darktable":
            attrs[name] = value

    def required(name: str) -> str:
        if name not in attrs:
            raise XmpParseError(f"{path}: <rdf:li> missing required darktable:{name}")
        return attrs[name]

    iop_order_raw = attrs.get("iop_order")
    iop_order = (
        _float_attr(iop_order_raw, "darktable:iop_order", path)
        if iop_order_raw is not None
        else None
    )

    return HistoryEntry(
        num=_int_attr(required("num"), "darktable:num", path),
        operation=required("operation"),
        enabled=_bool_attr(required("enabled"), "darktable:enabled", path),
        modversion=_int_attr(required("modversion"), "darktable:modversion", path),
        params=required("params"),
        multi_name=attrs.get("multi_name", ""),
        multi_name_hand_edited=_bool_attr(
            attrs.get("multi_name_hand_edited", "0"),
            "darktable:multi_name_hand_edited",
            path,
        ),
        multi_priority=_int_attr(required("multi_priority"), "darktable:multi_priority", path),
        blendop_version=_int_attr(required("blendop_version"), "darktable:blendop_version", path),
        blendop_params=required("blendop_params"),
        iop_order=iop_order,
    )


def _parse_description_attrs(
    description: Any, path: Path
) -> tuple[int, str, bool, int, int, list[tuple[str, str, str]]]:
    rating = 0
    label = ""
    auto_presets_applied = False
    history_end = 0
    iop_order_version = 0
    extra_attrs: list[tuple[str, str, str]] = []

    for clark_key, value in description.attrib.items():
        prefix, name = _split_clark(clark_key)
        qname = _qname_str(clark_key)
        if prefix == "rdf" and name == "about":
            continue
        if prefix == "xmp" and name == "Rating":
            rating = _int_attr(value, qname, path)
        elif prefix == "xmp" and name == "Label":
            label = value.strip()
        elif prefix == "darktable" and name == "auto_presets_applied":
            auto_presets_applied = _bool_attr(value, qname, path)
        elif prefix == "darktable" and name == "history_end":
            history_end = _int_attr(value, qname, path)
        elif prefix == "darktable" and name == "iop_order_version":
            iop_order_version = _int_attr(value, qname, path)
        else:
            extra_attrs.append(("attr", qname, value))

    return (
        rating,
        label,
        auto_presets_applied,
        history_end,
        iop_order_version,
        extra_attrs,
    )


def _parse_description_children(
    description: Any, path: Path
) -> tuple[list[HistoryEntry], list[tuple[str, str, str]]]:
    history: list[HistoryEntry] = []
    extra_elems: list[tuple[str, str, str]] = []
    for child in description:
        prefix, name = _split_clark(child.tag)
        if prefix == "darktable" and name == "history":
            seq = child.find(f"{{{_NS['rdf']}}}Seq")
            if seq is not None:
                for li in seq.findall(f"{{{_NS['rdf']}}}li"):
                    history.append(_parse_history_entry(li, path))
        else:
            # Fixed-point normalization: ET serializes namespaces using
            # registered prefixes, but the *first* tostring on a parsed
            # subtree may differ from a subsequent re-serialization. Run
            # one parse+serialize cycle on capture so the stored string
            # is a stable fixed point under round-trip.
            raw = ET.tostring(child, encoding="unicode")
            normalized = ET.tostring(_defused_fromstring(raw), encoding="unicode")
            extra_elems.append(("elem", _qname_str(child.tag), normalized))
    return history, extra_elems


def _parse_description_to_xmp(description: Any, source: Path) -> Xmp:
    """Common post-find logic shared by :func:`parse_xmp` and
    :func:`parse_xmp_from_bytes`. ``source`` is used only for error
    message formatting; for the from-bytes path it's a synthetic
    ``Path("<bytes>")`` or similar caller-supplied label.
    """
    (
        rating,
        label,
        auto_presets_applied,
        history_end,
        iop_order_version,
        extra_attrs,
    ) = _parse_description_attrs(description, source)
    history, extra_elems = _parse_description_children(description, source)

    # Validate: history_end is the count of *applied* entries; can be
    # less than len(history) (entries beyond are pending/disabled), but
    # exceeding the actual history length is malformed.
    if history_end > len(history):
        raise XmpParseError(
            f"{source}: darktable:history_end={history_end} exceeds actual "
            f"history length ({len(history)} entries)"
        )

    return Xmp(
        rating=rating,
        label=label,
        auto_presets_applied=auto_presets_applied,
        history_end=history_end,
        iop_order_version=iop_order_version,
        history=tuple(history),
        raw_extra_fields=tuple(extra_attrs + extra_elems),
    )


def parse_xmp(path: Path) -> Xmp:
    """Parse a darktable XMP sidecar file.

    Args:
        path: Path to an XMP file.

    Returns:
        An :class:`Xmp` capturing the file's first-class fields and any
        unmodeled attributes / nested elements via ``raw_extra_fields``.

    Raises:
        XmpParseError: malformed XML; missing ``<rdf:Description>``;
            invalid attribute values (e.g., non-integer ``history_end``).
        FileNotFoundError: ``path`` does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(path)

    try:
        tree = _defused_parse(path)
    except _DefusedParseError as exc:
        raise XmpParseError(f"{path}: malformed XML: {exc}") from exc

    root = tree.getroot()
    description = root.find(f".//{{{_NS['rdf']}}}Description")
    if description is None:
        raise XmpParseError(f"{path}: missing rdf:Description")

    return _parse_description_to_xmp(description, path)


def parse_xmp_from_bytes(data: bytes, *, source: str = "<bytes>") -> Xmp:
    """Parse an XMP from in-memory bytes.

    Counterpart to :func:`parse_xmp` that avoids a filesystem
    round-trip. Useful when the bytes already live in memory — e.g.,
    content-addressed reads from
    :class:`~chemigram.core.versioning.repo.ImageRepo`.

    Args:
        data: UTF-8 encoded XMP bytes.
        source: Human-readable label used in error messages (e.g.,
            ``"sha256:abc..."`` for content-addressed reads). Defaults
            to ``"<bytes>"``.

    Returns:
        An :class:`Xmp`.

    Raises:
        XmpParseError: malformed XML, invalid UTF-8, or missing
            ``<rdf:Description>``.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise XmpParseError(f"{source}: not valid UTF-8: {exc}") from exc

    try:
        root = _defused_fromstring(text)
    except _DefusedParseError as exc:
        raise XmpParseError(f"{source}: malformed XML: {exc}") from exc

    description = root.find(f".//{{{_NS['rdf']}}}Description")
    if description is None:
        raise XmpParseError(f"{source}: missing rdf:Description")

    return _parse_description_to_xmp(description, Path(source))


def _history_entry_attrs(entry: HistoryEntry) -> dict[str, str]:
    attrs: dict[str, str] = {
        _clark("darktable", "num"): str(entry.num),
        _clark("darktable", "operation"): entry.operation,
        _clark("darktable", "enabled"): "1" if entry.enabled else "0",
        _clark("darktable", "modversion"): str(entry.modversion),
        _clark("darktable", "params"): entry.params,
        _clark("darktable", "multi_name"): entry.multi_name,
        _clark("darktable", "multi_name_hand_edited"): (
            "1" if entry.multi_name_hand_edited else "0"
        ),
        _clark("darktable", "multi_priority"): str(entry.multi_priority),
        _clark("darktable", "blendop_version"): str(entry.blendop_version),
        _clark("darktable", "blendop_params"): entry.blendop_params,
    }
    if entry.iop_order is not None:
        attrs[_clark("darktable", "iop_order")] = str(entry.iop_order)
    return attrs


def write_xmp(xmp: Xmp, path: Path) -> None:
    """Serialize an :class:`Xmp` back to an XMP file.

    Round-trip property (semantic equality):
        parse_xmp(write_xmp(x, p)) == x

    Field ordering on output: ``raw_extra_fields`` attributes come
    first (in their stored order), then first-class fields (rating,
    label if non-empty, auto_presets_applied, history_end,
    iop_order_version), then ``raw_extra_fields`` child elements,
    then the synthesized ``<darktable:history>`` if non-empty.

    Args:
        xmp: The :class:`Xmp` to serialize.
        path: Destination path. Parent directory must exist; file is
            overwritten if present.
    """
    xmpmeta = ET.Element(_clark("x", "xmpmeta"))
    xmpmeta.set(_clark("x", "xmptk"), "XMP Core 4.4.0-Exiv2")
    rdf = ET.SubElement(xmpmeta, _clark("rdf", "RDF"))
    desc = ET.SubElement(rdf, _clark("rdf", "Description"))
    desc.set(_clark("rdf", "about"), "")

    for kind, qname, value in xmp.raw_extra_fields:
        if kind == "attr":
            desc.set(_qname_to_clark(qname), value)

    desc.set(_clark("xmp", "Rating"), str(xmp.rating))
    if xmp.label:
        desc.set(_clark("xmp", "Label"), xmp.label)
    desc.set(
        _clark("darktable", "auto_presets_applied"),
        "1" if xmp.auto_presets_applied else "0",
    )
    desc.set(_clark("darktable", "history_end"), str(xmp.history_end))
    desc.set(_clark("darktable", "iop_order_version"), str(xmp.iop_order_version))

    for kind, _qname, value in xmp.raw_extra_fields:
        if kind == "elem":
            child = _defused_fromstring(value)
            desc.append(child)

    if xmp.history:
        history_elem = ET.SubElement(desc, _clark("darktable", "history"))
        seq = ET.SubElement(history_elem, _clark("rdf", "Seq"))
        for entry in xmp.history:
            ET.SubElement(seq, _clark("rdf", "li"), _history_entry_attrs(entry))

    tree = ET.ElementTree(xmpmeta)
    ET.indent(tree, space=" ", level=0)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def _plugin_to_history(plugin: PluginEntry) -> HistoryEntry:
    """Convert a .dtstyle :class:`PluginEntry` into XMP :class:`HistoryEntry` shape.

    Field mapping (dtstyle XML → XMP `<rdf:li>`):

    - ``plugin.module`` → ``history.modversion``  (XML element renamed)
    - ``plugin.op_params`` → ``history.params``   (XML element renamed)
    - direct copies: ``num``, ``operation``, ``enabled``, ``multi_name``,
      ``multi_priority``, ``blendop_version``, ``blendop_params``
    - defaults: ``multi_name_hand_edited=False`` (not modeled in PluginEntry;
      Phase 0 fixtures uniformly have ``<multi_name_hand_edited>0</...>``)
    - ``iop_order=None`` (absent from dt 5.4.1; SET-replace inherits the
      baseline's slot in :func:`synthesize_xmp`)
    """
    return HistoryEntry(
        num=plugin.num,
        operation=plugin.operation,
        enabled=plugin.enabled,
        modversion=plugin.module,
        params=plugin.op_params,
        multi_name=plugin.multi_name,
        multi_name_hand_edited=False,
        multi_priority=plugin.multi_priority,
        blendop_version=plugin.blendop_version,
        blendop_params=plugin.blendop_params,
        iop_order=None,
    )


def synthesize_xmp(baseline: Xmp, entries: list[DtstyleEntry]) -> Xmp:
    """Compose vocabulary entries onto a baseline XMP (Path A only).

    SET semantics (ADR-002, RFC-006 closure / ADR-051): a plugin entry
    whose ``(operation, multi_priority)`` tuple matches a baseline
    history entry REPLACES that entry in place. ``num`` and
    ``iop_order`` are preserved from the baseline slot — Phase 0 finding:
    SET-replace inherits position implicitly because darktable computes
    pipeline ordering from the parent ``iop_order_version`` and an
    internal iop_list, not per-``<rdf:li>`` metadata.

    Path B (new-instance addition at a previously-unused
    ``(operation, multi_priority)``) appends a fresh ``HistoryEntry``
    at ``num = max(existing) + 1`` with ``iop_order=None``. Per
    RFC-018 v0.2's empirical evidence
    (``tests/fixtures/preflight-evidence/``), darktable 5.4.1 resolves
    pipeline order from the description-level ``iop_order_version`` +
    internal iop_list, so per-entry ``iop_order`` is unnecessary.
    ``history_end`` increments to match. Closes RFC-001's iop_order
    open question (deferred under ADR-051) and supersedes that ADR's
    NotImplementedError stance.

    Among multiple input plugins targeting the same
    ``(operation, multi_priority)``, the last one wins (input order).
    This deviates from RFC-006's original "synthesizer error" proposal;
    the closing ADR-051 captures the rationale.

    Args:
        baseline: starting :class:`Xmp`; not mutated.
        entries: vocabulary entries; order matters for last-writer-wins
            among entries that share ``(operation, multi_priority)``.

    Returns:
        A new frozen :class:`Xmp` with synthesized history. Top-level
        metadata (``rating``, ``label``, ``auto_presets_applied``,
        ``iop_order_version``, ``raw_extra_fields``) is preserved
        verbatim. ``history_end`` is recomputed as ``len(history)``
        — typically equal to the baseline value for Path A, larger
        for Path B.
    """
    current: list[HistoryEntry] = list(baseline.history)

    for entry in entries:
        for plugin in entry.plugins:
            target_idx: int | None = None
            for i, existing in enumerate(current):
                if (
                    existing.operation == plugin.operation
                    and existing.multi_priority == plugin.multi_priority
                ):
                    target_idx = i
                    break

            if target_idx is None:
                # Path B — new-instance addition. Per RFC-018 v0.2's
                # empirical evidence (tests/fixtures/preflight-evidence/),
                # darktable 5.4.1 resolves pipeline order from the
                # description-level iop_order_version + internal iop_list,
                # so per-entry iop_order stays None. Append a fresh
                # HistoryEntry at num = max(existing) + 1.
                new_num = max((e.num for e in current), default=-1) + 1
                appended = dataclasses.replace(
                    _plugin_to_history(plugin),
                    num=new_num,
                    iop_order=None,
                )
                current.append(appended)
                continue

            replacement = dataclasses.replace(
                _plugin_to_history(plugin),
                num=current[target_idx].num,
                iop_order=current[target_idx].iop_order,
            )
            current[target_idx] = replacement

    return dataclasses.replace(
        baseline,
        history=tuple(current),
        history_end=len(current),
    )
