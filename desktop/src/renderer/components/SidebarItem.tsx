import type { RunRow, Verdict } from '../../shared/types'
import { StatusDot } from './StatusDot'

const VERDICT_LABEL: Record<Verdict, string> = {
  build:  'Build',
  skip:   'Skip',
  unsure: '?',
}

interface SidebarItemProps {
  ideaId:    string
  ideaTitle: string
  latest:    RunRow | null
  active:    boolean
  onSelect:  (ideaId: string, runId: string) => void
  onSkip:    (ideaId: string) => void
}

export function SidebarItem({ ideaId, ideaTitle, latest, active, onSelect, onSkip }: SidebarItemProps) {
  const verdictText = latest?.verdict ? VERDICT_LABEL[latest.verdict] : null
  const status      = latest?.status ?? 'queued'

  return (
    <div
      style={{
        position:   'relative',
        display:    'flex',
        alignItems: 'center',
        borderRadius: 9,
        overflow:   'hidden',
      }}
    >
      {active && (
        <span
          style={{
            position:     'absolute',
            left:         0,
            top:          0,
            bottom:       0,
            width:        3,
            background:   'linear-gradient(180deg, #6c5ce7, #00cec9)',
            borderRadius: '0 2px 2px 0',
          }}
        />
      )}
      <button
        onClick={() => { if (latest) onSelect(ideaId, latest.runId) }}
        style={{
          flex:        1,
          minWidth:    0,
          display:     'flex',
          alignItems:  'center',
          gap:         8,
          padding:     '8px 10px',
          background:  active ? 'rgba(108,92,231,0.10)' : 'transparent',
          border:      'none',
          borderRadius: 9,
          cursor:      latest ? 'pointer' : 'default',
          textAlign:   'left',
          overflow:    'hidden',
          transition:  'background 0.12s',
        }}
        onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(108,92,231,0.06)' }}
        onMouseLeave={e => { if (!active) e.currentTarget.style.background = active ? 'rgba(108,92,231,0.10)' : 'transparent' }}
      >
        <StatusDot status={status} />
        <span
          style={{
            flex:         1,
            minWidth:     0,
            fontSize:     13,
            fontFamily:   'var(--t-font)',
            fontWeight:   active ? 500 : 400,
            color:        'var(--t-text)',
            overflow:     'hidden',
            textOverflow: 'ellipsis',
            whiteSpace:   'nowrap',
          }}
        >
          {ideaTitle}
        </span>
        {verdictText && (
          <span
            style={{
              fontSize:      10,
              fontFamily:    'var(--t-font)',
              fontWeight:    500,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color:         'var(--t-text-3)',
              flexShrink:    0,
            }}
          >
            {verdictText}
          </span>
        )}
      </button>
      <button
        aria-label="Skip idea"
        onClick={() => onSkip(ideaId)}
        style={{
          flexShrink:   0,
          padding:      '4px 8px',
          background:   'transparent',
          border:       'none',
          borderRadius: 6,
          fontSize:     10,
          fontFamily:   'var(--t-font)',
          color:        'var(--t-text-3)',
          cursor:       'pointer',
          opacity:      0.7,
        }}
        onMouseEnter={e => { e.currentTarget.style.opacity = '1' }}
        onMouseLeave={e => { e.currentTarget.style.opacity = '0.7' }}
      >
        Skip
      </button>
    </div>
  )
}
