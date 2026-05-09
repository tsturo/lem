import { type ButtonHTMLAttributes } from 'react'

type ChipTone = 'default' | 'purple' | 'teal'

interface ChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  tone?: ChipTone
}

const TONE_STYLES: Record<ChipTone, React.CSSProperties> = {
  default: {
    background:  'var(--t-bg)',
    borderColor: 'var(--t-border)',
    color:       'var(--t-text-2)',
  },
  purple: {
    background:  'rgba(108, 92, 231, 0.10)',
    borderColor: 'rgba(108, 92, 231, 0.25)',
    color:       'var(--t-purple)',
  },
  teal: {
    background:  'rgba(0, 206, 201, 0.10)',
    borderColor: 'rgba(0, 206, 201, 0.25)',
    color:       'var(--t-teal)',
  },
}

export default function Chip({ tone = 'default', children, style, ...props }: ChipProps) {
  return (
    <button
      data-tone={tone}
      style={{
        display:        'inline-flex',
        alignItems:     'center',
        gap:            6,
        padding:        '6px 12px',
        border:         '1px solid',
        borderRadius:   'var(--t-radius-pill)',
        fontSize:       12,
        fontFamily:     'var(--t-font)',
        cursor:         'pointer',
        transition:     'border-color 0.18s, color 0.18s',
        outline:        'none',
        ...TONE_STYLES[tone],
        ...style,
      }}
      onMouseEnter={e => {
        const el = e.currentTarget
        el.style.borderColor = tone === 'teal' ? 'var(--t-teal)' : 'var(--t-purple)'
        if (tone === 'default') el.style.color = 'var(--t-purple)'
      }}
      onMouseLeave={e => {
        const el = e.currentTarget
        el.style.borderColor = TONE_STYLES[tone].borderColor as string
        el.style.color       = TONE_STYLES[tone].color as string
      }}
      onFocus={e => {
        e.currentTarget.style.boxShadow = '0 0 0 3px rgba(108, 92, 231, 0.15)'
      }}
      onBlur={e => {
        e.currentTarget.style.boxShadow = ''
      }}
      {...props}
    >
      {children}
    </button>
  )
}
