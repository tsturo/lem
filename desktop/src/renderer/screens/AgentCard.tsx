import { useEffect, useRef, useState } from 'react'
import type { RoleSnapshot } from '../../types/lem-events'
import { ROLE_META } from '../lib/roles'
import { formatDuration } from '../lib/format'

interface AgentCardProps {
  role: RoleSnapshot
  phaseDuration?: number
}

const ROLE_TONE_BG: Record<string, string> = {
  purple: 'rgba(108, 92, 231, 0.12)',
  teal:   'rgba(0, 206, 201, 0.14)',
  navy:   'rgba(30, 60, 114, 0.08)',
}

export function AgentCard({ role, phaseDuration = 0 }: AgentCardProps) {
  const [elapsed, setElapsed] = useState(phaseDuration)
  const initialOffsetRef = useRef(phaseDuration)
  const meta = ROLE_META[role.name] ?? { icon: '🤖', tone: 'purple', label: role.name }
  const cardBg = ROLE_TONE_BG[meta.tone] ?? 'var(--t-card-bg)'

  useEffect(() => {
    if (role.state !== 'thinking') {
      setElapsed(0)
      return
    }
    initialOffsetRef.current = phaseDuration
    setElapsed(phaseDuration)
    const mountTime = Date.now()
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - mountTime) / 1000) + initialOffsetRef.current)
    }, 1000)
    return () => clearInterval(id)
  }, [role.state]) // phaseDuration intentionally excluded — captured by ref on state entry

  return (
    <div
      data-role={role.name}
      style={{
        background:   cardBg,
        border:       '1px solid var(--t-border)',
        borderRadius: 14,
        overflow:     'hidden',
        boxShadow:    'var(--t-shadow-card)',
      }}
    >
      {/* Head */}
      <div
        style={{
          display:      'flex',
          alignItems:   'center',
          gap:          8,
          padding:      '12px 18px',
          borderBottom: '1px solid var(--t-border)',
        }}
      >
        <span style={{ fontSize: 20 }} data-icon>{meta.icon}</span>
        <span style={{ flex: 1, fontWeight: 600, fontSize: 14, color: 'var(--t-text)' }}>
          {meta.label}
        </span>
        <span
          data-status={role.state}
          style={{
            fontSize:     12,
            fontWeight:   500,
            color:        role.state === 'done' ? 'var(--t-purple)' : 'var(--t-text-3)',
            background:   role.state === 'done'
              ? 'rgba(108,92,231,0.10)'
              : 'var(--t-surface)',
            padding:      '3px 9px',
            borderRadius: 100,
          }}
        >
          {role.state === 'done' ? 'done' : 'thinking'}
        </span>
      </div>

      {/* Body */}
      <div
        style={{
          padding:    18,
          minHeight:  200,
          fontSize:   14,
          lineHeight: 1.55,
          color:      'var(--t-text-2)',
        }}
      >
        {role.state === 'thinking' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <span style={{ fontSize: 12, color: 'var(--t-text-3)' }} data-timer>
              thinking... {formatDuration(elapsed)}
            </span>
            <div className="animate-t-bounce" style={{ display: 'flex', gap: 5, paddingTop: 4 }}>
              {[0, 1, 2].map(i => (
                <span
                  key={i}
                  style={{
                    display:      'inline-block',
                    width:        8,
                    height:       8,
                    borderRadius: '50%',
                    background:   'var(--t-purple)',
                  }}
                />
              ))}
            </div>
          </div>
        ) : (
          <p style={{ margin: 0 }}>{role.output ?? ''}</p>
        )}
      </div>

      {/* Foot */}
      <div
        style={{
          padding:    '10px 18px',
          borderTop:  '1px solid var(--t-border)',
          fontSize:   13,
          color:      'var(--t-purple)',
          cursor:     'pointer',
        }}
        data-foot
      >
        Show full output →
      </div>
    </div>
  )
}
