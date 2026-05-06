# lem v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to execute this plan. Dispatch one fresh subagent per task. Review output before moving to the next task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **No code in tasks by design.** Each task gives outcome, files, acceptance criteria, and test expectations. The implementing subagent decides the code. Mark decision points (`> DECISION:`) require either a defensible default with rationale OR a question back to the human.

**Goal:** Build lem v1 — a Python-orchestrated multi-agent CLI that refines a one-line app idea into 3 polished markdown deliverables (executive-summary, mvp-plan, risks-and-rejected-paths) ending in an explicit verdict.

**Architecture:** A Python `typer` CLI dispatches a daemonized Python orchestrator process. The orchestrator runs a declarative pipeline of phases, each spawning `claude -p --output-format json` subprocesses with role-specific system prompts. Workers read/write a shared markdown workspace (Obsidian-friendly). A `textual` TUI reads workspace meta files for live status. Outputs are validated against per-role frontmatter+section schemas with retry-on-failure.

**Tech Stack:** Python 3.11+, typer, pyyaml, jinja2, textual, rich, pytest, ruff, pyright, pipx for install. No Anthropic SDK (auth piggybacks on `claude` CLI). No frontend stack. No database.

**Source of truth for design:** `docs/superpowers/specs/2026-05-06-lem-framework-design.md` (v2 with chat deltas — material updates from chat are inlined in this plan; refer to spec for design rationale).

**Material design deltas from spec v2 (already encoded in this plan):**
- Drop SDK worker mode entirely — all workers via `claude -p` CLI; auth via `claude` CLI
- Drop Discover-skeptic specialist; 3 specialists (architect, designer, market)
- Phase 0.5 = JTBD-extract (one line), Phase 1.6 = full frame-shifter (contrastive)
- Tighten architect/designer schemas to non-overlapping frontmatter
- Expand market schema (business_model, customer_development_signal, target_user_acuteness)
- Skeptic outputs: schema-enforced (per-option attack / conflict pairs / leveraged assumptions)
- `## Upstream sanity` section required for any role consuming a single upstream artifact
- `exit_criteria` per required_section in role frontmatter
- Auto-downgrade rule moved pre-synthesis (`verdict_constraint` in synthesizer's extra_context)
- Hoist frame-shifter and skeptics into `process_roles/`
- Default model tier `opus-heavy` (every specialist + skeptic + frame-shifter + pruner + synthesizer on Opus; disagreement-detector on Sonnet; distiller on Haiku)
- Background-default for `lem refine`; `--attach` for foreground TUI
- XDG storage default (`$XDG_DATA_HOME/lem/runs/`); git-style upward walk for `.lem/` opt-in
- Tokens+wall-clock display by default; `--show-cost` for dollars
- Drop decimal phase numbers from primary view (linear named view)
- 7 visible CLI verbs: `refine`, `watch`, `list`, `show`, `logs`, `rerun`, `cancel`
- `--max-wall-clock` flag (default 4h); stalled-worker detection via median × 3
- Hooks: `on_complete`, `on_error`, `--webhook`
- `lem render <id>` static HTML report
- No web UI in v1

---

## File Structure

```
lem/
  pyproject.toml                       # Python package config + deps
  README.md                            # User-facing docs
  .gitignore                           # Standard Python + .lem/, .venv/, etc.
  docs/                                # Spec, plan, future ADRs
  src/lem/
    __init__.py
    cli.py                             # typer app, command registration
    types.py                           # Dataclasses: WorkerInvocation, WorkerResult, PhaseSpec, Role, Profile, RunState
    paths.py                           # XDG resolution, workspace location, run-id generation
    auth.py                            # claude CLI presence + auth check
    intake.py                          # Phase 0 interactive flow
    orchestrator.py                    # Main run loop, phase iteration, daemon entry
    daemon.py                          # POSIX double-fork detach
    phases.py                          # Declarative PHASES: list[PhaseSpec]
    profile.py                         # Profile loader (profile.yaml + roles)
    workers/
      cli_worker.py                    # claude -p subprocess wrapper
      dispatch.py                      # Worker invocation with timeout, retry, schema validation
    schema/
      parser.py                        # Frontmatter + section parser (role files, output files)
      validator.py                     # Output schema validation against role's declared schema
    state/
      run_state.py                     # state.json read/write, atomic
      events.py                        # meta/events/*.json writer
      cost.py                          # cost.jsonl + tracking (notional dollar tracking)
      timeline.py                      # timeline.jsonl
      log.py                           # log.jsonl structured logging
    failure/
      timeout.py                       # SIGTERM-then-SIGKILL with grace
      retry.py                         # Exponential backoff for 429/5xx, schema retry
      breaker.py                       # Phase-level circuit breaker
      ceiling.py                       # --max-cost + --max-wall-clock pre-checks
      stalled.py                       # Median × 3 stalled-worker detection
    control.py                         # meta/control.json polling for TUI commands (pause/resume/cancel)
    hooks.py                           # on_complete, on_error, webhook
    notify.py                          # Terminal bell + osascript/notify-send
    render/
      report.py                        # `lem render` static HTML generator
      template.html                    # Jinja2 template for static report
    tui/
      app.py                           # textual App entry
      main_view.py                     # Pipeline + active workers + recent + issues
      worker_view.py                   # Per-worker drill-down
      phase_view.py                    # Per-phase drill-down
      artifact_view.py                 # Inline rendered markdown
      logs_view.py                     # Filterable log tail
      tree_view.py                     # Workspace file browser
      controls.py                      # Key bindings, control.json writer
    commands/
      refine.py                        # `lem refine`
      watch.py                         # `lem watch`
      list.py                          # `lem list`
      show.py                          # `lem show` (with --in pager|obsidian|browser)
      logs.py                          # `lem logs`
      rerun.py                         # `lem rerun`
      cancel.py                        # `lem cancel`
      render.py                        # `lem render`
  process_roles/                       # Profile-independent role files
    jtbd-extractor.md
    frame-shifter.md                   # Profile supplies a domain prompt fragment via {{prompt_fragment}}
    disagreement-detector.md
    branch-skeptic.md
    pruner.md
    distiller.md
    cross-skeptic.md
    kill-case-skeptic.md
    synthesizer.md
  profiles/
    app-idea/
      profile.yaml                     # Specialists list, branching policy, verdict frame, deliverable list
      intake-prompt.md                 # Profile-specific intake guidance
      prompt-fragments/
        frame-shifter.md               # app-idea-specific framing prompt fragment
      roles/
        architect.md
        designer.md
        market.md
      deliverables/
        executive-summary.md.j2
        mvp-plan.md.j2
        risks-and-rejected-paths.md.j2
        investor-onepager.md.j2        # flag-gated
        roadmap.md.j2                  # flag-gated
        tech-stack.md.j2               # flag-gated
  templates/
    workspace-readme.md.j2             # Initial MOC written at run start
    obsidian-config/                   # .obsidian/ files copied per workspace
  .claude/
    commands/
      lem-refine.md                    # CC slash command
    agents/                            # Symlinks to active profile's roles + process_roles
  tests/
    unit/                              # Per-module
    integration/                       # Multi-module flows
    e2e/                               # Stub-profile end-to-end runs
    fixtures/
      stub-profile/                    # Mock profile with deterministic stub workers (no API calls)
      sample-runs/                     # Pre-baked workspace dirs for testing read commands
```

Each file has a single, focused responsibility. Tests mirror the source layout under `tests/unit/`.

---

## Execution notes

- **TDD**: every task includes "Tests should cover" — write tests first, run, fail, implement, pass, commit. Subagent decides specific test code.
- **Commits**: at the end of each task. Commit message format: `<phase-id>.<task-id>: <one-line summary>`.
- **`> DECISION:`** markers in tasks call out judgment-required moments. Implementer should pick a defensible default with a one-line rationale in commit message OR ask the human.
- **Stub profile** (fixtures/stub-profile/) provides deterministic workers that return canned outputs — used heavily for testing without API calls.

---

## Phase 1: Bootstrap

### Task 1.1: Initialize Python project

**Outcome**: A working `pyproject.toml` with Python 3.11+ requirement, runtime deps (typer, pyyaml, jinja2, textual, rich), dev deps (pytest, ruff, pyright), entrypoint `lem = "lem.cli:app"`. Project installable with `pip install -e .` and `lem --help` works.

**Files**:
- Create: `pyproject.toml`
- Create: `src/lem/__init__.py` (with `__version__`)
- Create: `src/lem/cli.py` (typer app stub with `--help`/`--version`)

**Acceptance**:
- `pip install -e .` succeeds in a fresh venv
- `lem --help` exits 0 and prints command list (empty for now)
- `lem --version` prints version
- `pytest` exits 0 (no tests yet, but pytest must be configured)
- `ruff check src/` and `pyright src/` pass

**Tests should cover**: existence of `lem.__version__`, version flag returns it.

> DECISION: build backend (hatchling vs setuptools vs pdm). Pick one with rationale.

---

### Task 1.2: Directory scaffold

**Outcome**: Empty modules and directories per the File Structure above. All `__init__.py` files in place. Each module file has a one-line docstring stating its responsibility.

**Files**:
- Create all directories under `src/lem/`, `process_roles/`, `profiles/app-idea/`, `templates/`, `tests/`, `.claude/commands/`, `.claude/agents/` as specified
- Create `__init__.py` in every Python package dir
- Create empty placeholders for module files (one-line docstring only)
- Create `.gitignore` (standard Python + `.venv/`, `.lem/`, `dist/`, `build/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`)

**Acceptance**:
- `tree src/lem` matches File Structure exactly
- `tree process_roles profiles tests` matches
- `python -c "import lem.cli"` succeeds
- `python -c "import lem.orchestrator"` succeeds (and every other module)
- `.gitignore` excludes the right things

**Tests should cover**: importability of every module (a single `test_imports.py` that imports all top-level modules).

---

### Task 1.3: Initial commit + GitHub repo

**Outcome**: Local git repo initialized, all bootstrap files committed, GitHub repo `tszturo/lem` (verify username with user before creating) created public, initial commit pushed.

**Files**: none new

**Acceptance**:
- `git log` shows at least one commit
- `gh repo view` shows the public repo with the README+spec+plan committed
- A clone of the remote can `pip install -e .` and run `lem --help`

> DECISION: confirm GitHub username `tszturo` before `gh repo create`. The original prompt said `tsturo` — likely a typo. ASK the human if uncertain.

> DECISION: license. Pick one with rationale (MIT is the default unless user objects).

---

## Phase 2: Core Types & I/O

### Task 2.1: Core dataclasses

**Outcome**: `src/lem/types.py` defines all dataclasses used across modules: `WorkerInvocation`, `WorkerResult`, `PhaseSpec`, `Role`, `Profile`, `RunState`, `CostEvent`, `LogEvent`. Frozen where mutability isn't needed.

**Files**:
- Create: `src/lem/types.py`
- Test: `tests/unit/test_types.py`

**Acceptance**:
- All dataclasses present with the fields specified in the spec (Worker contract section)
- Type hints are precise (Literal for enums, explicit Optional)
- pyright passes with strict mode on this file
- Each dataclass instantiable from the test fixtures

**Tests should cover**: instantiation, field defaults, frozen immutability where applicable.

---

### Task 2.2: Role + output frontmatter parser

**Outcome**: `src/lem/schema/parser.py` parses markdown files with YAML frontmatter into a structured form: `(frontmatter: dict, body: str, sections: dict[str, str])`. Used for both role files and worker outputs.

**Files**:
- Create: `src/lem/schema/parser.py`
- Test: `tests/unit/test_parser.py`
- Fixtures: `tests/fixtures/parser/` (sample valid + malformed files)

**Acceptance**:
- Parses standard `---\n...\n---\nbody` format
- Returns frontmatter as parsed YAML (dict)
- Splits body into sections keyed by `## Heading` (H2)
- Detects malformed frontmatter (raises with line number)
- Detects missing closing `---` (raises clearly)
- Handles files with no frontmatter (frontmatter={})

**Tests should cover**: valid file, no frontmatter, malformed YAML, missing closing fence, multiple H2 sections, H2 inside code block (must not be treated as section).

---

### Task 2.3: Output schema validator

**Outcome**: `src/lem/schema/validator.py` validates a parsed worker output against a role's declared `output_schema`. Returns `ValidationResult(valid: bool, errors: list[str])`. Errors are actionable (point to specific issue with location).

**Files**:
- Create: `src/lem/schema/validator.py`
- Test: `tests/unit/test_validator.py`
- Fixtures: `tests/fixtures/validator/` (valid + invalid output samples)

**Acceptance**:
- Checks `required_frontmatter` keys are present and well-typed
- Checks `required_sections` are present (matched by H2 heading) and non-empty
- Checks `enums` (e.g., `saturation: [low, medium, high, very-high]`) — value must be in list
- Checks `exit_criteria` (when expressible — e.g. minimum count of bullet points or named items in a section)
- Detects unresolved placeholders in body: `<TBD>`, `<placeholder>`, `[TODO]`, `<...>` patterns
- Returns multiple errors at once (don't bail on first)

**Tests should cover**: valid output, each individual failure mode, multiple simultaneous failures, edge cases (empty section, only-whitespace section, placeholder inside code block — should NOT trigger).

> DECISION: how to express `exit_criteria` declaratively. Suggested: a small DSL ("min_bullets: 3", "names_count: ≥3"). Alternative: free-form string the validator can't check (just a hint to the prompt). Pick simplest that covers obvious cases.

---

## Phase 3: Worker layer

### Task 3.1: CLI worker wrapper

**Outcome**: `src/lem/workers/cli_worker.py` provides a function that invokes `claude -p --output-format json` as a subprocess with: system prompt from role body, allowed tools from role frontmatter, model from role frontmatter, max-output-tokens from role's `output_cap`, working directory set, input prompt assembled from workspace files referenced in `WorkerInvocation.allowed_read_paths`.

**Files**:
- Create: `src/lem/workers/cli_worker.py`
- Test: `tests/unit/test_cli_worker.py`

**Acceptance**:
- Builds the correct `claude -p` command line for a given `WorkerInvocation`
- Captures stdout (JSON) + stderr (logs) without mixing
- Parses claude's JSON envelope to extract output text + token usage
- Writes worker output to `output_path` atomically (tmp + rename)
- Returns a populated `WorkerResult` with all fields set
- Distinguishes `stop_reason`: end_turn / max_tokens / error
- Surfaces claude CLI auth error (exit 69 mapped from claude's error)

**Tests should cover**: command-line construction (parametrized over models / tools / prompts), JSON parsing (incl. malformed envelope), stdout capture, output file written atomically, stop_reason detection. Use a stubbed `claude` script in tests/fixtures/ that produces canned JSON.

> DECISION: how to discover claude CLI path (PATH lookup vs configurable). Default: PATH; configurable via `LEM_CLAUDE_BIN` env var.

> DECISION: prompt assembly format — how do `allowed_read_paths` get embedded? Suggested: workspace files inlined as fenced markdown sections in the user-prompt, with explicit "READ-ONLY context" framing. Implementer picks the exact format; document it.

---

### Task 3.2: Worker dispatch with timeout

**Outcome**: `src/lem/workers/dispatch.py` provides `dispatch_worker(inv: WorkerInvocation) -> WorkerResult` that runs `cli_worker.invoke(inv)` under a wall-clock timeout (from role frontmatter), with SIGTERM-then-SIGKILL escalation (10s grace).

**Files**:
- Create: `src/lem/workers/dispatch.py`
- Create: `src/lem/failure/timeout.py`
- Test: `tests/unit/test_dispatch_timeout.py`

**Acceptance**:
- Subprocess timeout enforced precisely (within 200ms)
- SIGTERM sent at timeout, then SIGKILL after 10s if still alive
- Returns `WorkerResult` with `stop_reason="timeout"` on timeout
- Output file is NOT written on timeout (leaves no partial file)
- Logs the timeout event to log.jsonl

**Tests should cover**: timeout fires correctly, SIGTERM sent, SIGKILL sent if SIGTERM ignored, partial file not left behind, fast-completing invocation isn't impacted.

---

### Task 3.3: Retry + schema validation loop

**Outcome**: `dispatch_worker` (extended) wraps the timeout layer with: schema validation after success, one retry on schema failure (with errors as a continuation prompt), exponential backoff for 429/5xx, retry-once on non-zero exit. Final retry-exhausted state is recorded; preserves partial workspace.

**Files**:
- Modify: `src/lem/workers/dispatch.py`
- Create: `src/lem/failure/retry.py`
- Test: `tests/unit/test_dispatch_retry.py`, `tests/unit/test_retry.py`

**Acceptance**:
- Successful first attempt → returns immediately
- Schema-invalid first attempt → retry once with errors appended; success on second → ok; second failure → mark phase-failed
- 429 response → exponential backoff (5s base, 2× factor, max 60s, max 3 attempts), respect `Retry-After` header
- 5xx → same backoff, 3 attempts
- 401/403 → fail run immediately (exit code 69)
- All retries logged; cost.jsonl includes failed attempts

**Tests should cover**: successful first try, retry on schema fail, retry on 429, backoff timing, Retry-After honored, 401 fails immediately, retry exhaustion.

---

## Phase 4: State, Cost, Failure

### Task 4.1: RunState + meta/ atomic writes

**Outcome**: `src/lem/state/run_state.py` manages `meta/state.json` lifecycle: read, write (atomic tmp+rename), update phase/status/cost/timing fields. `src/lem/state/events.py` writes per-worker events to `meta/events/<phase>-<role>-<ts>.json`. `src/lem/state/log.py` does append-only structured JSONL logging.

**Files**:
- Create: `src/lem/state/run_state.py`
- Create: `src/lem/state/events.py`
- Create: `src/lem/state/log.py`
- Test: `tests/unit/test_state.py`

**Acceptance**:
- state.json always atomically written (tmp+rename)
- Reading state.json mid-write never sees a partial file (verify with concurrent test)
- log.jsonl uses O_APPEND for atomic line writes
- events/<id>.json uniquely named (timestamp + collision suffix)
- Graceful when meta/ doesn't exist (creates it)

**Tests should cover**: atomic write under concurrent reads, JSONL append safety, unique event filenames, schema of state.json (keys + types), recovery from partial state (corrupt file → log error, continue).

---

### Task 4.2: Cost tracker

**Outcome**: `src/lem/state/cost.py` tracks notional cost per worker per phase. Aggregates `meta/events/*.json` into `meta/cost.jsonl` at phase boundaries. Knows model rates (in `lem/state/rates.py` or constants in cost.py). Notional on Max — display gated by `--show-cost`.

**Files**:
- Create: `src/lem/state/cost.py`
- Create: `src/lem/state/timeline.py`
- Test: `tests/unit/test_cost.py`

**Acceptance**:
- Per-worker cost computed from tokens_in × rate_in + tokens_out × rate_out
- Phase total = sum of worker costs
- Run total = sum of phase totals
- cost.jsonl writes one line per worker (after phase boundary)
- timeline.jsonl writes one line per worker with start/end/duration
- Rates are constants for haiku/sonnet/opus (input + output rates)
- Output: tokens + duration are primary, dollars are computed but optional for display

**Tests should cover**: cost arithmetic, aggregation correctness, JSONL line format, rate table.

> DECISION: keep model rates as a constant table or read from a config file. Default: constants in code, with a `LEM_RATES_FILE` env override for users who want custom rates.

---

### Task 4.3: Cost ceiling + wall-clock cap pre-checks

**Outcome**: `src/lem/failure/ceiling.py` provides `check_cost_ceiling(state, projected_worker_cost) -> bool` and `check_wall_clock(state) -> bool`. Called by orchestrator before each worker dispatch. Aborts run with `state.status = "cost-aborted"` or `"wall-clock-aborted"` on breach. Workspace preserved.

**Files**:
- Create: `src/lem/failure/ceiling.py`
- Test: `tests/unit/test_ceiling.py`

**Acceptance**:
- Cost projection: `current_spend + worker.input_estimate × rate + worker.output_cap × rate`
- Wall-clock: `now - run.started_at > max_wall_clock`
- Default `max-cost`=$25, `max-wall-clock`=4 hours
- Both checks run pre-dispatch
- Breach → orchestrator aborts run cleanly (writes final state.json, runs `on_error` hook)

**Tests should cover**: pass-through under ceiling, abort at ceiling, abort at wall-clock, projection arithmetic.

---

### Task 4.4: Stalled-worker detection

**Outcome**: `src/lem/failure/stalled.py` computes the median runtime per role across past runs (read from `meta/timeline.jsonl` files in the runs directory). A currently-running worker is "stalled" if `now - started > 3 × median`. Pure function — used by TUI for badge display, NOT by orchestrator for kill (kill is via hard timeout).

**Files**:
- Create: `src/lem/failure/stalled.py`
- Test: `tests/unit/test_stalled.py`

**Acceptance**:
- Reads timeline.jsonl from all past runs to compute per-role medians
- Falls back to a baseline (e.g., 60s) when no history exists
- Returns `(stalled: bool, median: float, threshold: float)` per worker
- Tolerant of missing/malformed history files

**Tests should cover**: median computation, fallback when no history, edge cases (1 sample, all same time, missing files).

---

## Phase 5: Orchestrator

### Task 5.1: PhaseSpec + declarative pipeline

**Outcome**: `src/lem/phases.py` defines `PhaseSpec` and a module-level `PHASES: list[PhaseSpec]` describing the entire pipeline declaratively. Each PhaseSpec has: id, name (linear, no decimals shown), workers_fn (returns list of WorkerInvocation given current state + profile), parallel (bool), gate_fn (skip phase if predicate false).

**Files**:
- Create: `src/lem/phases.py`
- Test: `tests/unit/test_phases.py`

**Acceptance**:
- 9 phases declared: intake, jtbd-extract, discover, disagreement-check, reframe, explore, distill, cross-critique, synthesize
- Each phase has clear workers_fn that reads profile + state + workspace and returns invocations
- explore.gate_fn returns false unless disagreement-detector found ≥1 candidate axis
- Internal phase IDs use decimals (0, 0.5, 1, 1.5, 1.6, 2, 2.5, 3, 4) for spec correspondence
- Display name is decimals-free ("Intake", "JTBD", "Discover", "Disagreement", "Reframe", "Explore", "Distill", "Critique", "Synthesize")

**Tests should cover**: PHASES list integrity, workers_fn invocation with sample state, gate_fn correctness for explore, profile-driven specialist count.

---

### Task 5.2: Orchestrator main loop

**Outcome**: `src/lem/orchestrator.py` provides `run_orchestrator(workspace_path, profile, config)` that iterates `PHASES`, dispatches each phase's workers (parallel or sequential per spec), polls `meta/control.json` for pause/resume/cancel between phases, updates state.json at boundaries, runs hooks at end.

**Files**:
- Create: `src/lem/orchestrator.py`
- Create: `src/lem/control.py`
- Test: `tests/integration/test_orchestrator_stub.py`

**Acceptance**:
- Iterates phases in PHASES order
- Skipped phases respect gate_fn
- Parallel phases dispatch workers concurrently (asyncio or concurrent.futures), respecting `--max-concurrent`
- Sequential phases dispatch in order, blocking
- Reads `meta/control.json` between phases: `{action: "pause" | "resume" | "cancel"}`
- On pause: blocks until resume action appears
- On cancel: kills active workers, writes final state, exits cleanly
- On phase failure (>50% workers fail or schema retries exhausted): aborts run, preserves workspace
- Calls `on_complete` or `on_error` hook at end
- Calls webhook if configured

**Tests should cover** (using stub-profile):
- Full pipeline runs end-to-end with stubbed workers
- Pause/resume mid-run via control.json injection
- Cancel mid-phase
- Phase failure aborts run
- Wall-clock cap aborts mid-run
- Cost ceiling aborts mid-run

> DECISION: asyncio vs concurrent.futures.ThreadPoolExecutor for parallel worker dispatch. Default: asyncio (cleaner for subprocess management). Implementer can change if there's a strong reason.

---

### Task 5.3: Phase circuit breaker

**Outcome**: `src/lem/failure/breaker.py` evaluates phase health after all workers complete. If failure rate > 50% (configurable), phase is marked failed and orchestrator aborts run. Synthesize phase has no breaker (single worker — already covered by retry).

**Files**:
- Create: `src/lem/failure/breaker.py`
- Test: `tests/unit/test_breaker.py`

**Acceptance**:
- Computes failure rate from WorkerResults
- Threshold default 50%, configurable per-phase
- Returns `(should_abort: bool, reason: str)`

**Tests should cover**: 0% / 25% / 50% / 75% / 100% failure rates, single-worker phase (synthesize) bypasses breaker.

---

### Task 5.4: Daemonization

**Outcome**: `src/lem/daemon.py` provides `daemonize(workspace_path)` that POSIX-double-forks the orchestrator, redirects stdio to log files, returns to caller (in original process) with the run-id printed to stdout. Used by `lem refine` (default) and skipped by `--attach`.

**Files**:
- Create: `src/lem/daemon.py`
- Test: `tests/integration/test_daemon.py`

**Acceptance**:
- After daemonize() returns in parent, child process is detached (different process group, no controlling terminal)
- Child stdout/stderr redirect to `meta/log.jsonl` (JSON lines)
- Child stdin from /dev/null
- Parent process exits cleanly with the run-id on stdout
- Child process survives parent exit (verified by ps after parent exits)
- Skipped on `--attach` mode (orchestrator runs in foreground)

**Tests should cover**: child survives parent exit, stdout/stderr redirected, run-id printed exactly once on stdout, non-POSIX (Windows) raises clear NotImplementedError.

> DECISION: macOS-specific quirks (e.g., setsid behavior). Test on macOS specifically. Linux is assumed; Windows out of scope.

---

## Phase 6: Phase implementations

Each task in this phase implements ONE pipeline phase by writing the phase's `workers_fn` (and `gate_fn` if applicable). They all share the orchestrator infrastructure built in Phase 5.

### Task 6.1: Intake (Phase 0)

**Outcome**: `src/lem/intake.py` implements interactive intake. Reads profile's `intake-prompt.md`, asks ≤3 questions in the terminal, writes `idea.md` (clarified brief) and `assumptions.yaml` (each load-bearing assumption flagged confirmed/unconfirmed with `would_change_verdict_if_false`). Skipped when `--skip-intake` (slash-command flow does intake itself before invoking `lem refine --skip-intake`).

**Files**:
- Create: `src/lem/intake.py`
- Test: `tests/unit/test_intake.py`

**Acceptance**:
- Reads profile's intake-prompt
- Asks at most 3 questions
- Generates idea.md from one-liner + answers
- Generates assumptions.yaml with explicit confirmed/unconfirmed flags
- Schema-validates assumptions.yaml on write

**Tests should cover**: question generation under various one-liners, idea.md structure, assumptions.yaml fields, --skip-intake path.

> DECISION: how is intake intelligence achieved? Two options: (a) intake is itself a `claude -p` worker dedicated to intake, with a system prompt that tells it to ask + write the files; (b) intake is hand-coded prompt logic in Python with a small claude call per question. Pick (a) — simpler, more flexible. Implementer documents.

---

### Task 6.2: JTBD-extract (Phase 0.5)

**Outcome**: `phases.py` `jtbd_extract_workers_fn` returns a single worker invocation for the `jtbd-extractor` process role. Output: `frame-shifter/jtbd.md` containing one line stripped to the underlying job-to-be-done.

**Files**:
- Modify: `src/lem/phases.py`
- Create: `process_roles/jtbd-extractor.md` (in Phase 7.3, but referenced here)
- Test: `tests/integration/test_phase_jtbd.py` (with stub profile)

**Acceptance**:
- Single worker dispatch
- Output is a single line `## Job to be done: <one line>`
- Schema enforces non-empty single-line content

**Tests should cover**: phase produces exactly one file in expected path, schema validates.

---

### Task 6.3: Discover (Phase 1)

**Outcome**: `phases.py` `discover_workers_fn` returns parallel worker invocations for the profile's specialists. Each reads `idea.md`, `assumptions.yaml`, `frame-shifter/jtbd.md`. Each writes `<role>/draft-1.md` with required `## Frame engagement` section listing JTBD considerations.

**Files**:
- Modify: `src/lem/phases.py`
- Test: `tests/integration/test_phase_discover.py`

**Acceptance**:
- 3 specialists for app-idea profile dispatched in parallel
- Each reads correct allowed_read_paths
- Each output validates against role's schema (incl. Frame engagement section)
- Specialists count matches profile.yaml

**Tests should cover**: 3 workers dispatched, allowed_read_paths correct, schema enforced.

---

### Task 6.4: Disagreement check + branching gate (Phase 1.5)

**Outcome**: `phases.py` `disagreement_workers_fn` returns one worker (disagreement-detector). Output `disagreements.md` lists substantive divergences AND per-domain candidate alternative axes. Devil's-advocate prompt fires automatically if <2 substantive divergences detected. Output gates Phase 2 branching: a domain branches in Phase 2 only if (a) role.branchable AND (b) detector identified an axis for that domain.

**Files**:
- Modify: `src/lem/phases.py`
- Test: `tests/integration/test_phase_disagreement.py`

**Acceptance**:
- Single detector worker dispatched
- Output schema includes `axes_by_domain: {<domain>: <axis_description>}` (possibly empty per domain)
- Devil's-advocate auto-fires if substantive divergences <2 (sub-step within Phase 1.5)
- Phase 2 branching gate reads `axes_by_domain` to decide which domains branch

**Tests should cover**: high-divergence path, low-divergence triggers devil's-advocate, gate logic for explore phase.

---

### Task 6.5: Reframe (Phase 1.6)

**Outcome**: `phases.py` `reframe_workers_fn` returns one worker (frame-shifter, profile-supplied prompt fragment). Reads all Discover drafts + JTBD. Writes `frame-shifter/draft-1.md` with required sections: `## Underlying job`, `## Alternative shapes`, `## Alternative customer`, `## Heretical take`. IDs assigned to each alternative shape so synthesizer can reference them.

**Files**:
- Modify: `src/lem/phases.py`
- Test: `tests/integration/test_phase_reframe.py`

**Acceptance**:
- Single worker
- Reads Discover outputs + JTBD as inputs
- Output schema includes structured alternative shapes with IDs (e.g., `alt-001`, `alt-002`)
- Heretical take section is required and non-empty

**Tests should cover**: schema enforcement, IDs assigned and unique, all required sections present.

---

### Task 6.6: Explore (Phase 2)

**Outcome**: `phases.py` `explore_workers_fn` returns invocations for opt-in branching domains: per domain that earned branching, K=2 alternative-generator invocations for the specialist + branch-skeptic invocations + pruner invocation. Domains that didn't earn branching: rename `draft-1.md` → `decision.md` with frontmatter-fill pass.

**Files**:
- Modify: `src/lem/phases.py`
- Test: `tests/integration/test_phase_explore.py`

**Acceptance**:
- Branching only for domains gated in (per Phase 1.5)
- K=2 (configurable per `--depth`: 1 quick, 2 normal, 3 deep)
- Each option: specialist generates → branch-skeptic attacks → pruner picks survivor
- Loser → `<domain>/_archive/option-X.md` with structured rejection frontmatter (alternative, specific_tradeoff, revisit_if, cost_of_being_wrong)
- Survivor → `<domain>/decision.md` with chosen path + WHY + links to losers
- Non-branching domains: draft-1.md → decision.md

**Tests should cover**: branching path, non-branching path, K respected, archive frontmatter present, decision.md links to archive.

---

### Task 6.7: Distill (Phase 2.5)

**Outcome**: Single Haiku invocation summarizing the workspace. Reads all decision.md files + cross-cutting artifacts. Writes `meta/distilled/post-explore.md` (~8K tokens). Verdict-bound fields are NOT distilled — synthesizer reads them raw.

**Files**:
- Modify: `src/lem/phases.py`
- Test: `tests/integration/test_phase_distill.py`

**Acceptance**:
- Haiku model
- Output schema: required headings matching domain count + assumption summary + reframings summary
- Output size approximately 8K tokens (output_cap enforces hard ceiling; prompt asks for compactness)

**Tests should cover**: schema, size ceiling.

---

### Task 6.8: Cross-Critique (Phase 3)

**Outcome**: Two sequential workers. (1) `cross-skeptic` reads distilled summary + raw decision.md frontmatters, writes `cross-critique.md` with structured `conflict_pairs`. (2) `kill-case-skeptic` reads `cross-critique.md` + raw decisions + `assumptions.yaml`, writes `kill-case.md` with structured `kill_argument` + `assumptions_leveraged` + `conflicts_leveraged` (both must be non-empty, IDs from upstream).

**Files**:
- Modify: `src/lem/phases.py`
- Test: `tests/integration/test_phase_cross_critique.py`

**Acceptance**:
- Sequential dispatch (kill-case after cross-skeptic completes)
- cross-critique.md schema enforces conflict_pairs structure
- kill-case.md schema enforces non-empty leveraged lists with valid upstream IDs
- Each role has `## Upstream sanity` section flagging unsupported upstream claims (1–3 bullets, may be empty but heading required)

**Tests should cover**: sequential ordering, schema for both, upstream sanity heading required.

---

### Task 6.9: Synthesize (Phase 4)

**Outcome**: Single Opus worker. Pre-synthesis: orchestrator computes the assumptions ratio (load-bearing unconfirmed / total). Passes `verdict_constraint: "insufficient_info" | "free_choice"` in worker's extra_context. Synthesizer writes `executive-summary.md` (with assumptions register opening + verdict closing), `mvp-plan.md`, `risks-and-rejected-paths.md` (must include "Reframings considered" section drawn from frame-shifter output IDs).

**Files**:
- Modify: `src/lem/phases.py`
- Test: `tests/integration/test_phase_synthesize.py`

**Acceptance**:
- Opus model
- verdict_constraint computed pre-dispatch and passed as context
- Three default deliverables generated
- Flag-gated additions: `--with-pitch`, `--with-roadmap`, `--with-techstack`
- `--no-verdict` omits verdict section
- Schema-validated

**Tests should cover**: verdict_constraint logic (50% threshold), 3 deliverables present, flag-gated additions, no-verdict path, reframings IDs present in risks artifact.

---

## Phase 7: app-idea Profile content

These tasks produce the actual prompts and templates. **Quality matters here — these are the soul of lem. The implementing subagent should DRAFT each role/template, then halt for human review before final commit.**

### Task 7.1: Profile metadata + intake prompt

**Outcome**: `profiles/app-idea/profile.yaml` declaring specialists (architect, designer, market), branching policy (architect: yes, designer: conditional, market: yes), verdict frame (5 options including "Insufficient information"), deliverable list. `profiles/app-idea/intake-prompt.md` with profile-specific intake guidance.

**Files**:
- Create: `profiles/app-idea/profile.yaml`
- Create: `profiles/app-idea/intake-prompt.md`
- Test: `tests/unit/test_profile_loader.py`

**Acceptance**:
- profile.yaml schema-valid (loaded by `src/lem/profile.py`)
- intake-prompt.md guides the intake worker on what kinds of clarifying questions matter for app ideas (audience, goal, mechanism, geography, success metric)
- All deliverable templates referenced exist

**Tests should cover**: profile loads, all referenced files exist, verdict options match orchestrator's expectations.

---

### Task 7.2: Specialist role files (architect, designer, market)

**Outcome**: Three role files for app-idea: `architect.md`, `designer.md`, `market.md`. Each with: full system prompt, frontmatter (name, model: opus, worker: cli, output_cap, timeout_s, branchable, output_schema with required_frontmatter + required_sections + enums + exit_criteria, tools).

**Specifics:**
- **architect**: system shape, tractability for small team. required_frontmatter: `data_entities`, `external_dependencies`, `state_locus`. required_sections include Frame engagement, Architecture overview, Build complexity, Tractability.
- **designer**: UX flows + interaction patterns + failure states. required_frontmatter: `primary_flow_steps`, `core_interaction_pattern`, `failure_states`. (Non-overlapping with architect.)
- **market**: TAM, competitors, saturation, customer development. required_frontmatter: `saturation` (enum), `direct_competitors`, `closest_analogue`, `genuine_differentiator`, `business_model`, `customer_development_signal`, `target_user_acuteness`. Tools: WebFetch, WebSearch.

**Files**:
- Create: `profiles/app-idea/roles/architect.md`
- Create: `profiles/app-idea/roles/designer.md`
- Create: `profiles/app-idea/roles/market.md`
- Test: `tests/unit/test_role_files.py` (loads each, checks frontmatter completeness)

**Acceptance**:
- Each role loads successfully via `src/lem/profile.py`
- Frontmatter passes pyright-style key validation
- System prompts are constraint-shaped (concrete tasks, exit criteria, examples — not vague verbs)
- Architect/designer schemas non-overlapping (verified by test)
- Market schema includes all 7 required frontmatter keys

**Tests should cover**: each role loads, frontmatter schemas non-overlapping (architect ∩ designer = ∅ for required_frontmatter), enum values legal.

> HUMAN REVIEW REQUIRED: each role's prompt body is the highest-leverage content in lem. Subagent drafts; human reviews before commit.

---

### Task 7.3: Process role files

**Outcome**: 9 process role files in `process_roles/`: `jtbd-extractor.md`, `frame-shifter.md`, `disagreement-detector.md`, `branch-skeptic.md`, `pruner.md`, `distiller.md`, `cross-skeptic.md`, `kill-case-skeptic.md`, `synthesizer.md`. Each with full prompt + frontmatter + output_schema. Frame-shifter prompt references `{{prompt_fragment}}` substituted from the active profile's `prompt-fragments/frame-shifter.md`.

**Files**:
- Create: 9 files in `process_roles/`
- Create: `profiles/app-idea/prompt-fragments/frame-shifter.md`
- Test: `tests/unit/test_process_roles.py`

**Acceptance**:
- Each role loads
- Frame-shifter has substitution placeholder; profile's fragment is concrete (lists app-specific solution shapes: app, service, community, hardware, content product, marketplace, managed service)
- Each skeptic's output_schema enforces structured fields per spec (per-option attack / conflict pairs / leveraged assumptions)
- Synthesizer's prompt enforces deliverable-quality guards (no advice-mode verbs without object, must cite specifics from idea.md, no filler sections)
- distiller targeted at compactness, not depth

**Tests should cover**: each role loads, frame-shifter substitution works, each schema valid.

> HUMAN REVIEW REQUIRED: same as 7.2. Skeptic prompts are especially load-bearing — subagent drafts, human reviews.

---

### Task 7.4: Deliverable templates

**Outcome**: 6 Jinja2 templates in `profiles/app-idea/deliverables/`: `executive-summary.md.j2`, `mvp-plan.md.j2`, `risks-and-rejected-paths.md.j2` (default), `investor-onepager.md.j2`, `roadmap.md.j2`, `tech-stack.md.j2` (flag-gated). Each provides structure but is filled by the synthesizer's output. Templates supply: assumptions register section, verdict section structure, named field placeholders for synthesizer to fill.

**Files**:
- Create: 6 templates
- Test: `tests/unit/test_deliverable_templates.py`

**Acceptance**:
- Each template renders with sample synthesizer output (jinja2 vars all defined)
- executive-summary opens with `## Assumptions` and ends with `## Verdict`
- mvp-plan has sections: Problem & user, MVP scope (in/out), Architecture sketch, UX flow, 3-phase build sequence, Open questions
- risks-and-rejected-paths has sections: Top 5 risks, Paths considered and rejected, Reframings considered

**Tests should cover**: all templates render without missing-var errors given a synthesizer-output fixture.

---

## Phase 8: CLI surface

### Task 8.1: `lem refine` command

**Outcome**: `src/lem/commands/refine.py` implements `lem refine "<idea>"` with all flags: `--profile`, `--depth`, `--model-tier`, `--max-cost`, `--max-wall-clock`, `--max-concurrent`, `--workspace`, `--no-verdict`, `--with-pitch/roadmap/techstack`, `--skip-intake`, `--webhook`, `--name`, `--show-cost`, `--attach`, `--dry-run`, `--open`. Default: background-detached daemon. `--dry-run` prints estimate.

**Files**:
- Create: `src/lem/commands/refine.py`
- Modify: `src/lem/cli.py` (register command)
- Test: `tests/integration/test_refine_cmd.py`

**Acceptance**:
- All flags parse correctly (typer handles equals or space syntax)
- --dry-run prints structured estimate (tokens, time, cost vs caps) without spawning workers
- Default mode: daemonizes (Task 5.4) and prints run-id to stdout
- --attach mode: runs orchestrator in foreground, with TUI (Phase 9 dependency — stub for now, real TUI integrated in 9.1)
- Run-id format: `<YYYY-MM-DD-HHMM>-<slug>-<6hex>`
- Workspace path resolution: --workspace > ./.lem if exists in cwd or ancestor > $XDG_DATA_HOME/lem/runs/<id>

**Tests should cover**: every flag, --dry-run, run-id format, workspace resolution, daemon detach.

---

### Task 8.2: Read commands (`watch`, `list`, `show`, `logs`)

**Outcome**: Four read-only commands. `lem watch [<id>] [--once] [--json]` (TUI default; --once = snapshot; --json = machine-readable). `lem list [--running] [--grep] [--json]`. `lem show <id> [--in pager|obsidian|browser]`. `lem logs <id> [--phase] [--role] [--errors-only]`.

**Files**:
- Create: `src/lem/commands/watch.py`
- Create: `src/lem/commands/list.py`
- Create: `src/lem/commands/show.py`
- Create: `src/lem/commands/logs.py`
- Modify: `src/lem/cli.py`
- Test: `tests/integration/test_read_cmds.py`

**Acceptance**:
- `lem watch <id>` launches TUI (Phase 9.1 integration)
- `lem watch <id> --once` prints snapshot to stderr (TUI not invoked)
- `lem watch <id> --json` prints state.json contents to stdout
- `lem list` reads all `runs/*/state.json`, prints table (newest first), with NAME (from --name flag), STATUS, TIME, VERDICT (glyph: ✓/✗/—/?)
- `lem list --grep <term>` matches on idea.md content + name
- `lem show <id>` defaults to `$PAGER` on executive-summary.md
- `lem show <id> --in obsidian` prints obsidian:// URL and (if --open or env LEM_AUTOOPEN) launches it
- `lem show <id> --in browser` opens markdown rendered in browser (use `lem render` output)
- `lem logs <id>` tails meta/log.jsonl with filters

**Tests should cover**: each command + flags, output format (TTY vs piped), JSON schema, glyph mapping.

---

### Task 8.3: Lifecycle commands (`rerun`, `cancel`)

**Outcome**: `lem rerun <id>` reads original args from state.json, kicks off a NEW run with same idea + flags (different run-id). `lem cancel <id>` writes cancel action to `meta/control.json` for the orchestrator to pick up; if orchestrator is dead, marks state as `cancelled`.

**Files**:
- Create: `src/lem/commands/rerun.py`
- Create: `src/lem/commands/cancel.py`
- Modify: `src/lem/cli.py`
- Test: `tests/integration/test_lifecycle_cmds.py`

**Acceptance**:
- `lem rerun <id>` invokes refine flow with original args, returns new run-id
- `lem cancel <id>` writes control.json action; orchestrator picks it up within ~5s and shuts down cleanly
- If orchestrator process is dead (PID gone), cancel writes final state directly

**Tests should cover**: rerun copies args correctly, cancel signals running orchestrator, cancel handles dead orchestrator.

---

### Task 8.4: `lem render`

**Outcome**: `src/lem/commands/render.py` + `src/lem/render/report.py` generate a self-contained HTML file (`report.html`) for a given run. Embeds CSS + JS inline. Renders pipeline timeline, cost/duration charts (uPlot), all deliverables with markdown rendering, verdict surface up top.

**Files**:
- Create: `src/lem/commands/render.py`
- Create: `src/lem/render/report.py`
- Create: `src/lem/render/template.html`
- Modify: `src/lem/cli.py`
- Test: `tests/integration/test_render.py`

**Acceptance**:
- Single HTML file produced (~50–200 KB)
- All assets inlined (no external CDN dependencies)
- Renders in any modern browser
- Markdown rendered with syntax highlighting
- Charts visible (cost over time, durations per phase)
- Verdict displayed prominently

**Tests should cover**: file produced, no external URLs, HTML validates, sample run renders without errors.

> DECISION: markdown rendering library (mistune, markdown-it-py, etc.). Pick one with rationale.

---

## Phase 9: TUI

### Task 9.1: Main TUI view

**Outcome**: `src/lem/tui/app.py` + `main_view.py` provide the main textual app: pipeline progress (linear, named phases), active workers grid (with full liveness signal: role | model | elapsed | tokens | last-activity), recent completions (scrollable), issues line (retries/timeouts/breaker trips), cost OR tokens display (gated by `--show-cost`).

**Files**:
- Create: `src/lem/tui/app.py`
- Create: `src/lem/tui/main_view.py`
- Test: `tests/integration/test_tui_main.py` (using textual's Pilot for headless TUI testing)

**Acceptance**:
- Reads workspace's state.json + events/ + cost.jsonl
- Auto-refreshes every 2s (configurable)
- Liveness signal updates from worker's stdout tail (last 80 chars)
- Issues line shows count of retries / timeouts / breakers from log.jsonl
- Stalled workers (median × 3) visually badged (e.g., yellow text)
- Phase names linear, no decimals visible

**Tests should cover**: snapshot test of rendered output for various states (idle, mid-discover, mid-explore, completed, aborted), refresh tick fires, stalled badge appears.

---

### Task 9.2: Drill-down panes

**Outcome**: Worker detail view, phase detail view, artifact view (inline rendered markdown), logs view (filterable), workspace tree view. All accessible via Enter/keyboard nav from main view.

**Files**:
- Create: `src/lem/tui/worker_view.py`
- Create: `src/lem/tui/phase_view.py`
- Create: `src/lem/tui/artifact_view.py`
- Create: `src/lem/tui/logs_view.py`
- Create: `src/lem/tui/tree_view.py`
- Test: `tests/integration/test_tui_drilldown.py`

**Acceptance**:
- Enter on a worker → worker detail (inputs, model, retries, live output preview, log)
- Enter on a phase → phase detail (workers, artifacts, schema status)
- Enter on an artifact → rendered markdown view
- `l` → logs view (scrollable, filterable by phase/role/severity)
- `w` → workspace tree (file browser with `o`=open in editor, `b`=open in obsidian)
- Esc returns to parent view

**Tests should cover**: each view renders, keyboard navigation works (using Pilot), filter behavior in logs.

---

### Task 9.3: Control protocol

**Outcome**: `src/lem/tui/controls.py` writes `meta/control.json` on key bindings. `p` → pause at next phase boundary. `r` → resume. `c` → cancel run (with confirmation modal). `k` → kill selected worker (rare).

**Files**:
- Create: `src/lem/tui/controls.py`
- Test: `tests/integration/test_tui_controls.py`

**Acceptance**:
- `p` writes `{action: "pause"}` to control.json
- `r` writes `{action: "resume"}`
- `c` shows confirmation modal then writes `{action: "cancel"}` if confirmed
- `k` writes `{action: "kill", target: <worker_id>}` (only useful for retry storms)
- TUI shows control state (paused / running) in header
- Orchestrator (Phase 5.2) honors these

**Tests should cover**: each control, confirmation modal, control.json roundtrip with orchestrator.

---

## Phase 10: Hooks + Slash Command

### Task 10.1: Lifecycle hooks

**Outcome**: `src/lem/hooks.py` runs `on_complete` and `on_error` shell commands from `lem.toml` config (project-level) or `~/.config/lem/config.toml` (user-level). Passes env vars: `LEM_RUN_ID`, `LEM_WORKSPACE`, `LEM_VERDICT`, `LEM_COST`, `LEM_DURATION`, `LEM_ERROR` (only on error).

**Files**:
- Create: `src/lem/hooks.py`
- Modify: `src/lem/orchestrator.py` (call hooks on completion)
- Test: `tests/unit/test_hooks.py`

**Acceptance**:
- Reads config from project + user TOML
- Project overrides user
- Hooks run via subprocess.run with timeout (30s default)
- Env vars set per spec
- Hook failure logged but does not affect run state

**Tests should cover**: hook invocation, env var population, project-vs-user precedence, hook timeout, hook failure handling.

---

### Task 10.2: Webhook + notifications

**Outcome**: `--webhook <url>` flag on `lem refine`. POST JSON `{run_id, verdict, cost, duration, deliverables_path, status}` on completion. `src/lem/notify.py` does terminal bell + osascript (macOS) / notify-send (Linux) on completion when `LEM_NOTIFY=1` or config flag set.

**Files**:
- Modify: `src/lem/hooks.py` (add webhook poster)
- Create: `src/lem/notify.py`
- Test: `tests/unit/test_webhook.py`, `tests/unit/test_notify.py`

**Acceptance**:
- Webhook POSTs JSON, retries 3× on failure with backoff, logs result
- Webhook timeout 10s
- Notifications fire on success and error (different titles)
- Terminal bell only when stderr is a tty
- OS notification falls back to bell if notify-send/osascript missing

**Tests should cover**: webhook POST format, retry on 5xx, notification command builds correctly per platform, no-tty case.

---

### Task 10.3: CC slash command + .claude/agents

**Outcome**: `.claude/commands/lem-refine.md` defines the `/lem-refine` slash command (interactive intake in CC main agent → shells to `lem refine --skip-intake --workspace=<path>`). `.claude/agents/` contains symlinks to active profile's roles + process_roles, so users can invoke `@architect` etc. interactively in CC.

**Files**:
- Create: `.claude/commands/lem-refine.md`
- Create: install script that creates `.claude/agents/` symlinks at profile-load time
- Test: manual smoke + `tests/integration/test_slash_command.py` (validates the command file structure)

**Acceptance**:
- `/lem-refine "<idea>"` in a CC session triggers main agent to do intake conversation
- After intake, main agent writes idea.md + assumptions.yaml then shells `lem refine --skip-intake`
- `.claude/agents/architect.md` resolves to `profiles/app-idea/roles/architect.md`
- All roles + process_roles are exposed
- Symlinks created on first run if not present

**Tests should cover**: slash command file is well-formed CC command, symlinks resolve, no broken links.

> DECISION: symlinks vs copies for `.claude/agents/`. Default: symlinks on POSIX, fall back to copies on Windows (which is out of v1 scope but doesn't hurt to be robust).

---

## Phase 11: Smoke test + Public release

### Task 11.1: End-to-end stub-profile test

**Outcome**: A stub profile under `tests/fixtures/stub-profile/` with deterministic stub workers (no API calls — they return canned outputs from fixture files). End-to-end test runs the full pipeline using stub-profile and verifies all expected workspace files exist with correct shape.

**Files**:
- Create: `tests/fixtures/stub-profile/profile.yaml`
- Create: `tests/fixtures/stub-profile/roles/*.md`
- Create: `tests/fixtures/stub-profile/canned-outputs/*` (per-role canned files)
- Modify: `src/lem/workers/cli_worker.py` (support `LEM_STUB_MODE=1` env var to skip claude invocation and read canned outputs)
- Create: `tests/e2e/test_stub_pipeline.py`

**Acceptance**:
- Test runs full pipeline via `lem refine --skip-intake --profile=stub` in a temp workspace
- Completes in <30s (no network)
- All expected files present: idea.md, frame-shifter/jtbd.md, frame-shifter/draft-1.md, <domain>/decision.md, deliverables/*.md, meta/state.json, meta/cost.jsonl
- Verdict in executive-summary.md is one of the legal options
- state.json shows status="completed"

**Tests should cover**: full happy path, abort path (cost ceiling), pause/resume via control.json, schema validation surfacing.

---

### Task 11.2: End-to-end live smoke test

**Outcome**: A live integration test runs `lem refine --depth=quick --max-cost=5 "an app for X"` against the real claude CLI (gated by `LEM_LIVE_TEST=1` env var so it doesn't run in normal CI). Verifies the run completes within budget and produces deliverables.

**Files**:
- Create: `tests/e2e/test_live_smoke.py`
- Create: `docs/development.md` (running live tests, $LEM_LIVE_TEST=1)

**Acceptance**:
- With `LEM_LIVE_TEST=1`, test runs against real claude CLI
- Without env var, test is skipped
- Verifies run completes (status="completed")
- Verifies deliverables produced
- Verifies cost < max-cost ceiling
- Documents the human-eyes-on review for output quality

**Tests should cover**: live happy path, manual review of one set of deliverables.

---

### Task 11.3: README + public release

**Outcome**: User-facing README with quickstart, install instructions, example session, link to docs. `gh repo edit` to update description + topics. Tag v0.1.0. Create GitHub release.

**Files**:
- Create/modify: `README.md`
- Create: `docs/quickstart.md`, `docs/configuration.md`, `docs/profiles.md`
- Add LICENSE file

**Acceptance**:
- README has: 30-second pitch, install (`pipx install lem`), quickstart (3 commands), link to spec
- `pipx install lem` works for someone cloning the repo
- v0.1.0 tag pushed; GitHub release created with built wheel attached

**Tests should cover**: README links resolve, install works in a fresh venv.

> DECISION: package distribution. PyPI vs GitHub-only releases? Defer to user — start with GitHub releases; PyPI if ready.

---

## Self-review

Spec coverage map (each spec section → task that implements it):

| Spec section | Implementing task(s) |
|---|---|
| Profiles concept | 5.1, 7.1 |
| Worker contract | 2.1, 3.1 |
| Worker invocation (CLI mode) | 3.1 |
| Concurrency / writes | 4.1, 5.2 |
| Repository layout | 1.2 |
| Workspace layout | 4.1, 6.x |
| Roles (specialists, process roles) | 7.2, 7.3 |
| Output schema validation | 2.3, 3.3 |
| Pipeline phases (Intake, JTBD, Discover, Disagreement, Reframe, Explore, Distill, Cross-Critique, Synthesize) | 6.1–6.9 |
| Verdict format | 6.9, 7.4 |
| Failure semantics (timeouts, retries, breaker, max-cost, max-wall-clock, atomic writes) | 3.2, 3.3, 4.1, 4.3, 5.3 |
| Stalled-worker detection | 4.4 |
| Observability (state.json, events, cost, timeline, log) | 4.1, 4.2 |
| Auth (claude CLI piggyback) | 3.1 |
| Cost design + tiering | 4.2, 7.2, 7.3 |
| TUI | 9.1, 9.2, 9.3 |
| CLI (7 verbs) | 8.1–8.4 |
| Storage (XDG + git-style walk) | 8.1 |
| Hooks (on_complete, on_error, webhook) | 10.1, 10.2 |
| Static report (`lem render`) | 8.4 |
| Slash command | 10.3 |
| End-to-end smoke | 11.1, 11.2 |
| Public release | 1.3, 11.3 |

No spec gaps. All 11 phases produce testable software.

---

## Execution recommendation

**Use `superpowers:subagent-driven-development`**:

1. Main session reads this plan into context
2. Per task: dispatch a fresh subagent with the task spec + relevant prior context (the source spec, prior task outputs)
3. Subagent implements (writes tests, then code, runs tests, commits)
4. Main session reviews the diff against acceptance criteria + tests pass
5. If review fails: feedback loop with the same subagent
6. If pass: mark task complete, move to next

**Halt-and-review checkpoints** (don't auto-advance through these):
- After Phase 1 (bootstrap): user verifies repo + install
- After Phase 5 (orchestrator): user verifies the orchestrator works on stub-profile
- After Phase 7 (profile content): **user reviews every role prompt** before merging
- After Phase 11.1 (stub e2e): user verifies the pipeline end-to-end
- Before Phase 11.2 (live smoke): user authorizes spending live tokens
- Before Phase 11.3 (release): user reviews README + license

**Parallelizable tasks** (can run concurrently):
- Phase 7.2 (3 specialist roles) and 7.3 (9 process roles) — different files, can dispatch in parallel after 7.1 completes
- Phase 8.2's four read commands — different files, parallelizable
- Phase 9.2's drill-down panes — different files, parallelizable

Sequential dependencies block elsewhere; trust the dependencies-listed-above guidance.

**Total task count: 41**. Estimated 80–120 hours of agent-driven implementation work, depending on prompt-quality iteration in Phase 7.
