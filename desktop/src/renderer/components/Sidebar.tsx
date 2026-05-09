import type { RunGroup, RunRow } from '../../shared/types'
import { SidebarItem } from './SidebarItem'

const GROUP_LABEL: Record<RunGroup, string> = {
  active:  'Active',
  done:    'Done',
  archive: 'Archive',
}

const GROUP_ORDER: RunGroup[] = ['active', 'done', 'archive']

interface SidebarProps {
  items:      RunRow[]
  activeId?:  string
  onNewIdea:  () => void
  onSelect:   (runId: string) => void
}

export function Sidebar({ items, activeId, onNewIdea, onSelect }: SidebarProps) {
  const byGroup: Partial<Record<RunGroup, RunRow[]>> = {}
  for (const item of items) {
    if (!byGroup[item.group]) byGroup[item.group] = []
    byGroup[item.group]!.push(item)
  }

  return (
    <div
      style={{
        display:       'flex',
        flexDirection: 'column',
        height:        '100%',
        padding:       '10px 8px',
        gap:           4,
      }}
    >
      <button
        onClick={onNewIdea}
        style={{
          display:        'flex',
          alignItems:     'center',
          justifyContent: 'center',
          gap:            6,
          width:          '100%',
          padding:        '10px 0',
          background:     'linear-gradient(135deg, #6c5ce7, #00cec9)',
          color:          '#ffffff',
          border:         'none',
          borderRadius:   12,
          fontSize:       13,
          fontFamily:     'var(--t-font)',
          fontWeight:     600,
          cursor:         'pointer',
          boxShadow:      'var(--t-shadow-cta)',
          transition:     'transform 0.12s, box-shadow 0.12s',
          marginBottom:   4,
        }}
        onMouseEnter={e => {
          e.currentTarget.style.transform = 'translateY(-1px)'
        }}
        onMouseLeave={e => {
          e.currentTarget.style.transform = ''
        }}
      >
        + New idea
      </button>

      {items.length === 0 ? (
        <div
          style={{
            padding:   '20px 10px',
            textAlign: 'center',
          }}
        >
          <p
            style={{
              margin:     0,
              fontSize:   13,
              fontFamily: 'var(--t-font)',
              color:      'var(--t-text-3)',
              lineHeight: 1.5,
            }}
          >
            Your ideas will appear here
          </p>
        </div>
      ) : (
        GROUP_ORDER.map(group => {
          const groupItems = byGroup[group]
          if (!groupItems || groupItems.length === 0) return null
          return (
            <section key={group}>
              <div
                style={{
                  fontSize:      10,
                  fontFamily:    'var(--t-font)',
                  fontWeight:    500,
                  textTransform: 'uppercase',
                  letterSpacing: '0.10em',
                  color:         'var(--t-text-3)',
                  padding:       '10px 10px 6px',
                }}
              >
                {GROUP_LABEL[group]}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {groupItems.map(item => (
                  <SidebarItem
                    key={item.runId}
                    item={item}
                    active={item.runId === activeId}
                    onSelect={onSelect}
                  />
                ))}
              </div>
            </section>
          )
        })
      )}
    </div>
  )
}
