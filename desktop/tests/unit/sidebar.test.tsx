/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom" />
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { Sidebar } from '@/components/Sidebar'
import type { Idea, RunRow } from '../../src/shared/types'

function makeIdea(id: string, title: string): Idea {
  return { id, title, createdAt: 1_700_000_000 }
}

function makeRound(runId: string, ideaId: string, opts: Partial<RunRow> = {}): RunRow {
  return {
    runId,
    idea:          opts.idea          ?? 'test idea',
    verdict:       opts.verdict       ?? null,
    status:        opts.status        ?? 'completed',
    group:         opts.group         ?? 'done',
    workspacePath: opts.workspacePath ?? '/tmp',
    createdAt:     opts.createdAt     ?? new Date().toISOString(),
    updatedAt:     new Date().toISOString(),
    ideaId,
    roundDepth:    opts.roundDepth    ?? 1,
    parentRunId:   opts.parentRunId   ?? null,
    branchLabel:   opts.branchLabel   ?? null,
  }
}

const baseProps = {
  onNewIdea:         vi.fn(),
  onSelectIdeaRound: vi.fn(),
  onSkipIdea:        vi.fn(),
}

function setupLem(ideas: Idea[], roundsMap: Record<string, RunRow[]>) {
  vi.stubGlobal('lem', {
    ideas: {
      list:      vi.fn().mockResolvedValue(ideas),
      getRounds: vi.fn().mockImplementation((id: string) =>
        Promise.resolve(roundsMap[id] ?? []),
      ),
    },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

// --- Empty state -----------------------------------------------------------

describe('Sidebar — empty state', () => {
  it('shows "No ideas yet" when no ideas returned', async () => {
    setupLem([], {})
    render(<Sidebar {...baseProps} />)
    await waitFor(() => expect(screen.getByText('No ideas yet')).toBeInTheDocument())
  })
})

// --- 3 ideas rendered ------------------------------------------------------

describe('Sidebar — idea rows', () => {
  it('renders one row per idea', async () => {
    const ideas = [
      makeIdea('i1', 'Idea One'),
      makeIdea('i2', 'Idea Two'),
      makeIdea('i3', 'Idea Three'),
    ]
    setupLem(ideas, {
      i1: [makeRound('r1', 'i1')],
      i2: [makeRound('r2', 'i2')],
      i3: [makeRound('r3', 'i3')],
    })
    render(<Sidebar {...baseProps} />)
    await waitFor(() => {
      expect(screen.getByText('Idea One')).toBeInTheDocument()
      expect(screen.getByText('Idea Two')).toBeInTheDocument()
      expect(screen.getByText('Idea Three')).toBeInTheDocument()
    })
  })
})

// --- Latest verdict --------------------------------------------------------

describe('Sidebar — latest verdict', () => {
  it('shows the verdict of the highest-depth round', async () => {
    const ideas = [makeIdea('i1', 'Multi-round idea')]
    setupLem(ideas, {
      i1: [
        makeRound('r1', 'i1', { roundDepth: 1, verdict: 'skip',   createdAt: '2024-01-01T00:00:00Z' }),
        makeRound('r2', 'i1', { roundDepth: 2, verdict: 'unsure', createdAt: '2024-01-02T00:00:00Z' }),
        makeRound('r3', 'i1', { roundDepth: 3, verdict: 'build',  createdAt: '2024-01-03T00:00:00Z' }),
      ],
    })
    render(<Sidebar {...baseProps} />)
    await waitFor(() => expect(screen.getByText('Build')).toBeInTheDocument())
  })
})

// --- Click callback --------------------------------------------------------

describe('Sidebar — click callback', () => {
  it('fires onSelectIdeaRound(ideaId, latestRunId) when idea row clicked', async () => {
    const onSelectIdeaRound = vi.fn()
    const ideas = [makeIdea('i1', 'Clickable Idea')]
    setupLem(ideas, {
      i1: [makeRound('r1', 'i1', { roundDepth: 1, verdict: 'build' })],
    })
    render(<Sidebar {...baseProps} onSelectIdeaRound={onSelectIdeaRound} />)
    await waitFor(() => expect(screen.getByText('Clickable Idea')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Clickable Idea'))
    expect(onSelectIdeaRound).toHaveBeenCalledWith('i1', 'r1')
  })
})

// --- Single-round idea: no chevron, no badge --------------------------------

describe('Sidebar — single-round idea', () => {
  it('shows no chevron and no count badge for a 1-round idea', async () => {
    const ideas = [makeIdea('i1', 'Solo Idea')]
    setupLem(ideas, {
      i1: [makeRound('r1', 'i1', { roundDepth: 1 })],
    })
    render(<Sidebar {...baseProps} />)
    await waitFor(() => expect(screen.getByText('Solo Idea')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: /expand rounds/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/^·\d/)).not.toBeInTheDocument()
  })
})

// --- Multi-round: badge, expand, round-row click ---------------------------

describe('Sidebar — multi-round expand', () => {
  it('shows ·3 badge and expands 3 round rows on chevron click; fires onSelectRound', async () => {
    const onSelectRound = vi.fn()
    const ideas = [makeIdea('i1', 'Three-round Idea')]
    setupLem(ideas, {
      i1: [
        makeRound('r1', 'i1', { roundDepth: 1, createdAt: '2024-01-01T00:00:00Z' }),
        makeRound('r2', 'i1', { roundDepth: 2, createdAt: '2024-01-02T00:00:00Z' }),
        makeRound('r3', 'i1', { roundDepth: 3, createdAt: '2024-01-03T00:00:00Z' }),
      ],
    })
    render(<Sidebar {...baseProps} onSelectRound={onSelectRound} />)

    await waitFor(() => expect(screen.getByText('Three-round Idea')).toBeInTheDocument())

    // Badge ·3 visible
    expect(screen.getByText('·3')).toBeInTheDocument()

    // No round rows yet (collapsed)
    expect(screen.queryByText('Round 1')).not.toBeInTheDocument()

    // Click chevron to expand
    fireEvent.click(screen.getByRole('button', { name: /expand rounds/i }))
    await waitFor(() => expect(screen.getByText('Round 1')).toBeInTheDocument())
    expect(screen.getByText('Round 2')).toBeInTheDocument()
    expect(screen.getByText('Round 3')).toBeInTheDocument()

    // Click Round 2 row → onSelectRound fired
    fireEvent.click(screen.getByText('Round 2'))
    expect(onSelectRound).toHaveBeenCalledWith('i1', 'r2')
  })
})

// --- Branching: ⑂2 badge + 2 branch rows -----------------------------------

describe('Sidebar — branching idea', () => {
  it('shows ·3 ⑂2 badges and renders both branch rows on expand', async () => {
    const ideas = [makeIdea('i1', 'Branching Idea')]
    setupLem(ideas, {
      i1: [
        makeRound('r1', 'i1', { roundDepth: 1, parentRunId: null }),
        makeRound('r2', 'i1', { roundDepth: 2, parentRunId: 'r1', branchLabel: 'mobile-first' }),
        makeRound('r3', 'i1', { roundDepth: 2, parentRunId: 'r1', branchLabel: 'enterprise' }),
      ],
    })
    render(<Sidebar {...baseProps} />)

    await waitFor(() => expect(screen.getByText('Branching Idea')).toBeInTheDocument())

    // Both badges present
    expect(screen.getByText('·3')).toBeInTheDocument()
    expect(screen.getByText('⑂2')).toBeInTheDocument()

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /expand rounds/i }))
    await waitFor(() => expect(screen.getByText('mobile-first')).toBeInTheDocument())
    expect(screen.getByText('enterprise')).toBeInTheDocument()
  })
})

// --- Auto-expand ----------------------------------------------------------

describe('Sidebar — auto-expand', () => {
  it('auto-expands the idea containing activeId on initial render', async () => {
    const ideas = [
      makeIdea('i1', 'Idea Alpha'),
      makeIdea('i2', 'Idea Beta'),
    ]
    setupLem(ideas, {
      i1: [
        makeRound('r1a', 'i1', { roundDepth: 1 }),
        makeRound('r1b', 'i1', { roundDepth: 2 }),
      ],
      i2: [
        makeRound('r2a', 'i2', { roundDepth: 1 }),
        makeRound('r2b', 'i2', { roundDepth: 2 }),
      ],
    })
    render(<Sidebar {...baseProps} activeId="r1b" />)

    // Idea Alpha (owns r1b) should be auto-expanded — its round rows appear
    await waitFor(() => expect(screen.getAllByText('Round 1').length).toBeGreaterThanOrEqual(1))

    // Only i1 is expanded: exactly 2 round rows visible
    const roundLabels = screen.getAllByText(/^Round \d+$/)
    expect(roundLabels).toHaveLength(2)
  })
})

// --- Toggle collapse -------------------------------------------------------

describe('Sidebar — toggle expand/collapse', () => {
  it('collapses an expanded idea when chevron is clicked again', async () => {
    const ideas = [makeIdea('i1', 'Toggle Idea')]
    setupLem(ideas, {
      i1: [
        makeRound('r1', 'i1', { roundDepth: 1 }),
        makeRound('r2', 'i1', { roundDepth: 2 }),
      ],
    })
    render(<Sidebar {...baseProps} />)

    await waitFor(() => expect(screen.getByText('Toggle Idea')).toBeInTheDocument())

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /expand rounds/i }))
    await waitFor(() => expect(screen.getByText('Round 1')).toBeInTheDocument())

    // Collapse
    fireEvent.click(screen.getByRole('button', { name: /collapse rounds/i }))
    await waitFor(() => expect(screen.queryByText('Round 1')).not.toBeInTheDocument())
  })
})
