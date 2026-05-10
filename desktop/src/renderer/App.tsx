import { useEffect, useRef, useState } from 'react'
import { AppShell } from '@/components/AppShell'
import { BrandMark } from '@/components/BrandMark'
import { FirstRunWizard } from '@/components/FirstRunWizard'
import { Sidebar } from '@/components/Sidebar'
import { Topbar } from '@/components/Topbar'
import { IntakeInput } from '@/screens/IntakeInput'
import { IntakeChat } from '@/screens/IntakeChat'
import { Theater } from '@/screens/Theater'
import { Brief } from '@/screens/Brief'
import type { ChatMessage, RefineRequest, RunRow, Verdict } from '../shared/types'
import type { LogLine, ProgressEvent } from '../types/lem-events'
import type { TimelineRound, TimelineVerdict } from '@/components/TimelineStrip'
import { useSettings } from '@/store/settings'
import { useRuntime } from '@/store/runtime'
import { useLibrary } from '@/store/library'

type ScreenKind = 'empty' | 'intake-input' | 'intake-chat' | 'theater' | 'brief' | 'error'

const MOCK_QUESTIONS = [
  "Who's the primary user — is it you, a small team, or a broader consumer audience?",
  "What's the biggest pain point this solves? What do users do today instead?",
  "Any constraints we should know about — timeline, budget, tech stack, or regulatory concerns?",
]

function ts(): string {
  return new Date().toISOString()
}

function verdictToTimeline(v: Verdict | null): TimelineVerdict {
  if (v === 'build') return 'BUILD'
  if (v === 'skip') return 'DONT'
  if (v === 'unsure') return 'INSUFFICIENT'
  return 'UNKNOWN'
}

function toTimelineRounds(rows: RunRow[]): TimelineRound[] {
  return rows.map(r => ({
    runId:       r.runId,
    roundDepth:  r.roundDepth ?? 1,
    verdict:     verdictToTimeline(r.verdict),
    branchLabel: r.branchLabel ?? null,
    parentRunId: r.parentRunId ?? null,
  }))
}

function rootIdeaFromRounds(rows: RunRow[]): string {
  const root = rows.find(r => (r.roundDepth ?? 1) === 1) ?? rows[0]
  return root?.idea ?? ''
}

interface ConfirmationCardProps {
  idea: string
  onStart: () => void
}

function ConfirmationCard({ idea, onStart }: ConfirmationCardProps) {
  return (
    <div
      data-screen="confirmation"
      style={{
        maxWidth:      560,
        margin:        '0 auto',
        padding:       '48px 32px',
        display:       'flex',
        flexDirection: 'column',
        gap:           24,
      }}
    >
      <span
        style={{
          fontSize:      11,
          fontWeight:    700,
          fontFamily:    'var(--t-font)',
          letterSpacing: '0.10em',
          textTransform: 'uppercase',
          color:         'var(--t-purple)',
        }}
      >
        READY TO GO
      </span>

      <h2
        style={{
          margin:        0,
          fontSize:      28,
          fontWeight:    700,
          fontFamily:    'var(--t-font)',
          letterSpacing: '-0.02em',
          lineHeight:    1.25,
          color:         'var(--t-text)',
        }}
      >
        Ready to analyze?
      </h2>

      <div
        style={{
          background:   'var(--t-surface)',
          border:       '1px solid var(--t-border)',
          borderRadius: 12,
          padding:      '16px 20px',
        }}
      >
        <p
          style={{
            margin:     0,
            fontSize:   16,
            fontFamily: 'var(--t-font)',
            lineHeight: 1.55,
            color:      'var(--t-text)',
            fontStyle:  'italic',
          }}
        >
          "{idea}"
        </p>
      </div>

      <p
        style={{
          margin:     0,
          fontSize:   14,
          fontFamily: 'var(--t-font)',
          lineHeight: 1.6,
          color:      'var(--t-text-2)',
        }}
      >
        Three specialists will weigh in — architect, designer, and market
        analyst. This takes about 15 minutes.
      </p>

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          data-action="start-analysis"
          onClick={onStart}
          style={{
            display:      'inline-flex',
            alignItems:   'center',
            gap:          6,
            padding:      '12px 24px',
            background:   'linear-gradient(135deg, #6c5ce7, #00cec9)',
            color:        '#fff',
            border:       'none',
            borderRadius: 12,
            fontSize:     14,
            fontFamily:   'var(--t-font)',
            fontWeight:   600,
            cursor:       'pointer',
            boxShadow:    'var(--t-shadow-cta)',
            transition:   'transform 0.12s, box-shadow 0.12s',
          }}
          onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)' }}
          onMouseLeave={e => { e.currentTarget.style.transform = '' }}
        >
          Start analysis →
        </button>
      </div>
    </div>
  )
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div
      data-screen="error"
      style={{
        display:        'flex',
        alignItems:     'center',
        justifyContent: 'center',
        height:         '100%',
      }}
    >
      <div
        style={{
          maxWidth:     480,
          padding:      '32px',
          background:   'rgba(255,0,80,0.06)',
          border:       '1px solid rgba(255,0,80,0.20)',
          borderRadius: 14,
          fontFamily:   'var(--t-font)',
          color:        'var(--t-text)',
          textAlign:    'center',
        }}
      >
        <div style={{ fontSize: 28, marginBottom: 12 }}>⚠️</div>
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6 }}>{message}</p>
      </div>
    </div>
  )
}

function RefineErrorToast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div
      data-refine-error
      role="alert"
      style={{
        position:   'fixed',
        bottom:     24,
        left:       '50%',
        transform:  'translateX(-50%)',
        background: 'rgba(200, 40, 40, 0.96)',
        color:      '#fff',
        padding:    '12px 20px',
        borderRadius: 10,
        fontFamily: 'var(--t-font)',
        fontSize:   14,
        display:    'flex',
        alignItems: 'center',
        gap:        12,
        boxShadow:  '0 4px 20px rgba(0,0,0,0.30)',
        zIndex:     100,
        maxWidth:   480,
      }}
    >
      <span>⚠ {message}</span>
      <button
        aria-label="Dismiss error"
        onClick={onDismiss}
        style={{
          background: 'transparent',
          border:     'none',
          color:      '#fff',
          cursor:     'pointer',
          fontSize:   16,
          padding:    0,
          opacity:    0.75,
          lineHeight: 1,
        }}
      >
        ✕
      </button>
    </div>
  )
}

export default function App() {
  const loadSettings = useSettings(s => s.load)
  const [detectionState, setDetectionState] = useState<'pending' | 'found' | 'missing'>('pending')

  const detectClaude = (): void => {
    setDetectionState('pending')
    window.lem.claude.detect().then(path => {
      if (path) {
        useSettings.setState({ claudePath: path })
        setDetectionState('found')
      } else {
        setDetectionState('missing')
      }
    }).catch(() => setDetectionState('missing'))
  }

  useEffect(() => {
    detectClaude()
  }, [])

  const initRun        = useRuntime(s => s.initRun)
  const onPhaseStart   = useRuntime(s => s.onPhaseStart)
  const onPhaseDone    = useRuntime(s => s.onPhaseDone)
  const onPhaseSkipped = useRuntime(s => s.onPhaseSkipped)
  const onRoleDone     = useRuntime(s => s.onRoleDone)
  const failRun        = useRuntime(s => s.failRun)
  const runs           = useRuntime(s => s.runs)
  const activeRunId    = useRuntime(s => s.activeRunId)

  const loadLibrary  = useLibrary(s => s.load)
  const selectRun    = useLibrary(s => s.select)
  const libraryItems = useLibrary(s => s.items)

  const [screen,      setScreen]      = useState<ScreenKind>('intake-input')
  const [activeId,    setActiveId]    = useState<string | undefined>()
  const [ideaText,    setIdeaText]    = useState('')
  const [messages,    setMessages]    = useState<ChatMessage[]>([])
  const [questionIdx, setQuestionIdx] = useState(0)
  const [allAnswered, setAllAnswered] = useState(false)
  const [errorMsg,    setErrorMsg]    = useState('')

  const [currentIdeaId, setCurrentIdeaId] = useState<string | undefined>()
  const [rounds,        setRounds]        = useState<TimelineRound[]>([])
  const [rootIdeaText,  setRootIdeaText]  = useState('')
  const [refineError,   setRefineError]   = useState<string | null>(null)

  const activeRunIdRef    = useRef<string | null>(null)
  const currentIdeaIdRef  = useRef<string | null>(null)

  useEffect(() => {
    activeRunIdRef.current = activeRunId
  }, [activeRunId])

  useEffect(() => {
    currentIdeaIdRef.current = currentIdeaId ?? null
  }, [currentIdeaId])

  useEffect(() => {
    loadSettings()
    loadLibrary()
  }, [loadSettings, loadLibrary])

  useEffect(() => {
    const off = window.lem.run.onEvent((rawEvent) => {
      const runId = activeRunIdRef.current
      if (!runId) return
      const ev = rawEvent as { kind: string } & Record<string, unknown>

      if (ev.kind === 'phase_start' || ev.kind === 'phase_done' || ev.kind === 'phase_skipped') {
        const pev = rawEvent as ProgressEvent
        if (ev.kind === 'phase_start') {
          onPhaseStart(runId, pev)
        } else if (ev.kind === 'phase_done') {
          onPhaseDone(runId, pev)
          if (pev.phase_id === '4') {
            const ideaId = currentIdeaIdRef.current
            void Promise.all([
              loadLibrary(),
              ideaId
                ? window.lem.ideas.getRounds(ideaId).then(rawRounds => {
                    setRounds(toTimelineRounds(rawRounds))
                    setRootIdeaText(rootIdeaFromRounds(rawRounds))
                  }).catch(err => console.error('Failed to reload rounds after refine:', err))
                : Promise.resolve(),
            ]).then(() => setScreen('brief')).catch(() => setScreen('brief'))
          }
        } else {
          onPhaseSkipped(runId, pev)
        }
      } else if (ev.kind === 'run_exit') {
        const run = useRuntime.getState().runs[runId]
        if (run && run.status !== 'completed') {
          failRun(runId)
          setErrorMsg('Analysis stopped unexpectedly. Check logs for details.')
          setScreen('error')
        }
      }
    })
    return off
  }, [onPhaseStart, onPhaseDone, onPhaseSkipped, failRun, loadLibrary])

  useEffect(() => {
    const off = window.lem.run.onLog((logLine: LogLine) => {
      const runId = activeRunIdRef.current
      if (!runId) return
      if (logLine.event === 'worker_done' && logLine.phase_id && logLine.role) {
        onRoleDone(runId, logLine.phase_id, logLine.role, logLine.message ?? '')
      }
    })
    return off
  }, [onRoleDone])

  if (detectionState === 'pending') {
    return (
      <div
        style={{
          display:        'flex',
          alignItems:     'center',
          justifyContent: 'center',
          height:         '100vh',
        }}
      >
        <BrandMark size={48} className="animate-t-pulse" />
      </div>
    )
  }

  if (detectionState === 'missing') {
    return <FirstRunWizard variant="not-found" onRetry={detectClaude} />
  }

  async function handleStartAnalysis() {
    const runId = await window.lem.run.start({ idea: ideaText })
    initRun(runId)
    setScreen('theater')
  }

  function handleSubmitIdea(idea: string) {
    setIdeaText(idea)
    setMessages([{ role: 'assistant', content: MOCK_QUESTIONS[0], timestamp: ts() }])
    setQuestionIdx(0)
    setAllAnswered(false)
    setScreen('intake-chat')
  }

  function handleSend(content: string) {
    const next = questionIdx + 1
    if (next < MOCK_QUESTIONS.length) {
      setMessages(prev => [
        ...prev,
        { role: 'user', content, timestamp: ts() },
        { role: 'assistant', content: MOCK_QUESTIONS[next], timestamp: ts() },
      ])
      setQuestionIdx(next)
    } else {
      setMessages(prev => [...prev, { role: 'user', content, timestamp: ts() }])
      setAllAnswered(true)
    }
  }

  function handleNewIdea() {
    setScreen('intake-input')
    setActiveId(undefined)
    setAllAnswered(false)
  }

  async function handleSelectIdeaRound(ideaId: string, runId: string) {
    setCurrentIdeaId(ideaId)
    selectRun(runId)
    setActiveId(runId)
    const runtimeRun = runs[runId]
    if (runtimeRun && runtimeRun.status === 'running') {
      setScreen('theater')
      return
    }
    const item = libraryItems.find(r => r.runId === runId)
    if (item?.status === 'completed') {
      try {
        const rawRounds = await window.lem.ideas.getRounds(ideaId)
        setRounds(toTimelineRounds(rawRounds))
        setRootIdeaText(rootIdeaFromRounds(rawRounds))
      } catch (err) {
        console.error('Failed to load rounds for idea:', err)
      }
      setScreen('brief')
    } else if (item?.status === 'running') {
      setScreen('theater')
    } else {
      setScreen('empty')
    }
  }

  function handleRoundSelect(runId: string) {
    setActiveId(runId)
  }

  async function handleContinue(req: Omit<RefineRequest, 'idea' | 'parentRunId'>) {
    setRefineError(null)
    try {
      const idea: string = rootIdeaText || ideaText
      const refineReq: RefineRequest = {
        idea,
        parentRunId: activeId,
        branchLabel: '',
        contextText: req.contextText,
      }
      const { runId } = await window.lem.run.refine(refineReq)
      initRun(runId)
      setActiveId(runId)
      setScreen('theater')
    } catch (err) {
      setRefineError(
        err instanceof Error ? err.message : 'Failed to start refinement. Please try again.',
      )
    }
  }

  async function handleBranch(req: Omit<RefineRequest, 'idea' | 'parentRunId'>) {
    setRefineError(null)
    try {
      const idea: string = rootIdeaText || ideaText
      const refineReq: RefineRequest = {
        idea,
        parentRunId: activeId,
        ...(req.branchLabel ? { branchLabel: req.branchLabel } : {}),
        contextText: req.contextText,
      }
      const { runId } = await window.lem.run.refine(refineReq)
      initRun(runId)
      setActiveId(runId)
      setScreen('theater')
    } catch (err) {
      setRefineError(
        err instanceof Error ? err.message : 'Failed to start branch. Please try again.',
      )
    }
  }

  function handleSkipIdea(_ideaId: string) {
    // cascade logic is out of scope for this task
  }

  function handleStop() {
    if (activeRunId) {
      window.lem.run.cancel(activeRunId)
    }
  }

  const topbarTitle = (() => {
    switch (screen) {
      case 'intake-input': return 'New Idea'
      case 'intake-chat':  return ideaText || 'Refining…'
      case 'theater':      return rootIdeaText || ideaText || 'Analyzing…'
      case 'brief': {
        const item = libraryItems.find(r => r.runId === activeId)
        return item?.idea ?? 'Analysis'
      }
      case 'error':        return 'Error'
      default:             return 'lem'
    }
  })()

  function renderScreen() {
    switch (screen) {
      case 'intake-input':
        return <IntakeInput onSubmit={handleSubmitIdea} />

      case 'intake-chat':
        if (allAnswered) {
          return (
            <ConfirmationCard
              idea={ideaText}
              onStart={handleStartAnalysis}
            />
          )
        }
        return (
          <IntakeChat
            ideaTitle={ideaText}
            messages={messages}
            questionIndex={questionIdx}
            totalQuestions={MOCK_QUESTIONS.length}
            onSend={handleSend}
          />
        )

      case 'theater': {
        const runId = activeRunId ?? activeId
        const run   = runId ? runs[runId] : undefined
        if (!run) return null
        return (
          <Theater
            run={run}
            idea={rootIdeaText || ideaText}
            onStop={handleStop}
          />
        )
      }

      case 'error':
        return <ErrorBanner message={errorMsg} />

      case 'brief': {
        const item = libraryItems.find(r => r.runId === activeId)
        if (!item) return null
        const verdictLabel = item.verdict === 'build' ? 'Build'
          : item.verdict === 'skip' ? "Don't build"
          : item.verdict === 'unsure' ? 'Insufficient info'
          : '—'
        return (
          <Brief
            idea={item.idea}
            verdict={item.verdict ?? 'unsure'}
            workspacePath={item.workspacePath}
            tabs={[
              { id: 'exec', label: 'Executive summary', content: '' },
              { id: 'mvp', label: 'MVP plan', content: '' },
              { id: 'risks', label: 'Risks & rejected', content: '' },
            ]}
            calloutStats={{ recommendation: verdictLabel, confidence: '—', firstMilestone: '—' }}
            signalPills={[]}
            meta={{ version: '0.1.0', phases: 11, specialists: 3, date: item.createdAt.split('T')[0] ?? '—' }}
            rounds={rounds}
            currentRunId={activeId ?? ''}
            onRoundSelect={handleRoundSelect}
            onContinue={handleContinue}
            onBranch={handleBranch}
          />
        )
      }

      case 'empty':
      default: {
        const item = libraryItems.find(r => r.runId === activeId)
        return (
          <div
            style={{
              display:        'flex',
              alignItems:     'center',
              justifyContent: 'center',
              height:         '100%',
              fontSize:       14,
              fontFamily:     'var(--t-font)',
              color:          'var(--t-text-3)',
            }}
          >
            {item ? `${item.idea} — completed` : 'Select a run or start a new idea'}
          </div>
        )
      }
    }
  }

  const chatActive    = screen === 'intake-chat' && !allAnswered
  const theaterActive = screen === 'theater'
  const briefActive   = screen === 'brief'

  return (
    <AppShell
      sidebar={
        <Sidebar
          activeId={activeId}
          onNewIdea={handleNewIdea}
          onSelectIdeaRound={handleSelectIdeaRound}
          onSkipIdea={handleSkipIdea}
        />
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {!theaterActive && !briefActive && <Topbar title={topbarTitle} />}
        <div
          style={{
            flex:      1,
            minHeight: 0,
            overflowY: chatActive || theaterActive || briefActive ? 'hidden' : 'auto',
          }}
        >
          {renderScreen()}
        </div>
      </div>
      {refineError && (
        <RefineErrorToast
          message={refineError}
          onDismiss={() => setRefineError(null)}
        />
      )}
    </AppShell>
  )
}
