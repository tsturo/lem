export type TimelineVerdict = 'BUILD' | 'DONT' | 'SKIP' | 'INSUFFICIENT' | 'UNKNOWN'

export type TimelineRound = {
  runId: string
  roundDepth: number
  verdict: TimelineVerdict
  branchLabel?: string | null
  parentRunId?: string | null
}

export type TimelineStripProps = {
  rounds: TimelineRound[]
  currentRunId: string
  onRoundSelect: (runId: string) => void
}

type VerdictPalette = {
  bg: string
  color: string
}

const VERDICT_PALETTE: Record<TimelineVerdict, VerdictPalette> = {
  BUILD: {
    bg:    'rgba(108, 92, 231, 0.15)',
    color: 'var(--t-purple)',
  },
  DONT: {
    bg:    'rgba(217, 112, 112, 0.15)',
    color: 'var(--t-status-error)',
  },
  SKIP: {
    bg:    'rgba(217, 112, 112, 0.15)',
    color: 'var(--t-status-error)',
  },
  INSUFFICIENT: {
    bg:    'rgba(0, 206, 201, 0.12)',
    color: 'var(--t-teal)',
  },
  UNKNOWN: {
    bg:    'rgba(200, 200, 212, 0.12)',
    color: 'var(--t-status-muted)',
  },
}

const BASE_SIZE    = 28
const CURRENT_SIZE = Math.round(BASE_SIZE * 1.3)

function detectBranches(rounds: TimelineRound[]): boolean {
  const childCount = new Map<string | null, number>()
  for (const r of rounds) {
    if (r.parentRunId === undefined) continue
    const key = r.parentRunId ?? null
    childCount.set(key, (childCount.get(key) ?? 0) + 1)
  }
  return [...childCount.values()].some(n => n >= 2)
}

function buildThreads(rounds: TimelineRound[]): TimelineRound[][] {
  const childrenOf = new Map<string, TimelineRound[]>()
  const roots: TimelineRound[] = []
  const runIdSet = new Set(rounds.map(r => r.runId))

  rounds.forEach(r => childrenOf.set(r.runId, []))
  rounds.forEach(r => {
    const pid = r.parentRunId
    if (pid && runIdSet.has(pid)) {
      childrenOf.get(pid)!.push(r)
    } else {
      roots.push(r)
    }
  })

  const threads: TimelineRound[][] = []
  const dfs = (r: TimelineRound, path: TimelineRound[]) => {
    const next = [...path, r]
    const children = childrenOf.get(r.runId) ?? []
    if (!children.length) threads.push(next)
    else children.forEach(c => dfs(c, next))
  }
  roots.forEach(r => dfs(r, []))
  return threads
}

function mainThreadIndex(threads: TimelineRound[][]): number {
  return threads.reduce((best, t, i) => {
    const depth     = t[t.length - 1].roundDepth
    const bestDepth = threads[best][threads[best].length - 1].roundDepth
    return depth > bestDepth ? i : best
  }, 0)
}

function sharedPrefixLen(a: TimelineRound[], b: TimelineRound[]): number {
  let k = 0
  while (k < a.length && k < b.length && a[k].runId === b[k].runId) k++
  return k
}

function formatVerdict(v: TimelineVerdict): string {
  return v === 'DONT' ? "DON'T" : v
}

export function TimelineStrip({ rounds, currentRunId, onRoundSelect }: TimelineStripProps) {
  if (!detectBranches(rounds)) {
    return (
      <div
        data-timeline-strip
        style={{
          display:    'inline-flex',
          alignItems: 'center',
          userSelect: 'none',
        }}
      >
        {rounds.map((round, index) => {
          const isCurrent = round.runId === currentRunId
          const palette   = VERDICT_PALETTE[round.verdict]
          const size      = isCurrent ? CURRENT_SIZE : BASE_SIZE

          return (
            <div
              key={round.runId}
              style={{ display: 'inline-flex', alignItems: 'center' }}
            >
              {index > 0 && (
                <div
                  data-connector
                  style={{
                    width:      16,
                    height:     1,
                    background: palette.color,
                    opacity:    0.25,
                    flexShrink: 0,
                  }}
                />
              )}
              <button
                data-pill
                data-round={round.roundDepth}
                data-verdict={round.verdict}
                data-current={isCurrent}
                onClick={() => onRoundSelect(round.runId)}
                style={{
                  display:        'inline-flex',
                  alignItems:     'center',
                  justifyContent: 'center',
                  width:          size,
                  height:         size,
                  borderRadius:   '50%',
                  background:     palette.bg,
                  color:          palette.color,
                  fontSize:       isCurrent ? 13 : 11,
                  fontWeight:     700,
                  fontFamily:     'var(--t-font)',
                  border:         isCurrent
                                    ? `2px solid ${palette.color}`
                                    : '2px solid transparent',
                  cursor:         'pointer',
                  flexShrink:     0,
                  padding:        0,
                }}
              >
                {round.roundDepth}
              </button>
            </div>
          )
        })}
      </div>
    )
  }

  const allThreads = buildThreads(rounds)
  const mainIdx    = mainThreadIndex(allThreads)
  const mainThread = allThreads[mainIdx]
  const ordered    = [mainThread, ...allThreads.filter((_, i) => i !== mainIdx)]

  return (
    <div
      data-timeline-strip
      style={{
        display:       'inline-flex',
        flexDirection: 'column',
        gap:           7,
        userSelect:    'none',
        overflowY:     'auto',
        maxHeight:     120,
      }}
    >
      {ordered.map((thread, threadIndex) => {
        const isMain    = threadIndex === 0
        const prefixLen = isMain ? 0 : sharedPrefixLen(mainThread, thread)
        const lastRound = thread[thread.length - 1]

        return (
          <div
            key={lastRound.runId}
            data-timeline-row={isMain ? 'main' : 'branch'}
            style={{ display: 'inline-flex', alignItems: 'center' }}
          >
            {thread.map((round, index) => {
              const isPlaceholder = !isMain && index < prefixLen
              const isFirstReal   = !isMain && index === prefixLen && prefixLen > 0
              const palette       = VERDICT_PALETTE[round.verdict]
              const isCurrent     = round.runId === currentRunId
              const size          = isCurrent ? CURRENT_SIZE : BASE_SIZE

              return (
                <div
                  key={round.runId}
                  style={{ display: 'inline-flex', alignItems: 'center' }}
                >
                  {index > 0 && (
                    isFirstReal ? (
                      <div
                        data-l-connector
                        style={{
                          width:        16,
                          height:       BASE_SIZE,
                          borderLeft:   '1px solid var(--t-border-subtle)',
                          borderBottom: '1px solid var(--t-border-subtle)',
                          opacity:      0.5,
                          flexShrink:   0,
                          alignSelf:    'flex-end',
                        }}
                      />
                    ) : isPlaceholder ? (
                      <div style={{ width: 16, height: 1, flexShrink: 0, visibility: 'hidden' }} />
                    ) : (
                      <div
                        data-connector
                        style={{
                          width:      16,
                          height:     1,
                          background: palette.color,
                          opacity:    0.25,
                          flexShrink: 0,
                        }}
                      />
                    )
                  )}
                  {isPlaceholder ? (
                    <div
                      data-pill
                      data-round={round.roundDepth}
                      data-verdict={round.verdict}
                      data-current={false}
                      data-placeholder={true}
                      style={{
                        width:        BASE_SIZE,
                        height:       BASE_SIZE,
                        borderRadius: '50%',
                        flexShrink:   0,
                        visibility:   'hidden',
                      }}
                    />
                  ) : (
                    <button
                      data-pill
                      data-round={round.roundDepth}
                      data-verdict={round.verdict}
                      data-current={isCurrent}
                      onClick={() => onRoundSelect(round.runId)}
                      style={{
                        display:        'inline-flex',
                        alignItems:     'center',
                        justifyContent: 'center',
                        width:          size,
                        height:         size,
                        borderRadius:   '50%',
                        background:     palette.bg,
                        color:          palette.color,
                        fontSize:       isCurrent ? 13 : 11,
                        fontWeight:     700,
                        fontFamily:     'var(--t-font)',
                        border:         isCurrent
                                          ? `2px solid ${palette.color}`
                                          : '2px solid transparent',
                        cursor:         'pointer',
                        flexShrink:     0,
                        padding:        0,
                      }}
                    >
                      {round.roundDepth}
                    </button>
                  )}
                </div>
              )
            })}
            {lastRound.branchLabel != null && (
              <span
                data-branch-label
                style={{
                  marginLeft: 8,
                  fontSize:   11,
                  color:      'var(--t-status-muted)',
                  fontFamily: 'var(--t-font)',
                  whiteSpace: 'nowrap',
                }}
              >
                {lastRound.branchLabel} · {formatVerdict(lastRound.verdict)}
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}
