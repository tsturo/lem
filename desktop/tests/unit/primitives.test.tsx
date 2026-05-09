import { render } from '@testing-library/react'
import { StatusDot } from '@/components/StatusDot'
import { VerdictPill } from '@/components/VerdictPill'
import { StepRail } from '@/components/StepRail'
import { Callout } from '@/components/Callout'

// --- StatusDot --------------------------------------------------------------

describe('StatusDot', () => {
  it('sets data-status to the given status prop', () => {
    const { container } = render(<StatusDot status="completed" />)
    expect(container.firstElementChild?.getAttribute('data-status')).toBe('completed')
  })

  it('sets data-status="running" when status is running', () => {
    const { container } = render(<StatusDot status="running" />)
    expect(container.firstElementChild?.getAttribute('data-status')).toBe('running')
  })

  it('sets data-status="failed" for failed status', () => {
    const { container } = render(<StatusDot status="failed" />)
    expect(container.firstElementChild?.getAttribute('data-status')).toBe('failed')
  })

  it('sets data-status="queued" for queued status', () => {
    const { container } = render(<StatusDot status="queued" />)
    expect(container.firstElementChild?.getAttribute('data-status')).toBe('queued')
  })
})

// --- VerdictPill ------------------------------------------------------------

describe('VerdictPill', () => {
  it('renders checkmark glyph and Build label for build verdict', () => {
    const { container } = render(<VerdictPill verdict="build" />)
    expect(container.querySelector('[data-glyph]')?.textContent).toBe('✓')
    expect(container.querySelector('[data-label]')?.textContent).toBe('Build')
  })

  it('renders cross glyph and Skip label for skip verdict', () => {
    const { container } = render(<VerdictPill verdict="skip" />)
    expect(container.querySelector('[data-glyph]')?.textContent).toBe('✗')
    expect(container.querySelector('[data-label]')?.textContent).toBe('Skip')
  })

  it('renders question mark glyph and Insufficient info label for unsure verdict', () => {
    const { container } = render(<VerdictPill verdict="unsure" />)
    expect(container.querySelector('[data-glyph]')?.textContent).toBe('?')
    expect(container.querySelector('[data-label]')?.textContent).toBe('Insufficient info')
  })
})

// --- StepRail ---------------------------------------------------------------

describe('StepRail', () => {
  it('renders the correct number of segments', () => {
    const { container } = render(<StepRail total={9} active={4} />)
    expect(container.querySelectorAll('[data-state]')).toHaveLength(9)
  })

  it('distributes data-state correctly for active=2 total=9', () => {
    const { container } = render(<StepRail total={9} active={2} />)
    const segments = Array.from(container.querySelectorAll('[data-state]'))
    expect(segments[0].getAttribute('data-state')).toBe('done')
    expect(segments[1].getAttribute('data-state')).toBe('done')
    expect(segments[2].getAttribute('data-state')).toBe('active')
    expect(segments[3].getAttribute('data-state')).toBe('queued')
    expect(segments[8].getAttribute('data-state')).toBe('queued')
  })

  it('marks all segments as done when active equals total', () => {
    const { container } = render(<StepRail total={5} active={5} />)
    const segments = Array.from(container.querySelectorAll('[data-state]'))
    expect(segments.every(s => s.getAttribute('data-state') === 'done')).toBe(true)
  })

  it('marks all segments as queued when active is -1', () => {
    const { container } = render(<StepRail total={3} active={-1} />)
    const segments = Array.from(container.querySelectorAll('[data-state]'))
    expect(segments.every(s => s.getAttribute('data-state') === 'queued')).toBe(true)
  })
})

// --- Callout ----------------------------------------------------------------

describe('Callout', () => {
  const stats = [
    { label: 'Phases',  value: '9' },
    { label: 'Time',    value: '4 min' },
    { label: 'Verdict', value: 'Build', tone: 'purple' as const },
  ]

  it('renders all stat items', () => {
    const { container } = render(<Callout stats={stats} />)
    expect(container.querySelectorAll('[data-stat]')).toHaveLength(3)
  })

  it('renders each stat label', () => {
    const { container } = render(<Callout stats={stats} />)
    const labels = Array.from(container.querySelectorAll('[data-stat]')).map(
      el => el.firstElementChild?.textContent
    )
    expect(labels).toContain('Phases')
    expect(labels).toContain('Time')
    expect(labels).toContain('Verdict')
  })

  it('renders each stat value', () => {
    const { container } = render(<Callout stats={stats} />)
    const values = Array.from(container.querySelectorAll('[data-stat]')).map(
      el => el.lastElementChild?.textContent
    )
    expect(values).toContain('9')
    expect(values).toContain('4 min')
    expect(values).toContain('Build')
  })
})
