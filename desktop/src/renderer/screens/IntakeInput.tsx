import { useState, useRef } from 'react'
import { PrimaryButton } from '@/components/PrimaryButton'
import { Chip } from '@/components/Chip'

interface Attachment {
  id: string
  name: string
}

export interface IntakeInputProps {
  onSubmit?: (idea: string, attachments: string[]) => void
}

function useAttachments() {
  const [items, setItems] = useState<Attachment[]>([])

  const add = (name: string) =>
    setItems(prev => [...prev, { id: `${Date.now()}-${Math.random()}`, name }])

  const remove = (id: string) =>
    setItems(prev => prev.filter(a => a.id !== id))

  return { items, add, remove }
}

export function IntakeInput({ onSubmit }: IntakeInputProps) {
  const [idea, setIdea] = useState('')
  const { items: attachments, add: addAttachment, remove: removeAttachment } = useAttachments()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const canSubmit = idea.trim().length > 0

  const handleAttach = async () => {
    if (window.lem?.shell?.openFile) {
      const path = await window.lem.shell.openFile()
      if (path) addAttachment(path.split('/').pop() ?? path)
    } else {
      fileInputRef.current?.click()
    }
  }

  const handlePaste = (e: React.ClipboardEvent) => {
    const { files } = e.clipboardData
    if (files && files.length > 0) {
      e.preventDefault()
      Array.from(files).forEach(f => addAttachment(f.name))
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    Array.from(e.target.files ?? []).forEach(f => addAttachment(f.name))
    e.target.value = ''
  }

  const handleSubmit = () => {
    if (canSubmit) onSubmit?.(idea.trim(), attachments.map(a => a.name))
  }

  return (
    <div
      data-screen="intake-input"
      style={{
        maxWidth: 640,
        margin: '0 auto',
        padding: '48px 32px',
        display: 'flex',
        flexDirection: 'column',
        gap: 24,
      }}
    >
      <span
        style={{
          fontSize: 11,
          fontWeight: 700,
          fontFamily: 'var(--t-font)',
          letterSpacing: '0.10em',
          textTransform: 'uppercase',
          color: 'var(--t-purple)',
        }}
      >
        NEW IDEA
      </span>

      <h1
        style={{
          margin: 0,
          fontSize: 36,
          fontWeight: 700,
          fontFamily: 'var(--t-font)',
          letterSpacing: '-0.02em',
          lineHeight: 1.2,
          color: 'var(--t-text)',
        }}
      >
        What's the{' '}
        <span data-accent className="t-accent">
          idea
        </span>
        ?
      </h1>

      <p
        style={{
          margin: 0,
          maxWidth: 560,
          fontSize: 16,
          fontFamily: 'var(--t-font)',
          lineHeight: 1.6,
          color: 'var(--t-text-2)',
        }}
      >
        One line is fine. Lem will ask a couple of clarifying questions, then
        three specialists weigh in. About 15 minutes start to finish.
      </p>

      <textarea
        className="intake-textarea"
        rows={3}
        placeholder="e.g. a calendar app that..."
        value={idea}
        onChange={e => setIdea(e.target.value)}
        onPaste={handlePaste}
        aria-label="Your idea"
      />

      <div
        style={{
          border: '1.5px dashed var(--t-border)',
          borderRadius: 'var(--t-radius-md)',
          background: 'var(--t-surface)',
          padding: '14px 16px',
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}
      >
        <span
          style={{
            fontSize: 13,
            fontFamily: 'var(--t-font)',
            fontWeight: 500,
            color: 'var(--t-text-2)',
          }}
        >
          Anything else lem should know?{' '}
          <span style={{ color: 'var(--t-text-3)', fontWeight: 400 }}>(optional)</span>
        </span>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          <Chip onClick={handleAttach} aria-label="Attach file">
            📎 Attach file
          </Chip>

          {attachments.map(a => (
            <div
              key={a.id}
              data-attachment-chip
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                padding: '5px 10px',
                border: '1px solid rgba(108, 92, 231, 0.25)',
                borderRadius: 'var(--t-radius-pill)',
                background: 'rgba(108, 92, 231, 0.10)',
                fontSize: 12,
                fontFamily: 'var(--t-font)',
                color: 'var(--t-purple)',
              }}
            >
              {a.name}
              <button
                onClick={() => removeAttachment(a.id)}
                aria-label={`Remove ${a.name}`}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '0 0 0 2px',
                  fontSize: 14,
                  color: 'inherit',
                  lineHeight: 1,
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <span
          style={{
            fontSize: 12,
            fontFamily: 'var(--t-font)',
            color: 'var(--t-text-3)',
          }}
        >
          Default · Standard · $0
        </span>
        <PrimaryButton disabled={!canSubmit} onClick={handleSubmit}>
          Refine my idea →
        </PrimaryButton>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,.pdf,.md,.txt"
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />
    </div>
  )
}
