# Iterate on an idea — design spec

**Status:** approved 2026-05-10 (brainstormed with @tomek via visual companion)
**Branch:** `feature/electron-ui-alpha`
**Companion (parked):** `docs/future-work/dynamic-intake.md` (Feature B)

## Goal

Let a user click "Refine again" on an existing idea, add new context (e.g. "now it should be mobile-first with comments and ticket-saving"), and run a fresh evaluation that is genealogically linked to the previous round. Surface the verdict trajectory so "Don't build → Build" is obvious. Optionally branch from any round to explore alternative directions in parallel.

## Decisions

### 1. Mental model — Linear by default, branch on demand
Most iteration is sequential ("now consider X"). A separate "Branch alternative" action exists for the rarer "compare two visions" case. Tree UIs are not forced on casual users.

### 2. Input mechanism — Free-text box (graduated by Feature B later)
Modal with a single textarea ("What's changed about this idea?"). Feature B's adaptive Claude-driven intake bolts on later as an opt-in toggle on the same modal — not a replacement.

### 3. Pipeline scope — Full re-run each round
All 11 phases run from scratch for every round (~10 min, ~$1.50). Predictable cost/time, simplest implementation, most honest verdict comparison. Skip-phase / smart-cache optimizations are explicitly out of scope.

### 4. Brief view timeline — Verdict-pill strip
Horizontal strip above the deliverable tabs. Each round = a colored pill (verdict-coded). Current round enlarged with outline. Click to switch.

### 5. Branch rendering — Stacked threads
When branches exist the strip splits into multiple rows. Shared ancestors align visually. Each thread shows its branch label + verdict on the right.

### 6. Sidebar — Expandable, rounds as nested rows
Ideas at the top level. Click an idea to expand; rounds appear as indented child rows, each independently clickable. The currently-viewed round is highlighted. The active idea auto-expands; collapse state per-idea is remembered. Sidebar and Brief-strip selection stay in sync.

### 7. Branch trigger — Split button "Refine again ▾"
Main button click = continue current thread (90% case, one click). Chevron dropdown exposes "⑂ Branch alternative". V2 hook: dropdown can later expose "Branch from this round" with a round-picker, allowing branches off non-current rounds.

### 8. Modal — Lean + optional branch name
Continue mode: title + round number + textarea + cost line.
Branch mode: title + parent label + optional "Label this branch" field + textarea + cost line.
Cost line: small grey text, *"~10 min · ~$1.50 of Max tokens"*. No confirmation gate.

### 9. Round-2+ prompt strategy
Specialists run from scratch (no parent phase outputs inherited). Each round-2+ run injects a small "Iteration context" header into Phase 0:

```
This is round N of refinement on this idea.
Round N-1 (parent) reached verdict: <verdict> (<confidence>).
The user has added the following context for this round:
> <user's "what's changed" text>

Your job: actively reconsider this idea given the new context.
Do NOT defer to the prior verdict. If the new context shifts your
analysis, say so explicitly.
```

Synthesizer gets one extra instruction for round-2+: in the executive summary, reference the parent verdict and explain what changed (one paragraph max).

## Data model

### Filesystem (unchanged)
Each round = self-contained run dir at `~/.local/share/lem/runs/<run-id>/`. No symlinks, no shared phase outputs. Two new files in the run's `meta/`:
- `meta/parent_run_id` — text file, parent run ID (absent for root)
- `meta/branch_label` — text file, 2-4 word label (absent if user didn't set one and Claude extraction failed)

### SQLite (`library.db`)

New `ideas` table:
```sql
CREATE TABLE ideas (
  id          TEXT PRIMARY KEY,    -- ULID
  title       TEXT NOT NULL,       -- auto from first round; user-editable
  created_at  INTEGER NOT NULL     -- epoch seconds
);
```

Add columns to `runs`:
```sql
ALTER TABLE runs ADD COLUMN idea_id        TEXT REFERENCES ideas(id);
ALTER TABLE runs ADD COLUMN parent_run_id  TEXT REFERENCES runs(id);
ALTER TABLE runs ADD COLUMN branch_label   TEXT;
ALTER TABLE runs ADD COLUMN round_depth    INTEGER NOT NULL DEFAULT 1;
```

`round_depth` is the round number visible to the user. Two branches off Round 1 are both `round_depth = 2`.

### Backfill
On startup, the workspace-scanner extends to handle linkage:
- Any run with no `idea_id` → create an `ideas` row (title = run's existing `idea` field), assign `idea_id`, set `parent_run_id = NULL`, `round_depth = 1`. Every legacy run becomes a 1-round idea.
- Any run dir containing `meta/parent_run_id` → look up the parent in the DB by run ID; if found, set `idea_id` to parent's `idea_id`, set `parent_run_id`, set `round_depth = parent.round_depth + 1`. Read `meta/branch_label` if present.
- Idempotent: a second scan is a no-op.

### Sidebar query shape
```
SELECT * FROM ideas ORDER BY created_at DESC;
-- per idea (on expand):
SELECT * FROM runs WHERE idea_id = ? ORDER BY round_depth ASC, created_at ASC;
```

Round-count badge: `COUNT(*)` of rounds for an idea. Branch badge: count of leaf rounds (rounds with no children) when > 1.

## File-level architecture

### Python (`src/lem/`)
- `cli.py` — new `--parent-run-id <id>` and `--branch-label <text>` flags on `lem refine`.
- `orchestrator.py` — when `parent_run_id` is set: read parent run's `idea.md` and `meta/synthesis.md` verdict, build the Iteration context header, inject into Phase 0 input. Write `meta/parent_run_id` and `meta/branch_label` to the new run's workspace.
- `branch_label.py` (new) — `extract_branch_label(context_text: str) -> str`. Tiny `claude -p` worker call producing a 2-4 word label. Fallback to `f"round-{depth}"` on failure. Used when `--branch-label` not supplied AND parent_run_id is set.
- `process_roles/synthesizer.md` — append a conditional block that activates when iteration context is present in the workspace.

### Desktop main (`desktop/src/main/`)
- `library-db.ts` — migration adds `ideas` table and the four new `runs` columns. New methods: `createIdea`, `listIdeas`, `getRoundsForIdea(ideaId)`, `getRunDag(ideaId)`, `renameIdea`, `setBranchLabel`.
- `workspace-scanner.ts` — extend to read `meta/parent_run_id` + `meta/branch_label` and populate the new columns on import. Also handle the legacy backfill described above.
- `orchestrator-bridge.ts` — `spawnRefine` accepts `{ idea, parentRunId?, branchLabel?, contextText? }`. Maps to `lem refine` flags. Writes `meta/parent_run_id` and `meta/branch_label` into the new run dir before/while the child runs.
- `ipc/ideas.ts` (new) — handlers: `ideas.list`, `ideas.getRounds`, `ideas.getDag`, `ideas.rename`, `runs.refine`, `runs.setBranchLabel`. Registered via the existing `registerXxxHandlers(ipcMain, deps)` pattern.
- `preload.ts` — expose new IPC surface as `window.lem.ideas.*` and extend `window.lem.runs.*`.

### Desktop renderer (`desktop/src/renderer/`)
All under `components/` unless noted:
- `Sidebar.tsx` — refactor: render ideas at top level; expandable rounds nested below. Round-count + branch-count badges. Active idea auto-expanded. Right-click → Rename for ideas; right-click round → Set label.
- `TimelineStrip.tsx` (new) — verdict-pill horizontal strip. Linear single-thread by default. Stacked-threads multi-row when DAG has branches. Click pill → switches active round.
- `RefineAgainButton.tsx` (new) — split button. Main click triggers `onContinue`. Chevron dropdown → "⑂ Branch alternative" triggers `onBranch`.
- `RefineModal.tsx` (new) — single component, two modes (`continue` | `branch`). Branch mode adds optional "Label this branch" input.
- `Brief.tsx` — wire `<TimelineStrip>` above the deliverable tabs; replace `<PrimaryButton onClick={onRefineAgain}>` with `<RefineAgainButton>`.
- `App.tsx` — modal state machine; on submit, call `window.lem.runs.refine(...)`, navigate to Theater for the new run, reload sidebar.

## Out of scope (explicitly)

- **Feature B — adaptive Claude-driven intake.** Parked at `docs/future-work/dynamic-intake.md`. The free-text box (Decision 2) is the alpha intake.
- **Smart skip / cached phases.** Every round = full pipeline. Optimization defers until usage data justifies it.
- **Branch from a non-current round** (right-click any round → Branch). Decision 7 v2 hook reserved; not implemented in this batch.
- **Side-by-side compare mode.** No split-screen Brief. Comparing branches = switching between them.
- **Compare/diff visualization** between two rounds. The synthesizer prose paragraph is the only diff surface for now.
- **Resume capability** for crashed mid-pipeline runs. Tracked separately in HANDOFF.md.
- **ETA learning from history.** Hardcoded `PHASE_ESTIMATES` stays.
- **AgentCard per-role events.** Tracked separately in HANDOFF.md.

## Acceptance for the batch

User opens an existing idea (1 round), clicks "Refine again", types "now mobile-first with comments and ticket-saving", clicks Refine. They see the Theater for round 2. ~10 min later, the Brief reloads showing the timeline strip with two pills. Sidebar shows the idea expanded with 2 round-rows. They click "Refine again ▾" → "⑂ Branch alternative", type a different direction, label it "B2B", and submit. After completion, the strip shows the stacked-threads view with the main thread (Round 1 → Round 2) and a branch (Round 2 — B2B). They can click any pill to switch the Brief content. Backfill: all existing runs from prior sessions appear as 1-round ideas in the sidebar.
