import { useEffect, useState } from 'react'
import { AppShell } from '@/components/AppShell'
import { BrandMark } from '@/components/BrandMark'
import { Sidebar } from '@/components/Sidebar'
import { Topbar } from '@/components/Topbar'
import { IntakeInput } from '@/screens/IntakeInput'
import { IntakeChat } from '@/screens/IntakeChat'
import type { ChatMessage, RunRow } from '../shared/types'
import { useSettings } from '@/store/settings'

type ScreenKind = 'empty' | 'intake-input' | 'intake-chat' | 'placeholder'

const MOCK_LIBRARY: RunRow[] = [
  {
    runId: 'run-1',
    idea: 'Dog walking app',
    verdict: 'build',
    status: 'completed',
    group: 'done',
    createdAt: '2026-05-08T10:00:00Z',
    updatedAt: '2026-05-08T14:30:00Z',
  },
  {
    runId: 'run-2',
    idea: 'Parent calendar',
    verdict: 'unsure',
    status: 'completed',
    group: 'done',
    createdAt: '2026-05-07T09:00:00Z',
    updatedAt: '2026-05-07T13:45:00Z',
  },
  {
    runId: 'run-3',
    idea: 'GitHub Actions AI',
    verdict: null,
    status: 'running',
    group: 'active',
    createdAt: '2026-05-09T08:00:00Z',
    updatedAt: '2026-05-09T08:15:00Z',
  },
  {
    runId: 'run-4',
    idea: 'Tofu pricing tracker',
    verdict: 'skip',
    status: 'completed',
    group: 'done',
    createdAt: '2026-05-06T11:00:00Z',
    updatedAt: '2026-05-06T15:20:00Z',
  },
]

const MOCK_QUESTIONS = [
  "Who's the primary user — is it you, a small team, or a broader consumer audience?",
  "What's the biggest pain point this solves? What do users do today instead?",
  "Any constraints we should know about — timeline, budget, tech stack, or regulatory concerns?",
]

function ts(): string {
  return new Date().toISOString()
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
          margin:      0,
          fontSize:    28,
          fontWeight:  700,
          fontFamily:  'var(--t-font)',
          letterSpacing: '-0.02em',
          lineHeight:  1.25,
          color:       'var(--t-text)',
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
            display:        'inline-flex',
            alignItems:     'center',
            gap:            6,
            padding:        '12px 24px',
            background:     'linear-gradient(135deg, #6c5ce7, #00cec9)',
            color:          '#fff',
            border:         'none',
            borderRadius:   12,
            fontSize:       14,
            fontFamily:     'var(--t-font)',
            fontWeight:     600,
            cursor:         'pointer',
            boxShadow:      'var(--t-shadow-cta)',
            transition:     'transform 0.12s, box-shadow 0.12s',
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

export default function App() {
  const claudePath = useSettings(s => s.claudePath)
  const load       = useSettings(s => s.load)

  const [screen,       setScreen]       = useState<ScreenKind>('intake-input')
  const [activeId,     setActiveId]     = useState<string | undefined>()
  const [ideaText,     setIdeaText]     = useState('')
  const [messages,     setMessages]     = useState<ChatMessage[]>([])
  const [questionIdx,  setQuestionIdx]  = useState(0)
  const [allAnswered,  setAllAnswered]  = useState(false)

  useEffect(() => { load() }, [load])

  if (claudePath === undefined) {
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

  function handleSelect(runId: string) {
    setActiveId(runId)
    setScreen('placeholder')
  }

  const topbarTitle = (() => {
    switch (screen) {
      case 'intake-input':  return 'New Idea'
      case 'intake-chat':   return ideaText || 'Refining…'
      case 'placeholder':   return MOCK_LIBRARY.find(r => r.runId === activeId)?.idea ?? 'Run'
      default:              return 'lem'
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
              onStart={() => { /* analysis launch not yet wired */ }}
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

      case 'placeholder': {
        const item = MOCK_LIBRARY.find(r => r.runId === activeId)
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
            Run view coming soon — {item?.idea ?? ''}
          </div>
        )
      }

      default:
        return null
    }
  }

  // IntakeChat manages its own scrolling with height: 100%; other screens need an overflow container.
  const chatActive = screen === 'intake-chat' && !allAnswered

  return (
    <AppShell
      sidebar={
        <Sidebar
          items={MOCK_LIBRARY}
          activeId={activeId}
          onNewIdea={handleNewIdea}
          onSelect={handleSelect}
        />
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Topbar title={topbarTitle} />
        <div
          style={{
            flex:       1,
            minHeight:  0,
            overflowY:  chatActive ? 'hidden' : 'auto',
          }}
        >
          {renderScreen()}
        </div>
      </div>
    </AppShell>
  )
}
