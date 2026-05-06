# lem — Framework Design Spec

**Status:** Draft v2 (revised after agent-team review)
**Date:** 2026-05-06

## What it is

`lem` is a framework that turns a one-line idea into a refined, decision-ready brief. A small Python orchestrator spawns headless Claude workers in parallel — each playing a specialist role from the active *profile* — that iterate over a shared markdown workspace. The pipeline branches at decision points where genuine alternatives exist, distills the workspace between phases, and synthesizes a small set of polished deliverables ending in an explicit verdict.

The design goal is "find the best, not the first" — encoded as a Reframe phase that escapes the chosen frame (alternative solution shapes, alternative customers, heretical takes on the premise), opt-in bounded branching (K=2 alternatives only when a real disagreement is detected), heterogeneous critique (four distinct skeptic role files with different prompts and reading inputs), schema-validated structured outputs, and an assumptions register that surfaces what the user confirmed vs. what the system inferred.

`lem` is **domain-general by architecture, single-profile in v1**. The pipeline is independent of what is being refined. Domain-specific knowledge — which roles run, which deliverable templates apply, what the verdict looks like — lives in a *profile*. v1 ships one profile: `app-idea`. v1.1+ adds others.

Named after Stanisław Lem.

## Goals (v1)

- Take a one-liner + ≤3 clarifying answers → produce 3 polished markdown deliverables in 60–90 minutes wall-clock at $10–15 per run, with the `app-idea` profile.
- Force the system to take a position: every run ends with a verdict gated on enough confirmed information to answer responsibly. "Insufficient information" is a first-class recommendation.
- Produce a browsable, Obsidian-friendly workspace with explicit `_archive/` history and structured rejection reasoning.
- Run non-interactively after intake; fire and forget, with clear crash recovery state.
- Architecturally support additional profiles in v1.1+ without changing the orchestrator core.
- Be honest about cost: `--dry-run` token estimator, `meta/cost.jsonl`, hard `--max-cost` ceiling.

## Non-goals (v1)

- No wireframes, UI mockups, or pixels. Text-out only.
- No code scaffolding for the refined idea.
- No real-time competitive intelligence.
- No runtime-generated specialist agents (casting director deferred to v1.1).
- No Refine phase (cut — critique-without-revision is signal enough).
- No multi-profile bundle in v1 (architecture supports it; only `app-idea` ships).
- No concurrent-run coordination (one `lem refine` per workspace root at a time).
- No Windows support (macOS/Linux only; WSL untested).
- No resume from crash in v1 (state is preserved for v1.1 resume).

## Profiles

A profile is a directory containing role files, deliverable templates, a verdict template, and intake guidance:

```
profiles/<name>/
  profile.yaml           # metadata, active roles, branching policy, verdict frame
  roles/                 # specialist role .md files
  deliverables/          # output templates (Jinja2 .md.j2)
  intake-prompt.md       # profile-specific intake guidance
```

`profile.yaml` example (`app-idea`):

```yaml
name: app-idea
description: Refines an app or feature idea into an investor-grade brief
specialists: [architect, designer, market, skeptic]
verdict:
  recommendation_options:
    - Build
    - Refine before building
    - Pivot the angle
    - Don't build
    - Insufficient information
deliverables:
  default: [executive-summary, mvp-plan, risks-and-rejected-paths]
  flag_gated:
    --with-pitch:    investor-onepager
    --with-roadmap:  roadmap
    --with-techstack: tech-stack
```

v1 ships `profiles/app-idea/`. v1.1 candidates: `research-idea`, `business-strategy`, `book-idea`, `product-feature`.

Branching policy and per-role config live in each role's frontmatter, not in `profile.yaml` — keeps role files self-contained.

## Architecture

### Orchestration model: hybrid

Entrypoint: a Claude Code slash command `/lem-refine "<one-liner>"` (and CLI: `lem refine "<one-liner>"`). The command shells to the Python orchestrator, which spawns headless workers for each role-phase pair.

Why hybrid: a 1–3 hour run inside an interactive Claude Code session would lock the user's session. Each worker getting its own clean context avoids quadratic-context cost.

### Worker invocation: hybrid (CLI + SDK)

- **CLI workers (`claude -p`)** for tool-using roles (specialists doing analysis with WebFetch, etc.). Preserves CC's permission model and tool stack.
- **SDK workers (Anthropic SDK direct)** for pure prompt-in/text-out roles (`disagreement-detector`, `distiller`, `pruner`). No tools needed; cleaner cost telemetry; faster.

Worker type is declared in role frontmatter (`worker: cli | sdk`).

### Worker contract

Orchestrator → worker:

```python
@dataclass
class WorkerInvocation:
    role_path: Path                 # path to role .md
    workspace_path: Path            # .lem/runs/<run-id>/
    output_path: Path               # role-scoped, single file
    allowed_read_paths: list[Path]  # whitelist
    model: Literal["haiku", "sonnet", "opus"]
    max_output_tokens: int          # from role frontmatter
    timeout_s: int                  # from role frontmatter
    extra_context: dict[str, str]   # phase-specific (e.g. branch alternative)
```

Worker → orchestrator:

```python
@dataclass
class WorkerResult:
    exit_code: int
    output_path: Path
    tokens_in: int
    tokens_out: int
    cost_usd: float
    duration_s: float
    stop_reason: Literal["end_turn", "max_tokens", "timeout", "error"]
    schema_valid: bool              # set after orchestrator runs validator
    schema_errors: list[str]
```

Success = `exit_code == 0` AND `stop_reason == "end_turn"` AND `schema_valid == True`. Anything else triggers the retry path (see Failure semantics).

### Concurrency and writes

Within a phase, workers fire simultaneously. Phases are serial. Workers:

- Write only to their declared `output_path` (role/phase-scoped, never shared)
- Use atomic writes (`tmp + rename`)
- Read only from `allowed_read_paths` (typically prior-phase outputs only, never sibling-worker outputs)

The orchestrator never schedules two workers to the same output path. Cross-domain coordination happens at phase boundaries only.

### Repository layout

```
lem/
  pyproject.toml
  src/lem/
    cli.py                    # entrypoint (lem refine, lem status, ...)
    orchestrator.py           # main run loop
    phases.py                 # PHASES: list[PhaseSpec], declarative
    intake.py                 # interactive Phase 0
    workers/
      cli_worker.py           # `claude -p` invocation
      sdk_worker.py           # Anthropic SDK invocation
    schema/
      validator.py            # frontmatter + section schema check
    cost/
      tracker.py
      estimator.py
      ceiling.py              # --max-cost enforcement
    failure/
      retry.py                # backoff, circuit breaker
      timeout.py
    state.py                  # state.json read/write
  profiles/
    app-idea/
      profile.yaml
      roles/
      deliverables/
      intake-prompt.md
  process_roles/              # profile-independent: detector, pruner, distiller, ...
  .claude/
    commands/
      lem-refine.md
    agents/                   # symlinks to active profile's roles/ + process_roles/
  templates/
    workspace-readme.md
    obsidian-config/
  README.md
```

### Workspace layout (per run)

```
.lem/runs/<run-id>/
  README.md                         # MOC
  idea.md                           # one-liner + clarified brief
  assumptions.yaml                  # user-confirmed vs agent-assumed
  roster.md                         # active profile + roles + models
  frame-shifter/
    draft-1.md                      # alternative framings, heretical take
  disagreements.md                  # detector output, gates Phase 2
  architecture/
    decision.md                     # winner + WHY (frontmatter-validated)
    option-a.md
    _archive/
      option-b.md                   # losers, structured rejection
  designer/  market/  skeptic/      # same structure
  cross-critique.md
  kill-case.md
  deliverables/
    executive-summary.md            # opens with assumptions, ends with verdict
    mvp-plan.md
    risks-and-rejected-paths.md
  meta/
    state.json                      # {phase, status, started_at, ...}
    events/
      <phase>-<role>-<ts>.json      # per-worker, written by worker
    cost.jsonl                      # aggregated by orchestrator at phase boundaries
    timeline.jsonl
    log.jsonl                       # structured logs
    distilled/
      post-explore.md
  .obsidian/
```

Each run has a unique run-id (timestamp + slug from one-liner). Workspaces live under `.lem/runs/` by default; `--workspace <path>` overrides.

## Roles

Each role is one markdown file. Frontmatter is a **superset** of Claude Code subagent format — CC-compatible keys (`name`, `description`, `model`, `tools`) are preserved so `@architect` works in a CC session, while lem-specific keys (`worker`, `output_cap`, `branchable`, `output_schema`, `phase`, `timeout_s`) are read by the orchestrator and ignored by CC.

Example (`profiles/app-idea/roles/market.md`):

```yaml
---
name: market
description: Names competitors, sizes the market, surfaces saturation.
model: sonnet
worker: cli
phase: discover
output_cap: 1800
timeout_s: 600
branchable: true
output_schema:
  required_frontmatter: [saturation, direct_competitors, closest_analogue, genuine_differentiator]
  required_sections: [TAM, Competitors, Saturation, Differentiator]
  enums:
    saturation: [low, medium, high, very-high]
tools: [WebFetch, WebSearch]
---
You are a market researcher specializing in...
```

### Specialists (Discover phase) — `app-idea` profile

| Role | Model | Worker | Output cap | Branchable |
|---|---|---|---|---|
| `architect` | Sonnet | cli | 1500 | yes |
| `designer` | Sonnet | cli | 1500 | conditional |
| `market` | Sonnet | cli | 1800 | yes |
| `skeptic` | Sonnet | cli | 1500 | no |

### Reframe role — `app-idea` profile

| Role | Model | Worker | Output cap | Phase |
|---|---|---|---|---|
| `frame-shifter` | Sonnet | sdk | 1000 | 0.5 (Reframe) |

Profile-specific (each profile defines its own frame-shifter, since alternative solution shapes differ by domain — `app-idea` thinks about app vs. service vs. community; `research-idea` would think about lab study vs. survey vs. computational simulation).

### Process roles (profile-independent)

| Role | Model | Worker | Output cap | Phase |
|---|---|---|---|---|
| `disagreement-detector` | Sonnet | sdk | 600 | After Discover |
| `branch-skeptic` | Sonnet | cli | 800 | Inside Explore |
| `pruner` | Sonnet | sdk | 400 | End of Explore |
| `distiller` | Haiku | sdk | 1000 | After Explore |
| `cross-skeptic` | Sonnet | cli | 1200 | Phase 3 |
| `kill-case-skeptic` | Sonnet | cli | 1500 | Phase 3 |
| `synthesizer` | Opus | cli | 4000 | Phase 4 |

The Discover-phase `skeptic` and the Phase-3 `kill-case-skeptic` are **different role files** with different system prompts and reading inputs. The kill-case-skeptic reads `cross-critique.md` first and is explicitly forbidden from rehashing Discover concerns — its job is to leverage cross-domain conflicts and unconfirmed assumptions for the strongest case to abandon.

Opus is used for one role only: `synthesizer`. Every other call is Sonnet or Haiku.

## Output schema validation

Every role declares `output_schema` in frontmatter. After each worker exits, `schema/validator.py` checks:

- **Frontmatter**: required keys present, well-typed, enum values legal
- **Sections**: required `## headings` present and non-empty
- **No unresolved placeholders**: `<TBD>`, `<placeholder>`, etc. are rejected

On schema failure:

1. Orchestrator retries the worker once, with the validation errors appended to the prompt as a "fix this" continuation
2. On second failure, the phase is marked failed, workspace is preserved, run aborts with a clear pointer to the offending output

The synthesizer reads structured frontmatter fields directly from `<domain>/decision.md` for verdict-bound fields (saturation, competitors, differentiator). It does **not** read these from the distilled summary — distillation is allowed to drop nuance from prose, but verdict-bound fields are always sourced from raw artifacts.

## Pipeline

| # | Phase | Workers | Model | Wall-clock |
|---|---|---|---|---|
| 0 | Intake | 1 (interactive) | Sonnet | ~5 min |
| 0.5 | Reframe | 1 (frame-shifter) | Sonnet | ~5 min |
| 1 | Discover | 4 parallel | Sonnet | ~20 min |
| 1.5 | Disagreement check | 1 | Sonnet | ~3 min |
| 2 | Explore (per opt-in domain) | K=2 + branch-skeptic + pruner | Sonnet | ~20 min |
| 2.5 | Distill | 1 | Haiku | ~2 min |
| 3 | Cross-Critique | cross-skeptic → kill-case-skeptic (sequential) | Sonnet | ~12 min |
| 4 | Synthesize | 1 | Opus | ~15 min |

Total nominal: ~85 min wall-clock.

### Phase 0 — Intake

Main agent receives the one-liner + chosen profile (`--profile=app-idea` default). Reads the profile's `intake-prompt.md`. If domain, audience, goal, or hard constraints are unclear, asks ≤3 clarifying questions. Writes:

- `idea.md` — clarified brief
- `assumptions.yaml` — every load-bearing assumption flagged as `confirmed: true | false`. Confirmed = explicitly stated in one-liner or clarification answer. Unconfirmed = inferred. Each entry includes `would_change_verdict_if_false: yes | no`.

After Phase 0 the run is non-interactive.

### Phase 0.5 — Reframe

A single Sonnet pass (`frame-shifter` role, profile-specific) reads `idea.md` + `assumptions.yaml` and writes `frame-shifter/draft-1.md` with required sections:

- **Underlying job-to-be-done** — the user need stripped of the proposed solution, one line
- **Alternative solution shapes** — 3–5 non-obvious solution categories that could serve the same job (e.g., for `app-idea`: not just an app — a service, a community, a piece of hardware, a content product, a managed offering)
- **Alternative customer** — who has this problem more acutely than the proposed user?
- **Heretical take** — strongest case the underlying premise is wrong

The frame-shifter prompt is explicitly constraint-shaped to avoid kitsch ("Uber for X" analogies, generic "consider B2B angle" suggestions): it must produce concrete categories with specifics, not abstractions.

Schema-validated. The output becomes input for all Discover specialists.

### Phase 1 — Discover

Profile's specialists fire in parallel. Each reads `idea.md` + `assumptions.yaml` + `frame-shifter/draft-1.md`. Each role's prompt is amended: **before answering, either acknowledge how the alternative framings change your take, or explicitly justify staying with the original frame**. This forces engagement with reframings rather than ignoring them.

Each writes `<role>/draft-1.md` with a required `## Frame engagement` section that names which reframings were considered and why the original frame was kept (or how the take shifted). Schema-validated on completion.

### Phase 1.5 — Disagreement check (gates Phase 2)

A single Sonnet pass reads all specialist drafts and writes `disagreements.md`:

- **Substantive cross-specialist divergences** (e.g., "architect assumes mobile-first; designer's flows assume desktop")
- **Per-domain candidate alternative axes** (e.g., "architecture could fork on monolith vs. microservices; market could fork on consumer vs. SMB")

This output **gates Phase 2 branching**. A domain branches in Phase 2 only if (a) `branchable: true | conditional` in the role's frontmatter AND (b) the detector identified a real candidate alternative axis for that domain. "Always branch" is gone — manufactured alternatives are eliminated.

If <2 substantive cross-specialist divergences are found, a devil's-advocate prompt fires that introduces a deliberately contrarian counter-position to the consensus, written to `disagreements.md`. This addresses the documented sycophantic-convergence failure mode (arXiv 2509.05396, 2502.08788).

### Phase 2 — Explore (opt-in branching)

For each domain that earned branching in Phase 1.5:

1. Specialist generates K=2 alternatives along the named axis → `<domain>/option-a.md`, `option-b.md`
2. Branch-skeptic attacks each alternative
3. Pruner picks the survivor
4. Loser moves to `<domain>/_archive/option-X.md` with structured rejection frontmatter (below)
5. Survivor + `<domain>/decision.md` (chosen path + WHY, links to losers)

Domains that didn't earn branching skip Phase 2 entirely; their `<domain>/draft-1.md` is renamed to `decision.md` with a frontmatter-fill pass.

`_archive/option-X.md` rejection frontmatter (required, schema-validated):

```yaml
rejected: true
alternative: <one-line summary>
specific_tradeoff: <what this option gave up vs the survivor>
revisit_if: <what would need to be true for this to win>
cost_of_being_wrong: <what we lose if survivor turns out worse>
```

This structure prevents handwave rejections like "rejected because higher complexity." The synthesizer reads these into `risks-and-rejected-paths.md`.

### Phase 2.5 — Distill

A single Haiku call summarizes the workspace from ~40K → ~8K tokens, written to `meta/distilled/post-explore.md`. The distilled summary is for *prose context*. Verdict-bound structured fields are always read from raw `<domain>/decision.md` frontmatter, never from the distilled version.

### Phase 3 — Cross-Critique

Sequential (not parallel) Sonnet calls:

1. `cross-skeptic` reads the distilled summary + raw `decision.md` frontmatters; writes `cross-critique.md`: cross-domain conflicts only (e.g., "architect's offline-first contradicts market's freemium model that requires server-side feature gating")
2. `kill-case-skeptic` reads `cross-critique.md` + raw decisions + `assumptions.yaml`; writes `kill-case.md`: the strongest argued case for not building this. Required to leverage cross-domain conflicts and unconfirmed assumptions.

### Phase 4 — Synthesize

One Opus call. Reads:

- `idea.md`, `assumptions.yaml`, `disagreements.md`
- `frame-shifter/draft-1.md` (alternative framings to surface in deliverables)
- All `<domain>/decision.md` files (raw, for verdict-bound fields)
- `meta/distilled/post-explore.md` (for prose context)
- `cross-critique.md`, `kill-case.md`
- All `_archive/*.md` rejection frontmatters

Writes:

- `executive-summary.md` (opens with assumptions register, ends with verdict)
- `mvp-plan.md`
- `risks-and-rejected-paths.md` — must include a "Reframings considered" section that surfaces the frame-shifter's alternative shapes and the structured reasoning for not pivoting (the same `revisit_if` / `cost_of_being_wrong` shape used for branch-archived alternatives)

Optional flag-gated additions: `--with-pitch`, `--with-roadmap`, `--with-techstack`. `--no-verdict` omits the verdict section.

### Deliverable quality guards

Synthesizer prompt enforces:

- **Must cite specifics**: every claim references content from `idea.md` or a specific `<domain>/decision.md`. Generic advice without an anchor is forbidden.
- **No advice-mode verbs without object**: phrases like "consider validating with users" without naming *which users* or *what to ask* are rejected.
- **No filler**: a section that can't be filled with non-trivial content is omitted (and the omission noted in the verdict).

These rules are part of the synthesizer's role prompt, with accept/reject examples.

## Verdict format

The synthesizer's `executive-summary.md` opens with the **Assumptions Register** and ends with the **Verdict** section.

```markdown
## Assumptions

**User-confirmed:**
- <assumption 1, traceable to idea.md or clarification>
- <assumption 2>

**Agent-assumed (not confirmed by user):**
- <assumption A> — would change verdict if false: yes | no
- <assumption B>

[summary body]

## Verdict

**Recommendation:** [Build / Refine before building / Pivot the angle / Don't build / Insufficient information]
**Confidence:** [Low / Medium / High] — one sentence why.

If "Insufficient information": list the 3 questions the user must answer before lem can responsibly recommend.

**Market context:** Saturation <from frontmatter>.
Direct competitors: <names>. Closest analogue: <name>.
Genuine differentiator: <one sentence, or "none material">.

**Strongest case to build:** <steel-manned paragraph>

**Strongest case to abandon:** <steel-manned paragraph>

**What would change our mind:**
- <falsifiable signal 1>
- <falsifiable signal 2>
- <falsifiable signal 3>
```

**Recommendation override rule**: if >50% of load-bearing assumptions are agent-assumed (where `would_change_verdict_if_false: yes`), the recommendation auto-falls to "Insufficient information" regardless of the synthesizer's own preference. Enforced by a small post-synthesis check in the orchestrator that reads `assumptions.yaml` + the verdict and rewrites the recommendation field if needed.

## Failure semantics

### Per-role timeouts

| Role class | Timeout |
|---|---|
| Specialists | 600s (10m) |
| Process roles (detector, branch-skeptic, pruner, cross-skeptic, kill-case-skeptic) | 300s (5m) |
| Distiller | 120s (2m) |
| Synthesizer | 1200s (20m) |

Timeout = SIGTERM with 10s grace, then SIGKILL. One retry. Second timeout = phase failure, run aborts, workspace preserved.

### Retry and backoff

- Anthropic 429 / 529: exponential backoff with jitter (initial 5s, 2× factor, max 60s, max 3 attempts), respect `Retry-After`
- Anthropic 5xx: same backoff, 3 attempts
- Anthropic 401 / 403: fail run immediately
- Worker non-zero exit (other): one retry without backoff
- Schema validation failure: one retry with errors as continuation

### Phase-level circuit breaker

If >50% of workers in a phase fail (after retries), the phase is marked failed and the run aborts. Synthesize phase has no circuit breaker (only one worker).

### Cost ceiling (`--max-cost`)

Default $25. Before each worker dispatch:

```
projected = current_spend + (worker.max_input_estimate × model.input_rate)
                          + (worker.output_cap × model.output_rate)
if projected > max_cost: abort
```

On breach, run aborts with `meta/state.json` set to `cost-aborted`, workspace preserved.

### Atomic writes

All worker outputs use `tmp + rename`. `cost.jsonl`, `timeline.jsonl`, `log.jsonl` are opened with `O_APPEND` (atomic line writes on POSIX). `state.json` is rewritten via `tmp + rename` after each phase boundary.

### Crash inspection

After a crash or kill, the workspace is in a known-good state. `meta/state.json` records `{phase, status, started_at, last_event_at, cost_so_far, error?}`. `lem status <run-id>` reads it. Resume is **out of scope for v1** — but state is preserved so v1.1 can implement resume without re-architecture.

## Observability

- `meta/log.jsonl` — structured per-event log (worker dispatch, completion, schema check, retry, phase boundary)
- `meta/cost.jsonl` — append-only per-worker cost record
- `meta/timeline.jsonl` — append-only per-worker duration record
- `meta/state.json` — current run state
- `lem status <run-id>` CLI — reads state.json + cost.jsonl, prints current phase, elapsed, $ spent, workers in flight
- During a foreground run, the orchestrator streams a one-line summary per worker completion to stderr

## Auth

Anthropic API key resolution order:

1. `ANTHROPIC_API_KEY` env var
2. `~/.lem/config.yaml` `api_key` field
3. Claude Code's stored credentials
4. Fail with a clear error pointing to env var setup

## Cost design

### Per-run target (app-idea profile, normal depth)

- Typical: $10–12
- Range: $8–18
- Hard ceiling: `--max-cost`, default $25

### Levers (in order of impact)

1. **Workspace distillation** between Explore and Cross-Critique — largest single lever
2. **Model tiering**: Opus only for synthesizer (~5% of calls)
3. **Hard output caps** in role frontmatter
4. **Opt-in branching** (Phase 1.5 gates Phase 2)
5. **Prompt caching** within parallel fan-out
6. **`--depth=quick|normal|deep`** — quick disables branching, deep raises K=3

### Cost tracking

Per-worker JSON event in `meta/events/<phase>-<role>-<ts>.json`. Orchestrator aggregates into `meta/cost.jsonl` at phase boundaries (serial — no race). Per-run total in `state.json`.

`lem refine --dry-run "<idea>"` estimates from role caps × planned invocations × model rates without spending tokens.

## Failure modes addressed

- **Sycophantic convergence**: disagreement detector + devil's-advocate pass
- **Critic theater**: four distinct skeptic role files (Discover-skeptic, branch-skeptic, cross-skeptic, kill-case-skeptic) with different prompts and inputs
- **Manufactured alternatives**: branching is opt-in, gated by detected divergence
- **Fake-positive verdict**: assumptions register, schema-enforced market saturation, kill-case mandatory, "Insufficient information" first-class, auto-downgrade rule
- **Generic / advice-mode slop**: synthesizer prompt enforces specifics-required + no-advice-without-object
- **Distillation losing critical info**: synthesizer reads raw decision.md frontmatter for verdict-bound fields
- **Workspace race conditions**: unique output paths per worker, atomic tmp+rename, per-worker event files aggregated at serial phase boundaries
- **Malformed structured output**: schema validation, retry-with-errors, hard-fail with workspace preserved
- **Runaway output**: hard token caps per role
- **Cost runaway from bugs**: `--max-cost` ceiling checked pre-dispatch
- **Hung workers**: per-role timeouts with SIGTERM/SIGKILL escalation
- **Anthropic outages**: exponential backoff, Retry-After respected, phase-level circuit breaker
- **Crash visibility**: state.json + lem status

## Open questions (resolve in implementation plan)

- `.claude/agents/` populated by symlinks or copies?
- Profile selection UX: `--profile` flag (default `app-idea`), or auto-detect from idea?
- Distiller compression aggressiveness: tunable in v1?
- WebFetch budget per market-researcher invocation: cap on number of fetches?

## v1 scope vs deferred

**v1 ships:**

- Pipeline above
- One profile: `app-idea`
- Schema-validated structured outputs
- Failure semantics (timeouts, backoff, circuit breaker, max-cost, atomic writes)
- Observability: `lem status`, JSONL logs, state.json
- Flags: `--profile`, `--depth`, `--dry-run`, `--no-verdict`, `--with-pitch`, `--with-roadmap`, `--with-techstack`, `--max-cost`, `--workspace`
- macOS + Linux

**v1.1 (deferred):**

- Additional profiles: `research-idea`, `business-strategy`, `book-idea`, `product-feature`
- Casting director (runtime-generated specialists)
- Resume from a prior crashed run
- Multi-iteration: re-run lem on the same idea, compare results
- Windows / WSL support
- "Promote to core" command for graduating runtime-generated roles into a profile

## Repository

Public GitHub repo: `tszturo/lem` (the user wrote `tsturo/lem` — likely a typo on the GitHub username; verify before `gh repo create`).

## Appendix: cost math (illustrative, app-idea profile)

- Total tokens per run: ~900K with distillation (~600K input, ~300K output)
- Cost mix (5% Opus synth, 90% Sonnet, 5% Haiku, ~25% effective input cache hit):
  - Input: ~$2.50
  - Output: ~$7.50
  - **Total: ~$10/run**
