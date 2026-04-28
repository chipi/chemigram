# RFC-005 — Pipeline stage protocol — abstract now or YAGNI

> Status · Decided (closed by ADR-052 at Slice 1 gate, 2026-04-28)
> TA anchor ·/components/render-pipeline
> Related · ADR-004
> Closed by · ADR-052 (PipelineStage Protocol with single v1 stage). The Protocol approach was justified — fake stages make unit-testing trivial, and the seam cost ~50 lines.
> Why this is an RFC · The architecture (04/8) describes a pipeline with multiple stages, but v1 only has one stage (`darktable-cli`). YAGNI says "just write the function" — abstraction adds complexity for a non-existent second stage. The architecture says "build the seam now to make Phase 3 cleaner." Both have merit. This RFC argues the choice and locks it.

## The question

Should v1's render pipeline be:

- **Option A — A `PipelineStage` Protocol with one implementation (`DarktableCliStage`).** The framework exists; adding stages later is straightforward.
- **Option B — A direct function call (`render(raw, xmp, output)`) that shells out to darktable-cli.** Simpler. Refactor to a Protocol if a second stage ever lands.

YAGNI principle (Option B) vs preserve-the-architectural-seam (Option A). The architecture document committed to the Protocol shape; this RFC examines whether v1 should ship it.

## Use cases

What would a "second stage" look like in practice?

- A future `LocalProcessingStage` for custom Python algorithms ("apply this denoise, then darktable-cli for the rest").
- A `ScalingStage` that delivers different output sizes from one render.
- An `ExternalServiceStage` that sends to a remote service (probably never wanted, but possible).

Are any of these likely to ship in the next 6 months? Probably not. Mode B might want a different stage architecture, but Mode B is itself unbuilt.

## Goals

- v1 ships the simplest correct render pipeline
- Refactoring to Protocol later (if needed) doesn't require breaking changes
- The right amount of abstraction at the right time

## Constraints

- TA/components/render-pipeline — render pipeline exists; how it's structured is open
- ADR-004 — `darktable-cli` invocation form is fixed; the question is whether it's wrapped in a Protocol or called directly

## Proposed approach

**Option A: Ship the Protocol. Single stage, but the seam exists.**

Concrete code shape:

```python
@dataclass
class StageResult:
    success: bool
    output_paths: dict[str, Path]
    elapsed_seconds: float
    diagnostics: dict


class PipelineStage(Protocol):
    @property
    def inputs(self) -> set[str]: ...
    @property
    def outputs(self) -> set[str]: ...
    def run(self, context: dict) -> StageResult: ...


class DarktableCliStage:
    @property
    def inputs(self) -> set[str]:
        return {"raw_path", "xmp_path"}

    @property
    def outputs(self) -> set[str]:
        return {"image_path"}

    def run(self, context: dict) -> StageResult:
        # ... shell out to darktable-cli ...
        return StageResult(...)


@dataclass
class Pipeline:
    stages: list[PipelineStage]

    def run(self, context: dict) -> StageResult:
        for stage in self.stages:
            result = stage.run(context)
            if not result.success:
                return result
            context.update(result.output_paths)
        return result
```

Yes, the Protocol adds ~30 lines vs a direct function call. But:
- It's consistent with what's committed in the architecture doc, section 8.
- The MCP server's render tools can compose stages declaratively (configuring which stages to run for previews vs exports).
- It costs almost nothing in v1 to maintain, and earns refactoring slack later.

The chosen path is Option A.

## Alternatives considered

- **Option B (YAGNI, direct function):** considered carefully. Saves ~30 lines now, but trades that for a future migration if a second stage lands. Migrations are exactly the kind of work LLM agents struggle with — they pattern-match the existing shape. The seam is cheap insurance.

- **Option C (Pipeline framework but only as docs, not code):** rejected — having a documented abstraction with no implementation is the worst of both worlds.

- **Option D (Use a real workflow library, e.g., Prefect):** rejected — wildly disproportionate to v1 scope. Custom Protocol is small and right-sized.

## Trade-offs

- Option A's main cost is mental overhead for new contributors reading the code: "why is there a Protocol with one implementation?" Mitigated by clear comments and the architecture document.
- Option A means the simplest "render this image" call goes through more layers: synthesizer → pipeline → stage → subprocess. Each layer is thin (~5 lines), so the overhead is modest, but stack traces are longer. Acceptable.
- Option A's Protocol shape might turn out to be wrong when a second stage lands. The first stage tells us a lot about pipeline shape; the second tells us whether that shape generalizes. We may need to revisit the Protocol when stage 2 lands. Acceptable: the current shape is informed by 04 thinking, not arbitrary.

## Open questions

- **Sync vs async stages.** v1 stages are synchronous (subprocess). Future stages might want to be async (network calls, background processing). Should `run()` be async from the start? Proposed: keep synchronous in v1; if an async stage lands, refactor to async-everywhere then. Mixing sync/async is worse than either consistently.
- **Stage configuration.** How does a stage receive its config (path to darktable-cli, default `--width`, etc.)? Proposed: constructor parameters; stage instances are configured once and reused.
- **Stage error handling.** What does a stage emit when darktable-cli returns nonzero? Proposed: `StageResult.success = False`, `diagnostics` populated. The caller decides whether to abort the pipeline or fall through.

## How this closes

This RFC closes into:
- **An ADR locking Option A** (Protocol with one stage in v1).
- The `PipelineStage` Protocol shape as documented above; subsequent ADRs (or amendments) refine it as second stages land.

## Links

- TA/components/render-pipeline
- ADR-004 (darktable-cli invocation form)
- 04/8 (Pipeline architecture)
