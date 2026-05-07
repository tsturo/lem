# lem

Refines an app or feature idea into a decision-ready, investor-grade markdown brief.
Multi-agent CLI orchestration over claude. Named after Stanisław Lem.

## Install

```
pipx install lem
```

Or for development:

```
git clone https://github.com/tsturo/lem
cd lem
pip install -e ".[dev]"
```

Requires Python 3.11+ and the `claude` CLI authenticated (Max subscription or API key).

## Quickstart

```
lem refine "an app that helps freelancers send invoices on time"
```

This:
1. Asks up to 3 clarifying questions in your terminal
2. Writes idea.md and assumptions.yaml
3. Runs the pipeline in the background (background-default; use --attach for foreground)
4. Produces deliverables in `$XDG_DATA_HOME/lem/runs/<run-id>/deliverables/`

Watch progress:

```
lem watch <run-id>
```

Show the executive summary:

```
lem show <run-id>
```

List runs:

```
lem list
```

## What lem produces

Three default markdown deliverables, ending in an explicit verdict:

- **executive-summary.md** — opens with assumptions register, ends with a verdict (Build / Refine / Pivot / Don't build / Insufficient information)
- **mvp-plan.md** — problem, MVP scope, architecture sketch, UX flow, 3-phase build sequence
- **risks-and-rejected-paths.md** — top 5 risks, paths considered and rejected, alternative framings

Optional flag-gated additions:

- `--with-pitch` → investor-onepager.md
- `--with-roadmap` → roadmap.md
- `--with-techstack` → tech-stack.md

## How it works

The pipeline runs 9 phases over a markdown workspace:

1. **Intake** (interactive): ≤3 clarifying questions
2. **JTBD-extract**: pulls the underlying job from your one-liner
3. **Discover** (parallel): 3 specialists weigh in (architect, designer, market)
4. **Disagreement check**: detects substantive divergences and branching axes
5. **Reframe**: alternative solution shapes + heretical takes
6. **Explore** (opt-in branching): K=2 alternatives where divergence was found, branch-skeptic attacks each, pruner picks survivor
7. **Distill**: Haiku compresses the workspace
8. **Cross-Critique**: cross-skeptic finds cross-domain conflicts; kill-case-skeptic argues for not building
9. **Synthesize**: Opus produces the final deliverables with verdict

Each phase has retry-on-schema-failure, atomic writes, and a per-phase circuit breaker.

## Cost

Typical run on app-idea profile: $10–15. Hard ceiling default $25 (--max-cost), wall-clock cap 4h (--max-wall-clock).

## CLI commands

- `lem refine "<idea>"` — start a run (background by default; --attach for foreground)
- `lem watch [<id>]` — TUI live view
- `lem list` — runs, statuses, verdicts
- `lem show <id>` — open executive summary in $PAGER (or --in obsidian/browser)
- `lem logs <id>` — tail meta/log.jsonl
- `lem rerun <id>` — kick off a new run with the same args
- `lem cancel <id>` — graceful stop
- `lem render <id>` — generate self-contained HTML report

Full reference: see [docs/configuration.md](docs/configuration.md).

## License

MIT — see [LICENSE](LICENSE).

## Repository

[github.com/tsturo/lem](https://github.com/tsturo/lem)
