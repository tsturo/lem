# ADR-0001: Electron UI Architecture Decisions

**Date:** 2026-05-09
**Status:** Accepted
**Context:** Phase 1 Alpha implementation of the lem Electron desktop app

## Context

The lem CLI/TUI tool needs a consumer-facing desktop surface for non-technical users. The implementation plan proposes Electron + React + TypeScript + Tailwind 4 in a `desktop/` subdirectory. Six specialist reviews (architect, UX, UI, Electron, AI, orchestration) identified critical issues that require plan amendments before implementation.

## Decisions

### 1. Shared types directory (`src/shared/`)

**Decision:** Create `desktop/src/shared/` for all cross-process types and constants (IPC channels, domain types like `Verdict`, `LibraryItem`, `ProgressEvent`).

**Rationale:** electron-vite builds main, preload, and renderer as separate entry points. Importing from `../main/` in the preload script breaks under `sandbox: true`. Three separate type definitions for `Verdict` guarantees divergence.

### 2. Tailwind 4 dark-mode token architecture

**Decision:** Use CSS variable indirection in `@theme`: `@theme { --color-bg: var(--t-bg); }` with `:root { --t-bg: #fff; }` and `[data-theme="dark"] { --t-bg: #0a0f1a; }`.

**Rationale:** Tailwind 4's `@theme` resolves tokens at build time. Without indirection, utility classes like `bg-bg` bake in the light-mode value and ignore runtime `data-theme` changes. Dark mode would be completely broken.

### 3. IPC registration pattern

**Decision:** Each main-process module (settings, library-db, claude-detect, orchestrator-bridge, workspace-reader) exports a `register(ipcMain, deps)` function. `main/index.ts` calls them all in sequence rather than accumulating inline `ipcMain.handle()` calls.

**Rationale:** Five tasks independently append to `main/index.ts`, `preload/index.ts`, and `types-global.d.ts`. This creates a serialization bottleneck that prevents parallel development. The registration pattern eliminates merge conflicts.

### 4. Stdout JSON-lines for Python→Electron event stream (not file-tailing)

**Decision:** Add a `--json-events` flag to `lem refine` that writes one JSON line per `ProgressEvent` to stdout. The Electron orchestrator bridge reads child stdout line-by-line.

**Rationale:** `ProgressEvent` objects are delivered via `progress_cb` callback — they are NOT written to `meta/log.jsonl`. The plan's file-tailing approach would receive only `LogEvent` entries, which have a different schema. Stdout piping is simpler, has no race conditions, and requires only a ~20-line Python change.

### 5. Atomic settings writes

**Decision:** All file writes in the Electron main process use `writeFileSync` to a `.tmp` file + `renameSync` to target path.

**Rationale:** The lem repo's key invariant is "atomic writes everywhere: tmp + os.replace." The original plan used direct `writeFileSync` which can corrupt on crash.

### 6. `shell.openExternal` via IPC for external URLs

**Decision:** Expose `shell.openExternal` through the IPC bridge. Never use `window.open()` from the renderer.

**Rationale:** With `sandbox: true` + `contextIsolation: true`, `window.open()` attempts to create a new Electron window, not open the system browser. This is both a UX bug and a security concern.

### 7. Tailwind 4 stable (not beta)

**Decision:** Pin `tailwindcss: ^4.1.0` and `@tailwindcss/postcss: ^4.1.0` (stable releases), not `^4.0.0-beta.6`.

**Rationale:** Tailwind 4 stable shipped Jan 2025. The beta pin pulls pre-release versions with known breaking changes.

### 8. Deferred App.tsx assembly

**Decision:** Screen components (IntakeInput, IntakeChat, Theater, Brief) are built as independent exports. App.tsx is assembled once at the end of each milestone, not incrementally after each task.

**Rationale:** App.tsx is modified by 11 of 20 tasks, creating a strict serialization chain. Building screens independently enables parallel development.

## Consequences

- Adds one structural task (shared types + IPC registration) before feature work
- Requires a small Python-side change (--json-events flag) — scoped and low-risk
- Enables 2-3x parallelism across development agents
- Dark mode works correctly from day one
- Settings are crash-safe from day one
