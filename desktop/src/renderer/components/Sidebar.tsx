import { useEffect, useState } from 'react'
import type { Idea, RunRow, RunGroup, RunStatus } from '../../shared/types'
import { StatusDot } from './StatusDot'

const GROUP_LABEL: Record<RunGroup, string> = {
  active:  'Active',
  done:    'Done',
  archive: 'Archive',
}

const GROUP_ORDER: RunGroup[] = ['active', 'done', 'archive']

const VERDICT_LABEL: Record<string, string> = {
  build: 'Build', skip: 'Skip', unsure: '?',
}

interface IdeaRow {
  idea:   Idea
  latest: RunRow | null
  rounds: RunRow[]
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

function countBranchLeaves(rounds: RunRow[]): number {
  const parentSet = new Set(
    rounds.map(r => r.parentRunId).filter((id): id is string => id != null),
  )
  const leaves = rounds.filter(r => !parentSet.has(r.runId))
  const childCount = new Map<string, number>()
  for (const r of rounds) {
    if (r.parentRunId != null) {
      childCount.set(r.parentRunId, (childCount.get(r.parentRunId) ?? 0) + 1)
    }
  }
  return leaves.filter(
    r => r.parentRunId != null && (childCount.get(r.parentRunId) ?? 0) > 1,
  ).length
}

interface SidebarRoundRowProps {
  round:    RunRow
  isActive: boolean
  ideaId:   string
  onSelect: (ideaId: string, runId: string) => void
}

function SidebarRoundRow({ round, isActive, ideaId, onSelect }: SidebarRoundRowProps) {
  return (
    <button
      onClick={() => onSelect(ideaId, round.runId)}
      style={{
        display:      'flex',
        alignItems:   'center',
        gap:          6,
        width:        '100%',
        padding:      '5px 10px 5px 10px',
        background:   isActive ? 'rgba(108,92,231,0.10)' : 'rgba(0,0,0,0.03)',
        border:       'none',
        borderRadius: 7,
        cursor:       'pointer',
        textAlign:    'left',
        transition:   'background 0.12s',
      }}
      onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'rgba(108,92,231,0.06)' }}
      onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'rgba(0,0,0,0.03)' }}
    >
      <StatusDot status={round.status} />
      <span style={{ fontSize: 11, fontFamily: 'var(--t-font)', color: isActive ? 'var(--t-text)' : 'var(--t-text-2)', fontWeight: isActive ? 500 : 400 }}>
        Round {round.roundDepth ?? 1}
      </span>
      {round.branchLabel != null && round.branchLabel !== '' && (
        <span style={{ fontSize: 10, fontFamily: 'var(--t-font)', color: 'var(--t-text-3)', fontStyle: 'italic', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {round.branchLabel}
        </span>
      )}
      {round.verdict != null && (
        <span style={{ marginLeft: 'auto', fontSize: 10, fontFamily: 'var(--t-font)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--t-text-3)', flexShrink: 0 }}>
          {VERDICT_LABEL[round.verdict]}
        </span>
      )}
    </button>
  )
}

interface SidebarProps {
  activeId?:           string
  onNewIdea:           () => void
  onSelectIdeaRound:   (ideaId: string, runId: string) => void
  onSelectRound?:      (ideaId: string, runId: string) => void
  onSkipIdea:          (ideaId: string) => void
}

export function Sidebar({
  activeId, onNewIdea, onSelectIdeaRound, onSelectRound, onSkipIdea,
}: SidebarProps) {
  const [rows,        setRows]        = useState<IdeaRow[]>([])
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    async function load() {
      const ideas = await window.lem.ideas.list()
      const resolved = await Promise.all(
        ideas.map(async idea => {
          const rounds = await window.lem.ideas.getRounds(idea.id)
          return { idea, latest: pickLatestRound(rounds), rounds }
        }),
      )
      setRows(resolved)
      if (activeId) {
        const owner = resolved.find(r => r.rounds.some(rnd => rnd.runId === activeId))
        if (owner) setExpandedIds(new Set([owner.idea.id]))
      }
    }
    void load()
  }, [])

  function toggleExpand(ideaId: string) {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(ideaId)) next.delete(ideaId)
      else next.add(ideaId)
      return next
    })
  }

  function handleRoundSelect(ideaId: string, runId: string) {
    ;(onSelectRound ?? onSelectIdeaRound)(ideaId, runId)
  }

  const byGroup: Partial<Record<RunGroup, IdeaRow[]>> = {}
  for (const row of rows) {
    const group = ideaGroup(row.latest?.status)
    if (!byGroup[group]) byGroup[group] = []
    byGroup[group]!.push(row)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '10px 8px', gap: 4 }}>
      <button
        onClick={onNewIdea}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          width: '100%', padding: '10px 0',
          background: 'linear-gradient(135deg, #6c5ce7, #00cec9)', color: '#ffffff',
          border: 'none', borderRadius: 12, fontSize: 13, fontFamily: 'var(--t-font)',
          fontWeight: 600, cursor: 'pointer', boxShadow: 'var(--t-shadow-cta)',
          transition: 'transform 0.12s, box-shadow 0.12s', marginBottom: 4,
        }}
        onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)' }}
        onMouseLeave={e => { e.currentTarget.style.transform = '' }}
      >
        + New idea
      </button>

      {rows.length === 0 ? (
        <div style={{ padding: '20px 10px', textAlign: 'center' }}>
          <p style={{ margin: 0, fontSize: 13, fontFamily: 'var(--t-font)', color: 'var(--t-text-3)', lineHeight: 1.5 }}>
            No ideas yet
          </p>
        </div>
      ) : (
        GROUP_ORDER.map(group => {
          const groupItems = byGroup[group]
          if (!groupItems?.length) return null
          return (
            <section key={group}>
              <div style={{ fontSize: 10, fontFamily: 'var(--t-font)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.10em', color: 'var(--t-text-3)', padding: '10px 10px 6px' }}>
                {GROUP_LABEL[group]}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {groupItems.map(({ idea, latest, rounds }) => {
                  const expanded     = expandedIds.has(idea.id)
                  const hasMultiple  = rounds.length >= 2
                  const branchLeaves = hasMultiple ? countBranchLeaves(rounds) : 0
                  const ideaActive   = rounds.some(r => r.runId === activeId)
                  const verdictText  = latest?.verdict != null ? VERDICT_LABEL[latest.verdict] : null
                  const status       = latest?.status ?? 'queued'
                  const sortedRounds = [...rounds].sort((a, b) => {
                    const da = a.roundDepth ?? 1, db = b.roundDepth ?? 1
                    if (da !== db) return da - db
                    return a.createdAt < b.createdAt ? -1 : 1
                  })

                  return (
                    <div key={idea.id} style={{ display: 'flex', flexDirection: 'column' }}>
                      <div style={{ position: 'relative', display: 'flex', alignItems: 'center', borderRadius: 9 }}>
                        {ideaActive && (
                          <span style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 3, background: 'linear-gradient(180deg, #6c5ce7, #00cec9)', borderRadius: '0 2px 2px 0', zIndex: 1 }} />
                        )}
                        {hasMultiple && (
                          <button
                            aria-label={expanded ? 'Collapse rounds' : 'Expand rounds'}
                            onClick={() => toggleExpand(idea.id)}
                            style={{ padding: '8px 4px 8px 8px', background: 'transparent', border: 'none', color: 'var(--t-text-3)', cursor: 'pointer', fontSize: 8, lineHeight: 1, flexShrink: 0 }}
                          >
                            {expanded ? '▼' : '▶'}
                          </button>
                        )}
                        <button
                          onClick={() => { if (latest) onSelectIdeaRound(idea.id, latest.runId) }}
                          style={{
                            flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: 8,
                            padding: hasMultiple ? '8px 8px 8px 4px' : '8px 10px',
                            background: ideaActive ? 'rgba(108,92,231,0.10)' : 'transparent',
                            border: 'none', borderRadius: 9, cursor: latest ? 'pointer' : 'default',
                            textAlign: 'left', overflow: 'hidden', transition: 'background 0.12s',
                          }}
                          onMouseEnter={e => { if (!ideaActive) e.currentTarget.style.background = 'rgba(108,92,231,0.06)' }}
                          onMouseLeave={e => { if (!ideaActive) e.currentTarget.style.background = 'transparent' }}
                        >
                          <StatusDot status={status} />
                          <span style={{ flex: 1, minWidth: 0, fontSize: 13, fontFamily: 'var(--t-font)', fontWeight: ideaActive ? 500 : 400, color: 'var(--t-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {idea.title}
                          </span>
                          <span style={{ display: 'flex', alignItems: 'center', gap: 3, flexShrink: 0 }}>
                            {verdictText != null && (
                              <span style={{ fontSize: 10, fontFamily: 'var(--t-font)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--t-text-3)' }}>
                                {verdictText}
                              </span>
                            )}
                            {hasMultiple && (
                              <span style={{ fontSize: 10, fontFamily: 'var(--t-font)', color: 'var(--t-text-3)', opacity: 0.6 }}>
                                ·{rounds.length}
                              </span>
                            )}
                            {branchLeaves > 0 && (
                              <span style={{ fontSize: 10, fontFamily: 'var(--t-font)', color: 'var(--t-text-3)', opacity: 0.6 }}>
                                ⑂{branchLeaves}
                              </span>
                            )}
                          </span>
                        </button>
                        <button
                          aria-label="Skip idea"
                          onClick={() => onSkipIdea(idea.id)}
                          style={{ flexShrink: 0, padding: '4px 8px', background: 'transparent', border: 'none', borderRadius: 6, fontSize: 10, fontFamily: 'var(--t-font)', color: 'var(--t-text-3)', cursor: 'pointer', opacity: 0.7 }}
                          onMouseEnter={e => { e.currentTarget.style.opacity = '1' }}
                          onMouseLeave={e => { e.currentTarget.style.opacity = '0.7' }}
                        >
                          Skip
                        </button>
                      </div>
                      {expanded && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 1, paddingLeft: 18, paddingBottom: 4 }}>
                          {sortedRounds.map(round => (
                            <SidebarRoundRow
                              key={round.runId}
                              round={round}
                              isActive={round.runId === activeId}
                              ideaId={idea.id}
                              onSelect={handleRoundSelect}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </section>
          )
        })
      )}
    </div>
  )
}
