interface StepRailProps {
  total: number
  active: number
  label?: string
  eta?: string
}

type SegmentState = 'done' | 'active' | 'queued'

function segmentState(index: number, active: number): SegmentState {
  if (index < active)  return 'done'
  if (index === active) return 'active'
  return 'queued'
}

const SEGMENT_BG: Record<SegmentState, string> = {
  done:   'linear-gradient(135deg, #6c5ce7, #00cec9)',
  active: 'linear-gradient(90deg, #6c5ce7 0%, #00cec9 60%, var(--t-border) 60%)',
  queued: 'var(--t-border)',
}

export default function StepRail({ total, active, label, eta }: StepRailProps) {
  return (
    <div>
      {(label || eta) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 12, color: 'var(--t-text-3)' }}>
          {label && <span>{label}</span>}
          {eta   && <span>{eta}</span>}
        </div>
      )}
      <div style={{ display: 'flex', gap: 4 }}>
        {Array.from({ length: total }, (_, i) => {
          const state = segmentState(i, active)
          return (
            <div
              key={i}
              data-state={state}
              style={{
                flex:         1,
                height:       5,
                borderRadius: 3,
                background:   SEGMENT_BG[state],
                position:     'relative',
              }}
            >
              {state === 'active' && (
                <div
                  style={{
                    position:     'absolute',
                    left:         '60%',
                    top:          -3,
                    width:        11,
                    height:       11,
                    borderRadius: '50%',
                    background:   'var(--t-purple)',
                    animation:    't-pulse 1.4s ease-in-out infinite',
                    transform:    'translateX(-50%)',
                  }}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
