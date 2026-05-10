import { useEffect, useState } from 'react'
import type { Idea, RunRow, RunGroup, RunStatus } from '../../shared/types'
import { SidebarItem } from './SidebarItem'

const GROUP_LABEL: Record<RunGroup, string> = {
  active:  'Active',
  done:    'Done',
  archive: 'Archive',
}

const GROUP_ORDER: RunGroup[] = ['active', 'done', 'archive']

interface IdeaRow {
  idea:   Idea
  latest: RunRow | null
}

function pickLatestRound(rounds: RunRow[]): RunRow | null {
  if (rounds.length === 0) return null
  return rounds.reduce((best, r) => {
    const bd = best.roundDepth ?? 0
    const rd = r.roundDepth ?? 0
    if (rd > bd) return r
    if (rd === bd && r.createdAt > best.createdAt) return r
    return best
  })
}

function ideaGroup(status: RunStatus | undefined): RunGroup {
  if (status === 'running') return 'active'
  if (status === 'archived') return 'archive'
  return 'done'
}

interface SidebarProps {
  activeId?:         string
  onNewIdea:         () => void
  onSelectIdeaRound: (ideaId: string, runId: string) => void
  onSkipIdea:        (ideaId: string) => void
}

export function Sidebar({ activeId, onNewIdea, onSelectIdeaRound, onSkipIdea }: SidebarProps) {
  const [rows, setRows] = useState<IdeaRow[]>([])

  useEffect(() => {
    async function load() {
      const ideas = await window.lem.ideas.list()
      const resolved = await Promise.all(
        ideas.map(async idea => {
          const rounds = await window.lem.ideas.getRounds(idea.id)
          return { idea, latest: pickLatestRound(rounds) }
        }),
      )
      setRows(resolved)
    }
    void load()
  }, [])

  const byGroup: Partial<Record<RunGroup, IdeaRow[]>> = {}
  for (const row of rows) {
    const group = ideaGroup(row.latest?.status)
    if (!byGroup[group]) byGroup[group] = []
    byGroup[group]!.push(row)
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
        onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)' }}
        onMouseLeave={e => { e.currentTarget.style.transform = '' }}
      >
        + New idea
      </button>

      {rows.length === 0 ? (
        <div style={{ padding: '20px 10px', textAlign: 'center' }}>
          <p
            style={{
              margin:     0,
              fontSize:   13,
              fontFamily: 'var(--t-font)',
              color:      'var(--t-text-3)',
              lineHeight: 1.5,
            }}
          >
            No ideas yet
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
                {groupItems.map(({ idea, latest }) => (
                  <SidebarItem
                    key={idea.id}
                    ideaId={idea.id}
                    ideaTitle={idea.title}
                    latest={latest}
                    active={latest?.runId === activeId}
                    onSelect={onSelectIdeaRound}
                    onSkip={onSkipIdea}
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
