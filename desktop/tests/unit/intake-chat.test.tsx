import { render, fireEvent } from '@testing-library/react'
import { IntakeChat } from '@/screens/IntakeChat'
import type { ChatMessage } from '../../src/shared/types'

const baseProps = {
  ideaTitle: 'My idea',
  messages: [] as ChatMessage[],
  questionIndex: 0,
  totalQuestions: 3,
  onSend: () => {},
}

describe('IntakeChat', () => {
  it('shows the eyebrow with idea title', () => {
    const { container } = render(<IntakeChat {...baseProps} ideaTitle="Awesome app" />)
    const eyebrow = container.querySelector('[data-eyebrow]')
    expect(eyebrow?.textContent).toContain('Awesome app')
  })

  it('shows the heading', () => {
    const { getByText } = render(<IntakeChat {...baseProps} />)
    expect(getByText('A couple of questions before we dive in')).toBeTruthy()
  })

  it('renders assistant messages on the left', () => {
    const messages: ChatMessage[] = [
      { role: 'assistant', content: 'What problem does it solve?', timestamp: '' },
    ]
    const { container } = render(<IntakeChat {...baseProps} messages={messages} />)
    expect(container.querySelector('[data-message="assistant"]')).toBeTruthy()
  })

  it('renders user messages on the right', () => {
    const messages: ChatMessage[] = [
      { role: 'user', content: 'It helps with scheduling', timestamp: '' },
    ]
    const { container } = render(<IntakeChat {...baseProps} messages={messages} />)
    expect(container.querySelector('[data-message="user"]')).toBeTruthy()
  })

  it('Enter sends the message (primary action)', () => {
    const onSend = vi.fn()
    const { container } = render(<IntakeChat {...baseProps} onSend={onSend} />)
    const textarea = container.querySelector('[data-input]') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'hello' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
    expect(onSend).toHaveBeenCalledWith('hello')
  })

  it('Shift+Enter does not send', () => {
    const onSend = vi.fn()
    const { container } = render(<IntakeChat {...baseProps} onSend={onSend} />)
    const textarea = container.querySelector('[data-input]') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'hello' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })
    expect(onSend).not.toHaveBeenCalled()
  })

  it('⌘↵ sends the message (accelerator)', () => {
    const onSend = vi.fn()
    const { container } = render(<IntakeChat {...baseProps} onSend={onSend} />)
    const textarea = container.querySelector('[data-input]') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'hello' } })
    fireEvent.keyDown(textarea, { key: 'Enter', metaKey: true, shiftKey: false })
    expect(onSend).toHaveBeenCalledWith('hello')
  })

  it('clears draft after sending', () => {
    const { container } = render(<IntakeChat {...baseProps} />)
    const textarea = container.querySelector('[data-input]') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: 'hello' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
    expect(textarea.value).toBe('')
  })

  it('does not send empty or whitespace-only input', () => {
    const onSend = vi.fn()
    const { container } = render(<IntakeChat {...baseProps} onSend={onSend} />)
    const textarea = container.querySelector('[data-input]') as HTMLTextAreaElement
    fireEvent.change(textarea, { target: { value: '   ' } })
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
    expect(onSend).not.toHaveBeenCalled()
  })

  it('lem avatar has 9px border-radius (--t-radius-sm)', () => {
    const messages: ChatMessage[] = [
      { role: 'assistant', content: 'Hi', timestamp: '' },
    ]
    const { container } = render(<IntakeChat {...baseProps} messages={messages} />)
    const avatar = container.querySelector('[data-avatar="lem"]') as HTMLElement
    expect(avatar.style.borderRadius).toBe('9px')
  })

  it('user avatar has 9px border-radius (--t-radius-sm)', () => {
    const messages: ChatMessage[] = [
      { role: 'user', content: 'Hi', timestamp: '' },
    ]
    const { container } = render(<IntakeChat {...baseProps} messages={messages} />)
    const avatar = container.querySelector('[data-avatar="user"]') as HTMLElement
    expect(avatar.style.borderRadius).toBe('9px')
  })

  it('lem avatar has ⌘ icon', () => {
    const messages: ChatMessage[] = [
      { role: 'assistant', content: 'Hi', timestamp: '' },
    ]
    const { container } = render(<IntakeChat {...baseProps} messages={messages} />)
    const avatar = container.querySelector('[data-avatar="lem"]')
    expect(avatar?.textContent).toBe('⌘')
  })

  it('lem avatar has 12% purple background', () => {
    const messages: ChatMessage[] = [
      { role: 'assistant', content: 'Hi', timestamp: '' },
    ]
    const { container } = render(<IntakeChat {...baseProps} messages={messages} />)
    const avatar = container.querySelector('[data-avatar="lem"]') as HTMLElement
    expect(avatar.style.background).toBe('rgba(108, 92, 231, 0.12)')
  })

  it('user avatar has gradient background', () => {
    const messages: ChatMessage[] = [
      { role: 'user', content: 'Hi', timestamp: '' },
    ]
    const { container } = render(<IntakeChat {...baseProps} messages={messages} />)
    const avatar = container.querySelector('[data-avatar="user"]') as HTMLElement
    expect(avatar.style.background).toContain('gradient')
  })

  it('user avatar shows white initials', () => {
    const messages: ChatMessage[] = [
      { role: 'user', content: 'Hi', timestamp: '' },
    ]
    const { container } = render(<IntakeChat {...baseProps} messages={messages} />)
    const avatar = container.querySelector('[data-avatar="user"]') as HTMLElement
    expect(avatar.style.color).toBe('rgb(255, 255, 255)')
    expect(avatar.textContent?.trim()).not.toBe('')
  })

  it('progress label shows "Question X of Y" format', () => {
    const { container } = render(
      <IntakeChat {...baseProps} questionIndex={1} totalQuestions={3} />
    )
    const label = container.querySelector('[data-progress-label]')
    expect(label?.textContent).toBe('Question 2 of 3')
  })

  it('progress dots renders correct number of dots', () => {
    const { container } = render(
      <IntakeChat {...baseProps} questionIndex={0} totalQuestions={3} />
    )
    const dots = container.querySelectorAll('[data-dot]')
    expect(dots).toHaveLength(3)
  })

  it('current question dot is marked active', () => {
    const { container } = render(
      <IntakeChat {...baseProps} questionIndex={1} totalQuestions={3} />
    )
    const dots = container.querySelectorAll('[data-dot]')
    expect(dots[1].getAttribute('data-dot')).toBe('active')
    expect(dots[0].getAttribute('data-dot')).toBe('inactive')
    expect(dots[2].getAttribute('data-dot')).toBe('inactive')
  })
})
