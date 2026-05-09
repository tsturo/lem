import { type ButtonHTMLAttributes } from 'react'

interface PrimaryButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode
}

export default function PrimaryButton({ children, disabled, style, ...props }: PrimaryButtonProps) {
  return (
    <button
      disabled={disabled}
      style={{
        display:        'inline-flex',
        alignItems:     'center',
        justifyContent: 'center',
        gap:            6,
        padding:        '10px 20px',
        background:     'linear-gradient(135deg, #6c5ce7, #00cec9)',
        color:          '#ffffff',
        border:         'none',
        borderRadius:   12,
        fontSize:       14,
        fontFamily:     'var(--t-font)',
        fontWeight:     600,
        cursor:         disabled ? 'not-allowed' : 'pointer',
        opacity:        disabled ? 0.5 : 1,
        boxShadow:      disabled ? 'none' : '0 4px 14px rgba(108, 92, 231, 0.30)',
        transition:     'transform 0.18s, box-shadow 0.18s, opacity 0.18s',
        outline:        'none',
        ...style,
      }}
      onMouseEnter={e => {
        if (!disabled) e.currentTarget.style.transform = 'translateY(-1px)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = ''
      }}
      onFocus={e => {
        e.currentTarget.style.boxShadow = '0 0 0 3px rgba(108, 92, 231, 0.15)'
      }}
      onBlur={e => {
        e.currentTarget.style.boxShadow = disabled ? 'none' : '0 4px 14px rgba(108, 92, 231, 0.30)'
      }}
      {...props}
    >
      {children}
    </button>
  )
}
