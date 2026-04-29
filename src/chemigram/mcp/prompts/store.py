"""PromptStore: load and render versioned Jinja2 prompts.

Per ADR-043 (Jinja2 templates, filename-versioned), ADR-044 (PromptStore API
+ ``MANIFEST.toml`` registry), and ADR-045 (prompt versions independent of
package SemVer). Closes RFC-016.

Templates live at ``<root>/<task>_v<N>.j2`` (e.g. ``mode_a/system_v1.j2``).
``MANIFEST.toml`` declares the active version per task plus context-key
contracts (``context_required`` and ``context_optional``).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound


class PromptError(Exception):
    """Base class for prompt-store errors."""


class PromptNotFoundError(PromptError):
    """Raised when a task path isn't declared in ``MANIFEST.toml``."""


class PromptVersionNotFoundError(PromptError):
    """Raised when a requested ``<task>_v<N>.j2`` isn't on disk."""


class PromptContextError(PromptError):
    """Raised when ``render`` is called with missing required context keys."""


class PromptStore:
    """Loads ``MANIFEST.toml`` plus Jinja2 templates from a directory.

    Args:
        root: Directory containing ``MANIFEST.toml`` plus the template tree
            (e.g. ``mode_a/system_v1.j2``).

    Raises:
        PromptError: ``MANIFEST.toml`` missing or malformed.
    """

    def __init__(self, root: Path) -> None:
        manifest_path = root / "MANIFEST.toml"
        if not manifest_path.exists():
            raise PromptError(f"MANIFEST.toml not found at {manifest_path}")
        try:
            data = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            raise PromptError(f"{manifest_path}: malformed TOML: {exc}") from exc

        prompts = data.get("prompts", {})
        if not isinstance(prompts, dict):
            raise PromptError(f"{manifest_path}: top-level [prompts] must be a table")

        self._root = root
        self._manifest: dict[str, dict[str, Any]] = {}
        for path, entry in prompts.items():
            if not isinstance(entry, dict):
                raise PromptError(f"{manifest_path}: prompts.{path!r} must be a table")
            if "active" not in entry:
                raise PromptError(
                    f"{manifest_path}: prompts.{path!r} missing required 'active' key"
                )
            self._manifest[path] = {
                "active": str(entry["active"]),
                "context_required": list(entry.get("context_required", [])),
                "context_optional": list(entry.get("context_optional", [])),
            }

        self._env = Environment(
            loader=FileSystemLoader(str(root)),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            autoescape=False,  # noqa: S701 — system prompts are plain text, not HTML
        )

    def render(
        self,
        path: str,
        context: dict[str, Any],
        *,
        version: str | None = None,
        provider: str | None = None,
    ) -> str:
        """Render the template at ``path`` with Jinja2.

        Args:
            path: Task path (e.g. ``"mode_a/system"``).
            context: Variables for Jinja2 interpolation. Must include every
                key declared in MANIFEST's ``context_required``.
            version: ``None`` uses the active version from MANIFEST. Pin
                explicitly (e.g. ``"v1"``) for eval reproducibility.
            provider: Reserved for provider-specific overrides (e.g.
                ``mode_a/system_v1_claude.j2``). Always ``None`` in v0.3.0;
                a non-None value raises :class:`PromptError`.

        Raises:
            PromptNotFoundError: ``path`` not in MANIFEST.
            PromptVersionNotFoundError: requested version's ``.j2`` missing.
            PromptContextError: required context key absent.
        """
        if provider is not None:
            raise PromptError(
                f"provider-specific templates not supported in v0.3.0 "
                f"(deferred to Slice 6 evidence); got provider={provider!r}"
            )
        if path not in self._manifest:
            raise PromptNotFoundError(f"prompt path {path!r} not in MANIFEST.toml")

        entry = self._manifest[path]
        resolved_version = version if version is not None else entry["active"]
        template_name = f"{path}_{resolved_version}.j2"

        missing = [k for k in entry["context_required"] if k not in context]
        if missing:
            raise PromptContextError(
                f"prompt {path!r} render missing required context keys: {missing}"
            )

        try:
            template = self._env.get_template(template_name)
        except TemplateNotFound as exc:
            raise PromptVersionNotFoundError(
                f"template not found: {self._root / template_name}"
            ) from exc

        return template.render(**context)

    def active_version(self, path: str) -> str:
        """Active version for ``path`` per MANIFEST."""
        if path not in self._manifest:
            raise PromptNotFoundError(f"prompt path {path!r} not in MANIFEST.toml")
        return str(self._manifest[path]["active"])

    def context_schema(self, path: str) -> dict[str, list[str]]:
        """Returns ``{"required": [...], "optional": [...]}`` for ``path``."""
        if path not in self._manifest:
            raise PromptNotFoundError(f"prompt path {path!r} not in MANIFEST.toml")
        entry = self._manifest[path]
        return {
            "required": list(entry["context_required"]),
            "optional": list(entry["context_optional"]),
        }

    def list_templates(self) -> list[str]:
        """All template paths declared in MANIFEST."""
        return sorted(self._manifest.keys())
