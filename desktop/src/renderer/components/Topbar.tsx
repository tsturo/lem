import type { ReactNode } from 'react'
import { IconButton } from './IconButton'

interface TopbarProps {
  title: string
  meta?: string
  rightSlot?: ReactNode
  onStop?: () => void
  onWorkspace?: () => void
  onToggleDetails?: () => void
  detailsActive?: boolean
}

export function Topbar({
  title,
  meta,
  rightSlot,
  onStop,
  onWorkspace,
  onToggleDetails,
  detailsActive = false,
}: TopbarProps) {
  return (
    <header
      data-topbar
      style={{
        display:       'flex',
        alignItems:    'flex-start',
        justifyContent: 'space-between',
        padding:       '18px 32px 14px',
        borderBottom:  '1px solid var(--t-border)',
        background:    'var(--t-bg)',
        gap:           16,
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <h1
          data-title
          style={{
            margin:     0,
            fontSize:   18,
            fontWeight: 700,
            fontFamily: 'var(--t-font)',
            color:      'var(--t-text)',
            lineHeight: 1.3,
            overflow:    'hidden',
            textOverflow: 'ellipsis',
            whiteSpace:  'nowrap',
          }}
        >
          {title}
        </h1>
        {meta && (
          <p
            data-meta
            style={{
              margin:     '3px 0 0',
              fontSize:   12,
              fontFamily: 'var(--t-font)',
              color:      'var(--t-text-2)',
              lineHeight: 1.4,
            }}
          >
            {meta}
          </p>
        )}
      </div>

      <div
        style={{
          display:    'flex',
          alignItems: 'center',
          gap:        10,
          flexShrink: 0,
        }}
      >
        {rightSlot && <div data-right-slot>{rightSlot}</div>}

        <div
          data-action-buttons
          style={{ display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <IconButton
            data-action="stop"
            title="Stop"
            onClick={onStop}
            aria-label="Stop"
          >
            ⏸
          </IconButton>

          <IconButton
            data-action="workspace"
            title="Open workspace"
            onClick={onWorkspace}
            aria-label="Open workspace"
          >
            📂
          </IconButton>

          <IconButton
            data-action="details"
            title="Details"
            onClick={onToggleDetails}
            active={detailsActive}
            aria-label="Toggle details"
            style={{ display: 'none' }}
          >
            ⚙
          </IconButton>
        </div>
      </div>
    </header>
  )
}
