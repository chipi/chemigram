# RFC-038 — Mode B autonomous session protocol

> Status · Draft v0.1
> TA anchor · /components/mcp · /components/eval · /contracts/per-image-repo · /constraints/single-process
> Related · PRD-002 (Mode B user-value argument), RFC-017 + ADR-046/047 (eval-harness substrate, built Phase 5), RFC-031 / ADR-051 (synthesizer same-module collision), concept/02 §2.2 + §10.5
> Closes into · ADR-NNN (Mode B session protocol), possibly a second ADR for the bounded-autonomy enforcement boundary
> Why this is an RFC · PRD-002 captured the user-value argument (the photographer hands off, the agent explores autonomously, three variants land on a branch each). RFC-017 + the eval harness gave us the headless-runnable substrate. But the *session protocol* — how a photographer initiates Mode B, how the agent's autonomy is bounded, how variants are surfaced for review, how the per-branch reasoning is captured — has never been argued. The answer is genuinely open: Mode B could ride existing MCP verbs orchestrated by a system prompt (cheap, prompt-only ship), or it could need a new session-shape on the tool surface (richer reporting, harder ship), or somewhere in between. The "right answer" depends on disciplines we haven't yet tested against real photographers running real autonomous sessions.

## The question

Mode B's user-value claim from PRD-002: photographer ends a Mode A session at `v1`, hands off with vectors to explore ("more dramatic shadow lift on tone, warmer subject on color, more clarity on rock texture"), agent runs alone for ~30 minutes, surfaces 3 branches each tagged + judged with a paragraph of reasoning. The eval harness (RFC-017) lets us run this headlessly against scenarios. What we don't have: the session shape itself.

The genuinely-open architectural question splits into four:

1. **Where does Mode B live on the tool surface?** As a new MCP verb (`start_mode_b_session(image_id, vectors, budget, ...)`) that internally orchestrates the existing verbs? Or as a Mode B prompt template that the agent loads + drives via existing verbs (apply_primitive, snapshot, branch, render_preview) with no new tool surface? Or some hybrid — a thin session verb that returns a session_id used by reporting tools?

2. **How is bounded autonomy enforced?** Time cap (30 minutes) is the obvious lever. Iteration cap (max 50 tool calls)? Branch cap (≤ N branches)? Token budget? Combination? Who enforces — the agent itself reading a budget object, or the engine refusing further mutating calls after the cap fires?

3. **How does the agent self-evaluate?** The eval harness exists for scenario-vs-rubric measurement; Mode B per-session is a different shape. Does the agent self-judge ("I tried X, it was worse, abandoned") via natural language only, or is there a structured judgment record (per-render score against criteria)? Does the photographer's `taste.md` + the brief + the explicit vectors form the criteria, or does Mode B accept a separate `criteria` input?

4. **What's the variant surfacing surface?** When the photographer comes back, what do they see? A list of branches with notes (low-level, current Mode A `log` style)? A purpose-built `mode_b summarize <session_id>` view showing per-branch judgments + comparison renders side-by-side? Something between?

## Use cases

- **Vector-guided variant exploration.** PRD-002's canonical example. Photographer commits to v1, hands off with N vectors (tone / color / structure / etc), gets N branches back each pushing one vector while staying within v1's spirit.
- **Open-ended depth-pushing.** "Go deeper on what we just did." No vectors specified; agent inherits Mode A's session direction and explores the same vector at higher intensity. Riskier; tighter cap.
- **Tactical "try the move I avoided."** Photographer says "I deliberately didn't go heavy on clarity; show me what heavy clarity looks like and explain why I should or shouldn't." One-axis exploration, paragraph-of-reasoning expected.
- **Brief-only exploration.** Photographer sets a brief but skips Mode A entirely. "Three variants matching this brief, starting from baseline." Less likely use case but architecturally must be supported.
- **Pre-session calibration.** Before a real Mode A session, photographer asks Mode B to "explore three different starting interpretations of this brief, surface them; I'll pick which to develop in Mode A." Inverts the usual flow (B before A); not the primary use case but the architecture shouldn't preclude it.

## Goals

1. **Mode B uses Mode A's vocabulary, prompts-as-distinct, and snapshot DAG.** No duplicate vocabulary system; no parallel state model; no separate workspace shape.
2. **Bounded autonomy is enforceable.** The photographer specifies a budget; the agent cannot exceed it. The enforcement is layered (agent honor-system + engine hard-cap) so a misbehaving prompt can't run unbounded.
3. **Every Mode B session is fully audit-able.** Per-branch transcript captures every primitive applied, every render judged, every dead-end abandoned. Replay-able later.
4. **Variant surfacing is honest.** The agent's per-branch judgment ("this is better than v1 in the structure axis but slightly worse in mood preservation") is captured as structured fields the surfacing UI can render. Not just free-form prose.
5. **Mode B never silently mutates `main`.** Variants land on `branch_b_*` refs. The photographer's review step is what promotes any variant.
6. **Mode B composes with the eval harness.** A scenario from `data/eval/golden_v1/scenarios/` can be run as a Mode B session; the same prompt + brief + taste produces deterministic-modulo-temperature variants the harness can measure.

## Constraints

- **`TA/constraints/single-process`** — Mode B runs inside the same Python process as Mode A. No background daemon; no IPC. The "agent runs while you're not at the keyboard" experience is wall-clock-asynchronous from the photographer's perspective but synchronous from the engine's. (A photographer who closes the laptop ends the session; the agent doesn't survive that.)
- **`PA/principles/agent-is-the-only-writer`** — Mode B mutates state, but every mutation rides through the same propose-and-confirm + snapshot discipline as Mode A. No silent direct writes.
- **`PA/promises/inspectable-state`** — Mode B's session must be replay-able. Every tool call recorded; every render reproducible (same XMP + same darktable version → same JPEG).
- **`constraints/serial-renders`** — Mode B is single-process; renders serialize through `darktable-cli` (one configdir per session). N branches exploring in parallel means render queueing; Mode B's 30-minute cap must account for serial render time (typically ~5s/render × N renders = real fraction of the cap).
- **ADR-051 (same-module collision)** — Mode B explores via the same SET-replace semantics. Branching from `v1` and applying alternative `sigmoid_contrast --value 2.0` replaces the v1 sigmoid in the branch. The branch is a divergence point on the snapshot DAG, not a layered overlay.

## Proposed approach

**The shape: a prompt template (`mode_b/system_v1.j2`) that drives existing MCP verbs, plus a thin budget-enforcement layer in the engine, plus a new MCP verb `start_mode_b_session` for session lifecycle. No new MCP tool for the per-step exploration — that rides existing `apply_primitive` / `snapshot` / `branch` / `render_preview` / `compare`.**

### Session lifecycle (the new verb surface)

Three new MCP tools (CLI mirrors per ADR-069):

1. **`start_mode_b_session(image_id, brief, vectors?, budget, criteria?)` → `{session_id, baseline_hash}`**
   - `image_id`: which image
   - `brief`: free-form brief (same shape as Mode A's per-image brief)
   - `vectors`: optional list of `{name, direction, intensity_hint?}` — the exploration axes (PRD-002's "tone / color / structure")
   - `budget`: `{time_seconds: int, max_iterations: int, max_branches: int}` — all three required; lowest-firing wins
   - `criteria`: optional structured criteria for self-evaluation. Defaults to "agent infers from taste.md + brief"
   - Returns a `session_id` (UUID) and the baseline_hash (the snapshot the session forked from — typically the current HEAD)
   - **Propose-and-confirm gate at start**: the agent sees the planned session shape and either confirms or asks for clarification before any state mutation begins.

2. **`end_mode_b_session(session_id)` → `{branches, session_summary}`**
   - Called by the agent when it decides the session is done (or by the engine when budget fires).
   - Returns the list of created branches each with `{ref_name, judged_score, judged_reasoning, key_moves}` for surfacing.
   - The agent's free-form session_summary captures cross-branch observations ("the tone axis was the strongest; the color axis introduced an unwanted cast and I abandoned all three attempts").

3. **`mode_b_status(session_id)` → `{budget_remaining, branches_so_far, current_branch, iterations_so_far}`**
   - Read-only. The photographer (or a watching agent) can poll for status. Mostly used by the eval harness to monitor headless runs.

### Per-step exploration uses existing verbs

Inside a Mode B session, the agent does its work via the verbs that already exist:

- `branch(image_id, ref_name, from=baseline_hash)` — create the exploration branch.
- `apply_primitive(image_id, ...)` — apply a vocabulary move on the branch.
- `snapshot(image_id, label=...)` — capture intermediate states.
- `render_preview(image_id, ref_or_hash=...)` — produce a JPEG to judge.
- `compare(image_id, hash_a, hash_b)` — side-by-side for self-evaluation.
- `log_vocabulary_gap(image_id, ...)` — Mode B logs gaps exactly like Mode A does.

The Mode B prompt template wraps these in the bounded-autonomy + honest-reporting discipline. No engine surface change for per-step operations.

### Bounded-autonomy enforcement (two-layer)

**Honor-system layer (agent reads its own budget):** The Mode B system prompt instructs the agent to check `mode_b_status` periodically and stop when budget is near. The agent's per-branch decisions ("this is good enough; move to the next vector") factor in remaining budget.

**Hard-cap layer (engine refuses):** A Mode B session's `session_id` is tracked in workspace state. When a mutating tool call (apply_primitive / snapshot / branch / etc) is invoked inside a session that has exceeded any budget cap, the engine returns `BUDGET_EXHAUSTED` and refuses. The agent cannot bypass via prompt drift.

The two layers exist because honor-system alone is fragile (a single hallucinated "I'll keep going" sentence breaks the budget); hard-cap alone is hostile (the agent doesn't know it's running out and can't gracefully conclude). Both together: agent self-manages, engine enforces.

### Self-evaluation shape

**Default: agent self-judges via natural language with structured fields.** After each candidate render on a branch, the agent emits a judgment in the structured form:

```
{
  "branch": "branch_b_tone",
  "hash": "abc123",
  "judged_score": 4,           // 1-5 scale; coarse but comparable
  "judged_reasoning": "Subject feels present without breaking the brief's 'subtle' intent. Sigmoid 1.7 + bilat 0.4 caught the rock texture without going past acceptable. The slight color shift on the iguana skin needs offset.",
  "comparable_to_baseline": true,
  "key_moves": ["sigmoid_contrast --value 1.7", "bilat_clarity_strength --value 0.4"]
}
```

The `judged_score` is coarse on purpose (1-5). Finer scales (1-10, 0.0-1.0) invite over-fitting to score-units that don't generalize. The reasoning paragraph is where the real judgment lives.

**Future: optional eval-LLM judge.** PRD-002 surfaced the question of "agent self-evaluates vs separate evaluator judges." Phase 1 ships agent-self-evaluates because it's simpler. A future RFC can add an optional `evaluator_provider` MCP-configurable that gets called per-render to produce a second opinion. RFC-017's eval harness substrate already supports this shape; Mode B adopts it additively if/when needed.

### Variant surfacing

A new `mode_b show <session_id>` CLI verb (sister to the existing `log`) renders the photographer's review surface:

```
Session a1b2c3 — iguana-galapagos — 28 min / 47 iterations / 3 branches
Baseline: v1 (hash 1234abc)

branch_b_tone (snapshot tag: branch_b_tone)
  Score: 4/5
  Reasoning: Subject feels present without breaking the brief's 'subtle' intent...
  Key moves: sigmoid_contrast 1.7, bilat 0.4
  [render preview: previews/branch_b_tone-1024.jpg]

branch_b_color (snapshot tag: branch_b_color)
  Score: 2/5  [agent flagged: weak]
  Reasoning: Tried temperature shifts at +0.4, +0.6, +0.8. All produced unwanted yellow cast on the rock. Abandoned all three. Returned to v1's color.
  Key moves: (none — all variants abandoned)
  [render preview: previews/branch_b_color-1024.jpg, identical to baseline]

branch_b_structure (snapshot tag: branch_b_structure)
  Score: 5/5  [agent flagged: strong]
  Reasoning: bilat 1.5 produced exactly what the brief was asking without...
  Key moves: bilat_clarity_strength 1.5, vignette -0.2
  [render preview: previews/branch_b_structure-1024.jpg]
```

The photographer reviews, makes their own judgment, and via standard `tag` / `checkout` verbs promotes the winner.

### Eval-harness composition

Mode B sessions and eval-harness scenarios share substrate. A scenario at `data/eval/golden_v1/scenarios/001_iguana_warm/` runs as a Mode B session against a fixed `mode_b/system_vN.j2` prompt; the resulting branches and judgments feed the metrics layer (RFC-017 mechanical + semantic metrics). This is the auto-research loop: vary prompt version, hold scenario set fixed, measure if v3 produces better variants than v2.

The eval-harness already has run manifests (ADR-047); Mode B session manifests are a superset (session_id + budget + variant-level judgments are extra fields).

## Alternatives considered

**Mode B as pure prompt template, no new MCP tools.** The agent reads a brief from `notes.md`, branches via existing `branch`, applies via existing `apply_primitive`, judges informally in chat. No `start_mode_b_session` / `end_mode_b_session` / `mode_b_status` tools. *Rejected* because bounded autonomy can't be hard-capped without a session abstraction the engine knows about. Pure prompt-template Mode B is honor-system-only; one bad prompt revision breaks the budget guarantee.

**Mode B as a long-running background daemon.** Photographer closes the laptop; the agent keeps running on a separate process / a remote runner / a cron job. *Rejected* because it violates `constraints/single-process` and the chemigram-is-not-a-service framing. Mode B sessions are bounded to the photographer's open session; a 30-minute cap with the laptop open is the right v1 surface. A "remote-run Mode B" sibling project is plausible later but is a different product.

**Multiple-LLM jury for self-evaluation.** Spawn 3 evaluator LLMs per render, take the majority verdict. *Rejected for v1* — produces expense without strong evidence it improves judgment quality. The PRD's "sharpest threat" frames the agent's taste calibration as the real risk; juries don't fix calibration, they just multiply the cost. Reconsider if v1 Mode B's hit rate is low and the diagnosis is "the agent's judgment is the bottleneck."

**Branch-per-iteration instead of branch-per-vector.** Each tool call lands on its own branch, producing a tree of dozens of branches per session. *Rejected* because it pollutes the photographer's review surface. The PRD-002 framing is "three branches, three judgments" — meaningful units. Branch-per-iteration is the eval-harness shape, not the photographer-review shape; conflating them costs review clarity.

**Real-time streaming of agent reasoning to the photographer (open laptop, watching the agent work).** *Rejected* because PRD-002 explicitly puts this out of scope. The hand-off discipline (write the instruction, walk away, come back) is the whole point. Watch-the-agent-work is a different mode (Mode A is the closest equivalent; v1 Mode A already streams).

**Mode B chooses its own branch names instead of using `branch_b_<vector>`.** Names like `more_drama_take_3` are more descriptive than `branch_b_tone`. *Rejected for v1* — non-deterministic names break the photographer's mental model + the eval harness's scenario-vs-output comparison. The agent can write descriptive prose in its judgment; the branch name should be stable and predictable.

## Trade-offs

- **+3 MCP verbs.** Adds to the agent's surface area. Mitigated by keeping per-step exploration on existing verbs (no new apply / snapshot / branch shapes) and limiting the new surface to session lifecycle.
- **Honor-system + hard-cap is two layers of code.** More to maintain. Mitigated by colocation — the budget object is owned by the session record; both layers read the same source of truth.
- **Coarse 1-5 judgment scale.** Some genuinely-better variants will score the same as some merely-good ones. Mitigated by the prose reasoning being the real signal; the score is a coarse sort key.
- **`mode_b show` is a new CLI sub-app on top of an already-rich CLI.** Adds another verb the photographer must learn. Mitigated by making it the natural "next step after running Mode B" — discoverable from the session_id returned by `start_mode_b_session`.
- **Prompt version v1 likely won't survive contact with real raws.** Mode B's first ship will be measured by the eval harness against the golden set; auto-research will iterate prompt versions. Plan for v2 / v3 within the first month of real use. The append-only prompt store (RFC-016 / ADR-043) makes this natural.

## Open questions

1. **Should `start_mode_b_session` accept an explicit `from_hash` instead of always forking from HEAD?** Probably yes — the photographer might want to start Mode B from a tagged earlier state, not just current HEAD. Cheap to add; document as a kwarg.
2. **What happens if Mode B is started while another Mode B session is active on the same image?** Reject with `STATE_ERROR`? Allow N parallel sessions on the same image (different `session_id`s)? Probably reject for v1 — same-image concurrent Mode B sessions complicate budget enforcement and review.
3. **Does Mode B respect named-mask references that resolve against the image's snapshots?** Yes, same as Mode A — the named-mask resolution layer is below the session abstraction.
4. **Should `judged_score` be required or optional?** Required, defaulting to 3 (neutral) if the agent can't form a judgment. A branch with no judgment defeats the purpose.
5. **Eval-harness Mode B sessions: how are budgets set?** Probably via the scenario's `scenario.toml` declaring `budget = {time = 600, ...}`. Lets the harness compare "same scenario, same budget, different prompt versions."
6. **How does `mode_b_status` interact with the eval harness?** Probably the harness polls it for progress; the harness ends a session deterministically (no agent "I'm done" call) so the comparison is fair across runs.
7. **The "abandon a variant" semantics.** What does the agent do with an abandoned exploration on `branch_b_color`? Leave the branch with the failed attempts visible? Reset the branch to baseline (so the photographer sees no diff)? Probably leave it visible with the agent's "all variants abandoned, returned to baseline" note — the photographer's audit trail benefits from seeing what was tried.
8. **Should there be a v0.1 "Mode B lite" that runs with no budget enforcement (honor-system only) so the prompt template can be iterated against the eval harness before the engine work lands?** Probably yes — lets prompt iteration happen in parallel with the engine work.

## How this closes

Two ADRs:

- **ADR-NNN — Mode B session protocol** — formalizes the three MCP verbs (`start_mode_b_session`, `end_mode_b_session`, `mode_b_status`), the session record shape in per-image state, the propose-and-confirm gate at session start, the budget-record format.
- **ADR-NNN — Bounded-autonomy enforcement boundary** — formalizes the two-layer enforcement (honor-system + hard-cap), the `BUDGET_EXHAUSTED` error code, the session-vs-engine boundary on budget checking.

A third ADR likely closes the self-evaluation shape (the `judged_score` + `judged_reasoning` structured fields, the coarse 1-5 scale, the abandoned-branch convention) once Phase 5+ work has shipped enough Mode B sessions to evaluate the framing.

**Decision-checkpoint dependency:** This RFC stays Draft until two preconditions land:

1. **The vocabulary is rich enough that exploration produces diverse variants** — PRD-002 explicitly names this as a precondition. v1.10.0's 114 entries across 19 modules probably meets the bar; we'll know when we try.
2. **The eval harness scenario set is populated** — RFC-017 design landed but Phase 5+ scenarios aren't curated yet. Without canonical scenarios, prompt-iteration on Mode B is unanchored.

The implementation work can ship in slices:

- **Slice 1 — prompt + eval-harness wiring.** Mode B v0.1 lite: `mode_b/system_v1.j2` ships; harness can run it headlessly against scenarios; no engine session abstraction; honor-system budget only. Establishes the prompt iteration loop.
- **Slice 2 — session abstraction.** `start_mode_b_session` / `end_mode_b_session` / `mode_b_status` ship; budget hard-cap fires; per-image state grows a `sessions/mode_b/` subdirectory. Mode A doesn't change.
- **Slice 3 — variant surfacing.** `chemigram mode-b show <session_id>` CLI + matching MCP read tool. Existing `log` / `diff` / `compare` verbs handle most of the surfacing; this slice adds the Mode-B-specific structured view.
- **Slice 4 — auto-research loop.** Prompt v2 / v3 / v4 land via the eval harness; metric history captures whether each version improves over its predecessor. Documented in `docs/guides/mode-b-prompt-iteration.md`.

## Links

- TA/components/mcp (3 new verbs)
- TA/components/eval (RFC-017's substrate — built Phase 5)
- TA/contracts/per-image-repo (`sessions/mode_b/<session_id>/` directory shape)
- PA/principles/agent-is-the-only-writer + restraint-before-push + honest-about-limits
- Related: PRD-002 (user-value argument), RFC-017 + ADR-046/047 (eval harness), RFC-016 + ADR-043..045 (prompt store; Mode B prompts ride this), RFC-014 + ADR-061 (end-of-session synthesis; Mode B has a different end-of-session shape)
- Source: roadmap pick — chosen as the v1.11+ "biggest next thing" after v1.10.0 ship per `docs/capability-survey.md` framing
- Blocker: vocabulary breadth (likely met at v1.10.0) + curated eval scenario set (Phase 5+ work to populate)
