import type { Verdict } from '../../shared/types'

interface VerdictConfig {
  glyph: string
  label: string
  glyphBg: string
  glyphColor: string
  pillBg: string
  textColor: string
}

const VERDICT_CONFIG: Record<Verdict, VerdictConfig> = {
  build: {
    glyph:      '✓',
    label:      'Build',
    glyphBg:    'linear-gradient(135deg, #6c5ce7, #00cec9)',
    glyphColor: '#ffffff',
    pillBg:     'rgba(108, 92, 231, 0.10)',
    textColor:  'var(--t-purple)',
  },
  skip: {
    glyph:      '✗',
    label:      'Skip',
    glyphBg:    'var(--t-status-error)',
    glyphColor: '#ffffff',
    pillBg:     'rgba(217, 112, 112, 0.10)',
    textColor:  'var(--t-status-error)',
  },
  unsure: {
    glyph:      '?',
    label:      'Insufficient info',
    glyphBg:    'var(--t-teal)',
    glyphColor: '#ffffff',
    pillBg:     'rgba(0, 206, 201, 0.12)',
    textColor:  'var(--t-teal)',
  },
}

interface VerdictPillProps {
  verdict: Verdict
}

export function VerdictPill({ verdict }: VerdictPillProps) {
  const cfg = VERDICT_CONFIG[verdict]
  return (
    <span
      data-verdict={verdict}
      style={{
        display:       'inline-flex',
        alignItems:    'center',
        gap:           6,
        padding:       '8px 14px',
        borderRadius:  100,
        background:    cfg.pillBg,
        fontFamily:    'var(--t-font)',
        fontSize:      13,
        fontWeight:    700,
        letterSpacing: '0.04em',
        color:         cfg.textColor,
      }}
    >
      <span
        data-glyph
        style={{
          display:        'inline-flex',
          alignItems:     'center',
          justifyContent: 'center',
          width:          18,
          height:         18,
          borderRadius:   '50%',
          background:     cfg.glyphBg,
          color:          cfg.glyphColor,
          fontSize:       11,
          fontWeight:     700,
          flexShrink:     0,
        }}
      >
        {cfg.glyph}
      </span>
      <span data-label>{cfg.label}</span>
    </span>
  )
}
