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
        "expo_plus_1p0.dtstyle",
        "expo_minus_0p5.dtstyle",
        "wb_warm_subtle.dtstyle",
        "multi_module_synthetic.dtstyle",
        "malformed_no_plugin.dtstyle",
        "malformed_xml.dtstyle",
        "with_builtin_filtered.dtstyle",
        "all_builtin_no_user.dtstyle",
    ):
        path = FIXTURES / "dtstyles" / name
        assert path.is_file(), f"missing dtstyle fixture: {path}"


def test_xmp_fixtures_present() -> None:
    for name in (
        "synthesized_v3_reference.xmp",
        "minimal.xmp",
        "single_history.xmp",
        "with_unknown_field.xmp",
    ):
        path = FIXTURES / "xmps" / name
        assert path.is_file(), f"missing xmp fixture: {path}"


def test_fixtures_readme_present() -> None:
    assert (FIXTURES / "README.md").is_file()
