import type { CSSProperties } from 'react'
import type { RunSnapshot } from '../../types/lem-events'
import { StepRail } from '../components/StepRail'
import { PHASE_LABELS, PHASE_TO_SEGMENT, TOTAL_SEGMENTS } from '../lib/phases'
import { AgentCard } from './AgentCard'
import { EarlierSteps } from './EarlierSteps'

interface TheaterProps {
  run: RunSnapshot
  idea: string
  onStop?: () => void
  onOpenWorkspace?: () => void
}

const BTN: CSSProperties = {
  padding:      '7px 14px',
  background:   'var(--t-surface)',
  border:       '1px solid var(--t-border)',
  borderRadius: 'var(--t-radius-sm)',
  fontSize:     13,
  color:        'var(--t-text-2)',
  cursor:       'pointer',
  fontFamily:   'var(--t-font)',
  flexShrink:   0,
}

export function Theater({ run, idea, onStop, onOpenWorkspace }: TheaterProps) {
  const activePhase = run.phases.find(p => p.state === 'active')
  const donePhases  = run.phases.filter(p => p.state === 'done')

  const activeSegment = activePhase != null
    ? (PHASE_TO_SEGMENT[activePhase.id] ?? run.currentPhase)
    : run.currentPhase

  const stepLabel = activePhase
    ? `Step ${activeSegment + 1} of ${TOTAL_SEGMENTS} — ${PHASE_LABELS[activePhase.id] ?? activePhase.id}`
    : undefined

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Topbar */}
      <div
        style={{
          display:      'flex',
          alignItems:   'center',
          gap:          12,
          padding:      '12px 20px',
          borderBottom: '1px solid var(--t-border)',
          background:   'var(--t-bg)',
          flexShrink:   0,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            data-idea-title
            style={{
              fontWeight:    700,
              fontSize:      15,
              color:         'var(--t-text)',
              overflow:      'hidden',
              textOverflow:  'ellipsis',
              whiteSpace:    'nowrap',
            }}
          >
            {idea}
          </div>
          <div style={{ fontSize: 12, color: 'var(--t-text-3)', marginTop: 2 }}>
            {run.eta ? `running · ~${run.eta} remaining` : 'running…'}
          </div>
        </div>
        <button onClick={onStop} style={BTN} data-action="stop">⏸ Stop</button>
        <button onClick={onOpenWorkspace} style={BTN} data-action="workspace">📂 Workspace</button>
      </div>

      {/* Step rail */}
      <div style={{ padding: '14px 20px', flexShrink: 0 }}>
        <StepRail
          total={TOTAL_SEGMENTS}
          active={activeSegment}
          label={stepLabel}
          eta={run.eta}
        />
      </div>

      {/* Theater body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 20px 20px' }}>
        {activePhase && activePhase.roles.length > 0 && (
          <div
            style={{
              display:             'grid',
              gridTemplateColumns: `repeat(${Math.min(activePhase.roles.length, 3)}, 1fr)`,
              gap:                 16,
              marginBottom:        24,
            }}
          >
            {activePhase.roles.map(role => (
              <AgentCard key={role.name} role={role} />
            ))}
          </div>
        )}

        {donePhases.length > 0 && <EarlierSteps phases={donePhases} />}
      </div>
    </div>
  )
}
