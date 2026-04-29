"""Deterministic byte form of darktable XMPs for content addressing.

Every snapshot in the versioning subsystem is keyed by
``xmp_hash(xmp) = sha256(canonical_bytes(xmp))``. The hash must be
stable across:

- The same :class:`~chemigram.core.xmp.Xmp` instance hashed twice in
  one process (trivially)
- The same logical edit state constructed via different code paths
- Round-trips: ``canonical_bytes(parse_xmp(write_canonical(x)))`` equals
  ``canonical_bytes(x)``
- Different Python interpreter runs (CPython 3.11 / 3.12 / 3.13)

Determinism rules (anchored by RFC-002 → ADR-054):

- Namespace prefix map is fixed (matches ``chemigram.core.xmp._NS``)
- Attributes on ``<rdf:Description>`` emitted in a fixed order:
  ``rdf:about`` first, then ``raw_extra_fields`` attrs in stored order,
  then first-class attrs (``xmp:Rating``, ``xmp:Label`` if non-empty,
  ``darktable:auto_presets_applied``, ``darktable:history_end``,
  ``darktable:iop_order_version``)
- Each ``<rdf:li>`` history entry's attributes emitted in
  :class:`~chemigram.core.xmp.HistoryEntry` field declaration order
- ``raw_extra_fields`` elem entries (already fixed-point normalized at
  parse time) are emitted verbatim
- UTF-8 encoding, LF line endings, no BOM, indented 1 space per level

This module reaches into ``chemigram.core.xmp``'s underscore-prefixed
namespace map and helpers. The two modules are tightly coupled by
design (both speak darktable's XMP shape); promoting the helpers to a
public surface would expose XML internals callers shouldn't depend on.
"""

import hashlib
import xml.etree.ElementTree as ET

from defusedxml.ElementTree import fromstring as _defused_fromstring

from chemigram.core.xmp import (
    _NS,
    HistoryEntry,
    Xmp,
    _clark,
    _qname_to_clark,
)


def _bool_to_str(value: bool) -> str:
    return "1" if value else "0"


def _history_entry_attrs(entry: HistoryEntry) -> dict[str, str]:
    """Build the ``<rdf:li>`` attribute dict in declaration order."""
    attrs: dict[str, str] = {}
    attrs[_clark("darktable", "num")] = str(entry.num)
    attrs[_clark("darktable", "operation")] = entry.operation
    attrs[_clark("darktable", "enabled")] = _bool_to_str(entry.enabled)
    attrs[_clark("darktable", "modversion")] = str(entry.modversion)
    attrs[_clark("darktable", "params")] = entry.params
    attrs[_clark("darktable", "multi_name")] = entry.multi_name
    attrs[_clark("darktable", "multi_name_hand_edited")] = _bool_to_str(
        entry.multi_name_hand_edited
    )
    attrs[_clark("darktable", "multi_priority")] = str(entry.multi_priority)
    attrs[_clark("darktable", "blendop_version")] = str(entry.blendop_version)
    attrs[_clark("darktable", "blendop_params")] = entry.blendop_params
    if entry.iop_order is not None:
        attrs[_clark("darktable", "iop_order")] = str(entry.iop_order)
    return attrs


def _build_tree(xmp: Xmp) -> ET.Element:
    xmpmeta = ET.Element(_clark("x", "xmpmeta"))
    xmpmeta.set(_clark("x", "xmptk"), "XMP Core 4.4.0-Exiv2")
    rdf = ET.SubElement(xmpmeta, _clark("rdf", "RDF"))
    desc = ET.SubElement(rdf, _clark("rdf", "Description"))
    desc.set(_clark("rdf", "about"), "")

    # raw_extra_fields attrs in stored order
    for kind, qname, value in xmp.raw_extra_fields:
        if kind == "attr":
            desc.set(_qname_to_clark(qname), value)

    # First-class attrs in fixed declaration order
    desc.set(_clark("xmp", "Rating"), str(xmp.rating))
    if xmp.label:
        desc.set(_clark("xmp", "Label"), xmp.label)
    desc.set(
        _clark("darktable", "auto_presets_applied"),
        _bool_to_str(xmp.auto_presets_applied),
    )
    desc.set(_clark("darktable", "history_end"), str(xmp.history_end))
    desc.set(_clark("darktable", "iop_order_version"), str(xmp.iop_order_version))

    # raw_extra_fields elem children in stored order (already fixed-point
    # normalized at parse time so re-serialization is stable)
    for kind, _qname, value in xmp.raw_extra_fields:
        if kind == "elem":
            child = _defused_fromstring(value)
            desc.append(child)

    # History as <darktable:history><rdf:Seq><rdf:li/>... </rdf:Seq></darktable:history>
    if xmp.history:
        history_elem = ET.SubElement(desc, _clark("darktable", "history"))
        seq = ET.SubElement(history_elem, _clark("rdf", "Seq"))
        for entry in xmp.history:
            ET.SubElement(seq, _clark("rdf", "li"), _history_entry_attrs(entry))

    return xmpmeta


def canonical_bytes(xmp: Xmp) -> bytes:
    """Return the deterministic byte form of an :class:`Xmp`.

    The output is a complete, valid XMP document. Use :func:`xmp_hash`
    for the SHA-256 hex digest used as the content-address key.
    """
    # Ensure namespace registrations are in place. xmp.py registers them
    # at module import; this is a defensive re-call that's idempotent.
    for prefix, uri in _NS.items():
        ET.register_namespace(prefix, uri)

    root = _build_tree(xmp)
    tree = ET.ElementTree(root)
    ET.indent(tree, space=" ", level=0)

    # Serialize without xml_declaration so we control the prologue exactly
    body = ET.tostring(root, encoding="unicode")

    # Normalize: strip BOM if any, force LF line endings
    if body.startswith("\ufeff"):
        body = body[1:]
    body = body.replace("\r\n", "\n").replace("\r", "\n")

    full = '<?xml version="1.0" encoding="UTF-8"?>\n' + body
    if not full.endswith("\n"):
        full += "\n"
    return full.encode("utf-8")


def xmp_hash(xmp: Xmp) -> str:
    """SHA-256 hex digest of :func:`canonical_bytes` (lowercase, 64 chars)."""
    return hashlib.sha256(canonical_bytes(xmp)).hexdigest()
