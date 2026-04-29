"""Per-image workspace orchestrator.

A :class:`Workspace` is the runtime object that ties one image's pieces
together: the per-image ``ImageRepo`` (objects/refs/HEAD/log), the symlinked
raw, the rendered preview/export caches, and references to shared
resources (configdir, vocabulary).

v0.3.0 ships the data shape and a path layout the MCP server can populate.
The orchestration seams (``ingest``, ``bind_layers``) land alongside their
tools; this module owns the dataclass, the layout convention, and the
:func:`init_workspace_root` helper that creates a freshly-formatted directory
matching ``contracts/per-image-repo`` in TA.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from chemigram.core.versioning import ImageRepo


@dataclass
class Workspace:
    """Runtime handle for one image's per-image directory.

    Attributes:
        image_id: Stable identifier (typically the basename of the raw
            without extension, plus a disambiguator if needed).
        root: Workspace directory, one level above the per-image repo.
        repo: :class:`ImageRepo` rooted at ``root``.
        raw_path: Absolute path to the original raw on disk. Stored as a
            symlink at ``root / "raw" / <basename>``.
        baseline_ref: Tag (or branch) name marking the session's baseline
            snapshot. Bare name — versioning's ``_resolve_input`` searches
            ``refs/heads/<name>`` then ``refs/tags/<name>``. Defaults to
            ``"baseline"`` (a tag): the ``ingest`` flow creates a
            ``baseline`` tag at the first snapshot so ``reset`` always
            returns to that point even after ``main`` advances.
        configdir: Optional dedicated darktable configdir per ADR-005.
            ``None`` means "use the global one".

    The previews/exports/sessions/masks/vocabulary_gaps subpaths follow
    ``contracts/per-image-repo`` and are surfaced as properties so callers
    don't restate the layout.
    """

    image_id: str
    root: Path
    repo: ImageRepo
    raw_path: Path
    baseline_ref: str = "baseline"
    configdir: Path | None = None

    @property
    def previews_dir(self) -> Path:
        return self.root / "previews"

    @property
    def exports_dir(self) -> Path:
        return self.root / "exports"

    @property
    def sessions_dir(self) -> Path:
        return self.root / "sessions"

    @property
    def masks_dir(self) -> Path:
        return self.root / "masks"

    @property
    def vocabulary_gaps_path(self) -> Path:
        return self.root / "vocabulary_gaps.jsonl"


def init_workspace_root(root: Path) -> None:
    """Create the directory shape declared in ``contracts/per-image-repo``.

    Only the directories whose existence the workspace assumes — the repo
    pieces (``objects/``, ``refs/``, ``HEAD``, ``log.jsonl``) come from
    :meth:`ImageRepo.init`, called separately by callers that need them.
    """
    root.mkdir(parents=True, exist_ok=True)
    for sub in ("raw", "previews", "exports", "sessions", "masks"):
        (root / sub).mkdir(exist_ok=True)
