# Design Spec — lem Electron UI

**Date:** 2026-05-08
**Author:** Tomek Szturo
**Status:** approved by user (pending implementation plan)
**Brand-system reference:** [`docs/electron-design-system.md`](../../electron-design-system.md)
**Brand book:** `mbtonale/tonale-landing/docs/tonale-brandbook.md`

This spec describes the desktop Electron UI for **lem**, the multi-agent
idea-refinement tool that today ships as a CLI + Textual TUI. The Electron
app is the consumer-facing surface; the CLI/TUI continue to exist as the
developer-grade interface.

---

## 1. Audience and constraints

- **Primary user:** a non-technical idea-haver. Founder, PM, anyone with
  an idea who'd never touch a terminal. The app *is* lem for them.
- **Secondary user:** the developer running lem on their machine for
  rapid iteration. They don't need a separate UI; the CLI suffices.
- **Auth model:** lem piggybacks on the user's local `claude` CLI
  (Anthropic Claude Code) and a Claude Max subscription. The Electron
  app does not bundle `claude`; it auto-detects it.
- **No hosted backend in v1.** The app is a local desktop tool that
  spawns the lem Python orchestrator as a child process.

A non-technical user must therefore:
1. Install the `.dmg` / `.exe` once.
2. Have a Claude Max account (a constraint we live with for v1).
3. On first run, the app helps them install the `claude` CLI if it's
   not on PATH.

If we cannot meet (3) cleanly, we ship a "thin client + hosted backend"
variant later. Out of scope for this spec.

---

## 2. Architecture

```
┌─────────────────────── Electron (renderer) ──────────────────────────┐
│ React + Tailwind, design-system tokens, theming via [data-theme]     │
│ Talks to main process over IPC                                       │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ IPC
┌────────────────────────────────▼─────────────────────────────────────┐
│ Electron main process                                                │
│   - Spawns Python orchestrator as a sidecar child process            │
│   - Tails meta/log.jsonl                                             │
│   - Receives the new ProgressEvent stream over a named pipe          │
│   - Forwards parsed events to renderer; receives commands            │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ stdio + JSONL files
┌────────────────────────────────▼─────────────────────────────────────┐
│ Bundled Python (PyOxidizer or PyInstaller-frozen)                    │
│   - lem package, all its deps                                        │
│   - Spawns `claude -p` per worker (auto-detected binary)             │
│   - Writes meta/log.jsonl, meta/synthesis.md, deliverables/*.md      │
└──────────────────────────────────────────────────────────────────────┘
```

### Bundling Python
- **Why bundled:** non-technical user does not run `pip install`.
- **How:** PyOxidizer preferred for cross-platform single-binary
  freezing. Fallback: PyInstaller `--onedir` if PyOxidizer can't handle
  Python 3.14 / our deps yet.
- **Size budget:** target < 80 MB compressed for the Python sidecar.
- **Path:** lives at `<app>.app/Contents/Resources/lem-bin/lem` on macOS.

### Detecting `claude`
On first run and on every launch:
1. Check `which claude` and common paths
   (`/usr/local/bin/claude`, `/opt/homebrew/bin/claude`,
   `~/.local/bin/claude`, `~/.claude/local/claude`).
2. If found, validate: `claude --version` exits 0 and returns a sane
   string.
3. If not found, show the **first-run wizard** with a single CTA
   linking to Anthropic's official Claude Code installer + a
   "I've installed it, retry" button.

`LEM_CLAUDE_BIN` env var honored (already supported by lem) for power
users who keep `claude` outside the standard locations.

### IPC contract
- **Main → renderer:** `progress`, `phase-summary`, `run-state`,
  `verdict`, `error`, `claude-not-found`, `auth-failed`.
- **Renderer → main:** `start-run`, `cancel-run`, `open-workspace`,
  `open-deliverable`, `set-theme`, `set-claude-path`.
- Transport: Electron's built-in `ipcRenderer` / `ipcMain`. No web
  sockets, no bonus services.

### Streaming agent text — deferred
We considered switching the worker layer from `claude -p
--output-format json` (full envelope at end) to `--output-format
stream-json --include-partial-messages` (token-by-token).
**Decision: defer to v1.1.** v1 ships the **reveal pattern**:
agent cards render an animated "thinking" state until the worker
finishes, then reveal the full output at once. Visually engaging
without the schema-validator risk and worker-layer rewrite.

---

## 3. Information architecture

The app uses a **library + workspace** shell (see design system §App
shell). Three states the workspace can be in:

| State | Trigger | Surface |
|-------|---------|---------|
| Intake | User clicks `+ New idea`, no run started yet | Idea form, then chat for ≤3 clarifying questions |
| Running | A run is active for the selected idea | Theater (cards + step rail) |
| Brief | The run finished | Deliverable reader (tabs + document) |

The sidebar lists every idea the user has ever started, grouped:
**Active**, **Done**, **Archive**. Items show a status dot, a 1-line
title, and either a verdict glyph (Build / Skip / `?`) or remaining
ETA for in-progress runs.

The `[⚙ Details]` toggle in the topbar opens a 320px right-hand
slide-over with phase IDs / costs / workspace path / live log. Hidden
by default; remembered per-run.

---

## 4. Screens

### 4.1 Intake

Two sub-states.

**Input** (just clicked `+ New idea`):

- Large headline: "What's the **idea**?" with the gradient on
  *idea*.
- Helper paragraph: "One line is fine. Lem will ask a couple of
  clarifying questions, then three specialists weigh in. About 15
  minutes start to finish."
- Single textarea (3 rows tall, expands).
- Optional **extras** block, dashed border, surface bg:
  - "Anything else lem should know? (optional)"
  - **One** chip: `📎 Attach file` — opens a file picker, accepts
    images/markdown/text/PDF.
  - The textarea is **paste-aware**: pasting an image/file places it
    inline as an attachment chip; pasting a URL keeps it as text.
  - **No "Voice memo" or "URL" chips in v1.** A user can paste a URL
    into the textarea; voice is post-v1.
- Bottom row: profile · depth · cost ($0 on Max) on the left, gradient
  CTA "Refine my idea →" on the right.

**Chat** (after submit, while lem asks ≤3 clarifying questions):

- Title: "A couple of questions before we dive in".
- Messages stack vertically, max-width 560px. User on right (gradient
  avatar with initials), lem on left (12% purple avatar with `⌘`).
- Input box at bottom: textarea + "⌘↵ to send" hint + a 3-dot setup
  progress indicator. The current dot uses the gradient.
- After question 3 (or earlier if lem decides it has enough), the run
  starts automatically and the workspace transitions to the Running
  state.

### 4.2 Running — theater

This is the centerpiece visual. Replaces `lem watch` for non-technical
users.

- **Topbar**: idea title + meta line ("…running… ~12 min remaining")
  + action buttons (`⏸ Stop`, `📂 Workspace`, `⚙ Details`).
- **Step rail**: 9 segments, gradient on done, gradient-with-pulse on
  active, border-grey on queued. Label above: "Step 4 of 9 — three
  specialists weighing in" + ETA.
- **Theater area**:
  - The **currently running phase** is the centerpiece, shown as
    cards (one per role for parallel phases, one card for serial).
  - **Earlier completed phases** collapse to a list of one-line
    summaries below the cards. Each row: ✓ purple checkmark + phase
    name + a one-line "money quote" pulled from that phase + duration.
    Click to expand inline.
- **Cards**:
  - Architect: 🏗 in 12% purple bg.
  - Designer: 🎨 in 14% teal bg.
  - Market: 📈 in 8% navy bg.
  - Head: icon + name + status (`streaming` / `thinking` / `done`).
  - Body: 14px text, 1.55 line-height. Streaming caret if/when we add
    streaming (v1: rendered all at once).
  - Foot: `Show full output →` opens the role's full markdown inline.
- **Branching phases (2.1–2.3)** get a different layout:
  - A subtle **disagreement-axis** card at the top, with chips
    showing the domains that disagreed.
  - Two side-by-side branch cards joined by a fork connector.
  - **Survivor** has purple-bordered card, gradient-A badge,
    "Survivor" pill in 10% purple.
  - **Rejected** has 65% opacity, surface bg, coral-X badge, "Rejected"
    pill in 10% coral.
  - Each card includes the branch-skeptic's critique in a dashed-top
    sub-block on a surface bg.

### 4.3 Brief — done view

- Topbar: title + verdict pill on the right (`✓ Build` purple, `✗ Skip`
  coral, `? Insufficient` teal). Action buttons: `↗ Share`, `⤓ PDF`,
  primary `Refine again`.
- Tab strip: **Executive summary** · **MVP plan** · **Risks &
  rejected**. Active tab gets a 2px gradient underline. Each tab can
  show a count chip (e.g. "MVP plan ▸ 12").
- Body: max-width 720px. Opens with a 3-stat **callout**:
  Recommendation · Confidence · First milestone.
- Headline (H1) with the gradient on a single accent word.
- **Lead paragraph** in `--text-2` at 17px, 1.6 line-height, max
  640px wide.
- **Signal pills** below the lead: "3/3 specialists agree", "2 strong
  reframings tested", "5 risks named", "2 paths rejected" — quick
  legibility cues.
- Body uses gradient-circle bullets, teal blockquotes for direct
  specialist quotes, soft typographic hierarchy (no bold-everywhere).
- Footer line: `Generated by lem 0.x · 9 phases · N specialists ·
  YYYY-MM-DD` in 13px text-3.

### 4.4 Details slide-over

320px right-side panel. Pushes main content (or overlays on narrow
windows). Sections:

1. **Phases** — 9 rows, one per phase. `[id] [name] [duration]
   [cost]`. Status glyphs: ✓ done, ● running, ○ queued.
2. **Run total** — 2 stat cards: wall-clock, cost. Footnote:
   "Cost is notional on Max — your subscription covers it."
3. **Workspace** — monospace path + 3 buttons: Open in Finder,
   Open in editor, Open in terminal.
4. **Live log** — 130px scroll window with the JSONL stream
   prettified (timestamp dim, event purple-tinted, role purple,
   monospace). "Open full log" button below opens the raw file.

The Details panel is the **only** place operator-grade information
(IDs, paths, costs, raw log) appears. The default UI keeps it
hidden.

### 4.5 First-run / onboarding

When the app launches and `claude` is not detected:

- Centered card on a tinted surface.
- Headline: "lem needs Claude Code".
- Body: "lem uses your local Claude Code installation to run AI
  agents. We couldn't find it on your machine."
- Primary CTA: "Install Claude Code" → opens
  `https://claude.com/claude-code` in the default browser.
- Secondary: "I've installed it — retry detection" button.
- Tertiary (text link): "Set custom path…" → opens a file picker.

When `claude` is detected but auth has expired (we run a quick
`claude --version`-style probe and check exit), show a similar card:

- Headline: "Sign in to Claude".
- Body: "Run `claude /login` in a terminal and come back."
- Primary: "Open terminal".
- Secondary: "Retry".

### 4.6 Failure UX

If a run fails, the workspace transitions to a failure state (similar
to the Brief view but with a different topbar pill):

- Verdict pill: amber "Couldn't finish" instead of build/skip/unsure.
- Body opens with **What happened** narrative pulled from the new
  `_UserPrinter._failure_blurb()` logic that landed in this branch's
  `fix9` commit (refine.py).
- Followed by **What to do** — re-run, raise wall-clock, etc.
- Then the partial workspace contents are accessible via the same
  Details panel.

This mirrors the CLI's `lem refine --attach` user-friendly failure
output, which means we can reuse the same blurb dictionary on both
surfaces.

---

## 5. Theming

Per the design system:

- Default to OS appearance (`prefers-color-scheme`).
- Settings exposes a manual override (Auto / Light / Dark), persisted
  to `~/Library/Application Support/lem/settings.json`.
- Theme is set on the `<html>` element via `[data-theme]`. Changing it
  triggers token swap; no JS-driven repaint of components needed.

Status colors per the design system (purple = success/build, coral =
error/skip, teal = info/unsure, navy-on-light = neutral, amber =
warning/failure-but-not-skip).

---

## 6. Library / persistence

- **Workspaces** continue to live at `~/.local/share/lem/runs/<run-id>/`
  (XDG, unchanged from the CLI). The Electron app does not move them.
- **Library index** at `~/Library/Application Support/lem/library.db`
  (macOS) / `~/.config/lem/library.db` (Linux):
  - SQLite, single-file.
  - One row per run with: `run_id`, `title`, `created_at`,
    `finished_at`, `status`, `verdict`, `cost`, `workspace_path`.
  - Populated on demand by scanning workspace directories on first
    launch; updated incrementally as the orchestrator emits
    progress events.
- **Settings** (theme, last `claude` path, etc.) at
  `~/Library/Application Support/lem/settings.json`.

---

## 7. Out of scope for v1

- **Streaming agent text** — see §2. Reveal pattern only.
- **Voice memo intake** — chip removed; v1.x.
- **Mid-run "add more context"** — folding additional input into a
  running pipeline is complex and error-prone. Defer; do "rerun with
  added context" post-run instead.
- **Hosted backend / share-link** — v2.
- **Multi-user / collaboration / team library** — v2+.
- **Profile editor in-app** — profiles stay file-based; advanced users
  edit them in their editor.
- **Export PDF as a custom-styled brand artifact** — v1 ships a
  Chromium "Save as PDF" of the brief tab. Custom-styled PDF is v1.x.

---

## 8. Open implementation questions

These are the questions the implementation plan will need to answer.
Listed for the planner; not part of this design.

1. **Bundling tool** — PyOxidizer vs PyInstaller — depends on Python
   3.14 support and dependency compatibility. Bench both in a spike.
2. **macOS code-signing + notarization** — need a developer
   certificate; budget time for the first release ceremony.
3. **Auto-update** — Squirrel.Mac (built into Electron) is the default;
   the lem-bin sidecar binary needs to be replaced atomically alongside
   the renderer.
4. **Library db migration** — when v2 changes the schema, we need a
   migration story. SQLite + a `schema_version` table is fine.
5. **Telemetry** — do we send anonymous run-completion / error events
   to a Tonale endpoint? Out of scope for *design*; needs a separate
   privacy decision.
6. **Windows / Linux** — focus macOS first; Windows + Linux follow.
   The design system covers the visual layer; window-control and
   vibrancy specifics are macOS-only and need equivalents.

---

## 9. Mockup record

The browser mockups produced in the brainstorm session are saved
under `.superpowers/brainstorm/<session>/content/`:

- `app-shell-tonale.html` — primary running view (light)
- `app-shell-light-vs-dark.html` — both modes
- `intake.html` — input + clarifying chat
- `brief.html` — done view with verdict, callout, tabs
- `branching-and-details.html` — fork visualization + details panel

These are throwaway HTML — the canonical visual contract lives in
`docs/electron-design-system.md`. The mockups are useful as a frozen
reference for the implementation team.

---

## 10. Build sequence (for the planner)

Suggested phases for the implementation plan that follows from this spec:

1. **Spike: Python bundling** — confirm PyOxidizer/PyInstaller works
   with lem's deps. Two days.
2. **Electron skeleton** — window chrome, sidebar + main pane shell,
   theming, design-system token import. Three days.
3. **Library db + sidebar** — read/write the SQLite index, populate
   the sidebar from existing workspaces. Two days.
4. **First-run wizard + claude detection** — offline-able, includes
   the auth-failed flow. Two days.
5. **Intake screen + clarifying chat** — wires to `lem refine` with
   the new `--from-file` and progress callback. Three days.
6. **Theater / running view** — IPC plumbing for ProgressEvents,
   per-phase card layouts, branching layout. **Five days.**
7. **Brief view** — markdown rendering, tabs, callout, verdict pill,
   PDF export. Three days.
8. **Details slide-over** — phase summary, totals, log tail, workspace
   actions. Two days.
9. **Failure UX + edge cases** — wall-clock abort, cost abort,
   orchestrator crash, partial workspace. Two days.
10. **Polish + a11y + reduced-motion + macOS package** — Three days.

Total estimate: ~30 dev-days. The most risky chunk is #6 (theater) —
that's where streaming-vs-reveal ambiguity lives, and where the IPC
+ rendering layer is most novel.
