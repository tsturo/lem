# Tonale Electron Design System

A cross-app design system for desktop Electron apps in the Tonale family.
Self-contained: this document doesn't depend on any one product, and can be
copied into any Tonale Electron repo as the visual contract.

It extends the [Tonale brand book](https://github.com/mbtonale/tonale-landing/blob/main/docs/tonale-brandbook.md)
with the patterns specific to native-feeling Electron apps: app shell,
titlebar, theme handling, library/workspace layouts, slide-overs, status
indicators, progress rails, animations.

When the brand book and this document conflict, the brand book wins.

---

## Principles

- **Brand-faithful, surface-quiet.** The purple→teal gradient is precious.
  Use it for moments that matter (CTAs, brand mark, active progress, verdict).
  Don't tile it across every surface.
- **Approachable, not toy.** Tonale's voice is "modern, confident, not stiff".
  In a desktop app that means: real density, real keyboard shortcuts, real
  affordances — but warm typography, generous radii, gentle shadows.
- **Library + workspace is the default shell.** Sidebar lists artifacts the
  user has accumulated; main pane shows the one they're working on.
- **Progressive disclosure.** Power-user details (IDs, costs, raw output,
  logs) live behind a single toggle (the Details slide-over), never in the
  default view.
- **Theme follows OS.** Default to the user's system appearance; manual
  override available in Settings, persisted per-user.

---

## Tokens

CSS custom properties, copy-paste from a Tonale repo's `globals.css` or the
landing-page brand book. The Electron design system adds **theme variants**
on top of the brand's neutral palette.

```css
:root {
  /* Brand */
  --t-purple: #6c5ce7;
  --t-teal: #00cec9;
  --t-grad: linear-gradient(135deg, #6c5ce7, #00cec9);

  /* Typography */
  --t-font: 'Rubik', -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
  --t-font-mono: 'SF Mono', Menlo, Consolas, monospace;

  /* Radii */
  --t-radius-sm: 9px;    /* rows, list items, small buttons */
  --t-radius-md: 12px;   /* inputs, cards, buttons */
  --t-radius-lg: 14px;   /* feature cards (theater, brief callouts) */
  --t-radius-xl: 16px;   /* window chrome, modals */
  --t-radius-pill: 100px;

  /* Spacing (4px base, brand-aligned) */
  --t-sp-1: 4px;  --t-sp-2: 8px;  --t-sp-3: 12px;
  --t-sp-4: 16px; --t-sp-5: 20px; --t-sp-6: 24px;
  --t-sp-8: 32px; --t-sp-10: 40px; --t-sp-12: 48px;

  /* Animation */
  --t-easing: cubic-bezier(0.2, 0.8, 0.2, 1);
  --t-dur-fast: 0.12s;
  --t-dur-base: 0.18s;
  --t-dur-slow: 0.30s;
}

/* Light (default; brand-primary) */
:root, [data-theme="light"] {
  --bg: #ffffff;
  --surface: #f7f7fb;
  --text: #1a1a2e;
  --text-2: #4a4a68;
  --text-3: #8888a4;
  --border: #e8e8f0;
  --shadow-card: 0 2px 12px rgba(10, 15, 26, 0.06);
  --shadow-card-hover: 0 4px 24px rgba(10, 15, 26, 0.10);
  --shadow-window: 0 30px 60px -20px rgba(10, 15, 26, 0.18);
  --shadow-cta: 0 4px 14px rgba(108, 92, 231, 0.30);
  --pulse-rgb: 108, 92, 231;            /* purple pulse on light */
}

/* Dark (Deep Navy + Cloud) */
[data-theme="dark"] {
  --bg: #0a0f1a;
  --surface: #131829;
  --card-bg: #11162a;
  --text: #e8edf3;
  --text-2: #a8b0c2;
  --text-3: #6b7388;
  --border: rgba(232, 237, 243, 0.08);
  --border-strong: rgba(232, 237, 243, 0.12);
  --shadow-card: 0 1px 0 rgba(232, 237, 243, 0.02);
  --shadow-card-hover: 0 8px 24px rgba(0, 0, 0, 0.40);
  --shadow-window: 0 30px 60px -20px rgba(0, 0, 0, 0.60);
  --shadow-cta: 0 4px 14px rgba(108, 92, 231, 0.40);
  --pulse-rgb: 0, 206, 201;             /* cooler pulse on dark for contrast */
}

/* Status colors (semantic) */
:root {
  --status-success: var(--t-purple);    /* "build" / positive verdicts */
  --status-info:    var(--t-teal);      /* "?" / unsure / informational */
  --status-warn:    #d4a843;            /* warnings, retries */
  --status-error:   #d97070;            /* "skip" / failures (soft coral) */
  --status-muted:   #c8c8d4;            /* archived / disabled */
}
[data-theme="dark"] {
  --status-error: #e08585;              /* slightly brighter on dark */
  --status-muted: #3a4258;
}
```

### Why a soft coral for error
The brand palette has no red. Semantic UI requires one. `#d97070` (light) /
`#e08585` (dark) is a desaturated coral that pairs cleanly with purple and
teal without screaming "Bootstrap alert". Use it sparingly: dot indicators,
verdict pills, error toasts. Never for body text.

---

## Typography

| Role | Family | Weight | Size | Letter spacing |
|------|--------|--------|------|----------------|
| Hero (intake H1, brief H1) | Rubik | 700 | 30–36px | -0.02em |
| Section heading (H2) | Rubik | 700 | 22px | -0.01em |
| Subsection (H3) | Rubik | 500 | 17px | 0 |
| Window topbar title | Rubik | 700 | 18–19px | -0.01em |
| Body large (lead) | Rubik | 400 | 16–17px | 0 |
| Body | Rubik | 400 | 14–15.5px | 0 |
| UI label (form labels, captions) | Rubik | 500 | 12–13px | 0 |
| Eyebrow / overline (UPPER) | Rubik | 700 | 10–11px | 0.10em |
| Mono (paths, logs, schemas) | SF Mono | 400 | 11–12px | 0 |

- Line height: **1.55–1.65** for body, **1.2** for headings.
- "Tonale" lowercase in running text; "Tonale" capitalized at sentence start.
- Never set body in caps; eyebrows + button-labels only.
- Maximum reading width: **720px** for documents (brief view); narrower
  in chat-style surfaces (560px).

### Brand mark — gradient text
Use the gradient on a single accent word in a hero:

```css
.accent {
  background: var(--t-grad);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  color: transparent;
}
```

---

## App shell

Every Tonale Electron app follows the same outer shape. Pieces are optional
per-app, but their positions are not negotiable.

```
┌─ titlebar ─────────────────────────────────────────────────────────────┐
│ ●●●   [logo-bars] appname · by tonale                                  │
├──────────────┬─────────────────────────────────────────────────────────┤
│              │ ┌─ topbar ─────────────────────────────────────────────┐│
│              │ │ Title           ▸ verdict-pill   ⏸ 📂 ⚙               ││
│  sidebar     │ │ meta line                                            ││
│              │ ├──────────────────────────────────────────────────────┤│
│  (library)   │ │ optional rail (progress / tabs)                      ││
│              │ ├──────────────────────────────────────────────────────┤│
│              │ │                                                      ││
│              │ │ workspace / theater / brief / chat                   ││
│              │ │                                                      ││
│              │ └──────────────────────────────────────────────────────┘│
└──────────────┴─────────────────────────────────────────────────────────┘
                                                              [Details ▸]
                                                              (slide-over)
```

### Window chrome
- macOS traffic-light dots stay visible (use `titleBarStyle: 'hidden'` +
  `trafficLightPosition` to nudge into the custom titlebar).
- Titlebar height: **36px**.
- Titlebar background: `var(--surface)` (light) / `var(--surface)` (dark).
- Centered: a small **logo bars** glyph (9 vertical bars, gradient,
  symmetric — see brand book, max 14px tall) followed by `appname · by tonale`
  in 13px Rubik 500.
- Right side reserved for app-specific window actions (most apps leave it empty).

### Library sidebar
- Width: **232–248px**.
- Background: `var(--surface)`.
- Right border: `1px solid var(--border)`.
- First child: the **primary CTA** (e.g. `+ New idea`). Gradient background,
  white text, 12px radius, full-width, 4px purple shadow.
- Section labels: 10px Rubik 500, uppercase, 0.10em letter-spacing,
  `var(--text-3)`, padding `10px 10px 6px`.
- Items: 8px-10px padding, 9px radius. Hover = `rgba(108,92,231,0.06)`.
  Active = `rgba(108,92,231,0.10)` + a 3px gradient bar `::before` flush
  to the left edge.
- Item layout: `[8px status-dot] [title (truncate)] [10px verdict-text]`.

### Main pane
- Background: `var(--bg)`.
- Topbar: 18px top padding, 32px horizontal. Bottom border `var(--border)`.
- Always reserves slot for `[⚙ Details]` toggle in the top-right.
- The pane's inner area is the *workspace* — this is where the app puts
  its mode-specific content (intake form, theater, brief, settings, etc.).

---

## Components

### Buttons

| Variant | Use | Style |
|---------|-----|-------|
| **Primary (gradient)** | The single most important action on the screen | `background: var(--t-grad)`, white text, 12px radius, `box-shadow: var(--shadow-cta)`, hover lifts 1px |
| **Secondary (outline)** | Common actions in toolbars | 1px border `var(--border)`, white bg, 10px radius, hover `var(--surface)` |
| **Ghost (text)** | Tertiary actions, danger-light | No border, no bg, hover `var(--surface)` |
| **Icon button** | 32px square, 9px radius, 1px border `var(--border)` | Active state: `rgba(108,92,231,0.14)` bg + `rgba(108,92,231,0.45)` border + purple text |

Never put more than **one** primary button per visible pane. CTAs compete.

### Inputs

```css
.input, .textarea {
  border: 1.5px solid var(--border);
  border-radius: var(--t-radius-md);     /* 12-14px */
  padding: 12-14px 16px;
  font: 400 15-16px var(--t-font);
  background: var(--bg);
  color: var(--text);
}
.input:focus, .textarea:focus {
  outline: none;
  border-color: var(--t-purple);
  box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.15);
}
```

- Textareas resize vertically by default; minimum 2-3 rows.
- Placeholders should be example content (`"e.g. a calendar app that…"`),
  not labels; labels live above the field.
- Field labels: 12px Rubik 500, `var(--text-2)`, 8px below margin.

### Chips
Pill-shaped 28-32px-tall containers for tags, attachments, filter values,
extras controls.

```css
.chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--border);
  background: var(--bg);
  border-radius: var(--t-radius-pill);
  font-size: 12px; color: var(--text-2);
}
.chip:hover { border-color: var(--t-purple); color: var(--t-purple); }
```

Status-tinted variants (`.chip.purple`, `.chip.teal`) use 10% bg + 25%
border of the brand color and the brand color for text.

### Cards
Multi-purpose container for feature content. Three sizes:

| Card | Use | Padding | Radius |
|------|-----|---------|--------|
| **Compact** | List rows, dashboard widgets | 14-16px | 12px |
| **Standard** | Theater agent, brief callout | 18px | 14px |
| **Feature** | Hero items, branching survivor | 20-22px | 16px |

Standard structure: head (icon + name + status) → body → foot (meta).
Each section separated by `1px solid var(--border)` with 12px padding.

### Status dots
8px circles with a 50% radius. Color from the **status colors** semantic
mapping. The "active" / "running" variant pulses (see Animations).

### Verdict pills
Used in topbars when an artifact has a final state.

```
[ ✓ ] Build       — purple gradient checkmark, purple text on 10% purple bg
[ ✗ ] Skip        — coral X, coral text on 10% coral bg
[ ? ] Unsure      — teal "?", teal text on 12% teal bg
```

8px padding, 14px horizontal, 100px radius, 13px Rubik 700,
0.04em letter-spacing.

### Step rail (progress)
For multi-phase processes (lem's 9 phases, an onboarding 3-step wizard, etc.).

```css
.steps { display: flex; gap: 4-5px; }
.step  { flex: 1; height: 5px; background: var(--border); border-radius: 3px; }
.step.done   { background: var(--t-grad); }
.step.active {
  background: linear-gradient(90deg, #6c5ce7 0%, #00cec9 60%, var(--border) 60%);
}
.step.active::after {
  content: ""; position: absolute; left: 60%; top: -3px;
  width: 11px; height: 11px; border-radius: 50%;
  background: var(--t-purple);
  animation: pulse 1.4s infinite;
  transform: translateX(-50%);
}
```

The active step's "post-cursor" portion uses `var(--border)` (not
`transparent`) so it visually reads as "not done". A pulsing dot at the
60% mark indicates "we're in the middle of this".

### Tabs
Horizontal tab strip with a gradient underline on the active tab.

```css
.tab.active {
  border-bottom: 2px solid;
  border-image: var(--t-grad) 1;
  color: var(--text);
}
```

Optional `.count` chip after a tab label (`MVP plan ▸ 12`).

### Callouts
Highlight an at-a-glance summary at the top of a long document.

```css
.callout {
  border: 1px solid rgba(108,92,231,0.18);
  border-left: 4px solid var(--t-purple);
  background: linear-gradient(180deg, rgba(108,92,231,0.04), rgba(0,206,201,0.04));
  border-radius: 12px;
  padding: 18px 22px;
}
```

Inside, a 2-3 column grid of `[stat-label / stat-value]` for the most
load-bearing facts. Brand-tinted but not loud.

### Slide-over (Details panel)
Right-side panel, **320px wide**, that pushes the main content left when
toggled (or overlays it on narrow windows).

- Background: `var(--bg)`.
- Left border: `1px solid var(--border)`.
- Box shadow: `-8px 0 24px rgba(10, 15, 26, 0.06)` to suggest depth.
- Header: 16px padding, `var(--surface)` background, 13px Rubik 700
  uppercase title.
- Sections divided by `1px solid var(--border)`.

The Details panel is the **only** place where operator-grade information
lives (raw IDs, paths, costs, JSONL log). Keep the default UI free of it.

### Chat / message bubbles
For conversational surfaces (intake clarifying questions, AI replies).

```
[avatar 32x32 9px radius] [bubble]
                          14px radius, 12px 16px padding
                          surface bg + border (lem) /
                          purple-tint bg + border (user)
                          15px Rubik 400, 1.55 line-height
                          max-width 560px
```

Avatar for "user" uses the gradient as background with 14px white
initials. Avatar for the AI agent uses 12% purple bg with the agent's
icon.

### Document body (rendered markdown)
For the Brief reader and any Markdown surface. Restricts to **720px**
content width. Bullets use a 6px gradient circle pseudo-element instead
of disc-style markers. Blockquotes have a teal left border and 5%
teal bg.

---

## Theming

- Default: **follow OS appearance** (`prefers-color-scheme`).
- User can override in Settings; preference persisted to disk and
  restored on launch.
- Theme tokens are CSS custom properties on `[data-theme="light"]` /
  `[data-theme="dark"]`. Toggling = swapping the attribute on `<html>`.
- The gradient is **shared** across themes — same `#6c5ce7 → #00cec9`.
- The "running" pulse animation uses `--pulse-rgb`: purple on light, teal
  on dark. Purple alone bleeds into the dark navy and reads weak.
- Borders on dark are `rgba(232, 237, 243, 0.08)` — alpha-on-light
  rather than a fixed grey, so they sit naturally on cards of slightly
  varying base.

---

## Animations

```css
@keyframes pulse {
  0%   { box-shadow: 0 0 0 0 rgba(var(--pulse-rgb), 0.5); }
  70%  { box-shadow: 0 0 0 8px rgba(var(--pulse-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--pulse-rgb), 0); }
}
@keyframes blink   { 50% { opacity: 0; } }
@keyframes bounce  {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40%           { transform: translateY(-3px); opacity: 1; }
}
```

| Pattern | Use |
|---------|-----|
| `pulse` (1.4s) | Status dots that mean "live / running" |
| `blink` (1s) | Streaming caret in text fields, "● running" markers in logs |
| `bounce` (1.4s, staggered 0.2s) | "Thinking" dots in chat or empty cards |
| `transform: translateY(-1px)` on hover | Primary buttons feel pressable |

Respect `prefers-reduced-motion`: collapse `pulse` and `bounce` to
constant opacity dots, skip the button lift.

---

## Density

Three density profiles. Pick one for the whole app; don't mix.

| Profile | Sidebar item | Card padding | Topbar height |
|---------|--------------|--------------|---------------|
| **Cozy** (default — non-technical, content-heavy apps) | 9px tall, 13px font | 18-20px | 64-72px |
| **Compact** (operator tools, dense data) | 7px tall, 12px font | 14-16px | 56-60px |
| **Roomy** (hero/marketing-adjacent, first-run) | 12px tall, 14px font | 24-32px | 80px+ |

The mockups for lem use **Cozy**.

---

## Iconography

- Source: **Lucide** (matches Rubik's rounded aesthetic).
- Stroke 1.5–2px, never filled.
- Default size 16px in inline UI, 18-20px in cards, 24px in feature spots.
- Color: `var(--text-2)` for neutral, `var(--t-purple)` for emphasis.
- Emoji is acceptable for human-warm spots (avatar fallbacks, intake
  chips), but never inside structured data.

---

## Accessibility minimums

- All interactive elements have a **2px purple focus ring** at 15% alpha:
  `box-shadow: 0 0 0 3px rgba(108, 92, 231, 0.15)`.
- Status meaning is never color-alone — always paired with a glyph (`✓`,
  `✗`, `?`) or label.
- Body text contrast minimum: **AA on the active surface**. Both
  `var(--text)` colors clear AA on their respective backgrounds.
- Don't use the gradient for body text. The mid-color portions drop
  below AA against white.
- Keyboard navigation parity: every clickable surface must be tab-able
  and Enter-actionable. Slide-overs trap focus when open.

---

## Window controls (macOS specifics)

- Use `titleBarStyle: 'hiddenInset'` so the traffic-lights show inside
  the custom titlebar.
- `vibrancy: 'sidebar'` on the sidebar pane (light + dark) for the
  native blur effect — don't fake it with CSS blur.
- Set the app's `name`, `productName`, and `appBundleId` to match
  Tonale's pattern: `lt.tonale.<app>`.

---

## What this design system intentionally doesn't cover

- **Marketing surfaces** — see the brand book.
- **iOS / Android** — these are Electron-desktop patterns. Mobile uses
  native idioms (SwiftUI on iOS), not these tokens.
- **Streaming / live cursor patterns** — single-app feature; document
  in the per-app spec if used.
- **Localization** — fonts (Rubik) cover Latin + Latin-ext including
  Lithuanian and Polish; specific locale strings live with the app.

---

## Quick implementation checklist

When starting a new Tonale Electron app:

- [ ] Vendor Rubik via Google Fonts in the renderer
- [ ] Drop the `:root` token block (light + dark + status) into `globals.css`
- [ ] Build the titlebar with traffic lights + logo bars + appname
- [ ] Sidebar with `+` CTA + section labels + status-dot rows
- [ ] Topbar with title block + actions + a single `[⚙ Details]` toggle
- [ ] At least one slide-over (`Details`) for advanced view
- [ ] Theme attribute on `<html>` driven by `matchMedia('(prefers-color-scheme: dark)')`
       with a manual override in Settings
- [ ] Verify focus-ring + reduced-motion + AA contrast on first screen
- [ ] App icon + favicon use the Tonale icon SVG (`tonale-final-icon.svg`)
