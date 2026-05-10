/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom" />
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { Sidebar } from './Sidebar'
import type { Idea, RunRow } from '../../shared/types'

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
