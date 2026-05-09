import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import type { ChatMessage } from '../../shared/types'

interface IntakeChatProps {
  ideaTitle: string
  messages: ChatMessage[]
  questionIndex: number
  totalQuestions: number
  onSend: (content: string) => void
}

export function IntakeChat({
  ideaTitle,
  messages,
  questionIndex,
  totalQuestions,
  onSend,
}: IntakeChatProps) {
  const [draft, setDraft] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  function send() {
    const trimmed = draft.trim()
    if (!trimmed) return
    onSend(trimmed)
    setDraft('')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--t-bg)' }}>
      <Header ideaTitle={ideaTitle} />

      <div
        ref={scrollRef}
        style={{ flex: 1, overflowY: 'auto', padding: '24px 32px' }}
      >
        <div style={{ maxWidth: 560, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
          {messages.map((msg, i) =>
            msg.role === 'assistant' ? (
              <LemBubble key={i} content={msg.content} />
            ) : (
              <UserBubble key={i} content={msg.content} />
            )
          )}
        </div>
      </div>

      <Footer
        draft={draft}
        questionIndex={questionIndex}
        totalQuestions={totalQuestions}
        onDraftChange={setDraft}
        onKeyDown={handleKeyDown}
        onSend={send}
      />
    </div>
  )
}

function Header({ ideaTitle }: { ideaTitle: string }) {
  return (
    <div style={{ padding: '24px 32px 16px', borderBottom: '1px solid var(--t-border)' }}>
      <p
        data-eyebrow
        style={{
          fontSize: 11,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: 'var(--t-text-3)',
          margin: 0,
          fontFamily: 'var(--t-font)',
        }}
      >
        SETUP · {ideaTitle}
      </p>
      <h2
        style={{
          fontSize: 22,
          fontWeight: 700,
          color: 'var(--t-text)',
          margin: '8px 0 0',
          fontFamily: 'var(--t-font)',
        }}
      >
        A couple of questions before we dive in
      </h2>
    </div>
  )
}

interface FooterProps {
  draft: string
  questionIndex: number
  totalQuestions: number
  onDraftChange: (v: string) => void
  onKeyDown: (e: KeyboardEvent<HTMLTextAreaElement>) => void
  onSend: () => void
}

function Footer({ draft, questionIndex, totalQuestions, onDraftChange, onKeyDown, onSend }: FooterProps) {
  const canSend = draft.trim().length > 0

  return (
    <div style={{ borderTop: '1px solid var(--t-border)', padding: '16px 32px 24px' }}>
      <Progress questionIndex={questionIndex} totalQuestions={totalQuestions} />

      <div
        style={{
          display: 'flex',
          gap: 8,
          alignItems: 'flex-end',
          background: 'var(--t-surface)',
          border: '1px solid var(--t-border)',
          borderRadius: 12,
          padding: '12px 12px 12px 16px',
        }}
      >
        <textarea
          data-input
          value={draft}
          onChange={e => onDraftChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Type your answer…"
          rows={1}
          style={{
            flex: 1,
            resize: 'none',
            border: 'none',
            outline: 'none',
            background: 'transparent',
            color: 'var(--t-text)',
            fontFamily: 'var(--t-font)',
            fontSize: 14,
            lineHeight: 1.55,
            padding: 0,
            minHeight: 21,
          }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingBottom: 2 }}>
          <span
            style={{
              fontSize: 11,
              color: 'var(--t-text-3)',
              whiteSpace: 'nowrap',
              fontFamily: 'var(--t-font)',
            }}
          >
            ⌘↵
          </span>
          <button
            data-send-btn
            onClick={onSend}
            disabled={!canSend}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '6px 14px',
              background: canSend ? 'linear-gradient(135deg, #6c5ce7, #00cec9)' : 'var(--t-border)',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              fontSize: 13,
              fontFamily: 'var(--t-font)',
              fontWeight: 600,
              cursor: canSend ? 'pointer' : 'not-allowed',
              opacity: canSend ? 1 : 0.6,
              transition: 'background 0.18s, opacity 0.18s',
            }}
          >
            Send
          </button>
        </div>
      </div>

      <p
        style={{
          fontSize: 11,
          color: 'var(--t-text-3)',
          margin: '6px 0 0',
          fontFamily: 'var(--t-font)',
        }}
      >
        Enter to send · Shift+Enter for newline
      </p>
    </div>
  )
}

function Progress({ questionIndex, totalQuestions }: { questionIndex: number; totalQuestions: number }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
      <span
        data-progress-label
        style={{ fontSize: 12, color: 'var(--t-text-3)', fontFamily: 'var(--t-font)' }}
      >
        Question {questionIndex + 1} of {totalQuestions}
      </span>
      <div data-progress-dots style={{ display: 'flex', gap: 4 }}>
        {Array.from({ length: totalQuestions }).map((_, i) => (
          <span
            key={i}
            data-dot={i === questionIndex ? 'active' : 'inactive'}
            style={{
              display: 'inline-block',
              width: 6,
              height: 6,
              borderRadius: '50%',
              background:
                i === questionIndex
                  ? 'linear-gradient(135deg, #6c5ce7, #00cec9)'
                  : 'var(--t-border)',
            }}
          />
        ))}
      </div>
    </div>
  )
}

function LemBubble({ content }: { content: string }) {
  return (
    <div data-message="assistant" style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
      <div
        data-avatar="lem"
        style={{
          width: 32,
          height: 32,
          borderRadius: 9,
          background: 'rgba(108, 92, 231, 0.12)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 14,
          flexShrink: 0,
        }}
      >
        ⌘
      </div>
      <div
        style={{
          background: 'var(--t-surface)',
          border: '1px solid var(--t-border)',
          borderRadius: 14,
          padding: '12px 16px',
          maxWidth: 460,
          fontSize: 15,
          fontFamily: 'var(--t-font)',
          lineHeight: 1.55,
          color: 'var(--t-text)',
        }}
      >
        {content}
      </div>
    </div>
  )
}

function UserBubble({ content }: { content: string }) {
  return (
    <div data-message="user" style={{ display: 'flex', alignItems: 'flex-start', gap: 10, justifyContent: 'flex-end' }}>
      <div
        style={{
          background: 'rgba(108, 92, 231, 0.08)',
          border: '1px solid rgba(108, 92, 231, 0.15)',
          borderRadius: 14,
          padding: '12px 16px',
          maxWidth: 460,
          fontSize: 15,
          fontFamily: 'var(--t-font)',
          lineHeight: 1.55,
          color: 'var(--t-text)',
        }}
      >
        {content}
      </div>
      <div
        data-avatar="user"
        style={{
          width: 32,
          height: 32,
          borderRadius: 9,
          background: 'linear-gradient(135deg, #6c5ce7, #00cec9)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 14,
          fontWeight: 700,
          color: '#fff',
          flexShrink: 0,
          fontFamily: 'var(--t-font)',
        }}
      >
        Y
      </div>
    </div>
  )
}
