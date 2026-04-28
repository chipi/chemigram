# ADR-014 — All image-processing via darktable

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/constraints/dt-orchestration-only ·/stack
> Related RFC · None (foundational; from ADR-003 discipline 2)

## Context

Photo editing involves color science, lens correction, denoise, tone curves, masks, sharpening, dehaze, and dozens of other capabilities. Each is a deep specialty; building any of them from scratch is a multi-year project. darktable already implements all of them at a high quality level.

## Decision

Chemigram does not implement image-processing capabilities. All raw decoding, color science, lens correction (Lensfun + embedded EXIF metadata), profiled denoise, tone equalizer, filmic, color balance rgb, masks (parametric, drawn, raster), sharpening, dehaze — every operation that produces visible change in a photo — comes from darktable. The engine's responsibility is orchestration only: vocabulary composition, render dispatch, versioning, sessions, agent integration.

## Rationale

- **Quality.** darktable's color science is competitive with commercial tools (Lightroom, Capture One). Reimplementing would produce a worse result at enormous engineering cost.
- **Maintenance.** darktable has a mature contributor base maintaining color profiles, lens databases (Lensfun), noise models. Free maintenance for us.
- **Scope discipline.** This ADR makes "could we add X processing capability?" answerable with a single rule: no, that's darktable's job.
- **Aligns with research thesis.** The project's thesis is about taste transmission via vocabulary, not about competing with darktable on processing quality. Building processing capability would dilute the research focus.

## Alternatives considered

- **Implement a thin shim of essential operations (e.g., basic exposure adjustment):** rejected — even "basic" operations have to integrate with the rest of the pipeline (gamma, color space, view transform). The shim would either be insufficient or grow into a duplicate pipeline.
- **Use a different processor (RawTherapee, ART, libraw + custom):** rejected — darktable's `darktable-cli` is the only one with the right combination of: headless render quality, scriptable invocation, mature module set, active maintenance, and good Apple Silicon performance. RawTherapee CLI has shaky headless behavior. Custom libraw-based processing reimplements the wheel.
- **Run multiple processors and let the photographer choose:** rejected for v1 — adds enormous integration surface for marginal benefit. Could be revisited via the pipeline-stages abstraction if a clear need surfaces (RFC-005).

## Consequences

Positive:
- Engine code is small and focused on orchestration
- Quality of output is darktable's quality of output (very good)
- Photographers familiar with darktable feel at home with Chemigram's vocabulary
- We don't compete with darktable; we extend it

Negative:
- Hard dependency on darktable being installed and runnable on the photographer's machine
- darktable releases can break us (mitigated by version pinning per ADR-026)
- Some photographers prefer other processors (RawTherapee, ART, ON1); they'd need to use those tools separately, not through Chemigram

## Implementation notes

The engine's `chemigram_core` package has no image-processing code. `pipeline.py` and `stages/darktable_cli.py` shell out to darktable. `xmp.py` and `dtstyle.py` operate on XML, not pixels. This is enforced by code review rather than by tooling.
