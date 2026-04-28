"""L1 vocabulary binding via EXIF lookup.

Per **RFC-015 → ADR-053**, takes :class:`~chemigram.core.exif.ExifData`
plus a :class:`VocabularyIndex` lookup and returns L1 entries matching
``(make, model, lens_model)`` **exactly**. No fuzzy matching, no
normalization, no focal-length awareness.

The "exact-match only" rule is intentional. Per **ADR-016**, L1 is
empty by default — the typical case is "no L1 entries match" and
:func:`bind_l1` returns an empty list. Photographers add L1 entries
keyed to their actual gear; fuzzy matching would silently introduce
ambiguity into a photographer-curated, intentionally narrow space.

Public API:
    - :class:`VocabularyIndex` — Protocol the vocabulary system implements
    - :func:`bind_l1` — pure resolution function
"""

from typing import Protocol

from chemigram.core.dtstyle import DtstyleEntry
from chemigram.core.exif import ExifData


class VocabularyIndex(Protocol):
    """Minimal interface :func:`bind_l1` needs from the vocabulary system.

    The full vocabulary index lands in a later issue; this Protocol is
    enough to test :func:`bind_l1` with a fake.
    """

    def lookup_l1(
        self,
        make: str,
        model: str,
        lens_model: str,
    ) -> list[DtstyleEntry]:
        """Return L1 entries that exactly match the camera+lens identity.

        Returns ``[]`` if no entries match. Empty is the expected
        default per ADR-016 (L1 is empty until photographer authors
        entries) — callers must not treat empty as an error.
        """
        ...


def bind_l1(exif: ExifData, vocabulary: VocabularyIndex) -> list[DtstyleEntry]:
    """Resolve L1 entries for a raw's camera+lens identity.

    v1 rule (RFC-015 / ADR-053): exact match on
    ``(exif.make, exif.model, exif.lens_model)``. Returns ``[]`` if no
    entry matches — common case during Phase 1 since the OSS starter
    pack has no L1 entries (ADR-016).

    Pure: no I/O, no mutation. The match logic lives in
    :meth:`VocabularyIndex.lookup_l1`; this function is the
    type-checked binding-call boundary.
    """
    return vocabulary.lookup_l1(exif.make, exif.model, exif.lens_model)
