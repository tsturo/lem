import { render, fireEvent } from '@testing-library/react'
import { TimelineStrip, type TimelineRound } from '@/components/TimelineStrip'

const ROUNDS: TimelineRound[] = [
  { runId: 'run-1', roundDepth: 1, verdict: 'BUILD' },
  { runId: 'run-2', roundDepth: 2, verdict: 'DONT' },
  { runId: 'run-3', roundDepth: 3, verdict: 'SKIP' },
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
