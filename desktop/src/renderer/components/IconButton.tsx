import { type ButtonHTMLAttributes } from 'react'

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean
  children: React.ReactNode
}

const ACTIVE_STYLES: React.CSSProperties = {
  background:  'rgba(108, 92, 231, 0.14)',
  borderColor: 'rgba(108, 92, 231, 0.45)',
  color:       'var(--t-purple)',
}

const IDLE_STYLES: React.CSSProperties = {
  background:  'transparent',
  borderColor: 'var(--t-border)',
  color:       'var(--t-text-2)',
}

export function IconButton({ active = false, children, style, ...props }: IconButtonProps) {
  return (
    <button
      data-active={active}
      style={{
        display:        'inline-flex',
        alignItems:     'center',
        justifyContent: 'center',
        width:          32,
        height:         32,
        borderRadius:   9,
        border:         '1px solid',
        cursor:         'pointer',
        transition:     'background 0.18s, border-color 0.18s, color 0.18s',
        outline:        'none',
        fontFamily:     'var(--t-font)',
        ...(active ? ACTIVE_STYLES : IDLE_STYLES),
        ...style,
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
