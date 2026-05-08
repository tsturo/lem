# lem implementation — agent prompt

Drop the prompt below into a fresh Claude session (Claude Code, CLI, or any environment that supports the `superpowers:subagent-driven-development` skill) to begin implementation.

---

You are implementing `lem`, a Python-orchestrated multi-agent CLI that refines app/feature ideas into investor-grade markdown deliverables. Working directory: `/Users/tomek/dev/lem`.

The brainstorming and design phases are done. Your job is to execute the implementation plan.

## What you're doing

Implementing `lem` v1 from a written plan. The plan has 41 tasks across 11 phases. Use the `superpowers:subagent-driven-development` skill to execute it: dispatch a fresh subagent per task, review the diff against the task's acceptance criteria, advance on pass, iterate on fail.

## Read these first

1. **Plan**: `docs/superpowers/plans/2026-05-06-lem-framework.md` — your task list. Code-free by design; subagents decide implementation choices given outcomes + acceptance criteria.
2. **Spec**: `docs/superpowers/specs/2026-05-06-lem-framework-design.md` — design rationale. The plan's intro inlines material design deltas from chat that aren't yet folded into the spec; treat the plan as authoritative when they disagree.

## Key context the plan assumes (don't re-litigate)

- All workers invoke `claude -p --output-format json`. Auth piggybacks on the user's `claude` CLI (Max subscription). No Anthropic SDK. No API key in the codebase.
- Tech stack: Python 3.11+, typer, pyyaml, jinja2, textual, rich, pytest, ruff, pyright. No frontend, no DB.
- Default model tier `opus-heavy` (every specialist + skeptic + frame-shifter + pruner + synthesizer on Opus; disagreement-detector on Sonnet; distiller on Haiku).
- Background-default for `lem refine`; `--attach` for foreground TUI. XDG storage default (`$XDG_DATA_HOME/lem/runs/`) with git-style upward-walk for `.lem/` opt-in.
- 7 visible CLI verbs: `refine`, `watch`, `list`, `show`, `logs`, `rerun`, `cancel`.

## Confirmed up-front decisions (do not re-ask)

- **License**: MIT.
- **Python build backend**: hatchling. Rationale: modern PEP 621 standard, no `setup.py`, plays well with `uv`/`pip`/`pipx`, lowest ceremony for a pure-Python CLI with no compiled extensions.
- **GitHub username**: `tsturo` (verified via `gh auth status`; the spec/plan suspicion that this was a typo for `tszturo` is incorrect — `tsturo` is correct).
- **Repo already exists**: `https://github.com/tsturo/lem` is cloned into the working dir. Phase 1.3's `gh repo create` step is therefore a no-op; that task collapses to "stage + commit bootstrap files + push to existing remote." Adjust the task accordingly when you reach it.

## Mandatory human-review checkpoints (DO NOT auto-advance)

The plan flags these. Stop and ask the user to confirm before proceeding past each:

1. **After Phase 1 (Bootstrap)**: user verifies repo + install
2. **After Phase 5 (Orchestrator)**: user verifies orchestrator works on stub-profile
3. **After Phase 7 (Profile content)**: **mandatory review of every role prompt** — subagents draft, human reviews each before commit. These prompts are the soul of lem; do not let drafts merge unreviewed.
4. **After Phase 11.1 (Stub e2e)**: user verifies pipeline end-to-end
5. **Before Phase 11.2 (Live smoke)**: user authorizes spending real tokens
6. **Before Phase 11.3 (Release)**: user reviews README + LICENSE

**Rollback policy if user rejects work at a checkpoint**: prefer forward-fix (a follow-up commit that addresses the issue) over rewriting history. Only use `git revert` (creates a new commit that undoes the prior one) when the rejection is "back this out entirely." Never use `git reset --hard` or force-push without explicit user approval — atomic per-task commits are the audit trail.

## Decisions and unknowns

Tasks marked `> DECISION:` in the plan need either a defensible default (with a one-line rationale in the commit message) or a question to the user.

**Decide-vs-ask threshold**:
- **Decide** (and note rationale in the commit): naming, internal style/structure, choice of equivalent libraries, test strategy within the task, file organization within already-listed files.
- **Ask the user**: anything user-visible (CLI flag names, output formats, file paths in the workspace), anything that changes the contract between phases, anything that adds a dependency not in the plan, anything that contradicts the spec, any decision where you can articulate two reasonable options that differ in feel/ergonomics rather than correctness.

When in doubt, ask. Cheap to ask; expensive to redo.

## Parallelizable tasks (dispatch concurrently in subagent-driven mode)

- Phase 7.2 (3 specialist role files) and 7.3 (9 process role files): different files, parallel after 7.1 lands
- Phase 8.2 (4 read commands): parallel
- Phase 9.2 (5 drill-down panes): parallel

## User preferences (from ~/.claude/CLAUDE.md)

- Don't add comments to code
- Don't add functionality the plan doesn't specify
- Prefer smaller methods, SOLID principles
- Stage files explicitly by name when committing; never `git add .` or `git add -A`
- Don't commit to main without asking; commit to feature branches autonomously is fine
- Push back when you see a better approach; don't agree reflexively
- For bugs, find and state the root cause; if applying a workaround, say so explicitly
- Don't suggest installing plugins/MCPs/dependencies beyond what the plan lists without asking

**Preference propagation**: include this entire preferences block verbatim in every dispatched subagent's brief. Subagents start with a fresh context and will not inherit these otherwise.

**Push-back vs. don't-re-litigate**: push back freely on task-level execution choices and acceptance-criteria interpretation. Do *not* re-open the frozen architectural decisions in the "Key context" and "Confirmed up-front decisions" sections — those are settled.

## Discipline

- **TDD per task** when the task is testable: write tests for the acceptance criteria first, watch them fail, implement, watch them pass, commit. Some tasks (drafting role-prompt markdown, writing `pyproject.toml`, populating Jinja2 templates) have no meaningful unit-test layer — for those, the acceptance criteria are the verification (e.g., `lem --help` exits 0, role file loads via the parser, template renders without missing-var errors). Run those checks before commit.
- **Commit message format**: `<phase>.<task>: <one-line summary>` — e.g. `1.1: initialize Python project with pyproject.toml`
- **Per-task file scope**: the subagent for a task should modify the files listed in that task. Mechanical touches to neighboring files (adding an import, registering a command in `cli.py`, updating an `__init__.py` export) are fine and do not require halting. Substantive edits to files outside the task's scope (changing logic in another module, modifying a sibling's tests, refactoring shared code) require halting and asking the user before proceeding.

## Start

1. Load the `superpowers:subagent-driven-development` skill via the Skill tool
2. Read the plan thoroughly (it's ~1140 lines, worth it)
3. Skim the spec for design context
4. Verify environment:
   - `claude --version` (CLI present)
   - `claude -p --output-format json "say only the word pong"` returns a valid JSON envelope (auth + invocation work end-to-end — costs a few cents, not free)
   - `python3 --version` (need 3.11+; this machine has 3.14.3)
   - `git --version`, `gh --version`, `gh auth status` (active account should be `tsturo`)
5. Begin Phase 1, Task 1.1

Stop and ask whenever the plan is ambiguous, a `> DECISION:` isn't obvious by the decide-vs-ask threshold above, or you hit something that conflicts with the spec or the confirmed up-front decisions.
