# lem

Multi-agent CLI that refines a one-line app/feature idea into investor-grade markdown deliverables ending in an explicit verdict. A Python orchestrator dispatches headless `claude -p` workers across a 9-phase pipeline; output is a markdown workspace with `executive-summary.md`, `mvp-plan.md`, `risks-and-rejected-paths.md`. Named after Stanisław Lem.

## Tech stack

- Python 3.11+ (developed on 3.14.3)
- typer (CLI), pyyaml, jinja2, textual (TUI), rich
- Dev: pytest, ruff, pyright
- Build: hatchling
- No Anthropic SDK — auth piggybacks on the user's `claude` CLI (Max subscription)

## Conventions

- **No comments unless explaining non-obvious WHY.** Module docstrings are fine; trivial line comments are not.
- **Smaller methods, SOLID.** Single responsibility per file. Public API surface minimal.
- **Stage files explicitly by name when committing.** Never `git add .` or `git add -A`.
- **Don't commit to main without asking.** Feature branches autonomous.
- **Push back on bad approaches.** Don't agree reflexively.
- **For bugs, find and state the root cause.** If applying a workaround, say so explicitly.
- **Don't add functionality the plan doesn't specify.**
- **Don't suggest installing plugins/MCPs/dependencies beyond what the plan lists** without asking.

## Key invariants

- All workers invoke `claude -p --output-format json`. No Anthropic SDK.
- User runs on Claude Max; dollar costs are notional. `--max-cost` is `None` by default. Cost-tracking machinery exists for benchmarking only.
- Strict pyright on `src/lem/types.py`; default mode elsewhere.
- Atomic writes everywhere: `tmp + os.replace` for `state.json`/event files; `O_APPEND` for JSONL logs.
- Schema-validated outputs per role; one retry on schema failure with errors fed back as continuation.
- SIGTERM-then-SIGKILL timeout escalation (10s grace) for `claude -p` subprocesses.
- Phase-level circuit breaker (`failure_rate > 0.5` aborts run; synthesize phase exempt).
- Verdict auto-downgrade: orchestrator rewrites `recommendation` to "Insufficient information" if >50% of load-bearing assumptions are unconfirmed.

## Repo layout

```
src/lem/
  cli.py                — typer entry, registers commands
  orchestrator.py       — main run loop, phase iteration, dispatch
  phases.py             — declarative PHASES: list[PhaseSpec]
  types.py              — frozen dataclasses (strict pyright)
  intake.py             — interactive Phase 0
  daemon.py             — POSIX double-fork
  control.py            — meta/control.json reader/writer
  paths.py              — XDG/run-id resolution
  profile.py            — Profile loader
  hooks.py              — TOML lifecycle hooks + webhook poster
  notify.py             — OS notifications
  post_synthesis.py     — verdict auto-downgrade
  install_agents.py     — .claude/agents symlink installer
  commands/             — refine, watch, list, show, logs, rerun, cancel, render
  workers/cli_worker.py — claude subprocess wrapper
  workers/dispatch.py   — retry + schema + signal-escalation timeout
  schema/parser.py      — frontmatter + section parser
  schema/validator.py   — output_schema enforcement
  state/                — run_state, events, log, cost, timeline
  failure/              — timeout, retry, breaker, ceiling, stalled
  tui/                  — textual app + drill-down panes + control protocol
  render/report.py      — HTML report generator
  render/deliverables.py — markdown render pass (jinja2 → templates)

process_roles/          — profile-independent role files (jtbd-extractor, frame-shifter,
                          disagreement-detector, branch-skeptic, pruner, distiller,
                          cross-skeptic, kill-case-skeptic, synthesizer)
profiles/app-idea/      — single v1 profile
  profile.yaml
  intake-prompt.md
  roles/                — architect, designer, market
  deliverables/*.md.j2  — Jinja2 templates rendered from synthesizer output
  prompt-fragments/     — domain-specific fragments (frame-shifter)

tests/unit/             — focused unit tests (most modules)
tests/integration/      — orchestrator + TUI + slash command + CLI command tests
tests/e2e/              — full-pipeline tests (stub + gated live smoke)
tests/fixtures/         — claude_stubs, parser/, validator/, stub-profile/

docs/
  superpowers/specs/    — design spec
  superpowers/plans/    — implementation plan
  superpowers/agent-prompt.md — kickoff brief
  reviews/              — three-reviewer audit (prompt, architect, AI prod) + SYNTHESIS.md
  quickstart.md, configuration.md, profiles.md, development.md
```

## How to run

```bash
pip install -e ".[dev]"        # install (use a venv)
pytest -q                      # run all tests
ruff check src/                # lint
pyright src/                   # type check

lem --help                     # CLI help
lem refine "your idea"         # default: daemonize + claude -p calls
lem refine "your idea" --attach   # foreground
lem watch <run-id>             # textual TUI live view
lem list                       # all runs

LEM_STUB_MODE=1 lem refine "..."  # no API calls, deterministic stub outputs
LEM_LIVE_TEST=1 pytest tests/e2e/test_live_smoke.py    # real claude (~$5-10 of tokens)
LEM_CLAUDE_BIN=/path/to/claude lem refine "..."        # override claude binary
LEM_NOTIFY=1 lem refine "..."                          # OS notification on done
```

## What lem does (pipeline overview)

1. **Intake** (interactive, before orchestrator) — ≤3 clarifying questions, writes `idea.md` + `assumptions.yaml`
2. **JTBD-extract** (0.5) — pulls underlying job-to-be-done as one line
3. **Reframe** (0.6) — frame-shifter produces alternative solution shapes + heretical takes
4. **Discover** (1, parallel) — 3 specialists weigh in (architect, designer, market); each engages with reframings
5. **Disagreement check** (1.5) — detector finds substantive divergences + branching axes per domain
6. **Explore** (2.1 generate → 2.2 critique → 2.3 prune, opt-in branching) — K=2 alternatives where divergence found, branch-skeptic attacks each, pruner picks survivor; loser archived with structured rejection frontmatter
7. **Distill** (2.5) — Haiku compresses workspace
8. **Cross-Critique** (3) — cross-skeptic finds cross-domain conflicts; kill-case-skeptic argues for not building
9. **Synthesize** (4) — Opus produces structured `meta/synthesis.md` frontmatter; render pass fills templates → `deliverables/*.md`; verdict auto-downgrade rewrites recommendation if >50% load-bearing assumptions unconfirmed

## Status

v0.1.0 implementation complete; **not tagged, not on PyPI, not merged to main**. See `HANDOFF.md` for current state and pending work.

## Pointers

- **Plan**: `docs/superpowers/plans/2026-05-06-lem-framework.md` (~1140 lines)
- **Spec**: `docs/superpowers/specs/2026-05-06-lem-framework-design.md` (~580 lines)
- **Three-reviewer audit**: `docs/reviews/SYNTHESIS.md` (start here) + `prompt-engineer.md`, `architect.md`, `ai-production.md`
- **Handoff**: `HANDOFF.md` (read this first when resuming after `/clear`)
- **Agent prompt** (original kickoff brief): `docs/superpowers/agent-prompt.md`
