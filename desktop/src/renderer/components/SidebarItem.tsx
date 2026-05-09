import type { RunRow, Verdict } from '../../shared/types'
import { StatusDot } from './StatusDot'

const VERDICT_LABEL: Record<Verdict, string> = {
  build:  'Build',
  skip:   'Skip',
  unsure: '?',
}

interface SidebarItemProps {
  item:     RunRow
  active:   boolean
  onSelect: (runId: string) => void
}

export function SidebarItem({ item, active, onSelect }: SidebarItemProps) {
  const verdictText = item.verdict ? VERDICT_LABEL[item.verdict] : null

  return (
    <button
      onClick={() => onSelect(item.runId)}
      style={{
        position:       'relative',
        display:        'flex',
        alignItems:     'center',
        gap:            8,
        width:          '100%',
        padding:        '8px 10px',
        background:     active ? 'rgba(108,92,231,0.10)' : 'transparent',
        border:         'none',
        borderRadius:   9,
        cursor:         'pointer',
        textAlign:      'left',
        overflow:       'hidden',
        transition:     'background 0.12s',
      }}
      onMouseEnter={e => {
        if (!active) e.currentTarget.style.background = 'rgba(108,92,231,0.06)'
      }}
      onMouseLeave={e => {
        if (!active) e.currentTarget.style.background = 'transparent'
      }}
    >
      {active && (
        <span
          style={{
            position:   'absolute',
            left:       0,
            top:        0,
            bottom:     0,
            width:      3,
            background: 'linear-gradient(180deg, #6c5ce7, #00cec9)',
            borderRadius: '0 2px 2px 0',
          }}
        />
      )}
      <StatusDot status={item.status} />
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
        {item.idea}
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
  )
}
