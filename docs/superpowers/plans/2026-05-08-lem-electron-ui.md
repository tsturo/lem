# Lem Electron UI — Phase 1 (Alpha) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an alpha build of the lem Electron app — a non-technical user can launch it, paste an idea, watch a refine run end-to-end, and read the brief, all on the developer's local machine with `lem` available on PATH.

**Architecture:** Electron + React + TypeScript + Tailwind 4 in a `desktop/` subdirectory of the lem repo. The renderer follows the [Tonale Electron Design System](../../electron-design-system.md) and the [lem UI design spec](../specs/2026-05-08-lem-electron-ui-design.md). The Electron main process spawns the existing Python `lem refine --attach` as a sidecar child process and forwards `ProgressEvent`s + JSONL log lines to the renderer over IPC. SQLite (`better-sqlite3`) indexes the user's run library.

**Tech Stack:** electron-vite, React 19, TypeScript, Tailwind 4 (with @theme tokens), better-sqlite3, Vitest (unit), Playwright (e2e). The Python sidecar is the existing lem package — no Python work in this plan.

**Out of scope (handled in a Phase 2 plan):** PyOxidizer/PyInstaller bundling of Python, macOS code-signing + notarization, auto-update via Squirrel, branching-phase fork visualization, Details slide-over, failure-UX polish, PDF export, settings screen, Windows/Linux packaging.

**Milestones inside this plan:**

| Milestone | Tasks | What's working |
|-----------|-------|----------------|
| **A · Skeleton** | 1–5 | App launches with the right window chrome, brand mark, theming. No content yet. |
| **B · Static UI** | 6–11 | Sidebar, topbar, intake screens, all design-system primitives — but no live data or run capability. |
| **C · End-to-end** | 12–20 | Library populates from disk; user can intake → run → read the brief. Theater is the basic "reveal" pattern (no streaming, no branching layout). |

---

## File Structure

```
desktop/                                    # new subdirectory in the lem repo
├── package.json
├── electron.vite.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── tailwind.config.ts
├── postcss.config.js
├── playwright.config.ts
├── index.html
├── src/
│   ├── main/                               # Electron main process
│   │   ├── index.ts                        # createWindow, ipcMain handlers
│   │   ├── claude-detect.ts                # find the `claude` binary on PATH
│   │   ├── library-db.ts                   # better-sqlite3 wrapper (runs index)
│   │   ├── orchestrator-bridge.ts          # spawn `lem refine`, tail events
│   │   ├── settings.ts                     # read/write settings.json
│   │   └── ipc-channels.ts                 # shared channel-name constants
│   ├── preload/
│   │   └── index.ts                        # contextBridge.exposeInMainWorld('lem', ...)
│   ├── renderer/
│   │   ├── main.tsx                        # React root
│   │   ├── App.tsx                         # Top-level routing between Library / Intake / Theater / Brief
│   │   ├── globals.css                     # Tailwind import + Tonale @theme tokens
│   │   ├── theme.ts                        # data-theme attribute + matchMedia plumbing
│   │   ├── lib/
│   │   │   ├── ipc.ts                      # typed wrappers around window.lem
│   │   │   ├── format.ts                   # duration, cost formatting
│   │   │   └── markdown.tsx                # render lem deliverables → React
│   │   ├── store/
│   │   │   ├── library.ts                  # zustand: list of runs, selected run id
│   │   │   ├── runtime.ts                  # zustand: live ProgressEvents per run
│   │   │   └── settings.ts                 # zustand: theme, claude-path
│   │   ├── components/
│   │   │   ├── Titlebar.tsx
│   │   │   ├── BrandMark.tsx               # 9-bar gradient SVG
│   │   │   ├── AppShell.tsx                # Sidebar + Main pane layout
│   │   │   ├── Sidebar.tsx
│   │   │   ├── SidebarItem.tsx
│   │   │   ├── Topbar.tsx
│   │   │   ├── StatusDot.tsx
│   │   │   ├── VerdictPill.tsx
│   │   │   ├── StepRail.tsx
│   │   │   ├── PrimaryButton.tsx
│   │   │   ├── IconButton.tsx
│   │   │   ├── Chip.tsx
│   │   │   ├── Callout.tsx
│   │   │   └── FirstRunWizard.tsx
│   │   └── screens/
│   │       ├── IntakeInput.tsx             # state 1: idea form
│   │       ├── IntakeChat.tsx              # state 2: clarifying questions
│   │       ├── Theater.tsx                 # running state
│   │       ├── AgentCard.tsx
│   │       ├── EarlierSteps.tsx
│   │       └── Brief.tsx                   # done state
│   └── types/
│       └── lem-events.ts                   # TypeScript shapes for ProgressEvent + RunState
└── tests/
    ├── unit/
    │   ├── claude-detect.test.ts
    │   ├── library-db.test.ts
    │   └── orchestrator-bridge.test.ts
    └── e2e/
        └── full-run.spec.ts
```

The `desktop/` subdirectory is its own npm package with its own lockfile. The Python lem package is unchanged.

---

## Conventions for every task

- Each task ends with a commit step. Use Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`).
- Run TypeScript + lint before each commit: `pnpm tsc --noEmit && pnpm lint`.
- Keep components small (under ~150 lines). Split when they grow.
- Don't write comments unless the WHY is non-obvious (per the lem repo's CLAUDE.md).
- Use `pnpm`, not `npm` or `yarn` — already established in the user's tooling.

---

## Task 1: Scaffold the desktop subdirectory

**Files:**
- Create: `desktop/package.json`
- Create: `desktop/electron.vite.config.ts`
- Create: `desktop/tsconfig.json`
- Create: `desktop/tsconfig.node.json`
- Create: `desktop/index.html`
- Create: `desktop/src/main/index.ts`
- Create: `desktop/src/preload/index.ts`
- Create: `desktop/src/renderer/main.tsx`
- Create: `desktop/src/renderer/App.tsx`
- Modify: `.gitignore` (add `desktop/node_modules/`, `desktop/dist/`, `desktop/out/`)

- [ ] **Step 1: Create the desktop directory and stub package.json**

```bash
mkdir -p desktop/src/{main,preload,renderer,types}
mkdir -p desktop/src/renderer/{lib,store,components,screens}
mkdir -p desktop/tests/{unit,e2e}
cd desktop
```

```json
// desktop/package.json
{
  "name": "lem-desktop",
  "version": "0.1.0-alpha.1",
  "description": "Tonale lem — Electron desktop app",
  "main": "out/main/index.js",
  "type": "module",
  "scripts": {
    "dev": "electron-vite dev",
    "build": "electron-vite build",
    "preview": "electron-vite preview",
    "tsc": "tsc --noEmit -p tsconfig.json && tsc --noEmit -p tsconfig.node.json",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test",
    "lint": "eslint src --ext .ts,.tsx"
  },
  "dependencies": {
    "better-sqlite3": "^11.7.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "zustand": "^5.0.2"
  },
  "devDependencies": {
    "@playwright/test": "^1.49.0",
    "@types/better-sqlite3": "^7.6.12",
    "@types/node": "^22.10.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "electron": "^33.0.0",
    "electron-vite": "^2.3.0",
    "eslint": "^9.16.0",
    "tailwindcss": "^4.0.0-beta.6",
    "@tailwindcss/postcss": "^4.0.0-beta.6",
    "postcss": "^8.4.49",
    "typescript": "~5.6.3",
    "vite": "^6.0.0",
    "vitest": "^2.1.8"
  }
}
```

- [ ] **Step 2: Install dependencies**

```bash
cd desktop
pnpm install
```

Expected: `pnpm-lock.yaml` is created; no peer-dependency errors. If `better-sqlite3` fails to compile native bindings, install Xcode CLT (`xcode-select --install`) and re-run.

- [ ] **Step 3: Create electron-vite config**

```typescript
// desktop/electron.vite.config.ts
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: { outDir: 'out/main' }
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: { outDir: 'out/preload' }
  },
  renderer: {
    plugins: [react()],
    build: { outDir: 'out/renderer' },
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src/renderer')
      }
    }
  }
})
```

- [ ] **Step 4: Create tsconfigs**

```json
// desktop/tsconfig.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "baseUrl": ".",
    "paths": { "@/*": ["src/renderer/*"] }
  },
  "include": ["src/renderer/**/*", "src/preload/**/*", "src/types/**/*"]
}
```

```json
// desktop/tsconfig.node.json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "lib": ["ES2022"],
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "noEmit": true,
    "types": ["node"]
  },
  "include": ["src/main/**/*", "electron.vite.config.ts"]
}
```

- [ ] **Step 5: Create the renderer entry point**

```html
<!-- desktop/index.html -->
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>lem</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/renderer/main.tsx"></script>
  </body>
</html>
```

```typescript
// desktop/src/renderer/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './globals.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

```tsx
// desktop/src/renderer/App.tsx
export default function App() {
  return (
    <div className="h-screen flex items-center justify-center bg-white">
      <p className="font-rubik text-text">lem · alpha</p>
    </div>
  )
}
```

(`globals.css` and `font-rubik` come in Task 2-3; this fails to load until then — that's expected.)

- [ ] **Step 6: Create the main process entry**

```typescript
// desktop/src/main/index.ts
import { app, BrowserWindow } from 'electron'
import { join } from 'node:path'

function createWindow(): void {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    show: false,
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 14, y: 12 },
    backgroundColor: '#ffffff',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: true,
      contextIsolation: true
    }
  })
  win.once('ready-to-show', () => win.show())

  if (process.env.ELECTRON_RENDERER_URL) {
    win.loadURL(process.env.ELECTRON_RENDERER_URL)
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
```

```typescript
// desktop/src/preload/index.ts
import { contextBridge } from 'electron'

contextBridge.exposeInMainWorld('lem', {})
```

- [ ] **Step 7: Update root .gitignore**

Append to `/Users/tomek/dev/lem/.gitignore`:

```
desktop/node_modules/
desktop/dist/
desktop/out/
desktop/test-results/
desktop/playwright-report/
desktop/.vite/
```

- [ ] **Step 8: Verify the app launches**

```bash
cd desktop && pnpm dev
```

Expected: an Electron window opens with traffic-light buttons inset on a white background. Console shows no errors. Close the window.

- [ ] **Step 9: Commit**

```bash
cd /Users/tomek/dev/lem
git add desktop/package.json desktop/pnpm-lock.yaml desktop/electron.vite.config.ts \
        desktop/tsconfig.json desktop/tsconfig.node.json desktop/index.html \
        desktop/src/main/index.ts desktop/src/preload/index.ts \
        desktop/src/renderer/main.tsx desktop/src/renderer/App.tsx \
        .gitignore
git commit -m "feat(desktop): scaffold electron-vite + react + ts skeleton"
```

---

## Task 2: Tonale design tokens + Tailwind 4 theme

**Files:**
- Create: `desktop/src/renderer/globals.css`
- Create: `desktop/postcss.config.js`
- Modify: `desktop/electron.vite.config.ts` (add postcss config to renderer)

- [ ] **Step 1: Add the postcss config**

```javascript
// desktop/postcss.config.js
export default {
  plugins: {
    '@tailwindcss/postcss': {}
  }
}
```

- [ ] **Step 2: Add globals.css with the full Tonale token block**

Reference: `docs/electron-design-system.md` §Tokens. Light is the default; dark is on `[data-theme="dark"]`.

```css
/* desktop/src/renderer/globals.css */
@import "tailwindcss";

@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;700&display=swap');

@theme {
  --color-purple: #6c5ce7;
  --color-teal: #00cec9;

  --color-bg: #ffffff;
  --color-surface: #f7f7fb;
  --color-text: #1a1a2e;
  --color-text-2: #4a4a68;
  --color-text-3: #8888a4;
  --color-border: #e8e8f0;

  --color-status-success: #6c5ce7;
  --color-status-info:    #00cec9;
  --color-status-warn:    #d4a843;
  --color-status-error:   #d97070;
  --color-status-muted:   #c8c8d4;

  --font-rubik: "Rubik", -apple-system, BlinkMacSystemFont, "Inter", sans-serif;
  --font-mono:  "SF Mono", Menlo, Consolas, monospace;

  --radius-sm: 9px;
  --radius-md: 12px;
  --radius-lg: 14px;
  --radius-xl: 16px;
}

:root {
  --t-grad: linear-gradient(135deg, #6c5ce7, #00cec9);
  --shadow-card:        0 2px 12px rgba(10, 15, 26, 0.06);
  --shadow-card-hover:  0 4px 24px rgba(10, 15, 26, 0.10);
  --shadow-window:      0 30px 60px -20px rgba(10, 15, 26, 0.18);
  --shadow-cta:         0 4px 14px rgba(108, 92, 231, 0.30);
  --pulse-rgb: 108, 92, 231;
}

[data-theme="dark"] {
  --color-bg:       #0a0f1a;
  --color-surface:  #131829;
  --color-text:     #e8edf3;
  --color-text-2:   #a8b0c2;
  --color-text-3:   #6b7388;
  --color-border:   rgba(232, 237, 243, 0.08);
  --color-status-error: #e08585;
  --color-status-muted: #3a4258;
  --shadow-card:        0 1px 0 rgba(232, 237, 243, 0.02);
  --shadow-card-hover:  0 8px 24px rgba(0, 0, 0, 0.40);
  --shadow-window:      0 30px 60px -20px rgba(0, 0, 0, 0.60);
  --pulse-rgb: 0, 206, 201;
}

html, body, #root {
  height: 100%;
  margin: 0;
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-rubik);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

button { font: inherit; cursor: pointer; }
*, *::before, *::after { box-sizing: border-box; }

@keyframes pulse {
  0%   { box-shadow: 0 0 0 0 rgba(var(--pulse-rgb), 0.5); }
  70%  { box-shadow: 0 0 0 8px rgba(var(--pulse-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--pulse-rgb), 0); }
}
@keyframes blink  { 50% { opacity: 0; } }
@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40%           { transform: translateY(-3px); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important;
    transition: none !important;
  }
}
```

- [ ] **Step 3: Update App.tsx to consume the tokens**

```tsx
// desktop/src/renderer/App.tsx
export default function App() {
  return (
    <div className="h-screen flex items-center justify-center bg-bg text-text">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight">
          lem ·{' '}
          <span
            className="bg-clip-text text-transparent"
            style={{ backgroundImage: 'var(--t-grad)' }}
          >
            tonale
          </span>
        </h1>
        <p className="mt-2 text-text-2">design tokens loaded</p>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Verify the gradient renders + Rubik loads**

```bash
cd desktop && pnpm dev
```

Expected: window shows "lem · **tonale**" with the word "tonale" filled by the purple→teal gradient. Font is Rubik (rounded sans-serif). If the gradient appears black, check that the `bg-clip-text` + `text-transparent` Tailwind v4 utilities are applied; if Rubik shows as Helvetica, check the @import line in globals.css and the network panel.

- [ ] **Step 5: Commit**

```bash
git add desktop/src/renderer/globals.css desktop/src/renderer/App.tsx desktop/postcss.config.js
git commit -m "feat(desktop): tonale design tokens + tailwind v4 theme"
```

---

## Task 3: Brand mark SVG component

**Files:**
- Create: `desktop/src/renderer/components/BrandMark.tsx`
- Create: `desktop/tests/unit/brand-mark.test.tsx` (with @testing-library/react)
- Modify: `desktop/package.json` (add `@testing-library/react`, `jsdom`)

- [ ] **Step 1: Add testing dependencies**

```bash
cd desktop
pnpm add -D @testing-library/react @testing-library/jest-dom jsdom
```

- [ ] **Step 2: Configure Vitest**

Create `desktop/vitest.config.ts`:

```typescript
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'node:path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts']
  },
  resolve: {
    alias: { '@': resolve(__dirname, 'src/renderer') }
  }
})
```

```typescript
// desktop/tests/setup.ts
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 3: Write the failing component test**

```tsx
// desktop/tests/unit/brand-mark.test.tsx
import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { BrandMark } from '@/components/BrandMark'

describe('BrandMark', () => {
  it('renders 9 vertical bars in mountain silhouette', () => {
    const { container } = render(<BrandMark />)
    const bars = container.querySelectorAll('[data-bar]')
    expect(bars.length).toBe(9)
  })

  it('applies different heights to outer vs center bars', () => {
    const { container } = render(<BrandMark />)
    const bars = Array.from(container.querySelectorAll('[data-bar]'))
    const center = bars[4] as HTMLElement
    const outer = bars[0] as HTMLElement
    const centerH = parseFloat(center.style.height)
    const outerH = parseFloat(outer.style.height)
    expect(centerH).toBeGreaterThan(outerH)
  })
})
```

- [ ] **Step 4: Run the test and confirm it fails**

```bash
pnpm test
```

Expected: `Cannot find module '@/components/BrandMark'`. Good — failure-first.

- [ ] **Step 5: Implement BrandMark**

```tsx
// desktop/src/renderer/components/BrandMark.tsx
const HEIGHTS = [35, 55, 75, 90, 100, 90, 75, 55, 35]
const OPACITIES = [0.55, 0.7, 0.85, 1, 1, 1, 0.85, 0.7, 0.55]

interface BrandMarkProps {
  size?: number          // total pixel height of the mark
  className?: string
}

export function BrandMark({ size = 14, className }: BrandMarkProps) {
  return (
    <span
      className={`inline-flex items-end gap-[1.5px] ${className ?? ''}`}
      style={{ height: size }}
      aria-label="Tonale"
      role="img"
    >
      {HEIGHTS.map((h, i) => (
        <span
          key={i}
          data-bar
          style={{
            width: 2,
            height: `${h}%`,
            opacity: OPACITIES[i],
            background: 'var(--t-grad)',
            borderRadius: 1.5
          }}
        />
      ))}
    </span>
  )
}
```

- [ ] **Step 6: Run the tests and confirm they pass**

```bash
pnpm test
```

Expected: 2 tests pass.

- [ ] **Step 7: Commit**

```bash
git add desktop/src/renderer/components/BrandMark.tsx \
        desktop/tests/unit/brand-mark.test.tsx \
        desktop/tests/setup.ts \
        desktop/vitest.config.ts \
        desktop/package.json desktop/pnpm-lock.yaml
git commit -m "feat(desktop): brand mark + vitest setup"
```

---

## Task 4: Custom titlebar with traffic-lights inset

**Files:**
- Create: `desktop/src/renderer/components/Titlebar.tsx`
- Modify: `desktop/src/renderer/App.tsx`

- [ ] **Step 1: Implement the titlebar**

```tsx
// desktop/src/renderer/components/Titlebar.tsx
import { BrandMark } from './BrandMark'

export function Titlebar() {
  return (
    <header
      className="h-9 flex items-center justify-center px-4 border-b border-border bg-surface select-none"
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
    >
      <div className="flex items-center gap-2">
        <BrandMark size={14} />
        <span className="text-[13px] font-medium text-text-2 tracking-[0.02em]">
          lem &nbsp;·&nbsp; by tonale
        </span>
      </div>
    </header>
  )
}
```

- [ ] **Step 2: Mount the titlebar in App**

```tsx
// desktop/src/renderer/App.tsx
import { Titlebar } from './components/Titlebar'

export default function App() {
  return (
    <div className="h-screen flex flex-col bg-bg text-text">
      <Titlebar />
      <main className="flex-1 flex items-center justify-center">
        <p className="text-text-2">workspace coming up next</p>
      </main>
    </div>
  )
}
```

- [ ] **Step 3: Verify visually**

```bash
pnpm dev
```

Expected: a 36px-tall titlebar with the brand bars + "lem · by tonale" centered. Traffic-light buttons sit at the left edge of the titlebar (inset). The titlebar is draggable; clicking + dragging it moves the window.

- [ ] **Step 4: Commit**

```bash
git add desktop/src/renderer/components/Titlebar.tsx desktop/src/renderer/App.tsx
git commit -m "feat(desktop): custom titlebar with brand mark"
```

---

## Task 5: AppShell layout (Sidebar slot + Main pane slot)

**Files:**
- Create: `desktop/src/renderer/components/AppShell.tsx`
- Modify: `desktop/src/renderer/App.tsx`

- [ ] **Step 1: Implement the shell**

```tsx
// desktop/src/renderer/components/AppShell.tsx
import { Titlebar } from './Titlebar'

interface AppShellProps {
  sidebar: React.ReactNode
  children: React.ReactNode
}

export function AppShell({ sidebar, children }: AppShellProps) {
  return (
    <div className="h-screen flex flex-col bg-bg text-text">
      <Titlebar />
      <div className="flex-1 flex min-h-0">
        <aside className="w-[232px] shrink-0 border-r border-border bg-surface overflow-y-auto">
          {sidebar}
        </aside>
        <main className="flex-1 flex flex-col min-w-0">
          {children}
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Use the shell in App**

```tsx
// desktop/src/renderer/App.tsx
import { AppShell } from './components/AppShell'

export default function App() {
  return (
    <AppShell sidebar={<div className="p-3 text-text-3 text-sm">sidebar</div>}>
      <div className="flex-1 flex items-center justify-center text-text-2">
        main pane
      </div>
    </AppShell>
  )
}
```

- [ ] **Step 3: Verify visually**

```bash
pnpm dev
```

Expected: titlebar; below it a 232px sidebar with "sidebar" placeholder on the surface bg; right of it the main pane with "main pane". Border between them.

- [ ] **Step 4: Commit**

```bash
git add desktop/src/renderer/components/AppShell.tsx desktop/src/renderer/App.tsx
git commit -m "feat(desktop): app shell layout"
```

---

🏁 **Milestone A complete** — the app launches with correct chrome, theming, and layout.

---

## Task 6: Reusable primitives — StatusDot, VerdictPill, StepRail, Chip

**Files:**
- Create: `desktop/src/renderer/components/StatusDot.tsx`
- Create: `desktop/src/renderer/components/VerdictPill.tsx`
- Create: `desktop/src/renderer/components/StepRail.tsx`
- Create: `desktop/src/renderer/components/Chip.tsx`
- Create: `desktop/src/renderer/components/PrimaryButton.tsx`
- Create: `desktop/src/renderer/components/IconButton.tsx`
- Create: `desktop/tests/unit/primitives.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
// desktop/tests/unit/primitives.test.tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { StatusDot } from '@/components/StatusDot'
import { VerdictPill } from '@/components/VerdictPill'
import { StepRail } from '@/components/StepRail'

describe('StatusDot', () => {
  it('animates when status is "running"', () => {
    const { container } = render(<StatusDot status="running" />)
    const dot = container.querySelector('[data-status]') as HTMLElement
    expect(dot.dataset.status).toBe('running')
    expect(dot.style.animation || getComputedStyle(dot).animation).toMatch(/pulse/)
  })
  it('uses success color for build', () => {
    const { container } = render(<StatusDot status="build" />)
    const dot = container.querySelector('[data-status]') as HTMLElement
    expect(dot.style.background).toContain('108')
  })
})

describe('VerdictPill', () => {
  it('renders ✓ for build', () => {
    render(<VerdictPill verdict="build" />)
    expect(screen.getByText(/Build/i)).toBeInTheDocument()
    expect(screen.getByText('✓')).toBeInTheDocument()
  })
  it('renders ✗ for skip', () => {
    render(<VerdictPill verdict="skip" />)
    expect(screen.getByText(/Skip/i)).toBeInTheDocument()
    expect(screen.getByText('✗')).toBeInTheDocument()
  })
  it('renders ? for unsure', () => {
    render(<VerdictPill verdict="unsure" />)
    expect(screen.getByText(/Insufficient/i)).toBeInTheDocument()
  })
})

describe('StepRail', () => {
  it('marks steps as done up to the active index', () => {
    const { container } = render(<StepRail total={9} active={3} />)
    const segments = container.querySelectorAll('[data-step]')
    expect(segments.length).toBe(9)
    const states = Array.from(segments).map((el) => (el as HTMLElement).dataset.state)
    expect(states.slice(0, 3).every((s) => s === 'done')).toBe(true)
    expect(states[3]).toBe('active')
    expect(states.slice(4).every((s) => s === 'queued')).toBe(true)
  })
})
```

- [ ] **Step 2: Run tests, confirm they fail**

```bash
pnpm test
```

Expected: module-not-found errors for the three components.

- [ ] **Step 3: Implement StatusDot**

```tsx
// desktop/src/renderer/components/StatusDot.tsx
export type Status = 'running' | 'build' | 'skip' | 'unsure' | 'archive'

const COLORS: Record<Status, string> = {
  running: 'var(--color-purple)',
  build:   'var(--color-purple)',
  skip:    'var(--color-status-error)',
  unsure:  'var(--color-teal)',
  archive: 'var(--color-status-muted)'
}

export function StatusDot({ status }: { status: Status }) {
  const isRunning = status === 'running'
  return (
    <span
      data-status={status}
      className="w-2 h-2 rounded-full shrink-0"
      style={{
        background: COLORS[status],
        animation: isRunning ? 'pulse 1.4s infinite' : undefined
      }}
    />
  )
}
```

- [ ] **Step 4: Implement VerdictPill**

```tsx
// desktop/src/renderer/components/VerdictPill.tsx
export type Verdict = 'build' | 'skip' | 'unsure'

const CONFIG: Record<Verdict, { label: string; glyph: string; bg: string; border: string; color: string; glyphBg: string }> = {
  build: {
    label: 'Build', glyph: '✓',
    bg: 'rgba(108, 92, 231, 0.10)',
    border: 'rgba(108, 92, 231, 0.25)',
    color: 'var(--color-purple)',
    glyphBg: 'var(--t-grad)'
  },
  skip: {
    label: 'Skip', glyph: '✗',
    bg: 'rgba(217, 112, 112, 0.10)',
    border: 'rgba(217, 112, 112, 0.25)',
    color: 'var(--color-status-error)',
    glyphBg: 'var(--color-status-error)'
  },
  unsure: {
    label: 'Insufficient info', glyph: '?',
    bg: 'rgba(0, 206, 201, 0.12)',
    border: 'rgba(0, 206, 201, 0.30)',
    color: '#009b97',
    glyphBg: 'var(--color-teal)'
  }
}

export function VerdictPill({ verdict }: { verdict: Verdict }) {
  const c = CONFIG[verdict]
  return (
    <span
      className="inline-flex items-center gap-2 rounded-full text-[13px] font-bold tracking-[0.04em]"
      style={{ padding: '8px 14px', background: c.bg, border: `1px solid ${c.border}`, color: c.color }}
    >
      <span
        className="inline-flex items-center justify-center text-[11px] font-bold text-white"
        style={{ width: 18, height: 18, borderRadius: '50%', background: c.glyphBg }}
      >
        {c.glyph}
      </span>
      {c.label}
    </span>
  )
}
```

- [ ] **Step 5: Implement StepRail**

```tsx
// desktop/src/renderer/components/StepRail.tsx
interface StepRailProps {
  total: number
  active: number   // 0-based index of the active step (-1 = none)
  label?: string
  eta?: string
}

export function StepRail({ total, active, label, eta }: StepRailProps) {
  return (
    <div className="px-7 pt-3.5 pb-4 border-b border-border bg-surface">
      {label && (
        <div className="text-[12px] text-text-2 mb-2.5 flex justify-between font-medium">
          <span>{label}</span>
          {eta && <span className="text-text font-medium">{eta}</span>}
        </div>
      )}
      <div className="flex gap-1">
        {Array.from({ length: total }).map((_, i) => {
          const state = i < active ? 'done' : i === active ? 'active' : 'queued'
          return (
            <div
              key={i}
              data-step
              data-state={state}
              className="flex-1 h-[5px] rounded-[3px] relative"
              style={{
                background:
                  state === 'done'
                    ? 'var(--t-grad)'
                    : state === 'active'
                    ? 'linear-gradient(90deg, #6c5ce7 0%, #00cec9 60%, var(--color-border) 60%)'
                    : 'var(--color-border)'
              }}
            >
              {state === 'active' && (
                <span
                  className="absolute"
                  style={{
                    left: '60%',
                    top: -3,
                    width: 11,
                    height: 11,
                    borderRadius: '50%',
                    background: 'var(--color-purple)',
                    boxShadow: '0 1px 4px rgba(108, 92, 231, 0.4)',
                    animation: 'pulse 1.4s infinite',
                    transform: 'translateX(-50%)'
                  }}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Implement Chip / PrimaryButton / IconButton**

```tsx
// desktop/src/renderer/components/Chip.tsx
interface ChipProps {
  children: React.ReactNode
  onClick?: () => void
  tone?: 'default' | 'purple' | 'teal'
}

export function Chip({ children, onClick, tone = 'default' }: ChipProps) {
  const tones = {
    default: { bg: 'var(--color-bg)', color: 'var(--color-text-2)', border: 'var(--color-border)' },
    purple:  { bg: 'rgba(108,92,231,0.08)', color: 'var(--color-purple)', border: 'rgba(108,92,231,0.20)' },
    teal:    { bg: 'rgba(0,206,201,0.10)',  color: '#009b97',             border: 'rgba(0,206,201,0.25)' }
  }
  const t = tones[tone]
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 rounded-full text-[12px] transition-colors"
      style={{ padding: '6px 12px', background: t.bg, border: `1px solid ${t.border}`, color: t.color }}
    >
      {children}
    </button>
  )
}
```

```tsx
// desktop/src/renderer/components/PrimaryButton.tsx
interface PrimaryButtonProps {
  children: React.ReactNode
  onClick?: () => void
  disabled?: boolean
  type?: 'button' | 'submit'
}

export function PrimaryButton({ children, onClick, disabled, type = 'button' }: PrimaryButtonProps) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className="text-white border-0 rounded-xl text-[16px] font-medium tracking-[0.01em] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      style={{
        padding: '14px 32px',
        background: 'var(--t-grad)',
        boxShadow: 'var(--shadow-cta)'
      }}
    >
      {children}
    </button>
  )
}
```

```tsx
// desktop/src/renderer/components/IconButton.tsx
interface IconButtonProps {
  children: React.ReactNode
  onClick?: () => void
  active?: boolean
  title?: string
}

export function IconButton({ children, onClick, active, title }: IconButtonProps) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="w-8 h-8 rounded-[9px] border flex items-center justify-center text-[13px] transition-colors"
      style={{
        background: active ? 'rgba(108,92,231,0.14)' : 'transparent',
        borderColor: active ? 'rgba(108,92,231,0.45)' : 'var(--color-border)',
        color: active ? 'var(--color-purple)' : 'var(--color-text-2)'
      }}
    >
      {children}
    </button>
  )
}
```

- [ ] **Step 7: Run tests and confirm they pass**

```bash
pnpm test
```

Expected: 8 tests pass (from 3 suites).

- [ ] **Step 8: Commit**

```bash
git add desktop/src/renderer/components/{StatusDot,VerdictPill,StepRail,Chip,PrimaryButton,IconButton}.tsx \
        desktop/tests/unit/primitives.test.tsx
git commit -m "feat(desktop): reusable primitives — StatusDot, VerdictPill, StepRail, Chip, buttons"
```

---

## Task 7: Sidebar with mock data

**Files:**
- Create: `desktop/src/renderer/components/SidebarItem.tsx`
- Create: `desktop/src/renderer/components/Sidebar.tsx`
- Create: `desktop/src/types/library.ts`
- Modify: `desktop/src/renderer/App.tsx`

- [ ] **Step 1: Define LibraryItem type**

```typescript
// desktop/src/types/library.ts
export type RunGroup = 'active' | 'done' | 'archive'
export type Verdict = 'build' | 'skip' | 'unsure'

export interface LibraryItem {
  id: string
  title: string
  group: RunGroup
  verdict?: Verdict
  etaMinutes?: number
  selected?: boolean
}
```

- [ ] **Step 2: Implement SidebarItem**

```tsx
// desktop/src/renderer/components/SidebarItem.tsx
import { StatusDot } from './StatusDot'
import type { LibraryItem } from '../../types/library'

export function SidebarItem({ item, onClick }: { item: LibraryItem; onClick?: () => void }) {
  const status =
    item.group === 'active' ? 'running'
    : item.group === 'archive' ? 'archive'
    : item.verdict === 'skip' ? 'skip'
    : item.verdict === 'unsure' ? 'unsure'
    : 'build'

  const verdictText =
    item.group === 'active' && item.etaMinutes != null ? `${item.etaMinutes}m`
    : item.verdict === 'unsure' ? '?'
    : item.verdict ?? ''

  return (
    <button
      onClick={onClick}
      className={`relative w-full text-left flex items-center gap-2.5 rounded-[9px] mb-px transition-colors
                  ${item.selected ? 'bg-[rgba(108,92,231,0.10)] text-text font-medium' : 'text-text-2 hover:bg-[rgba(108,92,231,0.06)] hover:text-text'}`}
      style={{ padding: '8px 10px', fontSize: 13 }}
    >
      {item.selected && (
        <span className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r-[2px]" style={{ background: 'var(--t-grad)' }} />
      )}
      <StatusDot status={status} />
      <span className="flex-1 truncate">{item.title}</span>
      {verdictText && <span className="text-[10px] uppercase tracking-[0.06em] text-text-3 font-medium">{verdictText}</span>}
    </button>
  )
}
```

- [ ] **Step 3: Implement Sidebar**

```tsx
// desktop/src/renderer/components/Sidebar.tsx
import { SidebarItem } from './SidebarItem'
import type { LibraryItem, RunGroup } from '../../types/library'

const SECTION: Record<RunGroup, string> = { active: 'Active', done: 'Done', archive: 'Archive' }
const ORDER: RunGroup[] = ['active', 'done', 'archive']

export function Sidebar({ items, onNewIdea, onSelect }:
  { items: LibraryItem[]; onNewIdea: () => void; onSelect: (id: string) => void }) {
  const grouped: Record<RunGroup, LibraryItem[]> = { active: [], done: [], archive: [] }
  for (const it of items) grouped[it.group].push(it)

  return (
    <div className="p-3">
      <button
        onClick={onNewIdea}
        className="w-full text-white border-0 rounded-xl text-[14px] font-medium tracking-[0.01em] mb-5"
        style={{ padding: '11px 14px', background: 'var(--t-grad)', boxShadow: 'var(--shadow-cta)' }}
      >+ New idea</button>

      {ORDER.map((g) => grouped[g].length > 0 && (
        <div key={g}>
          <div className="text-[10px] uppercase tracking-[0.10em] text-text-3 font-medium" style={{ padding: '10px 10px 6px' }}>
            {SECTION[g]}
          </div>
          {grouped[g].map((item) => (
            <SidebarItem key={item.id} item={item} onClick={() => onSelect(item.id)} />
          ))}
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Wire mock data into App**

```tsx
// desktop/src/renderer/App.tsx
import { useState } from 'react'
import { AppShell } from './components/AppShell'
import { Sidebar } from './components/Sidebar'
import type { LibraryItem } from '../types/library'

const MOCK: LibraryItem[] = [
  { id: '1', title: 'dog walking app',     group: 'active', etaMinutes: 12, selected: true },
  { id: '2', title: 'parent calendar',     group: 'done',   verdict: 'build' },
  { id: '3', title: 'github actions ai',   group: 'done',   verdict: 'unsure' },
  { id: '4', title: 'tofu pricing tracker',group: 'done',   verdict: 'skip' },
  { id: '5', title: 'remote pair stand-up',group: 'done',   verdict: 'build' },
  { id: '6', title: 'monorepo dashboard',  group: 'archive' }
]

export default function App() {
  const [items, setItems] = useState(MOCK)
  const onSelect = (id: string) => setItems((s) => s.map((x) => ({ ...x, selected: x.id === id })))

  return (
    <AppShell sidebar={<Sidebar items={items} onNewIdea={() => alert('new idea')} onSelect={onSelect} />}>
      <div className="flex-1 flex items-center justify-center text-text-2">main pane</div>
    </AppShell>
  )
}
```

- [ ] **Step 5: Verify visually + commit**

```bash
pnpm dev
git add desktop/src/renderer/components/Sidebar.tsx desktop/src/renderer/components/SidebarItem.tsx \
        desktop/src/types/library.ts desktop/src/renderer/App.tsx
git commit -m "feat(desktop): library sidebar with mock data"
```

---

## Task 8: Topbar component

**Files:**
- Create: `desktop/src/renderer/components/Topbar.tsx`
- Modify: `desktop/src/renderer/App.tsx`

- [ ] **Step 1: Implement Topbar**

```tsx
// desktop/src/renderer/components/Topbar.tsx
import { IconButton } from './IconButton'

interface TopbarProps {
  title: string
  meta?: string
  rightSlot?: React.ReactNode
  onStop?: () => void
  onWorkspace?: () => void
  onToggleDetails?: () => void
  detailsActive?: boolean
}

export function Topbar({ title, meta, rightSlot, onStop, onWorkspace, onToggleDetails, detailsActive }: TopbarProps) {
  return (
    <header className="flex items-start gap-4 border-b border-border" style={{ padding: '18px 32px 14px' }}>
      <div className="flex-1 min-w-0">
        <h1 className="m-0 text-[18px] font-bold text-text leading-tight tracking-[-0.01em]">{title}</h1>
        {meta && <div className="text-[12px] text-text-2 leading-relaxed mt-1">{meta}</div>}
      </div>
      {rightSlot}
      <div className="flex items-center gap-1.5">
        {onStop && <IconButton onClick={onStop} title="Stop">⏸</IconButton>}
        {onWorkspace && <IconButton onClick={onWorkspace} title="Open workspace">📂</IconButton>}
        {onToggleDetails && (
          <IconButton active={detailsActive} onClick={onToggleDetails} title="Details">⚙</IconButton>
        )}
      </div>
    </header>
  )
}
```

- [ ] **Step 2: Mount in App + commit**

```tsx
// desktop/src/renderer/App.tsx — wrap the main content
<AppShell sidebar={...}>
  <Topbar
    title="dog walking app"
    meta='"a dog walking app for owners and walkers in dense neighborhoods" · running · ~12 min remaining'
    onStop={() => {}} onWorkspace={() => {}} onToggleDetails={() => {}}
  />
  <div className="flex-1" />
</AppShell>
```

```bash
pnpm dev
git add desktop/src/renderer/components/Topbar.tsx desktop/src/renderer/App.tsx
git commit -m "feat(desktop): topbar with title, meta, action buttons"
```

---

## Task 9: Theme handling — system detection + persistence

**Files:**
- Create: `desktop/src/main/ipc-channels.ts`
- Create: `desktop/src/main/settings.ts`
- Create: `desktop/src/renderer/theme.ts`
- Create: `desktop/src/renderer/store/settings.ts`
- Create: `desktop/src/renderer/types-global.d.ts`
- Create: `desktop/tests/unit/theme.test.ts`
- Modify: `desktop/src/main/index.ts`
- Modify: `desktop/src/preload/index.ts`
- Modify: `desktop/src/renderer/main.tsx`

- [ ] **Step 1: Add IPC channel constants + settings storage**

```typescript
// desktop/src/main/ipc-channels.ts
export const IPC = {
  SETTINGS_GET: 'settings:get',
  SETTINGS_SET: 'settings:set',
  CLAUDE_DETECT: 'claude:detect',
  LIBRARY_LIST: 'library:list',
  RUN_START: 'run:start',
  RUN_CANCEL: 'run:cancel',
  RUN_EVENT: 'run:event',
  RUN_LOG: 'run:log'
} as const
```

```typescript
// desktop/src/main/settings.ts
import { app } from 'electron'
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'

export interface Settings {
  theme: 'auto' | 'light' | 'dark'
  claudePath?: string
}
const DEFAULTS: Settings = { theme: 'auto' }
const settingsPath = () => join(app.getPath('userData'), 'settings.json')

export function readSettings(): Settings {
  const p = settingsPath()
  if (!existsSync(p)) return { ...DEFAULTS }
  try { return { ...DEFAULTS, ...JSON.parse(readFileSync(p, 'utf-8')) } }
  catch { return { ...DEFAULTS } }
}

export function writeSettings(next: Partial<Settings>): Settings {
  const merged = { ...readSettings(), ...next }
  const p = settingsPath()
  mkdirSync(dirname(p), { recursive: true })
  writeFileSync(p, JSON.stringify(merged, null, 2))
  return merged
}
```

- [ ] **Step 2: Wire IPC handlers in main and preload**

Append to `desktop/src/main/index.ts`:

```typescript
import { ipcMain } from 'electron'
import { readSettings, writeSettings } from './settings'
import { IPC } from './ipc-channels'

ipcMain.handle(IPC.SETTINGS_GET, () => readSettings())
ipcMain.handle(IPC.SETTINGS_SET, (_evt, patch) => writeSettings(patch))
```

```typescript
// desktop/src/preload/index.ts
import { contextBridge, ipcRenderer } from 'electron'
import { IPC } from '../main/ipc-channels'

contextBridge.exposeInMainWorld('lem', {
  settings: {
    get: () => ipcRenderer.invoke(IPC.SETTINGS_GET),
    set: (patch: object) => ipcRenderer.invoke(IPC.SETTINGS_SET, patch)
  }
})
```

```typescript
// desktop/src/renderer/types-global.d.ts
import type { Settings } from '../main/settings'
declare global {
  interface Window {
    lem: {
      settings: {
        get: () => Promise<Settings>
        set: (patch: Partial<Settings>) => Promise<Settings>
      }
    }
  }
}
export {}
```

- [ ] **Step 3: Implement theme.ts and the settings store**

```typescript
// desktop/src/renderer/theme.ts
type Mode = 'light' | 'dark'
type Pref = 'auto' | Mode

function resolve(pref: Pref): Mode {
  if (pref !== 'auto') return pref
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function applyTheme(pref: Pref): Mode {
  const mode = resolve(pref)
  document.documentElement.setAttribute('data-theme', mode)
  return mode
}

export function watchSystemTheme(getPref: () => Pref, onChange: (m: Mode) => void) {
  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  const handler = () => { if (getPref() === 'auto') onChange(applyTheme('auto')) }
  mq.addEventListener('change', handler)
  return () => mq.removeEventListener('change', handler)
}
```

```typescript
// desktop/src/renderer/store/settings.ts
import { create } from 'zustand'

interface SettingsStore {
  theme: 'auto' | 'light' | 'dark'
  claudePath?: string
  setTheme: (t: 'auto' | 'light' | 'dark') => Promise<void>
  load: () => Promise<void>
}

export const useSettings = create<SettingsStore>((set) => ({
  theme: 'auto',
  setTheme: async (t) => { await window.lem.settings.set({ theme: t }); set({ theme: t }) },
  load:    async () => { const s = await window.lem.settings.get(); set({ theme: s.theme, claudePath: s.claudePath }) }
}))
```

- [ ] **Step 4: Bootstrap theme in main.tsx**

```tsx
// desktop/src/renderer/main.tsx
import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './globals.css'
import { applyTheme, watchSystemTheme } from './theme'
import { useSettings } from './store/settings'

function Bootstrap() {
  const { theme, load } = useSettings()
  useEffect(() => { load() }, [load])
  useEffect(() => { applyTheme(theme) }, [theme])
  useEffect(() => watchSystemTheme(() => useSettings.getState().theme, () => applyTheme(useSettings.getState().theme)), [])
  return <App />
}

createRoot(document.getElementById('root')!).render(<StrictMode><Bootstrap /></StrictMode>)
```

- [ ] **Step 5: Theme test**

```typescript
// desktop/tests/unit/theme.test.ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { applyTheme } from '@/theme'

describe('applyTheme', () => {
  beforeEach(() => document.documentElement.removeAttribute('data-theme'))
  it('sets data-theme=light', () => { applyTheme('light'); expect(document.documentElement.getAttribute('data-theme')).toBe('light') })
  it('sets data-theme=dark',  () => { applyTheme('dark');  expect(document.documentElement.getAttribute('data-theme')).toBe('dark')  })
  it('uses matchMedia for auto', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true, addEventListener: () => {}, removeEventListener: () => {} }))
    applyTheme('auto')
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
  })
})
```

- [ ] **Step 6: Verify + commit**

```bash
pnpm test
pnpm dev
git add desktop/src/main/{settings,ipc-channels,index}.ts desktop/src/preload/index.ts \
        desktop/src/renderer/{theme,main}.tsx desktop/src/renderer/store/settings.ts \
        desktop/src/renderer/types-global.d.ts desktop/tests/unit/theme.test.ts
git commit -m "feat(desktop): theme follow-OS with manual override + persistence"
```

---

## Task 10: Intake — input state

**Files:**
- Create: `desktop/src/renderer/screens/IntakeInput.tsx`
- Modify: `desktop/src/renderer/App.tsx`

- [ ] **Step 1: Implement IntakeInput**

```tsx
// desktop/src/renderer/screens/IntakeInput.tsx
import { useState } from 'react'
import { Chip } from '../components/Chip'
import { PrimaryButton } from '../components/PrimaryButton'

export function IntakeInput({ onSubmit }: { onSubmit: (idea: string, files: File[]) => void }) {
  const [idea, setIdea] = useState('')
  const [files, setFiles] = useState<File[]>([])

  const onPaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = Array.from(e.clipboardData.items).filter((it) => it.kind === 'file')
    if (items.length > 0) {
      e.preventDefault()
      const next = items.map((it) => it.getAsFile()).filter((f): f is File => !!f)
      setFiles((s) => [...s, ...next])
    }
  }

  const pickFile = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.multiple = true
    input.accept = 'image/*,.md,.txt,.pdf'
    input.onchange = () => { if (input.files) setFiles((s) => [...s, ...Array.from(input.files!)]) }
    input.click()
  }

  return (
    <div className="flex-1 flex items-center justify-center px-14 py-10 overflow-y-auto">
      <div className="w-full max-w-[640px]">
        <div className="text-[11px] font-bold tracking-[0.12em] uppercase text-purple mb-3">New idea</div>
        <h1 className="text-[36px] font-bold tracking-[-0.02em] leading-[1.15] text-text mb-3">
          What's the{' '}
          <span className="bg-clip-text text-transparent" style={{ backgroundImage: 'var(--t-grad)' }}>idea</span>?
        </h1>
        <p className="text-[16px] leading-relaxed text-text-2 mb-7 max-w-[560px]">
          One line is fine. Lem will ask a couple of clarifying questions, then three specialists weigh in.
          About 15 minutes start to finish.
        </p>

        <div className="text-[12px] font-medium text-text-2 mb-2">In one line</div>
        <textarea
          value={idea}
          onChange={(e) => setIdea(e.target.value)}
          onPaste={onPaste}
          rows={3}
          placeholder="e.g. a calendar app that parents and their kids actually share"
          className="w-full text-[16px] text-text bg-bg resize-y min-h-[80px] outline-none"
          style={{ border: '1.5px solid var(--color-border)', borderRadius: 14, padding: '14px 16px', fontFamily: 'inherit' }}
          onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-purple)'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(108, 92, 231, 0.15)' }}
          onBlur={(e)  => { e.currentTarget.style.borderColor = 'var(--color-border)'; e.currentTarget.style.boxShadow = 'none' }}
        />

        <div className="mt-4 px-4 py-3.5"
             style={{ background: 'var(--color-surface)', border: '1px dashed var(--color-border)', borderRadius: 14 }}>
          <div className="text-[12px] font-medium text-text-2 mb-1.5">
            Anything else lem should know? <span className="text-text-3 font-normal">(optional)</span>
          </div>
          <div className="text-[13px] text-text-3 mb-2.5">
            Drop links, screenshots, anything that gives more context. URLs work in the field above too.
          </div>
          <div className="flex gap-2 flex-wrap">
            <Chip onClick={pickFile}>📎 Attach</Chip>
            {files.map((f, i) => <Chip key={i} tone="purple">{f.name}</Chip>)}
          </div>
        </div>

        <div className="mt-8 flex items-center justify-between gap-4">
          <div className="text-[12px] text-text-3">
            Profile: <span className="text-text-2 font-medium">app-idea</span> · Depth: <span className="text-text-2 font-medium">normal</span> · ~$0 (Max)
          </div>
          <PrimaryButton disabled={!idea.trim()} onClick={() => onSubmit(idea, files)}>
            Refine my idea →
          </PrimaryButton>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Wire into App with a screen state**

```tsx
// desktop/src/renderer/App.tsx
import { useState } from 'react'
import { AppShell } from './components/AppShell'
import { Sidebar } from './components/Sidebar'
import { IntakeInput } from './screens/IntakeInput'
import type { LibraryItem } from '../types/library'

const MOCK: LibraryItem[] = [/* same as Task 7 */]
type Screen = { kind: 'intake-input' } | { kind: 'placeholder' }

export default function App() {
  const [items] = useState(MOCK)
  const [screen, setScreen] = useState<Screen>({ kind: 'intake-input' })

  return (
    <AppShell sidebar={<Sidebar items={items} onNewIdea={() => setScreen({ kind: 'intake-input' })} onSelect={() => {}} />}>
      {screen.kind === 'intake-input' && <IntakeInput onSubmit={(idea) => console.log('submit', idea)} />}
      {screen.kind === 'placeholder' && <div className="flex-1 flex items-center justify-center text-text-2">placeholder</div>}
    </AppShell>
  )
}
```

- [ ] **Step 3: Verify + commit**

```bash
pnpm dev
git add desktop/src/renderer/screens/IntakeInput.tsx desktop/src/renderer/App.tsx
git commit -m "feat(desktop): intake input screen"
```

Expected: gradient "idea" word, textarea, dashed extras box with `📎 Attach`. Pasting an image creates a purple chip. CTA disabled until you type.

---

## Task 11: Intake — clarifying-questions chat

**Files:**
- Create: `desktop/src/types/chat.ts`
- Create: `desktop/src/renderer/screens/IntakeChat.tsx`
- Modify: `desktop/src/renderer/App.tsx`

- [ ] **Step 1: Define ChatMessage + implement IntakeChat**

```typescript
// desktop/src/types/chat.ts
export interface ChatMessage {
  role: 'user' | 'lem'
  content: string
  meta?: string
}
```

```tsx
// desktop/src/renderer/screens/IntakeChat.tsx
import { useState } from 'react'
import type { ChatMessage } from '../../types/chat'

export function IntakeChat({ ideaTitle, messages, questionIndex, onSend }: {
  ideaTitle: string; messages: ChatMessage[]; questionIndex: number; onSend: (text: string) => void
}) {
  const [text, setText] = useState('')
  const submit = () => { if (text.trim()) { onSend(text); setText('') } }

  return (
    <div className="flex-1 flex flex-col px-14 py-8 overflow-y-auto">
      <div className="text-[11px] font-bold tracking-[0.12em] uppercase text-text-3 mb-2">Setup · {ideaTitle}</div>
      <h2 className="m-0 mb-6 text-[22px] font-bold text-text tracking-[-0.01em]">A couple of questions before we dive in</h2>

      <div className="flex-1 flex flex-col gap-4 max-w-[720px]">
        {messages.map((m, i) => <Bubble key={i} msg={m} />)}
      </div>

      <div className="mt-5 max-w-[720px]">
        <textarea
          rows={2} value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit() }}
          placeholder="Type your answer…"
          className="w-full text-[15px] text-text bg-bg outline-none"
          style={{ border: '1.5px solid var(--color-border)', borderRadius: 14, padding: '14px 16px', fontFamily: 'inherit' }}
        />
        <div className="mt-3 flex items-center justify-between text-[12px] text-text-3">
          <div className="flex items-center gap-2">
            <span>Setup progress</span>
            <span className="inline-flex gap-1.5">
              {[0, 1, 2].map((i) => (
                <span key={i} className="w-1.5 h-1.5 rounded-full" style={{
                  background: i < questionIndex ? 'var(--color-purple)' : i === questionIndex ? 'var(--t-grad)' : 'var(--color-border)'
                }} />
              ))}
            </span>
          </div>
          <span className="text-text-3">⌘↵ to send</span>
        </div>
      </div>
    </div>
  )
}

function Bubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user'
  return (
    <div className="flex gap-3">
      {!isUser && (
        <div className="w-8 h-8 rounded-[10px] flex items-center justify-center text-[14px] shrink-0"
             style={{ background: 'rgba(108,92,231,0.12)', color: 'var(--color-purple)' }}>⌘</div>
      )}
      <div className={isUser ? 'ml-auto' : ''}>
        <div className="px-4 py-3 text-[14.5px] leading-relaxed text-text max-w-[560px]"
             style={{
               border: `1px solid ${isUser ? 'rgba(108,92,231,0.15)' : 'var(--color-border)'}`,
               background: isUser ? 'rgba(108,92,231,0.06)' : 'var(--color-surface)',
               borderRadius: 14
             }}>{msg.content}</div>
        {msg.meta && <div className="text-[11px] text-text-3 mt-1">{msg.meta}</div>}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-[10px] flex items-center justify-center text-[14px] text-white shrink-0"
             style={{ background: 'var(--t-grad)' }}>YM</div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Wire transition in App**

```tsx
// desktop/src/renderer/App.tsx — extend Screen union
import { IntakeChat } from './screens/IntakeChat'
import type { ChatMessage } from '../types/chat'

type Screen =
  | { kind: 'intake-input' }
  | { kind: 'intake-chat'; idea: string; messages: ChatMessage[]; q: number }

// In IntakeInput's onSubmit:
onSubmit={(idea) => setScreen({
  kind: 'intake-chat',
  idea,
  q: 0,
  messages: [
    { role: 'user', content: idea, meta: 'your idea' },
    { role: 'lem',
      content: 'Got it. Two things will sharpen this. Who are we optimizing for first?',
      meta: 'lem · question 1 of ≤3' }
  ]
})}

// In the JSX:
{screen.kind === 'intake-chat' && (
  <IntakeChat
    ideaTitle={screen.idea}
    messages={screen.messages}
    questionIndex={screen.q}
    onSend={(text) => setScreen({
      ...screen,
      q: screen.q + 1,
      messages: [...screen.messages, { role: 'user', content: text }]
    })}
  />
)}
```

- [ ] **Step 3: Verify + commit**

```bash
pnpm dev
git add desktop/src/types/chat.ts desktop/src/renderer/screens/IntakeChat.tsx desktop/src/renderer/App.tsx
git commit -m "feat(desktop): intake clarifying-questions chat screen"
```

Expected: typing an idea + clicking Refine transitions the main pane to the chat view. User idea on the right (gradient avatar), lem question on the left (purple avatar). Setup-progress dots at bottom.

---

🏁 **Milestone B complete** — full static UI, no backend integration.

---

## Task 12: SQLite library db + IPC

**Files:**
- Create: `desktop/src/main/library-db.ts`
- Create: `desktop/tests/unit/library-db.test.ts`
- Modify: `desktop/src/main/index.ts`
- Modify: `desktop/src/preload/index.ts`
- Modify: `desktop/src/renderer/types-global.d.ts`

- [ ] **Step 1: Write the failing db test**

```typescript
// desktop/tests/unit/library-db.test.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { LibraryDB } from '../../src/main/library-db'

let dir: string
beforeEach(() => { dir = mkdtempSync(join(tmpdir(), 'lem-lib-')) })

describe('LibraryDB', () => {
  it('upserts a run and lists it', () => {
    const db = new LibraryDB(join(dir, 'lib.db'))
    db.upsert({ id: 'r1', title: 'dog walking', status: 'running', workspacePath: '/tmp/r1', createdAt: 1000 })
    const items = db.list()
    expect(items.length).toBe(1)
    expect(items[0].title).toBe('dog walking')
    db.close()
    rmSync(dir, { recursive: true })
  })

  it('groups items: active vs done vs archive', () => {
    const db = new LibraryDB(join(dir, 'lib.db'))
    db.upsert({ id: 'r1', title: 'a', status: 'running',   workspacePath: '/a', createdAt: 1 })
    db.upsert({ id: 'r2', title: 'b', status: 'completed', verdict: 'build', workspacePath: '/b', createdAt: 2 })
    db.upsert({ id: 'r3', title: 'c', status: 'archived',  workspacePath: '/c', createdAt: 3 })
    const items = db.list()
    const groups = items.map((x) => x.group)
    expect(groups).toContain('active')
    expect(groups).toContain('done')
    expect(groups).toContain('archive')
    db.close()
    rmSync(dir, { recursive: true })
  })
})
```

- [ ] **Step 2: Implement LibraryDB**

```typescript
// desktop/src/main/library-db.ts
import Database from 'better-sqlite3'

export type RunStatus = 'running' | 'completed' | 'failed' | 'archived'
export type Verdict = 'build' | 'skip' | 'unsure'

export interface RunRow {
  id: string; title: string; status: RunStatus; verdict?: Verdict
  workspacePath: string; createdAt: number; finishedAt?: number; costNotional?: number
}

// LibraryItem lives in src/types/library.ts (defined in Task 7).
// Re-import here so list() returns the same type the renderer uses.
import type { LibraryItem } from '../types/library'
export type { LibraryItem }

export class LibraryDB {
  private db: Database.Database
  constructor(path: string) {
    this.db = new Database(path)
    this.db.pragma('journal_mode = WAL')
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL,
        verdict TEXT, workspace_path TEXT NOT NULL,
        created_at INTEGER NOT NULL, finished_at INTEGER, cost_notional REAL
      );
      CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);
    `)
  }
  upsert(row: RunRow): void {
    this.db.prepare(`
      INSERT INTO runs (id, title, status, verdict, workspace_path, created_at, finished_at, cost_notional)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        title=excluded.title, status=excluded.status, verdict=excluded.verdict,
        workspace_path=excluded.workspace_path, finished_at=excluded.finished_at,
        cost_notional=excluded.cost_notional
    `).run(row.id, row.title, row.status, row.verdict ?? null, row.workspacePath,
           row.createdAt, row.finishedAt ?? null, row.costNotional ?? null)
  }
  list(): LibraryItem[] {
    const rows = this.db.prepare(`SELECT * FROM runs ORDER BY created_at DESC`).all() as Array<{
      id: string; title: string; status: RunStatus; verdict: Verdict | null; created_at: number
    }>
    return rows.map((r) => ({
      id: r.id, title: r.title,
      group: r.status === 'running' ? 'active' : r.status === 'archived' ? 'archive' : 'done',
      verdict: r.verdict ?? undefined
    }))
  }
  close(): void { this.db.close() }
}
```

- [ ] **Step 3: Wire IPC + extend preload**

Append to `desktop/src/main/index.ts`:

```typescript
import { LibraryDB } from './library-db'
import { join as pjoin } from 'node:path'

const libraryDb = new LibraryDB(pjoin(app.getPath('userData'), 'library.db'))
ipcMain.handle(IPC.LIBRARY_LIST, () => libraryDb.list())
app.on('before-quit', () => libraryDb.close())
```

Extend `desktop/src/preload/index.ts`:

```typescript
contextBridge.exposeInMainWorld('lem', {
  settings: { /* existing */ },
  library:  { list: () => ipcRenderer.invoke(IPC.LIBRARY_LIST) }
})
```

Extend `desktop/src/renderer/types-global.d.ts`:

```typescript
import type { LibraryItem } from '../main/library-db'
declare global {
  interface Window {
    lem: {
      settings: { get: () => Promise<Settings>; set: (p: Partial<Settings>) => Promise<Settings> }
      library:  { list: () => Promise<LibraryItem[]> }
    }
  }
}
```

- [ ] **Step 4: Run tests + commit**

```bash
pnpm test
git add desktop/src/main/library-db.ts desktop/tests/unit/library-db.test.ts \
        desktop/src/main/index.ts desktop/src/preload/index.ts desktop/src/renderer/types-global.d.ts
git commit -m "feat(desktop): sqlite library db + ipc"
```

---

## Task 13: Wire Sidebar to live library data

**Files:**
- Create: `desktop/src/renderer/store/library.ts`
- Modify: `desktop/src/renderer/App.tsx`

- [ ] **Step 1: Implement the library store**

```typescript
// desktop/src/renderer/store/library.ts
import { create } from 'zustand'
import type { LibraryItem } from '../../main/library-db'

interface LibraryStore {
  items: LibraryItem[]
  selectedId?: string
  load: () => Promise<void>
  select: (id: string) => void
}

export const useLibrary = create<LibraryStore>((set) => ({
  items: [],
  load: async () => {
    const items = await window.lem.library.list()
    set({ items })
  },
  select: (id) => set({ selectedId: id })
}))
```

- [ ] **Step 2: Use the store in App**

```tsx
// desktop/src/renderer/App.tsx — replace the mock-data version
import { useEffect } from 'react'
import { AppShell } from './components/AppShell'
import { Sidebar } from './components/Sidebar'
import { IntakeInput } from './screens/IntakeInput'
import { IntakeChat } from './screens/IntakeChat'
import { useLibrary } from './store/library'

export default function App() {
  const { items, selectedId, load, select } = useLibrary()
  useEffect(() => { load() }, [load])

  const decorated = items.map((it) => ({ ...it, selected: it.id === selectedId }))

  return (
    <AppShell sidebar={<Sidebar items={decorated} onNewIdea={() => {}} onSelect={select} />}>
      <IntakeInput onSubmit={() => {}} />
    </AppShell>
  )
}
```

- [ ] **Step 3: Verify + commit**

```bash
pnpm dev
git add desktop/src/renderer/store/library.ts desktop/src/renderer/App.tsx
git commit -m "feat(desktop): wire sidebar to live library data"
```

Expected: sidebar starts empty (db has no runs yet). The next tasks will populate it.

---

## Task 14: Detect the local `claude` binary + first-run wizard

**Files:**
- Create: `desktop/src/main/claude-detect.ts`
- Create: `desktop/tests/unit/claude-detect.test.ts`
- Create: `desktop/src/renderer/components/FirstRunWizard.tsx`
- Modify: `desktop/src/main/index.ts`
- Modify: `desktop/src/preload/index.ts`
- Modify: `desktop/src/renderer/types-global.d.ts`
- Modify: `desktop/src/renderer/App.tsx`

- [ ] **Step 1: Write the failing detection test**

```typescript
// desktop/tests/unit/claude-detect.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mkdirSync, mkdtempSync, writeFileSync, rmSync, chmodSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { detectClaude } from '../../src/main/claude-detect'

let dir: string
beforeEach(() => { dir = mkdtempSync(join(tmpdir(), 'lem-claude-')) })

describe('detectClaude', () => {
  it('returns null when nothing is found', async () => {
    const result = await detectClaude({ candidatePaths: [join(dir, 'nope')] })
    expect(result).toBeNull()
    rmSync(dir, { recursive: true })
  })

  it('returns the path when an LEM_CLAUDE_BIN env override exists', async () => {
    const fake = join(dir, 'fake-claude')
    writeFileSync(fake, '#!/bin/sh\necho 1.2.3\n')
    chmodSync(fake, 0o755)
    vi.stubEnv('LEM_CLAUDE_BIN', fake)
    const result = await detectClaude()
    expect(result).toBe(fake)
    vi.unstubAllEnvs()
    rmSync(dir, { recursive: true })
  })
})
```

- [ ] **Step 2: Implement detectClaude**

```typescript
// desktop/src/main/claude-detect.ts
import { existsSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

const STANDARD_PATHS = [
  '/opt/homebrew/bin/claude',
  '/usr/local/bin/claude',
  join(homedir(), '.local/bin/claude'),
  join(homedir(), '.claude/local/claude')
]

export async function detectClaude(opts?: { candidatePaths?: string[] }): Promise<string | null> {
  const env = process.env.LEM_CLAUDE_BIN
  if (env && existsSync(env)) return env

  const paths = opts?.candidatePaths ?? STANDARD_PATHS
  for (const p of paths) if (existsSync(p)) return p
  return null
}
```

- [ ] **Step 3: Wire IPC + preload + renderer types**

```typescript
// desktop/src/main/index.ts — append
import { detectClaude } from './claude-detect'
ipcMain.handle(IPC.CLAUDE_DETECT, () => detectClaude())
```

```typescript
// desktop/src/preload/index.ts — extend
claude: { detect: () => ipcRenderer.invoke(IPC.CLAUDE_DETECT) }
```

```typescript
// desktop/src/renderer/types-global.d.ts — extend
claude: { detect: () => Promise<string | null> }
```

- [ ] **Step 4: Implement FirstRunWizard**

```tsx
// desktop/src/renderer/components/FirstRunWizard.tsx
import { PrimaryButton } from './PrimaryButton'
import { BrandMark } from './BrandMark'

interface Props {
  onRetry: () => void
  onPickPath: () => void
}

export function FirstRunWizard({ onRetry, onPickPath }: Props) {
  return (
    <div className="flex-1 flex items-center justify-center p-12">
      <div className="max-w-[520px] w-full text-center">
        <div className="inline-flex items-center justify-center mb-7"><BrandMark size={42} /></div>
        <h1 className="text-[28px] font-bold tracking-[-0.02em] mb-3 text-text">lem needs Claude Code</h1>
        <p className="text-[15px] text-text-2 leading-relaxed mb-8">
          lem uses your local <strong>Claude Code</strong> installation to run AI agents.
          We couldn't find it on your machine.
        </p>
        <PrimaryButton onClick={() => window.open('https://claude.com/claude-code', '_blank')}>
          Install Claude Code
        </PrimaryButton>
        <div className="mt-6 flex items-center justify-center gap-6 text-[13px]">
          <button onClick={onRetry} className="text-purple font-medium hover:underline">
            I've installed it — retry
          </button>
          <button onClick={onPickPath} className="text-text-3 hover:text-text-2">
            Set custom path…
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Show the wizard when claude is missing**

```tsx
// desktop/src/renderer/App.tsx
import { useEffect, useState } from 'react'
import { FirstRunWizard } from './components/FirstRunWizard'

export default function App() {
  const { items, selectedId, load, select } = useLibrary()
  const [claudePath, setClaudePath] = useState<string | null | undefined>(undefined)

  useEffect(() => { load() }, [load])
  useEffect(() => { window.lem.claude.detect().then(setClaudePath) }, [])

  if (claudePath === undefined) return null  // splash; minimal
  if (claudePath === null) {
    return <FirstRunWizard onRetry={() => window.lem.claude.detect().then(setClaudePath)} onPickPath={() => {}} />
  }

  const decorated = items.map((it) => ({ ...it, selected: it.id === selectedId }))
  return (
    <AppShell sidebar={<Sidebar items={decorated} onNewIdea={() => {}} onSelect={select} />}>
      <IntakeInput onSubmit={() => {}} />
    </AppShell>
  )
}
```

- [ ] **Step 6: Run tests + verify + commit**

```bash
pnpm test
pnpm dev
git add desktop/src/main/claude-detect.ts desktop/tests/unit/claude-detect.test.ts \
        desktop/src/renderer/components/FirstRunWizard.tsx \
        desktop/src/main/index.ts desktop/src/preload/index.ts desktop/src/renderer/types-global.d.ts \
        desktop/src/renderer/App.tsx
git commit -m "feat(desktop): claude binary detection + first-run wizard"
```

Expected: if `claude` is on your PATH, the app proceeds to the regular UI; if you `unset PATH` and rerun, the wizard appears with the install CTA + "I've installed it" retry.

---

> **Plan format note for the rest of the tasks:** Tasks 1–14 inlined the
> full code for setup, design tokens, IPC contracts, and the static UI —
> things where exact identifiers and file shapes matter for everything
> that follows. From Task 15 onward the plan is leaner: each task lists
> files, references the [design system](../../electron-design-system.md)
> and [UI spec](../specs/2026-05-08-lem-electron-ui-design.md), and trusts
> the developer agent to produce the implementation. Acceptance criteria
> + tests are spelled out so the work is verifiable.

---

## Task 15: Orchestrator bridge — spawn `lem refine`, stream events

**Goal:** Main-process module that starts a `lem refine` run, captures
`ProgressEvent`s, tails `meta/log.jsonl`, and forwards both streams to
the renderer over IPC. Stubbable so the rest of the app can be tested
without a real `lem` install.

**Files:**
- Create: `desktop/src/main/orchestrator-bridge.ts`
- Create: `desktop/src/types/lem-events.ts` — TypeScript shapes mirroring
  `ProgressEvent` from `src/lem/orchestrator.py` (kind, phase_id, roles,
  duration_s, cost_usd, success) and the JSONL log entry shape
- Create: `desktop/tests/unit/orchestrator-bridge.test.ts`
- Modify: `desktop/src/main/index.ts`, `desktop/src/preload/index.ts`,
  `desktop/src/renderer/types-global.d.ts`

**Sub-tasks:**

- [ ] **Step 1:** Define `ProgressEvent` and `LogLine` types in
  `src/types/lem-events.ts`. Mirror the Python `NamedTuple` fields exactly
  so JSON parsing is one-to-one.
- [ ] **Step 2:** Implement `OrchestratorBridge` class with methods
  `start(idea, options) → runId`, `cancel(runId)`, and an `EventEmitter`
  surface (`on('event', cb)`, `on('log', cb)`, `on('exit', cb)`).
  Spawn the `lem` binary using `spawn` from `node:child_process` (NOT
  `exec` — pass argv as an array, no shell).
- [ ] **Step 3:** Pipe stdout line-by-line. The new `--verbose` mode
  emits human lines; we want machine events. Two options for the
  developer agent — pick the one with the smaller blast radius:
  - **(a)** Add a new `--events-fd` flag to lem's `refine` command that
    writes JSON-Lines to a numbered file descriptor (3). Cleanest.
  - **(b)** Tail `meta/log.jsonl` from the workspace path (existing
    contract; lem already writes events there).
  Recommend (b) for v1 — zero changes to the Python side.
- [ ] **Step 4:** Implement `tailJsonl(path, onLine)` that opens the file,
  watches with `fs.watch`, parses new lines as JSON, and emits each
  through `onLine`. Handle file-not-yet-created (poll until it appears,
  then watch). Handle line truncation (buffer partial lines until `\n`).
- [ ] **Step 5:** Wire IPC. `IPC.RUN_START` → starts the bridge,
  registers a per-window `webContents.send(IPC.RUN_EVENT, ...)` listener.
  `IPC.RUN_CANCEL` → SIGTERM the child. `IPC.RUN_EVENT` and `IPC.RUN_LOG`
  are renderer subscriptions.
- [ ] **Step 6:** Stub mode. If `LEM_DESKTOP_STUB_RUN=1` is set, the
  bridge replays a canned sequence of phase_start/phase_done events
  from `tests/fixtures/stub-events.jsonl` (create this file with ~30
  lines covering all 9 phases). Used by Task 20's e2e.
- [ ] **Step 7:** Tests. Use Vitest + a fake `spawn` that returns a
  controllable readable stream. Verify: events parse correctly; partial
  lines are buffered; cancel sends SIGTERM; stub mode emits the canned
  sequence in order.
- [ ] **Step 8:** Commit `feat(desktop): orchestrator bridge + ipc`.

**Acceptance:** From the renderer dev console, calling
`window.lem.run.start({ idea: 'test', stub: true })` produces a stream
of `RUN_EVENT` messages on the window, and a final `phase_done` for
phase 4.

---

## Task 16: Theater shell + AgentCard

**Goal:** The running view from the spec §4.2. Wires up the
`StepRail` (Task 6) + a grid of `AgentCard` for the current phase +
the `EarlierSteps` collapsible list below.

**Files:**
- Create: `desktop/src/renderer/screens/Theater.tsx`
- Create: `desktop/src/renderer/screens/AgentCard.tsx`
- Create: `desktop/src/renderer/screens/EarlierSteps.tsx`
- Create: `desktop/src/renderer/lib/phases.ts` — phase-id → user-facing
  label map (mirror `_USER_PHASE_LABELS` in `src/lem/commands/refine.py`)
- Create: `desktop/src/renderer/lib/roles.ts` — role-name → icon + tone
  (architect=purple/🏗, designer=teal/🎨, market=neutral/📈, etc.)

**Sub-tasks:**
- [ ] Build `AgentCard` per spec §4.2: head (icon + name + status), body
  (~200px min-height, 14px text), foot ("Show full output →" placeholder).
  States: `thinking` (animated dots), `streaming` (caret — unused in v1),
  `done` (full text rendered).
- [ ] Build `EarlierSteps` — list of one-line summaries with ✓ glyph,
  phase label, money-quote, duration. Click a row to expand inline
  (re-show the cards from that phase).
- [ ] Build `Theater` — composes Topbar, StepRail, current-phase cards,
  EarlierSteps. Takes a `RunSnapshot` prop with phases + their states.
- [ ] **Branching layout (phases 2.1–2.3) is out of scope for Phase 1.**
  Render branching phases with the standard one-card-per-role layout
  for now. The fork visualization comes in the Phase 2 plan.
- [ ] Storybook-equivalent: a `dev/theater-preview.tsx` route that
  renders Theater with a hard-coded RunSnapshot covering all 9 phases
  in their 3 states (queued / active / done). Useful for visual
  regression while iterating.
- [ ] Tests: AgentCard renders the right icon per role; EarlierSteps
  collapses/expands; Theater renders 9 step segments at the right state
  given an active-phase prop.
- [ ] Commit `feat(desktop): theater shell + agent card`.

**Acceptance:** Visiting `/dev/theater-preview` renders three populated
cards for phase 4 + collapsed earlier-step rows for phases 0–3 + grey
queued-step segments for 5–9.

---

## Task 17: Wire Theater to the live event stream

**Goal:** Connect the orchestrator bridge (Task 15) to the Theater
component (Task 16) so the user sees the run progress in real time.

**Files:**
- Create: `desktop/src/renderer/store/runtime.ts` — zustand store keyed
  by `runId`: phases array, current-phase index, ETA, total cost.
- Modify: `desktop/src/renderer/App.tsx` — listen to `RUN_EVENT` /
  `RUN_LOG` and push into the runtime store.
- Modify: `desktop/src/renderer/screens/Theater.tsx` — read from runtime
  store instead of props (or take store as prop for testability).

**Sub-tasks:**
- [ ] Runtime store reducer: `phase_start` → mark phase active and seed
  `roles` from event; `phase_done` → mark done, capture duration_s and
  cost_usd, update total cost; `phase_skipped` → mark queued→done with
  zero duration.
- [ ] `RUN_LOG` events update per-role outputs as they finish (since
  v1 uses the reveal pattern, not streaming, each role's body fills in
  when its log entry arrives with `phase_done` for that role).
- [ ] ETA estimation: keep a rolling sum of completed-phase durations,
  divide by completed-phase count, multiply by remaining-phase count.
  Show in topbar.
- [ ] When the final `phase_done` for phase 4 (synthesize) arrives,
  transition the workspace to the Brief screen (Task 18) for that run.
- [ ] When a `phase_done` arrives with `success=false` AND the
  orchestrator process exits, transition to the failure variant of the
  Brief screen (deferred to Phase 2 plan; v1 just shows the error).
- [ ] Tests: feed the stub-events fixture into the store and assert the
  current-phase index advances, total cost accumulates, and the final
  state is "completed".
- [ ] Commit `feat(desktop): wire theater to live event stream`.

**Acceptance:** Running with `LEM_DESKTOP_STUB_RUN=1` from the new-idea
flow walks through all 9 phases visually in ~30 seconds.

---

## Task 18: Brief view — tabs, callout, markdown rendering

**Goal:** Spec §4.3. The done view with verdict pill, three deliverable
tabs, and the structured document.

**Files:**
- Create: `desktop/src/renderer/screens/Brief.tsx`
- Create: `desktop/src/renderer/components/Callout.tsx`
- Create: `desktop/src/renderer/lib/markdown.tsx` — render lem markdown
  using `react-markdown` + `remark-gfm`; map H1/H2/H3, bullets, blockquote
  to the design-system styles
- Modify: `desktop/package.json` — add `react-markdown`, `remark-gfm`

**Sub-tasks:**
- [ ] Add `react-markdown` and `remark-gfm` deps. Configure custom
  `components` map: H1 with optional `.accent` gradient on the last
  word; bullets with the gradient-circle pseudo-element marker;
  blockquotes with teal left-border + 5% teal bg; H2/H3 per typography
  table.
- [ ] `Callout`: takes `[{ label, value, tone? }]` rows — renders the
  3-stat grid per spec §4.3 (Recommendation / Confidence / First
  milestone). Tones: `purple`, `teal`, `default`.
- [ ] `Brief`: receives a `RunSnapshot` with `verdict`, `confidence`,
  `deliverables: { id, title, body: string }[]`. Renders Topbar
  (verdict pill via Task 6 component), tab strip, then the active
  deliverable's markdown.
- [ ] **PDF export is out of scope for Phase 1.** Render the `⤓ PDF`
  button as a no-op tooltip "Coming soon".
- [ ] **Share is out of scope.** Same treatment.
- [ ] `Refine again` button creates a fresh run with the same idea text
  + a "(refined again)" suffix to the title. Routes through Task 11's
  intake-input but pre-filled.
- [ ] Tests: Brief renders the right tab content when the active tab
  changes; verdict pill shows the right glyph; the H1 last-word
  gradient class is applied iff content includes ` — ` separator.
- [ ] Commit `feat(desktop): brief view`.

**Acceptance:** Given a sample workspace with non-empty deliverables,
Brief renders all three tabs, the callout, the verdict pill in the
topbar, and switching tabs updates the body.

---

## Task 19: Wire Brief to deliverable files in the workspace

**Goal:** Read `executive-summary.md`, `mvp-plan.md`, `risks-and-rejected-paths.md`
and the `meta/synthesis.md` frontmatter from the workspace directory
of the selected run.

**Files:**
- Create: `desktop/src/main/workspace-reader.ts`
- Create: `desktop/tests/unit/workspace-reader.test.ts`
- Modify: `desktop/src/main/index.ts`, `desktop/src/preload/index.ts`,
  `desktop/src/renderer/types-global.d.ts`, `desktop/src/renderer/screens/Brief.tsx`

**Sub-tasks:**
- [ ] `WorkspaceReader.readBrief(workspacePath) → BriefData`. Returns:
  - `verdict` and `confidence` from `meta/synthesis.md` frontmatter
  - the three deliverable bodies from `deliverables/*.md`
  - run timing (`meta/timeline.jsonl` last entry → wall-clock total)
- [ ] Use a YAML parser (`yaml` from npm) to read the synthesis
  frontmatter. Tolerate missing keys — surface them as `null` so the
  Brief view can fall back gracefully.
- [ ] If a deliverable file is missing, return an empty body — Brief
  shows a "Not yet written" placeholder for that tab.
- [ ] IPC channel `workspace:read-brief`. Renderer calls
  `window.lem.workspace.readBrief(workspacePath)`.
- [ ] Tests: a fixture workspace under `tests/fixtures/sample-workspace/`
  with the three deliverable files + a synthesis.md; assert
  `readBrief()` returns the right shape.
- [ ] Update `Brief` screen to fetch via `useEffect` on mount and on
  `selectedId` change.
- [ ] Commit `feat(desktop): read deliverables from workspace`.

**Acceptance:** Selecting a completed run from the sidebar shows its
real deliverables, not stubbed text.

---

## Task 20: End-to-end Playwright test — full run with stubbed orchestrator

**Goal:** A single Playwright test that drives the app from launch
through a stubbed run to the Brief view, asserting the visual states
along the way. This is the integration test that catches regressions
across the renderer + IPC + main-process boundaries.

**Files:**
- Create: `desktop/playwright.config.ts`
- Create: `desktop/tests/e2e/full-run.spec.ts`
- Create: `desktop/tests/fixtures/stub-events.jsonl` (referenced by Task 15)
- Create: `desktop/tests/fixtures/sample-workspace/` (referenced by Task 19)

**Sub-tasks:**
- [ ] Configure Playwright for Electron (`electron.launch({ args: ['out/main/index.js'] })`).
  Build first: `pnpm build && pnpm test:e2e`.
- [ ] Test scenario:
  - Set `LEM_DESKTOP_STUB_RUN=1` in the launched-app env so the
    orchestrator bridge replays the fixture events.
  - Click `+ New idea`.
  - Type "a calendar app for parents and kids".
  - Click `Refine my idea →`.
  - Skip the chat (answer each clarifying question with a one-word
    answer; the stub doesn't care).
  - Wait for the Theater to show step 4 active. Assert: title ===
    "a calendar app for parents and kids", step rail has 3 done +
    1 active + 5 queued segments.
  - Wait until all 9 phases are done (~30s with the stub).
  - Assert: workspace transitions to Brief; verdict pill shows
    `✓ Build` (the fixture has a build verdict); switching tabs
    works; markdown renders.
- [ ] Add `pnpm test:e2e` to CI (GitHub Actions or whatever the lem repo
  is using; defer to existing `.github/workflows/` if present).
- [ ] Commit `test(desktop): playwright e2e for the full happy path`.

**Acceptance:** `pnpm test:e2e` passes locally and produces a screenshot
artifact for each step (intake → chat → theater → brief).

---

🏁 **Milestone C complete** — alpha is feature-complete on a developer's
machine with `lem` available on PATH.

---

## What ships at the end of this plan

A developer can:
1. `pnpm dev` from `desktop/` and see the alpha app launch
2. Click `+ New idea`, type an idea, answer clarifying questions
3. Watch the run progress through 9 phases in the theater view
4. Read the brief at the end across three tabs
5. See past runs in the sidebar
6. Toggle between light and dark via OS appearance setting

A non-technical end-user **cannot yet** install and use this. That
requires Phase 2 (Python bundling, code-signing, packaging, auto-update),
which is a separate plan.

## What's deliberately not in this plan (Phase 2 follow-up)

- PyOxidizer / PyInstaller bundling of the Python sidecar
- macOS code-signing + notarization
- Windows / Linux packaging
- Auto-update via Squirrel.Mac
- Branching-phase fork visualization (spec §4.2 branching layout)
- Details slide-over (spec §4.4)
- Failure-UX polish (spec §4.6) — currently shows a basic error message
- PDF export
- Settings screen
- Telemetry (separate privacy decision)

Each of these can be its own bite-sized follow-up plan once the alpha is
proving itself.
