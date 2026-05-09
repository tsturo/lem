type StatTone = 'default' | 'purple' | 'teal'

interface Stat {
  label: string
  value: string
  tone?: StatTone
}

interface CalloutProps {
  stats: Stat[]
}

const TONE_COLOR: Record<StatTone, string> = {
  default: 'var(--t-text)',
  purple:  'var(--t-purple)',
  teal:    'var(--t-teal)',
}

export function Callout({ stats }: CalloutProps) {
  return (
    <div
      style={{
        border:           '1px solid rgba(108, 92, 231, 0.18)',
        borderLeft:       '4px solid var(--t-purple)',
        background:       'linear-gradient(180deg, rgba(108, 92, 231, 0.04), rgba(0, 206, 201, 0.04))',
        borderRadius:     12,
        padding:          '18px 22px',
      }}
    >
      <div
        style={{
          display:             'grid',
          gridTemplateColumns: `repeat(${Math.min(stats.length, 3)}, 1fr)`,
          gap:                 16,
        }}
      >
        {stats.map((stat, i) => {
          const tone = stat.tone ?? 'default'
          return (
            <div key={i} data-stat>
              <div
                style={{
                  fontSize:   11,
                  fontWeight: 500,
                  color:      'var(--t-text-3)',
                  marginBottom: 4,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}
              >
                {stat.label}
              </div>
              <div
                style={{
                  fontSize:   16,
                  fontWeight: 700,
                  color:      TONE_COLOR[tone],
                }}
              >
                {stat.value}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
