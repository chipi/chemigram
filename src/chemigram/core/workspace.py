"""Per-image workspace orchestrator.

A :class:`Workspace` is the runtime object that ties one image's pieces
together: the per-image ``ImageRepo`` (objects/refs/HEAD/log), the symlinked
raw, the rendered preview/export caches, and references to shared
resources (configdir, vocabulary). Owns the directory layout from
``contracts/per-image-repo``.

Public surface:
    - :class:`Workspace` — runtime handle
    - :func:`init_workspace_root` — directory bootstrap
    - :func:`workspace_id_for` — derive a stable ``image_id`` from a raw path
    - :func:`Workspace.ingest` — full bootstrap (symlinks raw, extracts EXIF,
      creates ``ImageRepo``, writes a baseline XMP, snapshots it, tags
      ``baseline``)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from chemigram.core.binding import VocabularyIndex, bind_l1
from chemigram.core.dtstyle import DtstyleEntry
from chemigram.core.exif import ExifData, read_exif
from chemigram.core.versioning import ImageRepo
from chemigram.core.versioning.ops import snapshot, tag
from chemigram.core.xmp import Xmp, parse_xmp, synthesize_xmp

_BASELINE_FIXTURE = Path(__file__).resolve().parent / "_baseline_v1.xmp"


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
    exif: ExifData | None = None
    suggested_bindings: list[DtstyleEntry] = field(default_factory=list)

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


_SAFE_ID = re.compile(r"[^a-zA-Z0-9_.-]+")


def workspace_id_for(raw_path: Path, *, suffix: str | None = None) -> str:
    """Derive a stable, filesystem-safe ``image_id`` from a raw filename.

    Uses the basename without extension, sanitized to ``[A-Za-z0-9_.-]``.
    ``suffix`` (typically a short hash or timestamp) disambiguates collisions
    when the same basename has been ingested before.
    """
    base = _SAFE_ID.sub("_", raw_path.stem) or "image"
    return f"{base}_{suffix}" if suffix else base


def _baseline_xmp(exif: ExifData, suggested_l1: list[DtstyleEntry]) -> Xmp:
    """Build a fresh baseline XMP for a newly-ingested raw.

    v0.3.0 uses the bundled ``_baseline_v1.xmp`` fixture (the calibrated
    darktable 5.4.1 reference) as a stand-in for darktable-cli's own
    initial pipeline state. A future slice will replace this with a real
    ``darktable-cli`` invocation that exports the actual XMP for the raw;
    the stand-in keeps the seam stable so vocabulary primitives can SET-
    replace against a known set of baseline operations (Path A) instead
    of falling into Path B (new-instance add), which RFC-001 still owns.
    """
    baseline = parse_xmp(_BASELINE_FIXTURE)
    if suggested_l1:
        return synthesize_xmp(baseline, suggested_l1)
    return baseline


def ingest_workspace(
    raw_path: Path,
    *,
    workspace_root: Path,
    image_id: str | None = None,
    vocabulary: VocabularyIndex | None = None,
) -> Workspace:
    """Bootstrap a :class:`Workspace` for ``raw_path``.

    Steps:
        1. Resolve ``image_id`` (caller-provided or derived from raw stem).
        2. Create the per-image directory layout under ``workspace_root /
           image_id`` and initialize the :class:`ImageRepo`.
        3. Symlink the raw into ``raw/<basename>`` (relative if possible).
        4. Read EXIF, suggest L1 bindings via :func:`bind_l1`.
        5. Build a baseline :class:`Xmp` (with L1 applied if any), snapshot
           it, and tag the snapshot ``baseline``.

    Idempotent on the per-image directory: re-ingesting the same image_id
    does NOT clobber an existing repo — raises ``FileExistsError`` if the
    target root already has an ``objects/`` directory. Caller decides
    whether to disambiguate via ``image_id``.
    """
    if image_id is None:
        image_id = workspace_id_for(raw_path)
    root = workspace_root / image_id
    if (root / "objects").exists():
        raise FileExistsError(
            f"workspace at {root} already exists — pass a fresh image_id to ingest again"
        )

    init_workspace_root(root)
    repo = ImageRepo.init(root)

    raw_link = root / "raw" / raw_path.name
    if not raw_link.exists():
        raw_link.symlink_to(raw_path.resolve())

    exif = read_exif(raw_path)
    suggested = bind_l1(exif, vocabulary) if vocabulary is not None else []
    baseline_xmp = _baseline_xmp(exif, suggested)
    h = snapshot(repo, baseline_xmp, label="baseline", metadata={"ingested_at": _now_iso()})
    tag(repo, "baseline", h)

    return Workspace(
        image_id=image_id,
        root=root,
        repo=repo,
        raw_path=raw_link,
        exif=exif,
        suggested_bindings=list(suggested),
    )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
