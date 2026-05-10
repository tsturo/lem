# lem — Session handoff

**Last updated:** 2026-05-10
**Current branch:** `feature/electron-ui-alpha` (76+ commits ahead of `main`, all pushed to origin)
**Status:** Alpha shippable for internal use; PR not yet opened against main.

This file is for resuming work after `/clear`. Read first; then:
- `git log feature/electron-ui-alpha --oneline` for full history
- `cat docs/adr/ADR-0001-electron-ui-architecture.md` for the architectural decisions

---

## Where we are

Two completed batches on `feature/electron-ui-alpha`:

**Batch 1 (LEM-1 → LEM-27)** — initial Electron desktop alpha
- Full Electron + React 19 + TypeScript + Tailwind 4 app under `desktop/`
- Tonale design system implemented (BrandMark, Sidebar, Topbar, IntakeInput, IntakeChat, Theater, AgentCard, EarlierSteps, Brief, FirstRunWizard, primitives)
- SQLite library DB, claude-detect, orchestrator-bridge (spawns `lem refine --json-events`)
- Theme handling (light/dark/auto)
- 167+ unit tests + 1 Playwright e2e test
- ADR-0001 documents the architecture (shared types in `src/shared/`, Tailwind 4 dark-mode indirection, IPC registration pattern, stdout JSON-lines for Python→Electron, atomic settings writes, `shell.openExternal` via IPC)

**Batch 2 (LEM-28 → LEM-34)** — security hardening from 6-specialist code review
- LEM-28: CLAUDE_LOGIN path validated against detectClaude allowlist (was arbitrary code execution)
- LEM-29: WORKSPACE_READ_BRIEF realpath-confined to lem runs directory (was path traversal)
- LEM-30: will-navigate blocker + URL scheme allowlist for shell.openExternal
- LEM-31: Electron 33 → 39.8.10 (was 18 vulns, 4 high — now 0)
- LEM-32: OrchestratorBridge captures child stderr (was silent crashes)
- LEM-33: Python `lem refine` exits 69 on auth failure (was dead code on JS side)
- 186/186 unit tests passing, 623 Python tests, 0 audit vulns

**Hot-fix commit (2026-05-10, this session)** — alpha usability after first real-user run:
- Python parser tolerates missing closing `---` fence (synthesizer crash recovery)
- Synthesizer + 3 specialist prompts: "no jargon shorthand in prose" rule + final-check skeleton
- New `workspace-scanner.ts` imports on-disk runs into library DB on startup
- LibraryDB: added `workspace_path` column + idempotent migration
- App.tsx: wired `window.lem.claude.detect()` from renderer (was never called; splash hung forever); passes workspacePath to Brief; maps verdict tag to human-readable label
- Fixed `idea.md` heading-skip so sidebar shows real idea text not "Idea"

---

## How to verify the alpha works

```bash
cd desktop
pnpm install                # or: pnpm exec electron-rebuild -f -w better-sqlite3 if better-sqlite3 ABI mismatch
pnpm tsc --noEmit           # should be clean
pnpm test                   # should be 186/186 (or higher)
pnpm dev                    # should launch Electron window
```

Expected behavior:
1. Splash (BrandMark gradient) for ~1s while claude is detected
2. Sidebar populates with all on-disk runs (CLI + desktop, succeeded + failed) grouped under Done/Active/Archive
3. Click any completed run → Brief shows verdict pill, callout (recommendation/confidence/first-milestone), 3 tabs with deliverable markdown
4. Click `+ New idea` → IntakeInput → IntakeChat (3 mock questions) → Confirmation card → Theater (live phases) → Brief

If `claude` isn't on PATH, the FirstRunWizard appears with an "Install Claude Code" CTA (tested but `pickPath` flow is partial — see "Known issues" below).

```bash
# Run pipeline from CLI (no desktop)
LEM_STUB_MODE=1 lem refine "test idea" --attach    # deterministic, no API calls
lem refine "real idea here" --attach --json-events # real run, ~$1-1.50 of Max tokens, ~10 min
lem list                                            # see all runs
lem show <run-id>                                   # read deliverables
```

---

## Known issues (real runs surfaced these)

**Resume capability does not exist.** A run that fails mid-pipeline (synthesizer crash, cost ceiling, auth expired) cannot be resumed from the last successful phase. `lem rerun <id>` starts a fresh run with the same idea but re-pays for everything. Phase 2 feature; needs:
- `lem resume <run-id>` Python command that reads `meta/state.json` and skips completed phases
- Desktop UI: "Resume" button on failed runs in the sidebar/Brief
- Special-case for synthesizer crash: re-render deliverables from existing `synthesis.md` instead of re-running Opus

**Brief view shows hardcoded `phases: 11` and `specialists: 3`.** App.tsx:410 hardcodes the meta footer. Should derive from actual run data.

**Empty `confidence` and `firstMilestone` for some runs.** synthesis.md frontmatter doesn't reliably contain `first_milestone` — the field name in the synthesizer schema is `phase_1.name` (or similar). The workspace-reader.ts queries `frontmatter.first_milestone` which often returns null. Fix by mapping to `phase_1.name` or adding a top-level `first_milestone` field to the synthesizer schema.

**Old debug runs show "**Date:** 2026-05-07" in sidebar.** Their `idea.md` files start with date metadata after the `# Idea` heading. The scanner's `readIdea()` skips `#` headings but the next line is the date. Cosmetic; ignore.

**`AgentCard` reveal shows empty `<p />` during real runs.** Python's `ProgressEvent` is phase-grain, not per-role. The runtime store has `onRoleDone(runId, phaseId, roleName, output)` but nothing emits role-level events with output text. Either (a) extend the bridge to read individual `phase-N/<role>.md` files when a phase completes and synthesize per-role events, or (b) accept phase-grain reveals only.

**ETA estimator uses hardcoded constants.** `runtime.ts` has `PHASE_ESTIMATES` baked in. Should learn per-phase historical averages from `library.db` over time.

**`AppHandover/Resume` from old run requires full re-run.** No way to view a partial workspace from the desktop app's intake flow — only via the sidebar.

**The orchestrator-bridge spawns with `--skip-intake` hardcoded.** orchestrator-bridge.ts:63. The Python intake phase (Phase 0 clarifying questions) is permanently disabled from the desktop. The desktop UI has its own clarifying chat (mock questions) but they're not piped into the run. Decide: either pipe answers as `--from-file` content, or remove the desktop chat UI.

**Native module ABI mismatch on fresh installs.** `pnpm install` downloads the Node-prebuilt `better-sqlite3`; Electron uses a different ABI. Fix is `pnpm exec electron-rebuild -f -w better-sqlite3` after install. Originally LEM-24 was supposed to add a `postinstall` hook but was rejected; LEM-26 downgraded to Electron 33 instead; then LEM-31 bumped to Electron 39 without restoring the hook. **Do not add the postinstall hook back without verifying it works on `pnpm install` — it failed silently in LEM-24.**

---

## Open debussy tasks

Run `debussy board` to see live state. As of last session there are no open tasks — Batch 1 + 2 + hot-fix all complete.

If you want to resume: the `feature/electron-ui-alpha` branch is registered as the debussy base branch (`debussy config base_branch feature/electron-ui-alpha`).

---

## To resume after `/clear` (recommended prompt)

Paste this:

> I'm resuming work on the lem Electron desktop alpha. Read `HANDOFF.md` first, then `docs/adr/ADR-0001-electron-ui-architecture.md`. The current branch is `feature/electron-ui-alpha` (pushed). I have a real Claude Max license; the alpha works end-to-end on my machine. I want to: [DESCRIBE GOAL — e.g. "open a PR to main", "implement run-resume capability", "fix the empty AgentCard reveal", "polish the FirstRunWizard pickPath flow"].

Or for specific common follow-ups, use one of these:

**Open a PR against main:**
> Read HANDOFF.md. The feature branch is ready. Open a PR against main with a clear description of what shipped (Batch 1 alpha + Batch 2 security + hot-fix usability). Include test counts and audit results.

**Implement resume capability (Phase 2 feature):**
> Read HANDOFF.md (see "Known issues" → resume capability). Plan and implement `lem resume <run-id>` for the Python orchestrator + a "Resume" button in the desktop sidebar for failed runs. Use the conductor pattern (debussy tasks).

**Fix the AgentCard reveal pattern:**
> Read HANDOFF.md (see "Known issues" → AgentCard reveal). Implement per-role events from the orchestrator-bridge so the Theater shows individual specialist outputs as they complete, not just empty thinking-dots through the whole phase.

---

## Repo conventions (reminder for any agent)

From `CLAUDE.md`:
- No comments unless explaining non-obvious WHY
- Smaller methods, SOLID, single responsibility per file
- Stage files explicitly by name (never `git add .` or `git add -A`)
- Don't commit to main without asking
- Push back on bad approaches; don't agree reflexively
- For bugs, find and state the root cause; if applying a workaround, say so
- Don't add functionality the plan doesn't specify
- Don't suggest installing plugins/MCPs/dependencies beyond what the plan lists

From `docs/adr/ADR-0001-electron-ui-architecture.md`:
- All cross-process types in `desktop/src/shared/`, never `../main/` from preload/renderer
- Tailwind 4 dark-mode via CSS variable indirection (`@theme { --color-bg: var(--t-bg); }`)
- IPC registration pattern: each module exports `registerXxxHandlers(ipcMain, deps)`
- Atomic file writes (tmp + rename)
- `shell.openExternal` only via IPC, never `window.open()` from renderer
- electron-vite, not Electron Forge or Builder
- Tailwind 4 stable (not beta)

---

## Stack quick-ref

- Python: 3.14.3, typer, pyyaml, jinja2, textual, rich, pytest, ruff, pyright, hatchling
- Electron: 39.8.10, React 19, TypeScript, Tailwind 4.1, electron-vite 5, vitest, Playwright
- Native: `better-sqlite3` (needs electron-rebuild after install)
- Auth: piggybacks on user's `claude` CLI (Max subscription); no Anthropic SDK direct usage
