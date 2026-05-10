import { useState, useEffect, useRef } from 'react'

export type RefineAgainButtonProps = {
  onContinue: () => void
  onBranch: () => void
  disabled?: boolean
}

const GRADIENT = 'linear-gradient(135deg, #6c5ce7, #00cec9)'

const baseButtonStyle: React.CSSProperties = {
  background:   GRADIENT,
  color:        '#ffffff',
  border:       'none',
  fontSize:     14,
  fontFamily:   'var(--t-font)',
  fontWeight:   600,
  transition:   'transform 0.18s, box-shadow 0.18s, opacity 0.18s',
  outline:      'none',
}

const menuItemStyle: React.CSSProperties = {
  display:    'flex',
  alignItems: 'center',
  gap:        8,
  width:      '100%',
  padding:    '10px 14px',
  background: 'none',
  border:     'none',
  fontSize:   13,
  fontFamily: 'var(--t-font)',
  color:      'var(--t-text, #e0e0e0)',
  cursor:     'pointer',
  textAlign:  'left',
}

export function RefineAgainButton({ onContinue, onBranch, disabled = false }: RefineAgainButtonProps) {
  const [open, setOpen]     = useState(false)
  const containerRef        = useRef<HTMLDivElement>(null)
  const menuRef             = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onMouseDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onMouseDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  useEffect(() => {
    if (open && menuRef.current) {
      const first = menuRef.current.querySelector<HTMLElement>('[role=menuitem]')
      first?.focus()
    }
  }, [open])

  function openMenu() {
    if (!disabled) setOpen(true)
  }

  function handleChevronKeyDown(e: React.KeyboardEvent<HTMLButtonElement>) {
    if ((e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') && !disabled) {
      e.preventDefault()
      setOpen(true)
    }
  }

  function handleMenuKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    const items = Array.from(
      menuRef.current?.querySelectorAll<HTMLElement>('[role=menuitem]') ?? []
    )
    const idx = items.indexOf(document.activeElement as HTMLElement)
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      items[(idx + 1) % items.length]?.focus()
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      items[(idx - 1 + items.length) % items.length]?.focus()
    }
  }

  const disabledStyle: React.CSSProperties = disabled
    ? { cursor: 'not-allowed', opacity: 0.5 }
    : {}

  return (
    <div
      ref={containerRef}
      data-refine-again-button
      style={{ position: 'relative', display: 'inline-flex' }}
    >
      <div
        style={{
          display:      'inline-flex',
          alignItems:   'center',
          borderRadius: 12,
          boxShadow:    disabled ? 'none' : '0 4px 14px rgba(108, 92, 231, 0.30)',
        }}
      >
        <button
          data-main
          disabled={disabled}
          onClick={() => { if (!disabled) onContinue() }}
          style={{
            ...baseButtonStyle,
            ...disabledStyle,
            padding:      '10px 16px 10px 20px',
            borderRadius: '12px 0 0 12px',
            borderRight:  '1px solid rgba(255,255,255,0.2)',
          }}
          onMouseEnter={e => { if (!disabled) e.currentTarget.style.transform = 'translateY(-1px)' }}
          onMouseLeave={e => { e.currentTarget.style.transform = '' }}
        >
          Refine again
        </button>

        <button
          data-chevron
          disabled={disabled}
          aria-haspopup="true"
          aria-expanded={open}
          onClick={() => { if (open) setOpen(false); else openMenu() }}
          onKeyDown={handleChevronKeyDown}
          style={{
            ...baseButtonStyle,
            ...disabledStyle,
            padding:      '10px 12px',
            borderRadius: '0 12px 12px 0',
          }}
          onMouseEnter={e => { if (!disabled) e.currentTarget.style.transform = 'translateY(-1px)' }}
          onMouseLeave={e => { e.currentTarget.style.transform = '' }}
        >
          ▾
        </button>
      </div>

      {open && (
        <div
          ref={menuRef}
          role="menu"
          data-menu
          onKeyDown={handleMenuKeyDown}
          style={{
            position:   'absolute',
            top:        'calc(100% + 6px)',
            right:      0,
            background: 'var(--t-surface, #1e1e2e)',
            border:     '1px solid var(--t-border, rgba(255,255,255,0.1))',
            borderRadius: 10,
            boxShadow:  '0 8px 32px rgba(0,0,0,0.24)',
            minWidth:   200,
            overflow:   'hidden',
            zIndex:     50,
          }}
        >
          <button
            role="menuitem"
            data-menu-item="continue"
            onClick={() => { setOpen(false); onContinue() }}
            style={menuItemStyle}
          >
            ⊕ Continue this thread
          </button>
          <button
            role="menuitem"
            data-menu-item="branch"
            onClick={() => { setOpen(false); onBranch() }}
            style={{
              ...menuItemStyle,
              borderTop: '1px solid var(--t-border, rgba(255,255,255,0.1))',
            }}
          >
            ⑂ Branch alternative
          </button>
        </div>
      )}
    </div>
  )
}
