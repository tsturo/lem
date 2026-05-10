export type TimelineVerdict = 'BUILD' | 'DONT' | 'SKIP' | 'INSUFFICIENT' | 'UNKNOWN'

export type TimelineRound = {
  runId: string
  roundDepth: number
  verdict: TimelineVerdict
  branchLabel?: string | null
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

const BASE_SIZE = 28
const CURRENT_SIZE = Math.round(BASE_SIZE * 1.3)

export function TimelineStrip({ rounds, currentRunId, onRoundSelect }: TimelineStripProps) {
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
