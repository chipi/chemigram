"""Smoke tests: the package layout is sound and imports work.

These exist from Slice 1 prep onward as a permanent canary — if a
refactor breaks the package layout (renames, missing __init__,
broken pyproject.toml), these are the first tests to fail.
"""


def test_chemigram_imports() -> None:
    import chemigram  # noqa: F401


def test_chemigram_core_imports() -> None:
    import chemigram.core  # noqa: F401


def test_chemigram_mcp_imports() -> None:
    import chemigram.mcp  # noqa: F401
