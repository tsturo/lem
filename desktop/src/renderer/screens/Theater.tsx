import type { RunSnapshot } from '../../types/lem-events'
import { StepRail } from '../components/StepRail'
import { Topbar } from '../components/Topbar'
import { PHASE_LABELS, PHASE_TO_SEGMENT, TOTAL_SEGMENTS } from '../lib/phases'
import { AgentCard } from './AgentCard'
import { EarlierSteps } from './EarlierSteps'

interface TheaterProps {
  run: RunSnapshot
  idea: string
  onStop?: () => void
  onOpenWorkspace?: () => void
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

  const meta = run.eta ? `running · ~${run.eta} remaining` : 'running…'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <Topbar
        title={idea}
        meta={meta}
        onStop={onStop}
        onWorkspace={onOpenWorkspace}
      />

      <div style={{ padding: '14px 20px', flexShrink: 0 }}>
        <StepRail
          total={TOTAL_SEGMENTS}
          active={activeSegment}
          label={stepLabel}
          eta={run.eta}
        />
      </div>

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
