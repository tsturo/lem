import { useState } from 'react'
import type { PhaseSnapshot } from '../../types/lem-events'
import { PHASE_LABELS } from '../lib/phases'
import { AgentCard } from './AgentCard'

interface EarlierStepsProps {
  phases: PhaseSnapshot[]
}

function formatDuration(s?: number): string {
  if (s == null) return ''
  if (s < 60) return `${Math.round(s)}s`
  const m = Math.floor(s / 60)
  const rem = Math.round(s % 60)
  return `${m}m ${rem}s`
}

export function EarlierSteps({ phases }: EarlierStepsProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  if (phases.length === 0) return null

  function toggle(id: string) {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div
        style={{
          fontSize:      12,
          fontWeight:    600,
          color:         'var(--t-text-3)',
          marginBottom:  4,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}
      >
        Earlier steps
      </div>
      {phases.map(phase => {
        const isOpen = expanded.has(phase.id)
        const label = PHASE_LABELS[phase.id] ?? `Phase ${phase.id}`
        const duration = formatDuration(phase.durationS)
        return (
          <div key={phase.id} data-phase={phase.id}>
            <button
              onClick={() => toggle(phase.id)}
              style={{
                display:      'flex',
                alignItems:   'center',
                gap:          10,
                width:        '100%',
                padding:      '10px 14px',
                background:   isOpen ? 'var(--t-surface)' : 'transparent',
                border:       '1px solid var(--t-border)',
                borderRadius: isOpen ? '10px 10px 0 0' : 10,
                cursor:       'pointer',
                textAlign:    'left',
                transition:   'background 0.18s',
                fontFamily:   'var(--t-font)',
              }}
            >
              <span style={{ color: 'var(--t-purple)', fontWeight: 700, flexShrink: 0 }}>✓</span>
              <span style={{ flex: 1, fontSize: 13, color: 'var(--t-text)', fontWeight: 500 }}>
                {label}
              </span>
              {phase.summary && (
                <span
                  style={{
                    fontSize:     12,
                    color:        'var(--t-text-3)',
                    maxWidth:     260,
                    overflow:     'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace:   'nowrap',
                  }}
                >
                  {phase.summary}
                </span>
              )}
              {duration && (
                <span style={{ fontSize: 12, color: 'var(--t-text-3)', flexShrink: 0 }}>
                  {duration}
                </span>
              )}
              <span style={{ color: 'var(--t-text-3)', fontSize: 12, flexShrink: 0 }}>
                {isOpen ? '▲' : '▼'}
              </span>
            </button>

            {isOpen && phase.roles.length > 0 && (
              <div
                style={{
                  display:             'grid',
                  gridTemplateColumns: `repeat(${Math.min(phase.roles.length, 3)}, 1fr)`,
                  gap:                 12,
                  padding:             12,
                  background:          'var(--t-surface)',
                  border:              '1px solid var(--t-border)',
                  borderTop:           'none',
                  borderRadius:        '0 0 10px 10px',
                }}
              >
                {phase.roles.map(role => (
                  <AgentCard key={role.name} role={role} />
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
