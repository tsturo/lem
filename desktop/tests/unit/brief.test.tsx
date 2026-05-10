import { render, fireEvent } from '@testing-library/react'
import { Brief } from '@/screens/Brief'
import { MarkdownBody } from '@/lib/markdown'
import type { TimelineRound } from '@/components/TimelineStrip'

const TABS = [
  {
    id:      'exec',
    label:   'Executive summary',
    content: '# Build the thing\n\nLeading paragraph here.',
  },
  {
    id:      'mvp',
    label:   'MVP plan',
    count:   12,
    content: '## Phase 1\n\n- Feature A\n- Feature B',
  },
  {
    id:      'risks',
    label:   'Risks & rejected',
    content: '> Expert says: watch out for this\n\n- Risk 1\n- Risk 2',
  },
]

const CALLOUT = {
  recommendation: 'Build',
  confidence:     'High',
  firstMilestone: 'MVP in 6 weeks',
}

const META = {
  version:     '0.1.0',
  phases:      9,
  specialists: 3,
  date:        '2026-05-09',
}

const ROUNDS_3: TimelineRound[] = [
  { runId: 'run-1', roundDepth: 1, verdict: 'BUILD' },
  { runId: 'run-2', roundDepth: 2, verdict: 'DONT' },
  { runId: 'run-3', roundDepth: 3, verdict: 'BUILD' },
]

function renderBrief(props?: Partial<Parameters<typeof Brief>[0]>) {
  const onContinue    = vi.fn()
  const onBranch      = vi.fn()
  const onRoundSelect = vi.fn()
  const result = render(
    <Brief
      idea="Fast calendar app"
      verdict="build"
      tabs={TABS}
      calloutStats={CALLOUT}
      signalPills={[]}
      meta={META}
      rounds={[]}
      currentRunId=""
      onRoundSelect={onRoundSelect}
      onContinue={onContinue}
      onBranch={onBranch}
      {...props}
    />
  )
  return { ...result, onContinue, onBranch, onRoundSelect }
}

// --- VerdictPill in Brief ---------------------------------------------------

describe('Brief — verdict pill', () => {
  it('renders correct glyph and pill for build verdict', () => {
    const { container } = renderBrief({ verdict: 'build' })
    expect(container.querySelector('[data-verdict="build"]')).toBeTruthy()
    expect(container.querySelector('[data-glyph]')?.textContent).toBe('✓')
    expect(container.querySelector('[data-label]')?.textContent).toBe('Build')
  })

  it('renders correct glyph and pill for skip verdict', () => {
    const { container } = renderBrief({ verdict: 'skip' })
    expect(container.querySelector('[data-verdict="skip"]')).toBeTruthy()
    expect(container.querySelector('[data-glyph]')?.textContent).toBe('✗')
    expect(container.querySelector('[data-label]')?.textContent).toBe('Skip')
  })

  it('renders correct glyph and pill for unsure verdict', () => {
    const { container } = renderBrief({ verdict: 'unsure' })
    expect(container.querySelector('[data-verdict="unsure"]')).toBeTruthy()
    expect(container.querySelector('[data-glyph]')?.textContent).toBe('?')
    expect(container.querySelector('[data-label]')?.textContent).toBe('Insufficient info')
  })
})

// --- Tab switching ----------------------------------------------------------

describe('Brief — tab switching', () => {
  it('renders first tab content by default', () => {
    const { container } = renderBrief()
    expect(container.querySelector('[data-tab="exec"][data-active="true"]')).toBeTruthy()
    expect(container.querySelector('[data-lem-h1]')).toBeTruthy()
  })

  it('switches to mvp tab on click', () => {
    const { container } = renderBrief()
    const mvpTab = container.querySelector('[data-tab="mvp"]') as HTMLButtonElement
    fireEvent.click(mvpTab)
    expect(container.querySelector('[data-tab="mvp"][data-active="true"]')).toBeTruthy()
    expect(container.querySelector('[data-lem-h1]')).toBeFalsy()
    expect(container.querySelector('[data-lem-h2]')).toBeTruthy()
  })

  it('switches to risks tab on click', () => {
    const { container } = renderBrief()
    const risksTab = container.querySelector('[data-tab="risks"]') as HTMLButtonElement
    fireEvent.click(risksTab)
    expect(container.querySelector('[data-tab="risks"][data-active="true"]')).toBeTruthy()
    expect(container.querySelector('[data-lem-blockquote]')).toBeTruthy()
  })

  it('shows count chip on mvp tab', () => {
    const { container } = renderBrief()
    const mvpTab = container.querySelector('[data-tab="mvp"]')
    expect(mvpTab?.textContent).toContain('12')
  })
})

// --- Callout ----------------------------------------------------------------

describe('Brief — callout', () => {
  it('renders all 3 stat slots', () => {
    const { container } = renderBrief()
    expect(container.querySelectorAll('[data-stat]')).toHaveLength(3)
  })

  it('renders recommendation stat label and value', () => {
    const { container } = renderBrief()
    const stats = Array.from(container.querySelectorAll('[data-stat]'))
    const labels = stats.map(s => s.firstElementChild?.textContent)
    const values = stats.map(s => s.lastElementChild?.textContent)
    expect(labels).toContain('Recommendation')
    expect(values).toContain('Build')
  })

  it('renders confidence stat', () => {
    const { container } = renderBrief()
    const stats = Array.from(container.querySelectorAll('[data-stat]'))
    const labels = stats.map(s => s.firstElementChild?.textContent)
    expect(labels).toContain('Confidence')
  })

  it('renders first milestone stat', () => {
    const { container } = renderBrief()
    const stats = Array.from(container.querySelectorAll('[data-stat]'))
    const labels = stats.map(s => s.firstElementChild?.textContent)
    expect(labels).toContain('First milestone')
  })
})

// --- TimelineStrip in Brief -------------------------------------------------

describe('Brief — TimelineStrip', () => {
  it('renders 3 pills when 3 rounds passed', () => {
    const { container } = renderBrief({ rounds: ROUNDS_3, currentRunId: 'run-2' })
    const pills = container.querySelectorAll('[data-timeline-strip] [data-pill]')
    expect(pills).toHaveLength(3)
  })

  it('middle pill is highlighted when currentRunId is round 2', () => {
    const { container } = renderBrief({ rounds: ROUNDS_3, currentRunId: 'run-2' })
    const pills = Array.from(container.querySelectorAll('[data-pill]'))
    const current = pills.filter(p => p.getAttribute('data-current') === 'true')
    expect(current).toHaveLength(1)
    expect(current[0].getAttribute('data-round')).toBe('2')
  })

  it('does not render timeline wrapper when rounds is empty', () => {
    const { container } = renderBrief({ rounds: [], currentRunId: '' })
    expect(container.querySelector('[data-timeline-wrapper]')).toBeNull()
  })

  it('clicking a pill fires onRoundSelect with the runId', () => {
    const { container, onRoundSelect } = renderBrief({ rounds: ROUNDS_3, currentRunId: 'run-3' })
    const pills = Array.from(container.querySelectorAll('[data-pill]:not([data-placeholder])'))
    const middlePill = pills.find(p => p.getAttribute('data-round') === '2') as HTMLElement
    fireEvent.click(middlePill)
    expect(onRoundSelect).toHaveBeenCalledWith('run-2')
  })
})

// --- RefineAgainButton in Brief ---------------------------------------------

describe('Brief — RefineAgainButton', () => {
  it('renders RefineAgainButton instead of a plain PrimaryButton', () => {
    const { container } = renderBrief()
    expect(container.querySelector('[data-refine-again-button]')).toBeTruthy()
  })

  it('clicking main Refine again opens modal in continue mode', () => {
    const { container } = renderBrief({ rounds: ROUNDS_3, currentRunId: 'run-1' })
    fireEvent.click(container.querySelector('[data-main]')!)
    const dialog = container.querySelector('[role="dialog"]')
    expect(dialog).toBeTruthy()
    expect(dialog?.querySelector('[data-modal-title]')?.textContent).toBe('Refine again')
  })

  it('clicking chevron then Branch alternative opens modal in branch mode', () => {
    const { container } = renderBrief({ rounds: ROUNDS_3, currentRunId: 'run-1' })
    fireEvent.click(container.querySelector('[data-chevron]')!)
    fireEvent.click(container.querySelector('[data-menu-item="branch"]')!)
    const dialog = container.querySelector('[role="dialog"]')
    expect(dialog).toBeTruthy()
    expect(dialog?.querySelector('[data-modal-title]')?.textContent).toBe('⑂ Branch alternative')
  })
})

// --- Modal submit / cancel --------------------------------------------------

describe('Brief — modal submit and cancel', () => {
  it('submitting continue modal calls onContinue with payload and closes modal', () => {
    const { container, onContinue } = renderBrief({ rounds: ROUNDS_3, currentRunId: 'run-1' })
    fireEvent.click(container.querySelector('[data-main]')!)

    const dialog = container.querySelector('[role="dialog"]')!
    fireEvent.change(dialog.querySelector('textarea')!, { target: { value: 'now mobile-first' } })

    const refineBtn = Array.from(dialog.querySelectorAll('button')).find(b => b.textContent === 'Refine')!
    fireEvent.click(refineBtn)

    expect(onContinue).toHaveBeenCalledWith({ contextText: 'now mobile-first' })
    expect(container.querySelector('[role="dialog"]')).toBeNull()
  })

  it('submitting branch modal calls onBranch with payload and closes modal', () => {
    const { container, onBranch } = renderBrief({ rounds: ROUNDS_3, currentRunId: 'run-1' })
    fireEvent.click(container.querySelector('[data-chevron]')!)
    fireEvent.click(container.querySelector('[data-menu-item="branch"]')!)

    const dialog = container.querySelector('[role="dialog"]')!
    const textarea = dialog.querySelector('textarea')!
    fireEvent.change(textarea, { target: { value: 'focus on B2B' } })

    const buttons = Array.from(dialog.querySelectorAll('button'))
    const branchBtn = buttons.find(b => b.textContent === 'Branch')!
    fireEvent.click(branchBtn)

    expect(onBranch).toHaveBeenCalledWith({ contextText: 'focus on B2B' })
    expect(container.querySelector('[role="dialog"]')).toBeNull()
  })

  it('cancelling modal fires no callback and closes modal', () => {
    const { container, onContinue, onBranch } = renderBrief({ rounds: ROUNDS_3, currentRunId: 'run-1' })
    fireEvent.click(container.querySelector('[data-main]')!)
    expect(container.querySelector('[role="dialog"]')).toBeTruthy()

    const dialog = container.querySelector('[role="dialog"]')!
    const buttons = Array.from(dialog.querySelectorAll('button'))
    const cancelBtn = buttons.find(b => b.textContent === 'Cancel')!
    fireEvent.click(cancelBtn)

    expect(onContinue).not.toHaveBeenCalled()
    expect(onBranch).not.toHaveBeenCalled()
    expect(container.querySelector('[role="dialog"]')).toBeNull()
  })
})

// --- MarkdownBody -----------------------------------------------------------

describe('MarkdownBody', () => {
  it('renders H1 with data-lem-h1 and accent span', () => {
    const { container } = render(<MarkdownBody content="# Hello World" />)
    expect(container.querySelector('[data-lem-h1]')).toBeTruthy()
    expect(container.querySelector('[data-accent]')).toBeTruthy()
  })

  it('applies gradient accent to the last word of H1', () => {
    const { container } = render(<MarkdownBody content="# Hello beautiful World" />)
    const accent = container.querySelector('[data-accent]')
    expect(accent?.textContent).toBe('World')
  })

  it('renders single-word H1 with full text as accent', () => {
    const { container } = render(<MarkdownBody content="# Everything" />)
    const accent = container.querySelector('[data-accent]')
    expect(accent?.textContent).toBe('Everything')
  })

  it('renders H2 with data-lem-h2', () => {
    const { container } = render(<MarkdownBody content="## Section heading" />)
    expect(container.querySelector('[data-lem-h2]')).toBeTruthy()
  })

  it('renders H3 with data-lem-h3', () => {
    const { container } = render(<MarkdownBody content="### Sub heading" />)
    expect(container.querySelector('[data-lem-h3]')).toBeTruthy()
  })

  it('renders bullet list items', () => {
    const { container } = render(<MarkdownBody content={'- Item A\n- Item B\n- Item C'} />)
    expect(container.querySelectorAll('li')).toHaveLength(3)
  })

  it('renders blockquote with data-lem-blockquote', () => {
    const { container } = render(<MarkdownBody content="> Quote here" />)
    expect(container.querySelector('[data-lem-blockquote]')).toBeTruthy()
  })

  it('wraps content in a .lem-md div', () => {
    const { container } = render(<MarkdownBody content="hello" />)
    expect(container.querySelector('.lem-md')).toBeTruthy()
  })
})
