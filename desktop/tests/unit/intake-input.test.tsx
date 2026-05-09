import { render, screen, fireEvent, createEvent } from '@testing-library/react'
import { IntakeInput } from '@/screens/IntakeInput'

describe('IntakeInput', () => {
  it('renders "NEW IDEA" eyebrow', () => {
    render(<IntakeInput />)
    expect(screen.getByText('NEW IDEA')).toBeInTheDocument()
  })

  it('renders hero heading with gradient accent span on "idea"', () => {
    const { container } = render(<IntakeInput />)
    const accent = container.querySelector('[data-accent]')
    expect(accent?.textContent).toBe('idea')
    expect(accent?.classList.contains('t-accent')).toBe(true)
  })

  it('renders helper text', () => {
    render(<IntakeInput />)
    expect(screen.getByText(/one line is fine/i)).toBeInTheDocument()
  })

  it('CTA button is disabled when textarea is empty', () => {
    render(<IntakeInput />)
    expect(screen.getByRole('button', { name: /refine my idea/i })).toBeDisabled()
  })

  it('CTA button is enabled when textarea has content', () => {
    render(<IntakeInput />)
    const textarea = screen.getByRole('textbox', { name: /your idea/i })
    fireEvent.change(textarea, { target: { value: 'An app for tracking hikes' } })
    expect(screen.getByRole('button', { name: /refine my idea/i })).not.toBeDisabled()
  })

  it('CTA stays disabled when textarea contains only whitespace', () => {
    render(<IntakeInput />)
    const textarea = screen.getByRole('textbox', { name: /your idea/i })
    fireEvent.change(textarea, { target: { value: '   ' } })
    expect(screen.getByRole('button', { name: /refine my idea/i })).toBeDisabled()
  })

  it('calls onSubmit with trimmed idea and empty attachments list', () => {
    const onSubmit = vi.fn()
    render(<IntakeInput onSubmit={onSubmit} />)
    const textarea = screen.getByRole('textbox', { name: /your idea/i })
    fireEvent.change(textarea, { target: { value: '  An app for tracking hikes  ' } })
    fireEvent.click(screen.getByRole('button', { name: /refine my idea/i }))
    expect(onSubmit).toHaveBeenCalledWith('An app for tracking hikes', [])
  })

  it('does not call onSubmit when CTA is disabled', () => {
    const onSubmit = vi.fn()
    render(<IntakeInput onSubmit={onSubmit} />)
    fireEvent.click(screen.getByRole('button', { name: /refine my idea/i }))
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('pasting a file in the textarea adds an attachment chip', () => {
    const { container } = render(<IntakeInput />)
    const textarea = screen.getByRole('textbox', { name: /your idea/i })

    const file = new File([''], 'design.png', { type: 'image/png' })
    const pasteEvent = createEvent.paste(textarea)
    Object.defineProperty(pasteEvent, 'clipboardData', {
      value: { files: [file], getData: () => '' },
      configurable: true,
    })
    fireEvent(textarea, pasteEvent)

    const chips = container.querySelectorAll('[data-attachment-chip]')
    expect(chips).toHaveLength(1)
    expect(chips[0].textContent).toContain('design.png')
  })

  it('pasting multiple files adds a chip for each', () => {
    const { container } = render(<IntakeInput />)
    const textarea = screen.getByRole('textbox', { name: /your idea/i })

    const files = [
      new File([''], 'photo.png', { type: 'image/png' }),
      new File([''], 'notes.md', { type: 'text/markdown' }),
    ]
    const pasteEvent = createEvent.paste(textarea)
    Object.defineProperty(pasteEvent, 'clipboardData', {
      value: { files, getData: () => '' },
      configurable: true,
    })
    fireEvent(textarea, pasteEvent)

    expect(container.querySelectorAll('[data-attachment-chip]')).toHaveLength(2)
  })

  it('pasting plain text does not add a chip', () => {
    const { container } = render(<IntakeInput />)
    const textarea = screen.getByRole('textbox', { name: /your idea/i })

    const pasteEvent = createEvent.paste(textarea)
    Object.defineProperty(pasteEvent, 'clipboardData', {
      value: { files: [], getData: () => 'https://example.com' },
      configurable: true,
    })
    fireEvent(textarea, pasteEvent)

    expect(container.querySelectorAll('[data-attachment-chip]')).toHaveLength(0)
  })

  it('removes attachment chip when × button is clicked', () => {
    const { container } = render(<IntakeInput />)
    const textarea = screen.getByRole('textbox', { name: /your idea/i })

    const file = new File([''], 'doc.pdf', { type: 'application/pdf' })
    const pasteEvent = createEvent.paste(textarea)
    Object.defineProperty(pasteEvent, 'clipboardData', {
      value: { files: [file], getData: () => '' },
      configurable: true,
    })
    fireEvent(textarea, pasteEvent)
    expect(container.querySelectorAll('[data-attachment-chip]')).toHaveLength(1)

    const removeBtn = screen.getByRole('button', { name: /remove doc\.pdf/i })
    fireEvent.click(removeBtn)
    expect(container.querySelectorAll('[data-attachment-chip]')).toHaveLength(0)
  })

  it('textarea element has intake-textarea CSS class for focus ring', () => {
    render(<IntakeInput />)
    const textarea = screen.getByRole('textbox', { name: /your idea/i })
    expect(textarea.classList.contains('intake-textarea')).toBe(true)
  })

  it('attach file chip is present in extras area', () => {
    render(<IntakeInput />)
    expect(screen.getByRole('button', { name: /attach file/i })).toBeInTheDocument()
  })

  it('calls onSubmit including attachment names', () => {
    const onSubmit = vi.fn()
    render(<IntakeInput onSubmit={onSubmit} />)
    const textarea = screen.getByRole('textbox', { name: /your idea/i })
    fireEvent.change(textarea, { target: { value: 'my idea' } })

    const file = new File([''], 'brief.pdf', { type: 'application/pdf' })
    const pasteEvent = createEvent.paste(textarea)
    Object.defineProperty(pasteEvent, 'clipboardData', {
      value: { files: [file], getData: () => '' },
      configurable: true,
    })
    fireEvent(textarea, pasteEvent)

    fireEvent.click(screen.getByRole('button', { name: /refine my idea/i }))
    expect(onSubmit).toHaveBeenCalledWith('my idea', ['brief.pdf'])
  })
})
