"""Unit tests for chemigram.core.binding.bind_l1 + VocabularyIndex Protocol."""

from __future__ import annotations

from chemigram.core.binding import VocabularyIndex, bind_l1
from chemigram.core.dtstyle import DtstyleEntry, PluginEntry
from chemigram.core.exif import ExifData


def _exif(
    make: str = "NIKON CORPORATION",
    model: str = "NIKON D850",
    lens_model: str = "NIKKOR Z 24-70mm f/2.8 S",
) -> ExifData:
    return ExifData(make=make, model=model, lens_model=lens_model, focal_length_mm=70.0)


def _entry(name: str = "lens_correction") -> DtstyleEntry:
    plugin = PluginEntry(
        operation="lens",
        num=0,
        module=1,
        op_params="00",
        blendop_params="gz",
        blendop_version=14,
        multi_priority=0,
        multi_name="",
        enabled=True,
    )
    return DtstyleEntry(name=name, description="", iop_list=None, plugins=(plugin,))


class _FakeVocab:
    """Test double for VocabularyIndex."""

    def __init__(
        self,
        l1_map: dict[tuple[str, str, str], list[DtstyleEntry]] | None = None,
    ) -> None:
        self.l1_map = l1_map or {}
        self.calls: list[tuple[str, str, str]] = []

    def lookup_l1(self, make: str, model: str, lens_model: str) -> list[DtstyleEntry]:
        key = (make, model, lens_model)
        self.calls.append(key)
        return self.l1_map.get(key, [])


def test_bind_l1_exact_match() -> None:
    entry = _entry("nikkor_z_2470")
    vocab = _FakeVocab({("NIKON CORPORATION", "NIKON D850", "NIKKOR Z 24-70mm f/2.8 S"): [entry]})
    result = bind_l1(_exif(), vocab)
    assert result == [entry]


def test_bind_l1_no_match_returns_empty_list() -> None:
    vocab = _FakeVocab()  # empty map
    result = bind_l1(_exif(), vocab)
    assert result == []
    assert isinstance(result, list)  # not None, not error


def test_bind_l1_no_fuzzy_matching_case_sensitive() -> None:
    """RFC-015 / ADR-053: exact match only. Different case → no match."""
    vocab = _FakeVocab(
        {("nikon corporation", "nikon d850", "nikkor z 24-70mm f/2.8 s"): [_entry()]}
    )
    # ExifData has the all-caps form; lowercase key in vocab won't match
    result = bind_l1(_exif(), vocab)
    assert result == []


def test_bind_l1_passes_strings_unchanged() -> None:
    """bind_l1 forwards the EXIF fields verbatim to lookup_l1."""
    vocab = _FakeVocab()
    bind_l1(_exif(make="X", model="Y", lens_model="Z"), vocab)
    assert vocab.calls == [("X", "Y", "Z")]


def test_bind_l1_empty_lens_passes_through() -> None:
    """Manual lenses produce empty lens_model. bind_l1 forwards as-is."""
    vocab = _FakeVocab({("LEICA CAMERA AG", "Q3", ""): [_entry("leica_q3_l1")]})
    result = bind_l1(_exif(make="LEICA CAMERA AG", model="Q3", lens_model=""), vocab)
    assert len(result) == 1


def test_vocabulary_index_protocol_structural() -> None:
    """_FakeVocab implements VocabularyIndex via structural typing."""
    vocab: VocabularyIndex = _FakeVocab()
    assert vocab.lookup_l1("X", "Y", "Z") == []
