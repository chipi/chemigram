"""Unit tests for ``discover_workspace_from_cwd`` (B4 / RFC-020 §Q3)."""

from __future__ import annotations

from pathlib import Path

from chemigram.cli._workspace import discover_workspace_from_cwd


def _make_image_root(parent: Path, image_id: str) -> Path:
    image_root = parent / image_id
    (image_root / "objects").mkdir(parents=True)
    (image_root / "raw").mkdir()
    return image_root


def test_discover_at_image_root(tmp_path: Path) -> None:
    image_root = _make_image_root(tmp_path / "Pictures" / "Chemigram", "iguana")
    result = discover_workspace_from_cwd(image_root)
    assert result == (image_root.parent, "iguana")


def test_discover_in_subdirectory(tmp_path: Path) -> None:
    image_root = _make_image_root(tmp_path / "Pictures" / "Chemigram", "manta")
    deep = image_root / "previews"
    deep.mkdir(exist_ok=True)
    result = discover_workspace_from_cwd(deep)
    assert result is not None
    workspace_root, image_id = result
    assert image_id == "manta"
    assert workspace_root == image_root.parent


def test_discover_returns_none_outside_workspace(tmp_path: Path) -> None:
    # tmp_path is just a regular directory — no objects/ or raw/.
    assert discover_workspace_from_cwd(tmp_path) is None


def test_discover_requires_both_objects_and_raw(tmp_path: Path) -> None:
    """Must have BOTH objects/ and raw/ — neither alone is enough."""
    half_root = tmp_path / "half"
    (half_root / "objects").mkdir(parents=True)
    # raw/ deliberately missing
    assert discover_workspace_from_cwd(half_root) is None


def test_discover_picks_innermost_match(tmp_path: Path) -> None:
    """If two ancestors qualify (e.g. nested workspace layouts), use innermost."""
    outer = _make_image_root(tmp_path / "outer_pictures", "outer_img")
    inner = _make_image_root(outer / "subdir", "inner_img")
    result = discover_workspace_from_cwd(inner)
    assert result is not None
    _, image_id = result
    assert image_id == "inner_img"
