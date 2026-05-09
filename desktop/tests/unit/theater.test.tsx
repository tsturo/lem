import { render, fireEvent } from '@testing-library/react'
import { AgentCard } from '@/screens/AgentCard'
import { EarlierSteps } from '@/screens/EarlierSteps'
import { Theater } from '@/screens/Theater'
import type { RoleSnapshot, PhaseSnapshot, RunSnapshot } from '../../src/types/lem-events'

// --- AgentCard ---------------------------------------------------------------

describe('AgentCard', () => {
  it('renders the correct icon for the architect role', () => {
    const role: RoleSnapshot = { name: 'architect', state: 'thinking' }
    const { container } = render(<AgentCard role={role} />)
    expect(container.querySelector('[data-icon]')?.textContent).toBe('🏗')
  })

  it('renders the correct icon for the designer role', () => {
    const role: RoleSnapshot = { name: 'designer', state: 'thinking' }
    const { container } = render(<AgentCard role={role} />)
    expect(container.querySelector('[data-icon]')?.textContent).toBe('🎨')
  })

  it('renders the correct icon for the market role', () => {
    const role: RoleSnapshot = { name: 'market', state: 'thinking' }
    const { container } = render(<AgentCard role={role} />)
    expect(container.querySelector('[data-icon]')?.textContent).toBe('📈')
  })

  it('shows bounce dots animation when thinking', () => {
    const role: RoleSnapshot = { name: 'architect', state: 'thinking' }
    const { container } = render(<AgentCard role={role} />)
    const dots = container.querySelectorAll('.animate-t-bounce span')
    expect(dots).toHaveLength(3)
  })

  it('shows elapsed timer when thinking', () => {
    const role: RoleSnapshot = { name: 'architect', state: 'thinking' }
    const { container } = render(<AgentCard role={role} />)
    expect(container.querySelector('[data-timer]')?.textContent).toMatch(/thinking\.\.\./)
  })

  it('shows full output text when done', () => {
    const role: RoleSnapshot = { name: 'architect', state: 'done', output: 'The architecture is solid.' }
    const { container } = render(<AgentCard role={role} />)
    expect(container.textContent).toContain('The architecture is solid.')
  })

  it('shows done status badge when state is done', () => {
    const role: RoleSnapshot = { name: 'architect', state: 'done' }
    const { container } = render(<AgentCard role={role} />)
    expect(container.querySelector('[data-status="done"]')?.textContent).toBe('done')
  })

  it('shows thinking status badge when state is thinking', () => {
    const role: RoleSnapshot = { name: 'architect', state: 'thinking' }
    const { container } = render(<AgentCard role={role} />)
    expect(container.querySelector('[data-status="thinking"]')?.textContent).toBe('thinking')
  })

  it('renders "Show full output →" foot link', () => {
    const role: RoleSnapshot = { name: 'architect', state: 'done' }
    const { container } = render(<AgentCard role={role} />)
    expect(container.querySelector('[data-foot]')?.textContent).toContain('Show full output')
  })

  it('sets data-role to the role name', () => {
    const role: RoleSnapshot = { name: 'market', state: 'done' }
    const { container } = render(<AgentCard role={role} />)
    expect(container.querySelector('[data-role="market"]')).toBeTruthy()
  })
})

// --- EarlierSteps ------------------------------------------------------------

describe('EarlierSteps', () => {
  const phases: PhaseSnapshot[] = [
    {
      id:        '0.5',
      state:     'done',
      roles:     [{ name: 'jtbd-extractor', state: 'done', output: 'Underlying job: save time' }],
      durationS: 42,
      summary:   'Underlying job: save time',
    },
    {
      id:        '1',
      state:     'done',
      roles:     [
        { name: 'architect', state: 'done', output: 'Build with microservices.' },
        { name: 'designer',  state: 'done', output: 'Clean minimal UI.' },
        { name: 'market',    state: 'done', output: 'Market is ready.' },
      ],
      durationS: 180,
      summary:   'Specialists agree on core approach',
    },
  ]

  it('renders a row for each completed phase', () => {
    const { container } = render(<EarlierSteps phases={phases} />)
    expect(container.querySelectorAll('[data-phase]')).toHaveLength(2)
  })

  it('does not show agent cards before expanding', () => {
    const { container } = render(<EarlierSteps phases={phases} />)
    expect(container.querySelectorAll('[data-role]')).toHaveLength(0)
  })

  it('expands agent cards on click', () => {
    const { container } = render(<EarlierSteps phases={phases} />)
    const btn = container.querySelector('[data-phase="1"] button') as HTMLElement
    fireEvent.click(btn)
    expect(container.querySelectorAll('[data-phase="1"] [data-role]')).toHaveLength(3)
  })

  it('collapses agent cards on second click', () => {
    const { container } = render(<EarlierSteps phases={phases} />)
    const btn = container.querySelector('[data-phase="1"] button') as HTMLElement
    fireEvent.click(btn)
    fireEvent.click(btn)
    expect(container.querySelectorAll('[data-phase="1"] [data-role]')).toHaveLength(0)
  })

  it('expands multiple phases independently', () => {
    const { container } = render(<EarlierSteps phases={phases} />)
    const btn05 = container.querySelector('[data-phase="0.5"] button') as HTMLElement
    const btn1  = container.querySelector('[data-phase="1"] button') as HTMLElement
    fireEvent.click(btn05)
    fireEvent.click(btn1)
    expect(container.querySelectorAll('[data-phase="0.5"] [data-role]')).toHaveLength(1)
    expect(container.querySelectorAll('[data-phase="1"] [data-role]')).toHaveLength(3)
  })

  it('returns null for an empty phases array', () => {
    const { container } = render(<EarlierSteps phases={[]} />)
    expect(container.firstChild).toBeNull()
  })
})

// --- Theater -----------------------------------------------------------------

describe('Theater', () => {
  function makeRun(currentPhase: number, activePhaseId: string): RunSnapshot {
    const phases: PhaseSnapshot[] = [
      {
        id:    '0.5',
        state: currentPhase > 1 ? 'done' : 'queued',
        roles: [],
      },
      {
        id:    '1',
        state: activePhaseId === '1' ? 'active' : (currentPhase > 3 ? 'done' : 'queued'),
        roles: activePhaseId === '1'
          ? [
              { name: 'architect', state: 'thinking' },
              { name: 'designer',  state: 'thinking' },
              { name: 'market',    state: 'thinking' },
            ]
          : [],
      },
    ]
    return {
      id:           'run-test',
      phases,
      currentPhase,
      totalCost:    0,
      status:       'running',
    }
  }

  it('renders the idea title in the topbar', () => {
    const run = makeRun(3, '1')
    const { container } = render(<Theater run={run} idea="My brilliant idea" />)
    expect(container.querySelector('[data-idea-title]')?.textContent).toBe('My brilliant idea')
  })

  it('renders a StepRail with 9 segments', () => {
    const run = makeRun(3, '1')
    const { container } = render(<Theater run={run} idea="Test idea" />)
    expect(container.querySelectorAll('[data-state]')).toHaveLength(9)
  })

  it('sets the active segment correctly based on currentPhase', () => {
    const run = makeRun(3, '1')
    const { container } = render(<Theater run={run} idea="Test idea" />)
    const segments = Array.from(container.querySelectorAll('[data-state]'))
    expect(segments[3].getAttribute('data-state')).toBe('active')
    expect(segments[0].getAttribute('data-state')).toBe('done')
    expect(segments[8].getAttribute('data-state')).toBe('queued')
  })

  it('renders active phase cards for parallel phase (phase 1 — 3 specialists)', () => {
    const run = makeRun(3, '1')
    const { container } = render(<Theater run={run} idea="Test idea" />)
    expect(container.querySelectorAll('[data-role]')).toHaveLength(3)
  })

  it('renders stop and workspace buttons', () => {
    const run = makeRun(3, '1')
    const { container } = render(<Theater run={run} idea="Test idea" />)
    expect(container.querySelector('[data-action="stop"]')).toBeTruthy()
    expect(container.querySelector('[data-action="workspace"]')).toBeTruthy()
  })

  it('calls onStop when Stop button is clicked', () => {
    const onStop = vi.fn()
    const run = makeRun(3, '1')
    const { container } = render(<Theater run={run} idea="Test idea" onStop={onStop} />)
    fireEvent.click(container.querySelector('[data-action="stop"]') as HTMLElement)
    expect(onStop).toHaveBeenCalledOnce()
  })

  it('calls onOpenWorkspace when Workspace button is clicked', () => {
    const onOpenWorkspace = vi.fn()
    const run = makeRun(3, '1')
    const { container } = render(<Theater run={run} idea="Test idea" onOpenWorkspace={onOpenWorkspace} />)
    fireEvent.click(container.querySelector('[data-action="workspace"]') as HTMLElement)
    expect(onOpenWorkspace).toHaveBeenCalledOnce()
  })
})
