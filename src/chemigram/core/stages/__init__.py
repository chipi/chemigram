"""Render pipeline stages.

v1 has a single stage: :class:`DarktableCliStage`. Future stages
(GenAI processors, custom shaders, format converters) plug in via the
:class:`~chemigram.core.pipeline.PipelineStage` Protocol.
"""

from chemigram.core.stages.darktable_cli import DarktableCliStage

__all__ = ["DarktableCliStage"]
