import { render, fireEvent } from '@testing-library/react'
import { TimelineStrip, type TimelineRound } from '@/components/TimelineStrip'

const ROUNDS: TimelineRound[] = [
  { runId: 'run-1', roundDepth: 1, verdict: 'BUILD' },
  { runId: 'run-2', roundDepth: 2, verdict: 'DONT' },
  { runId: 'run-3', roundDepth: 3, verdict: 'SKIP' },
]

// 2-branch: R1 → R2-mobile / R1 → R2-desktop
const BRANCHED_2: TimelineRound[] = [
  { runId: 'run-1',  roundDepth: 1, verdict: 'BUILD', parentRunId: null },
  { runId: 'run-2m', roundDepth: 2, verdict: 'BUILD', parentRunId: 'run-1', branchLabel: 'mobile' },
  { runId: 'run-2d', roundDepth: 2, verdict: 'DONT',  parentRunId: 'run-1', branchLabel: 'desktop' },
]

// Mixed: R1 → R2 → R3 (main) with R2' branch off R1
const BRANCHED_MIXED: TimelineRound[] = [
  { runId: 'run-1',  roundDepth: 1, verdict: 'BUILD',        parentRunId: null },
  { runId: 'run-2',  roundDepth: 2, verdict: 'BUILD',        parentRunId: 'run-1' },
  { runId: 'run-3',  roundDepth: 3, verdict: 'BUILD',        parentRunId: 'run-2' },
  { runId: 'run-2p', roundDepth: 2, verdict: 'INSUFFICIENT', parentRunId: 'run-1', branchLabel: 'alt' },
]

describe('TimelineStrip', () => {
  it('renders 1 pill for a single round', () => {
    const { container } = render(
      <TimelineStrip
        rounds={[ROUNDS[0]]}
        currentRunId="run-1"
        onRoundSelect={() => {}}
      />,
    )
    expect(container.querySelectorAll('[data-pill]')).toHaveLength(1)
  })

  it('renders 3 pills with middle pill enlarged as current', () => {
    const { container } = render(
      <TimelineStrip
        rounds={ROUNDS}
        currentRunId="run-2"
        onRoundSelect={() => {}}
      />,
    )
    const pills = container.querySelectorAll('[data-pill]')
    expect(pills).toHaveLength(3)

    const middlePill = pills[1] as HTMLElement
    const outerPill  = pills[0] as HTMLElement
    expect(parseFloat(middlePill.style.width)).toBeGreaterThan(parseFloat(outerPill.style.width))
    expect(middlePill.getAttribute('data-current')).toBe('true')
    expect(outerPill.getAttribute('data-current')).toBe('false')
  })

  it('fires onRoundSelect with the correct runId when pill[2] is clicked', () => {
    const onRoundSelect = vi.fn()
    const { container } = render(
      <TimelineStrip
        rounds={ROUNDS}
        currentRunId="run-1"
        onRoundSelect={onRoundSelect}
      />,
    )
    const pills = container.querySelectorAll('[data-pill]')
    fireEvent.click(pills[2])
    expect(onRoundSelect).toHaveBeenCalledOnce()
    expect(onRoundSelect).toHaveBeenCalledWith('run-3')
  })

  it('applies correct data-verdict attribute per round', () => {
    const { container } = render(
      <TimelineStrip
        rounds={ROUNDS}
        currentRunId="run-1"
        onRoundSelect={() => {}}
      />,
    )
    const pills = container.querySelectorAll('[data-pill]')
    expect(pills[0].getAttribute('data-verdict')).toBe('BUILD')
    expect(pills[1].getAttribute('data-verdict')).toBe('DONT')
    expect(pills[2].getAttribute('data-verdict')).toBe('SKIP')
  })

  it('renders connectors between pills but not before the first pill', () => {
    const { container } = render(
      <TimelineStrip
        rounds={ROUNDS}
        currentRunId="run-1"
        onRoundSelect={() => {}}
      />,
    )
    expect(container.querySelectorAll('[data-connector]')).toHaveLength(2)
  })

  it('handles all verdict types without errors', () => {
    const allVerdicts: TimelineRound[] = [
      { runId: 'a', roundDepth: 1, verdict: 'BUILD' },
      { runId: 'b', roundDepth: 2, verdict: 'DONT' },
      { runId: 'c', roundDepth: 3, verdict: 'SKIP' },
      { runId: 'd', roundDepth: 4, verdict: 'INSUFFICIENT' },
      { runId: 'e', roundDepth: 5, verdict: 'UNKNOWN' },
    ]
    const { container } = render(
      <TimelineStrip
        rounds={allVerdicts}
        currentRunId="a"
        onRoundSelect={() => {}}
      />,
    )
    expect(container.querySelectorAll('[data-pill]')).toHaveLength(5)
  })
})

describe('TimelineStrip — branching', () => {
  it('linear rounds without parentRunId render as single row (D1 baseline)', () => {
    const { container } = render(
      <TimelineStrip rounds={ROUNDS} currentRunId="run-1" onRoundSelect={() => {}} />,
    )
    expect(container.querySelectorAll('[data-timeline-row]')).toHaveLength(0)
    expect(container.querySelectorAll('[data-pill]')).toHaveLength(3)
  })

  it('2-branch case renders 2 rows', () => {
    const { container } = render(
      <TimelineStrip rounds={BRANCHED_2} currentRunId="run-1" onRoundSelect={() => {}} />,
    )
    expect(container.querySelectorAll('[data-timeline-row]')).toHaveLength(2)
  })

  it('2-branch case: each row has 2 pills, branch-row R1 is a placeholder', () => {
    const { container } = render(
      <TimelineStrip rounds={BRANCHED_2} currentRunId="run-1" onRoundSelect={() => {}} />,
    )
    const rows = container.querySelectorAll('[data-timeline-row]')

    expect(rows[0].querySelectorAll('[data-pill]')).toHaveLength(2)
    expect(rows[1].querySelectorAll('[data-pill]')).toHaveLength(2)

    const placeholders = rows[1].querySelectorAll('[data-pill][data-placeholder]')
    expect(placeholders).toHaveLength(1)
  })

  it('mixed case: main row 3 pills, branch row 2 pills with L-connector', () => {
    const { container } = render(
      <TimelineStrip rounds={BRANCHED_MIXED} currentRunId="run-1" onRoundSelect={() => {}} />,
    )
    const rows = container.querySelectorAll('[data-timeline-row]')
    expect(rows[0].querySelectorAll('[data-pill]')).toHaveLength(3)
    expect(rows[1].querySelectorAll('[data-pill]')).toHaveLength(2)
    expect(rows[1].querySelectorAll('[data-l-connector]')).toHaveLength(1)
  })

  it('click on real pill in branch-row fires onRoundSelect', () => {
    const onSelect = vi.fn()
    const { container } = render(
      <TimelineStrip rounds={BRANCHED_2} currentRunId="run-1" onRoundSelect={onSelect} />,
    )
    const branchRow  = container.querySelector('[data-timeline-row="branch"]')!
    const realPill   = branchRow.querySelector('button[data-pill]')!
    fireEvent.click(realPill)
    expect(onSelect).toHaveBeenCalledOnce()
    expect(onSelect).toHaveBeenCalledWith('run-2d')
  })

  it('current pill in branch-row is highlighted', () => {
    const { container } = render(
      <TimelineStrip rounds={BRANCHED_2} currentRunId="run-2d" onRoundSelect={() => {}} />,
    )
    const branchRow = container.querySelector('[data-timeline-row="branch"]')!
    const realPill  = branchRow.querySelector('button[data-pill]') as HTMLElement
    expect(realPill.getAttribute('data-current')).toBe('true')
    expect(parseFloat(realPill.style.width)).toBeGreaterThan(28)
  })

  it('main thread is longest path (highest leaf roundDepth)', () => {
    const { container } = render(
      <TimelineStrip rounds={BRANCHED_MIXED} currentRunId="run-1" onRoundSelect={() => {}} />,
    )
    const mainRow   = container.querySelector('[data-timeline-row="main"]')!
    const branchRow = container.querySelector('[data-timeline-row="branch"]')!
    expect(mainRow.querySelectorAll('[data-pill]')).toHaveLength(3)
    expect(branchRow.querySelectorAll('[data-pill]')).toHaveLength(2)
  })
})
