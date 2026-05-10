import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import type { RefineRequest } from '../../shared/types'
import { PrimaryButton } from './PrimaryButton'

export type RefineModalProps = {
  mode: 'continue' | 'branch'
  open: boolean
  onClose: () => void
  onSubmit: (req: Omit<RefineRequest, 'idea' | 'parentRunId'>) => void
  parentRoundDepth: number
  parentIdeaTitle: string
  parentBranchLabel?: string | null
}

const COST_LINE = '~10 min · ~$1.50 of Max tokens'
const TITLE_MAX = 40

function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max) + '…' : text
}

const inputBase: CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  padding: '10px 12px',
  background: 'var(--t-input-bg, rgba(255,255,255,0.05))',
  border: '1px solid var(--t-border)',
  borderRadius: 10,
  fontSize: 14,
  fontFamily: 'var(--t-font)',
  color: 'var(--t-text-primary)',
  outline: 'none',
}

export function RefineModal({
  mode,
  open,
  onClose,
  onSubmit,
  parentRoundDepth,
  parentIdeaTitle,
  parentBranchLabel,
}: RefineModalProps) {
  const [contextText, setContextText] = useState('')
  const [branchLabel, setBranchLabel] = useState('')
  const dialogRef = useRef<HTMLDivElement>(null)
  const labelInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const triggerRef = useRef<Element | null>(null)

  useEffect(() => {
    if (open) {
      setContextText('')
      setBranchLabel('')
      triggerRef.current = document.activeElement
      const firstEl = mode === 'branch' ? labelInputRef.current : textareaRef.current
      setTimeout(() => firstEl?.focus(), 0)
    } else {
      if (triggerRef.current instanceof HTMLElement) {
        triggerRef.current.focus()
      }
    }
  }, [open, mode])

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  const title = truncate(parentIdeaTitle, TITLE_MAX)
  const subtitle =
    mode === 'continue'
      ? `Round ${parentRoundDepth + 1} of "${title}"`
      : parentBranchLabel
        ? `Forking from Round ${parentRoundDepth} of "${title}" (${parentBranchLabel})`
        : `Forking from Round ${parentRoundDepth} of "${title}"`

  const isSubmitDisabled = contextText.trim() === ''

  const handleSubmit = () => {
    if (isSubmitDisabled) return
    if (mode === 'continue') {
      onSubmit({ contextText })
    } else {
      const req: Omit<RefineRequest, 'idea' | 'parentRunId'> = { contextText }
      if (branchLabel.trim() !== '') req.branchLabel = branchLabel.trim()
      onSubmit(req)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key !== 'Tab' || !dialogRef.current) return
    const focusable = Array.from(
      dialogRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), input:not([disabled]), textarea:not([disabled])'
      )
    )
    if (focusable.length === 0) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault()
        last.focus()
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault()
        first.focus()
      }
    }
  }

  return (
    <div
      data-backdrop
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={mode === 'continue' ? 'Refine again' : 'Branch alternative'}
        onClick={e => e.stopPropagation()}
        onKeyDown={handleKeyDown}
        style={{
          background: 'var(--t-bg)',
          borderRadius: 16,
          padding: '28px 28px 20px',
          width: 480,
          maxWidth: '90vw',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
          display: 'flex',
          flexDirection: 'column',
          gap: 20,
        }}
      >
        <div>
          <div
            data-modal-title
            style={{
              fontSize: 18,
              fontWeight: 700,
              fontFamily: 'var(--t-font)',
              color: 'var(--t-text-primary)',
            }}
          >
            {mode === 'continue' ? 'Refine again' : '⑂ Branch alternative'}
          </div>
          <div
            data-modal-subtitle
            style={{
              fontSize: 13,
              color: 'var(--t-text-secondary)',
              marginTop: 4,
              fontFamily: 'var(--t-font)',
            }}
          >
            {subtitle}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {mode === 'branch' && (
            <div>
              <label
                htmlFor="refine-branch-label"
                style={{
                  display: 'block',
                  fontSize: 12,
                  color: 'var(--t-text-secondary)',
                  marginBottom: 4,
                  fontFamily: 'var(--t-font)',
                }}
              >
                Label this branch (optional)
              </label>
              <input
                id="refine-branch-label"
                ref={labelInputRef}
                type="text"
                value={branchLabel}
                onChange={e => setBranchLabel(e.target.value)}
                placeholder="e.g. mobile-first — auto-suggested if blank"
                style={inputBase}
              />
            </div>
          )}

          <div>
            {mode === 'branch' && (
              <label
                htmlFor="refine-context"
                style={{
                  display: 'block',
                  fontSize: 12,
                  color: 'var(--t-text-secondary)',
                  marginBottom: 4,
                  fontFamily: 'var(--t-font)',
                }}
              >
                What is different about this direction?
              </label>
            )}
            <textarea
              id="refine-context"
              ref={textareaRef}
              aria-label={mode === 'continue' ? 'What is changed about this idea?' : undefined}
              value={contextText}
              onChange={e => setContextText(e.target.value)}
              placeholder={
                mode === 'continue'
                  ? "What is changed about this idea? (e.g. 'now mobile-first, save trips, comment on stops')"
                  : 'Describe the alternative...'
              }
              rows={4}
              style={{ ...inputBase, resize: 'vertical', minHeight: 90 }}
            />
          </div>
        </div>

        <div>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: 12,
            }}
          >
            <button
              onClick={onClose}
              style={{
                background: 'none',
                border: '1px solid var(--t-border)',
                borderRadius: 10,
                padding: '10px 18px',
                fontSize: 14,
                fontFamily: 'var(--t-font)',
                color: 'var(--t-text-secondary)',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <PrimaryButton disabled={isSubmitDisabled} onClick={handleSubmit}>
              {mode === 'continue' ? 'Refine' : 'Branch'}
            </PrimaryButton>
          </div>
          <div
            data-cost-line
            style={{
              marginTop: 10,
              fontSize: 11,
              color: 'var(--t-text-secondary)',
              opacity: 0.6,
              fontFamily: 'var(--t-font)',
            }}
          >
            {COST_LINE}
          </div>
        </div>
      </div>
    </div>
  )
}
