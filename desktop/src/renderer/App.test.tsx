/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom" />
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import App from './App'
import type { BriefProps } from '@/screens/Brief'
import type { RefineRequest } from '../shared/types'

// ---------------------------------------------------------------------------
// Component mocks — keep them minimal; we only care about the App-level glue
// ---------------------------------------------------------------------------

vi.mock('@/screens/Brief', () => ({
  Brief: ({ onContinue, onBranch, onRoundSelect, currentRunId, rounds }: BriefProps) => (
    <div data-testid="brief-screen">
      <span data-testid="current-run-id">{currentRunId}</span>
      <span data-testid="rounds-count">{rounds.length}</span>
      <button
        data-testid="btn-continue"
        onClick={() => onContinue({ contextText: 'some context' })}
      >
        Continue
      </button>
      <button
        data-testid="btn-branch-labeled"
        onClick={() => onBranch({ branchLabel: 'mobile-first', contextText: 'try mobile' })}
      >
        Branch labeled
      </button>
      <button
        data-testid="btn-branch-empty"
        onClick={() => onBranch({ contextText: 'try something' })}
      >
        Branch unlabeled
      </button>
      <button
        data-testid="btn-round-select"
        onClick={() => onRoundSelect('r-prev')}
      >
        Round select
      </button>
    </div>
  ),
}))

vi.mock('@/screens/Theater', () => ({
  Theater: () => <div data-testid="theater-screen">Theater</div>,
}))

vi.mock('@/screens/IntakeInput', () => ({
  IntakeInput: () => <div data-testid="intake-screen">Intake</div>,
}))

vi.mock('@/screens/IntakeChat', () => ({
  IntakeChat: () => <div data-testid="intake-chat-screen">IntakeChat</div>,
}))

vi.mock('@/components/Sidebar', () => ({
  Sidebar: ({
    onSelectIdeaRound,
  }: {
    onSelectIdeaRound: (ideaId: string, runId: string) => void
  }) => (
    <button
      data-testid="sidebar-select"
      onClick={() => onSelectIdeaRound('idea-1', 'r-1')}
    >
      Select Idea
    </button>
  ),
}))

vi.mock('@/components/Topbar', () => ({
  Topbar: ({ title }: { title: string }) => <div data-testid="topbar">{title}</div>,
}))

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

function makeLibraryItem(runId = 'r-1') {
  return {
    runId,
    idea:          'My test idea',
    verdict:       'build' as const,
    status:        'completed' as const,
    workspacePath: '/tmp/workspace',
    createdAt:     '2024-01-01T00:00:00Z',
    updatedAt:     '2024-01-01T01:00:00Z',
  }
}

function makeRunRow(runId = 'r-1', ideaId = 'idea-1') {
  return {
    runId,
    idea:          'My test idea',
    verdict:       'build' as const,
    status:        'completed' as const,
    group:         'done' as const,
    workspacePath: '/tmp/workspace',
    createdAt:     '2024-01-01T00:00:00Z',
    updatedAt:     '2024-01-01T01:00:00Z',
    ideaId,
    roundDepth:    1,
    parentRunId:   null,
    branchLabel:   null,
  }
}

function setupLem(
  refineMock: ReturnType<typeof vi.fn> = vi.fn().mockResolvedValue({ runId: 'r-new' }),
) {
  vi.stubGlobal('lem', {
    claude: {
      detect: vi.fn().mockResolvedValue('/usr/local/bin/claude'),
    },
    settings: {
      get: vi.fn().mockResolvedValue({ theme: 'auto' }),
      set: vi.fn().mockResolvedValue(undefined),
    },
    library: {
      list: vi.fn().mockResolvedValue([makeLibraryItem(), makeLibraryItem('r-prev')]),
    },
    ideas: {
      list:      vi.fn().mockResolvedValue([{ id: 'idea-1', title: 'My test idea', createdAt: 1_700_000_000 }]),
      getRounds: vi.fn().mockResolvedValue([makeRunRow('r-prev'), makeRunRow()]),
      getDag:    vi.fn().mockResolvedValue([]),
      rename:    vi.fn().mockResolvedValue(undefined),
    },
    run: {
      start:          vi.fn().mockResolvedValue('r-start'),
      cancel:         vi.fn().mockResolvedValue(undefined),
      onEvent:        vi.fn().mockReturnValue(() => {}),
      onLog:          vi.fn().mockReturnValue(() => {}),
      refine:         refineMock,
      setBranchLabel: vi.fn().mockResolvedValue(undefined),
    },
    workspace: {
      readBrief: vi.fn().mockResolvedValue({ deliverables: {} }),
    },
    shell: {
      openExternal: vi.fn().mockResolvedValue(undefined),
    },
  })
  return refineMock
}

async function renderAndNavigateToBrief(
  refineMock: ReturnType<typeof vi.fn> = vi.fn().mockResolvedValue({ runId: 'r-new' }),
) {
  setupLem(refineMock)
  render(<App />)
  await waitFor(() => expect(screen.getByTestId('sidebar-select')).toBeInTheDocument())
  fireEvent.click(screen.getByTestId('sidebar-select'))
  await waitFor(() => expect(screen.getByTestId('brief-screen')).toBeInTheDocument())
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

// ---------------------------------------------------------------------------
// Continue flow
// ---------------------------------------------------------------------------

describe('App — continue flow', () => {
  it('calls window.lem.run.refine with correct payload including branchLabel=""', async () => {
    const refineMock = vi.fn().mockResolvedValue({ runId: 'r-new' })
    await renderAndNavigateToBrief(refineMock)

    fireEvent.click(screen.getByTestId('btn-continue'))

    await waitFor(() => expect(refineMock).toHaveBeenCalledOnce())
    expect(refineMock).toHaveBeenCalledWith(
      expect.objectContaining<Partial<RefineRequest>>({
        idea:        'My test idea',
        parentRunId: 'r-1',
        branchLabel: '',
        contextText: 'some context',
      }),
    )
  })

  it('navigates to theater after window.lem.run.refine resolves', async () => {
    const refineMock = vi.fn().mockResolvedValue({ runId: 'r-new' })
    await renderAndNavigateToBrief(refineMock)

    fireEvent.click(screen.getByTestId('btn-continue'))

    await waitFor(() => expect(screen.getByTestId('theater-screen')).toBeInTheDocument())
  })
})

// ---------------------------------------------------------------------------
// Branch flow (labeled)
// ---------------------------------------------------------------------------

describe('App — branch flow (labeled)', () => {
  it('calls window.lem.run.refine with user-provided branchLabel', async () => {
    const refineMock = vi.fn().mockResolvedValue({ runId: 'r-new' })
    await renderAndNavigateToBrief(refineMock)

    fireEvent.click(screen.getByTestId('btn-branch-labeled'))

    await waitFor(() => expect(refineMock).toHaveBeenCalledOnce())
    expect(refineMock).toHaveBeenCalledWith(
      expect.objectContaining<Partial<RefineRequest>>({
        idea:        'My test idea',
        parentRunId: 'r-1',
        branchLabel: 'mobile-first',
        contextText: 'try mobile',
      }),
    )
  })

  it('navigates to theater after branched refine resolves', async () => {
    await renderAndNavigateToBrief()

    fireEvent.click(screen.getByTestId('btn-branch-labeled'))

    await waitFor(() => expect(screen.getByTestId('theater-screen')).toBeInTheDocument())
  })
})

// ---------------------------------------------------------------------------
// Branch flow (empty / omitted label)
// ---------------------------------------------------------------------------

describe('App — branch flow (unlabeled)', () => {
  it('omits branchLabel key when modal label is blank', async () => {
    const refineMock = vi.fn().mockResolvedValue({ runId: 'r-new' })
    await renderAndNavigateToBrief(refineMock)

    fireEvent.click(screen.getByTestId('btn-branch-empty'))

    await waitFor(() => expect(refineMock).toHaveBeenCalled())
    const payload: RefineRequest = refineMock.mock.calls[0][0]
    expect('branchLabel' in payload).toBe(false)
    expect(payload.contextText).toBe('try something')
  })
})

// ---------------------------------------------------------------------------
// Error flow
// ---------------------------------------------------------------------------

describe('App — refine error handling', () => {
  it('shows error toast when window.lem.run.refine rejects', async () => {
    const refineMock = vi.fn().mockRejectedValue(new Error('Claude not authenticated'))
    await renderAndNavigateToBrief(refineMock)

    fireEvent.click(screen.getByTestId('btn-continue'))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByRole('alert')).toHaveTextContent('Claude not authenticated')
  })

  it('keeps brief screen visible (does not crash) when refine throws', async () => {
    const refineMock = vi.fn().mockRejectedValue(new Error('network error'))
    await renderAndNavigateToBrief(refineMock)

    fireEvent.click(screen.getByTestId('btn-continue'))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(screen.getByTestId('brief-screen')).toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Round select navigation
// ---------------------------------------------------------------------------

describe('App — round select (onRoundSelect)', () => {
  it('updates currentRunId passed to Brief when a round pill is clicked', async () => {
    await renderAndNavigateToBrief()

    expect(screen.getByTestId('current-run-id')).toHaveTextContent('r-1')

    fireEvent.click(screen.getByTestId('btn-round-select'))

    await waitFor(() =>
      expect(screen.getByTestId('current-run-id')).toHaveTextContent('r-prev'),
    )
  })
})
