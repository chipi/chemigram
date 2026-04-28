"""Smoke test: Phase 0 fixtures are committed and reachable.

Issues #1, #2, #3 all assume these fixtures exist. If a future
refactor moves or renames them, these tests fail loudly here
rather than mysteriously inside parser/synthesizer tests.
"""

from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_dtstyle_fixtures_present() -> None:
    for name in (
        "expo_plus_0p5.dtstyle",
        "expo_plus_0p0.dtstyle",
        "wb_warm_subtle.dtstyle",
    ):
        path = FIXTURES / "dtstyles" / name
        assert path.is_file(), f"missing dtstyle fixture: {path}"


def test_xmp_fixtures_present() -> None:
    path = FIXTURES / "xmps" / "synthesized_v3_reference.xmp"
    assert path.is_file(), f"missing xmp fixture: {path}"


def test_fixtures_readme_present() -> None:
    assert (FIXTURES / "README.md").is_file()
