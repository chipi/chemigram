"""Unit tests for chemigram.mcp.prompts.store."""

from __future__ import annotations

from pathlib import Path

import pytest

from chemigram.mcp.prompts import (
    PromptContextError,
    PromptError,
    PromptNotFoundError,
    PromptStore,
    PromptVersionNotFoundError,
)

TEST_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "prompts" / "test_manifest"
SHIPPED_ROOT = Path(__file__).resolve().parents[4] / "src" / "chemigram" / "mcp" / "prompts"


@pytest.fixture
def store() -> PromptStore:
    return PromptStore(TEST_ROOT)


def test_store_loads_manifest(store: PromptStore) -> None:
    assert store.list_templates() == ["mode_a/system", "mode_a/system_no_required"]


def test_render_active_version_default(store: PromptStore) -> None:
    out = store.render("mode_a/system", {"greeting": "hi", "name": "marko"})
    assert "hi, marko!" in out


def test_render_explicit_version(store: PromptStore) -> None:
    out = store.render("mode_a/system", {"greeting": "hi", "name": "m"}, version="v2")
    assert out.strip() == "v2: hi m."


def test_render_passes_optional_context(store: PromptStore) -> None:
    out = store.render(
        "mode_a/system",
        {"greeting": "hi", "name": "m", "mood": "calm"},
    )
    assert "You seem calm." in out


def test_render_missing_required_context_raises(store: PromptStore) -> None:
    with pytest.raises(PromptContextError, match="missing required context keys"):
        store.render("mode_a/system", {"greeting": "hi"})  # name missing


def test_render_unknown_path_raises(store: PromptStore) -> None:
    with pytest.raises(PromptNotFoundError, match="not in MANIFEST"):
        store.render("does_not/exist", {})


def test_render_unknown_version_raises(store: PromptStore) -> None:
    with pytest.raises(PromptVersionNotFoundError, match="template not found"):
        store.render(
            "mode_a/system",
            {"greeting": "hi", "name": "m"},
            version="v99",
        )


def test_active_version_returns_string(store: PromptStore) -> None:
    assert store.active_version("mode_a/system") == "v1"


def test_active_version_unknown_path_raises(store: PromptStore) -> None:
    with pytest.raises(PromptNotFoundError):
        store.active_version("nope")


def test_context_schema_shape(store: PromptStore) -> None:
    schema = store.context_schema("mode_a/system")
    assert schema == {"required": ["greeting", "name"], "optional": ["mood"]}


def test_context_schema_unknown_path_raises(store: PromptStore) -> None:
    with pytest.raises(PromptNotFoundError):
        store.context_schema("nope")


def test_provider_argument_rejected(store: PromptStore) -> None:
    with pytest.raises(PromptError, match="provider-specific"):
        store.render(
            "mode_a/system",
            {"greeting": "hi", "name": "m"},
            provider="claude",
        )


def test_missing_manifest_raises(tmp_path: Path) -> None:
    with pytest.raises(PromptError, match=r"MANIFEST\.toml not found"):
        PromptStore(tmp_path)


def test_malformed_manifest_raises(tmp_path: Path) -> None:
    (tmp_path / "MANIFEST.toml").write_text("[ not valid toml")
    with pytest.raises(PromptError, match="malformed TOML"):
        PromptStore(tmp_path)


def test_manifest_entry_missing_active_raises(tmp_path: Path) -> None:
    (tmp_path / "MANIFEST.toml").write_text('[prompts."mode_a/system"]\ncontext_required = []\n')
    with pytest.raises(PromptError, match="missing required 'active' key"):
        PromptStore(tmp_path)


def test_manifest_entry_must_be_table(tmp_path: Path) -> None:
    (tmp_path / "MANIFEST.toml").write_text('prompts = "not a table"\n')
    with pytest.raises(PromptError, match=r"\[prompts\] must be a table"):
        PromptStore(tmp_path)


def test_render_no_required_keys_works(store: PromptStore) -> None:
    out = store.render("mode_a/system_no_required", {})
    assert "no required keys" in out


def test_active_version_now_v2() -> None:
    real_store = PromptStore(SHIPPED_ROOT)
    assert real_store.active_version("mode_a/system") == "v3"


# ---------- v3 (active) ----------


def test_real_mode_a_v3_renders() -> None:
    """The shipped mode_a/system_v3.j2 renders against sample context."""
    real_store = PromptStore(SHIPPED_ROOT)
    out = real_store.render(
        "mode_a/system",
        {
            "vocabulary_size": 40,
            "image_id": "abc123",
            "vocabulary_packs": ["starter", "expressive-baseline"],
        },
    )
    assert "image `abc123`" in out
    assert "vocabulary of 40 named moves" in out
    # v3 references the real masking flow unconditionally
    assert "generate_mask" in out
    assert "regenerate_mask" in out


def test_real_mode_a_v3_lists_loaded_packs() -> None:
    """v3 enumerates the loaded vocabulary packs."""
    real_store = PromptStore(SHIPPED_ROOT)
    out = real_store.render(
        "mode_a/system",
        {
            "vocabulary_size": 40,
            "image_id": "x",
            "vocabulary_packs": ["starter", "expressive-baseline"],
        },
    )
    assert "`starter`" in out
    assert "`expressive-baseline`" in out


def test_real_mode_a_v3_navigating_section_present() -> None:
    """v3 adds explicit guidance on filter-first vocabulary navigation."""
    real_store = PromptStore(SHIPPED_ROOT)
    out = real_store.render(
        "mode_a/system",
        {
            "vocabulary_size": 40,
            "image_id": "x",
            "vocabulary_packs": ["starter", "expressive-baseline"],
        },
    )
    assert "Navigating the vocabulary" in out
    assert "filter-first" in out.lower() or "narrow first" in out.lower()


def test_real_mode_a_v3_references_propose_taste_categories() -> None:
    real_store = PromptStore(SHIPPED_ROOT)
    out = real_store.render(
        "mode_a/system",
        {
            "vocabulary_size": 40,
            "image_id": "x",
            "vocabulary_packs": ["starter"],
        },
    )
    assert "appearance" in out
    assert "process" in out
    assert "value" in out


def test_real_mode_a_v3_documents_end_session_orchestration() -> None:
    real_store = PromptStore(SHIPPED_ROOT)
    out = real_store.render(
        "mode_a/system",
        {
            "vocabulary_size": 40,
            "image_id": "x",
            "vocabulary_packs": ["starter"],
        },
    )
    assert "`end_session` tool" in out
    assert "you orchestrate" in out or "you use the existing tools" in out


# ---------- v2 (explicit; preserved per ADR-045) ----------


def test_v2_still_loadable_explicitly() -> None:
    """v2 stays on disk for eval reproducibility per ADR-045.

    Note: ``context_required`` in MANIFEST.toml applies globally per prompt
    path (not per version). v2 doesn't *use* ``vocabulary_packs`` but the
    validator demands it; v2 silently ignores the extra key — Jinja's
    default behavior. This is tolerable: reproducing an old version
    explicitly only requires the new context to be passed; the old
    template's output is unchanged.
    """
    real_store = PromptStore(SHIPPED_ROOT)
    out = real_store.render(
        "mode_a/system",
        {
            "vocabulary_size": 30,
            "image_id": "abc123",
            "vocabulary_packs": ["starter"],  # ignored by v2
        },
        version="v2",
    )
    assert "image `abc123`" in out
    assert "vocabulary of 30 named moves" in out
    # v2 doesn't have v3's pack enumeration section
    assert "Navigating the vocabulary" not in out


def test_v1_still_loadable_explicitly() -> None:
    """v1 stays on disk for eval reproducibility per ADR-045."""
    real_store = PromptStore(SHIPPED_ROOT)
    out = real_store.render(
        "mode_a/system",
        {
            "vocabulary_size": 30,
            "image_id": "abc123",
            "masker_available": True,
            "vocabulary_packs": ["starter"],  # ignored by v1
        },
        version="v1",
    )
    assert "image `abc123`" in out
    # v1 had the conditional masker branch
    assert "masker provider isn't installed" not in out
