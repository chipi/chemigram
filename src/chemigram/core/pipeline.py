"""Render pipeline.

v1 has a single stage (:class:`~chemigram.core.stages.darktable_cli.DarktableCliStage`).
The :class:`PipelineStage` Protocol exists to keep the seam clean and make
testing trivial — fakes are easy. Multi-stage chaining is YAGNI until a
real second stage materializes (closes RFC-005 → ADR-052).

Per ADR-005, a single ``darktable-cli`` runs per ``configdir`` at a time.
Serialization is enforced inside :class:`DarktableCliStage` via
per-configdir threading locks; the pipeline-level orchestrator is
otherwise plain sequential.

Public API:
    - :class:`StageContext`, :class:`StageResult` — frozen dataclasses
    - :class:`PipelineStage` — Protocol
    - :class:`Pipeline` — orchestrator (single-stage in v1)
    - :func:`render` — convenience entry point
"""

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class StageContext:
    """Inputs available to every render stage."""

    raw_path: Path
    xmp_path: Path
    output_path: Path
    configdir: Path
    width: int = 1024
    height: int = 1024
    high_quality: bool = False  # --hq flag; True for final exports


@dataclass(frozen=True)
class StageResult:
    """Outputs from a stage."""

    success: bool
    output_path: Path
    duration_seconds: float
    stderr: str
    error_message: str | None = None


class PipelineStage(Protocol):
    """A render-pipeline stage. v1 has one (:class:`DarktableCliStage`).

    Implementations are self-contained: a stage does its work and
    returns a :class:`StageResult`. Stages don't know about other stages.
    """

    def run(self, context: StageContext) -> StageResult: ...


class Pipeline:
    """Orchestrates a sequence of render stages.

    v1 has exactly one stage; multi-stage threading is YAGNI until a
    real second stage materializes. When that happens, ``run`` gains
    output-of-N → input-of-N+1 logic; today it's just a passthrough.
    """

    def __init__(self, stages: list[PipelineStage]) -> None:
        if not stages:
            raise ValueError("Pipeline requires at least one stage")
        self.stages = stages

    def run(self, context: StageContext) -> StageResult:
        """Run all stages sequentially.

        For v1 (single stage) this is just ``self.stages[0].run(context)``.
        """
        result: StageResult | None = None
        for stage in self.stages:
            result = stage.run(context)
            if not result.success:
                return result
        assert result is not None  # Pipeline guarantees at least one stage
        return result


def render(
    raw_path: Path,
    xmp_path: Path,
    output_path: Path,
    *,
    width: int = 1024,
    height: int = 1024,
    high_quality: bool = False,
    configdir: Path | None = None,
) -> StageResult:
    """Convenience: build the v1 single-stage pipeline and run it.

    Args:
        raw_path: input raw file (NEF, ARW, RAF, etc.)
        xmp_path: synthesized XMP sidecar to apply
        output_path: where to write the rendered JPEG
        width: max output width in pixels (default 1024)
        height: max output height in pixels (default 1024)
        high_quality: ``--hq`` flag — True for final exports, False for previews
        configdir: darktable configdir (per ADR-005, isolated per session).
            **Must be a pre-bootstrapped darktable configdir** — a fresh empty
            directory makes ``darktable-cli`` fail with "can't init develop
            system." If ``None``, a process-local tempdir is created lazily;
            real renders need a configdir that's been initialized at least
            once by the darktable GUI.

    Returns:
        :class:`StageResult` with success/duration/stderr/error_message.
    """
    # Local import to break a circular dependency: stages/darktable_cli.py
    # imports from pipeline (StageContext, StageResult, PipelineStage).
    from chemigram.core.stages.darktable_cli import DarktableCliStage

    if configdir is None:
        configdir = Path(tempfile.mkdtemp(prefix="chemigram-cfg-"))

    ctx = StageContext(
        raw_path=raw_path,
        xmp_path=xmp_path,
        output_path=output_path,
        configdir=configdir,
        width=width,
        height=height,
        high_quality=high_quality,
    )
    pipeline = Pipeline([DarktableCliStage()])
    return pipeline.run(ctx)
