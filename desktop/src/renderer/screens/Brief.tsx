import { useState, useEffect } from 'react'
import type { Verdict, RefineRequest } from '../../shared/types'
import { VerdictPill } from '../components/VerdictPill'
import { Callout } from '../components/Callout'
import { MarkdownBody } from '../lib/markdown'
import { TimelineStrip, type TimelineRound } from '../components/TimelineStrip'
import { RefineAgainButton } from '../components/RefineAgainButton'
import { RefineModal } from '../components/RefineModal'

export interface BriefTab {
  id: string
  label: string
  count?: number
  content: string
}

export interface BriefCalloutStats {
  recommendation: string
  confidence: string
  firstMilestone: string
}

export interface BriefMeta {
  version: string
  phases: number
  specialists: number
  date: string
}

export interface BriefProps {
  idea: string
  verdict: Verdict
  tabs: BriefTab[]
  calloutStats: BriefCalloutStats
  signalPills: string[]
  meta: BriefMeta
  rounds: TimelineRound[]
  currentRunId: string
  onRoundSelect: (runId: string) => void
  onContinue: (req: Omit<RefineRequest, 'idea' | 'parentRunId'>) => void
  onBranch: (req: Omit<RefineRequest, 'idea' | 'parentRunId'>) => void
  workspacePath?: string
}

type ModalState = { mode: 'continue' | 'branch' } | null

function DisabledActionButton({ label }: { label: string }) {
  return (
    <button
      disabled
      title="Coming soon"
      aria-label={label}
      style={{
        display:     'inline-flex',
        alignItems:  'center',
        gap:         4,
        padding:     '8px 12px',
        background:  'transparent',
        color:       'var(--t-text-3)',
        border:      '1px solid var(--t-border)',
        borderRadius: 10,
        fontSize:    13,
        fontFamily:  'var(--t-font)',
        cursor:      'not-allowed',
        opacity:     0.6,
      }}
    >
      {label}
    </button>
  )
}

function TabButton({
  tab,
  active,
  onClick,
}: {
  tab: BriefTab
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      data-tab={tab.id}
      data-active={active}
      onClick={onClick}
      style={{
        display:           'inline-flex',
        alignItems:        'center',
        gap:               6,
        padding:           '14px 4px',
        marginRight:       20,
        background:        'none',
        border:            'none',
        borderBottom:      '2px solid transparent',
        backgroundImage:   active ? 'linear-gradient(135deg, #6c5ce7, #00cec9)' : 'none',
        backgroundRepeat:  'no-repeat',
        backgroundPosition: 'bottom',
        backgroundSize:    active ? '100% 2px' : '0 2px',
        cursor:            'pointer',
        fontFamily:        'var(--t-font)',
        fontSize:          14,
        fontWeight:        active ? 600 : 400,
        color:             active ? 'var(--t-text)' : 'var(--t-text-2)',
        transition:        'color 0.18s',
        outline:           'none',
      }}
      onFocus={e => {
        e.currentTarget.style.boxShadow = '0 0 0 3px rgba(108, 92, 231, 0.15)'
      }}
      onBlur={e => {
        e.currentTarget.style.boxShadow = ''
      }}
    >
      {tab.label}
      {tab.count !== undefined && (
        <span
          style={{
            display:        'inline-flex',
            alignItems:     'center',
            justifyContent: 'center',
            padding:        '1px 6px',
            background:     'var(--t-surface)',
            border:         '1px solid var(--t-border)',
            borderRadius:   100,
            fontSize:       11,
            fontWeight:     500,
            color:          'var(--t-text-3)',
          }}
        >
          {tab.count}
        </span>
      )}
    </button>
  )
}

function SignalPill({ label }: { label: string }) {
  return (
    <span
      style={{
        display:      'inline-flex',
        alignItems:   'center',
        padding:      '4px 10px',
        background:   'var(--t-surface)',
        border:       '1px solid var(--t-border)',
        borderRadius: 100,
        fontSize:     12,
        fontFamily:   'var(--t-font)',
        color:        'var(--t-text-2)',
      }}
    >
      {label}
    </span>
  )
}

export function Brief({
  idea,
  verdict,
  tabs: tabsProp,
  calloutStats: calloutStatsProp,
  signalPills,
  meta,
  rounds,
  currentRunId,
  onRoundSelect,
  onContinue,
  onBranch,
  workspacePath,
}: BriefProps) {
  const [tabs, setTabs] = useState<BriefTab[]>(tabsProp)
  const [calloutStats, setCalloutStats] = useState<BriefCalloutStats>(calloutStatsProp)
  const [activeTab, setActiveTab] = useState(tabsProp[0]?.id ?? '')
  const [modalState, setModalState] = useState<ModalState>(null)

  useEffect(() => {
    if (!workspacePath) return
    window.lem.workspace.readBrief(workspacePath).then(data => {
      setTabs([
        {
          id:      'exec',
          label:   'Executive summary',
          content: data.deliverables.executiveSummary ?? '',
        },
        {
          id:      'mvp',
          label:   'MVP plan',
          content: data.deliverables.mvpPlan ?? '',
        },
        {
          id:      'risks',
          label:   'Risks & rejected',
          content: data.deliverables.risksAndRejectedPaths ?? '',
        },
      ])
      setCalloutStats({
        recommendation: data.verdict ?? calloutStatsProp.recommendation,
        confidence:     data.confidence ?? calloutStatsProp.confidence,
        firstMilestone: data.firstMilestone ?? calloutStatsProp.firstMilestone,
      })
    })
  }, [workspacePath])

  const activeContent = tabs.find(t => t.id === activeTab)?.content ?? ''
  const currentRound  = rounds.find(r => r.runId === currentRunId)
  const parentRoundDepth  = currentRound?.roundDepth ?? 1
  const parentBranchLabel = currentRound?.branchLabel ?? null

  function handleModalSubmit(req: Omit<RefineRequest, 'idea' | 'parentRunId'>) {
    if (modalState?.mode === 'continue') {
      onContinue(req)
    } else if (modalState?.mode === 'branch') {
      onBranch(req)
    }
    setModalState(null)
  }

  return (
    <div
      data-brief
      style={{
        display:       'flex',
        flexDirection: 'column',
        height:        '100%',
        background:    'var(--t-bg)',
      }}
    >
      {/* Topbar */}
      <div
        data-topbar
        style={{
          display:      'flex',
          alignItems:   'center',
          gap:          12,
          padding:      '18px 32px',
          borderBottom: '1px solid var(--t-border)',
        }}
      >
        <div style={{ flex: 1 }}>
          <span
            style={{
              fontFamily:    'var(--t-font)',
              fontWeight:    700,
              fontSize:      19,
              letterSpacing: '-0.01em',
              color:         'var(--t-text)',
            }}
          >
            {idea}
          </span>
        </div>
        <VerdictPill verdict={verdict} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <DisabledActionButton label="↗ Share" />
          <DisabledActionButton label="⤓ PDF" />
          <RefineAgainButton
            onContinue={() => setModalState({ mode: 'continue' })}
            onBranch={() => setModalState({ mode: 'branch' })}
          />
        </div>
      </div>

      {/* Timeline strip */}
      {rounds.length > 0 && (
        <div
          data-timeline-wrapper
          style={{
            padding:      '14px 32px 12px',
            borderBottom: '1px solid var(--t-border)',
          }}
        >
          <TimelineStrip
            rounds={rounds}
            currentRunId={currentRunId}
            onRoundSelect={onRoundSelect}
          />
        </div>
      )}

      {/* Tab strip */}
      <div
        data-tab-strip
        style={{
          display:      'flex',
          alignItems:   'center',
          padding:      '0 32px',
          borderBottom: '1px solid var(--t-border)',
        }}
      >
        {tabs.map(tab => (
          <TabButton
            key={tab.id}
            tab={tab}
            active={tab.id === activeTab}
            onClick={() => setActiveTab(tab.id)}
          />
        ))}
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '32px' }}>
        <div style={{ maxWidth: 720, margin: '0 auto' }}>
          <Callout
            stats={[
              { label: 'Recommendation', value: calloutStats.recommendation, tone: 'purple' },
              { label: 'Confidence',      value: calloutStats.confidence },
              { label: 'First milestone', value: calloutStats.firstMilestone },
            ]}
          />

          {signalPills.length > 0 && (
            <div
              data-signal-pills
              style={{
                display:      'flex',
                flexWrap:     'wrap',
                gap:          8,
                marginTop:    20,
                marginBottom: 8,
              }}
            >
              {signalPills.map((pill, i) => (
                <SignalPill key={i} label={pill} />
              ))}
            </div>
          )}

          <div style={{ marginTop: 24 }}>
            <MarkdownBody content={activeContent} />
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        data-footer
        style={{
          padding:    '12px 32px',
          borderTop:  '1px solid var(--t-border)',
          fontSize:   13,
          fontFamily: 'var(--t-font)',
          color:      'var(--t-text-3)',
        }}
      >
        Generated by lem {meta.version} · {meta.phases} phases · {meta.specialists} specialists · {meta.date}
      </div>

      <RefineModal
        mode={modalState?.mode ?? 'continue'}
        open={modalState !== null}
        onClose={() => setModalState(null)}
        onSubmit={handleModalSubmit}
        parentRoundDepth={parentRoundDepth}
        parentIdeaTitle={idea}
        parentBranchLabel={parentBranchLabel}
      />
    </div>
  )
}
