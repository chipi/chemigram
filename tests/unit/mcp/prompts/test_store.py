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
    assert real_store.active_version("mode_a/system") == "v2"


def test_real_mode_a_v2_renders() -> None:
    """The shipped mode_a/system_v2.j2 renders against sample context."""
    real_store = PromptStore(SHIPPED_ROOT)
    out = real_store.render(
        "mode_a/system",
        {"vocabulary_size": 30, "image_id": "abc123"},
    )
    assert "image `abc123`" in out
    assert "vocabulary of 30 named moves" in out
    # v2 references the real masking flow unconditionally
    assert "generate_mask" in out
    assert "regenerate_mask" in out


def test_real_mode_a_v2_drops_masker_conditional() -> None:
    """v2 doesn't have the v1 'masker provider isn't installed' branch."""
    real_store = PromptStore(SHIPPED_ROOT)
    out = real_store.render(
        "mode_a/system",
        {"vocabulary_size": 30, "image_id": "abc123"},
    )
    assert "masker provider isn't installed" not in out


def test_real_mode_a_v2_references_propose_taste_categories() -> None:
    """v2 names the category enum directly."""
    real_store = PromptStore(SHIPPED_ROOT)
    out = real_store.render(
        "mode_a/system",
        {"vocabulary_size": 30, "image_id": "abc123"},
    )
    assert "appearance" in out
    assert "process" in out
    assert "value" in out


def test_real_mode_a_v2_documents_end_session_orchestration() -> None:
    """v2 references ADR-061's agent-orchestrated end-of-session pattern."""
    real_store = PromptStore(SHIPPED_ROOT)
    out = real_store.render(
        "mode_a/system",
        {"vocabulary_size": 30, "image_id": "abc123"},
    )
    assert "`end_session` tool" in out
    assert "you orchestrate" in out or "you use the existing tools" in out


def test_v1_still_loadable_explicitly() -> None:
    """v1 stays on disk for eval reproducibility per ADR-045."""
    real_store = PromptStore(SHIPPED_ROOT)
    out = real_store.render(
        "mode_a/system",
        {"vocabulary_size": 30, "image_id": "abc123", "masker_available": True},
        version="v1",
    )
    assert "image `abc123`" in out
    # v1 had the conditional masker branch
    assert "masker provider isn't installed" not in out
