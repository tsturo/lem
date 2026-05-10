/// <reference types="vitest/globals" />
/// <reference types="@testing-library/jest-dom" />
import { render, screen, fireEvent } from '@testing-library/react'
import { RefineModal } from './RefineModal'
import type { RefineModalProps } from './RefineModal'

const baseProps: RefineModalProps = {
  mode:             'continue',
  open:             true,
  onClose:          vi.fn(),
  onSubmit:         vi.fn(),
  parentRoundDepth: 1,
  parentIdeaTitle:  'An app for tracking hikes',
}

function renderModal(overrides: Partial<RefineModalProps> = {}) {
  const props = { ...baseProps, onClose: vi.fn(), onSubmit: vi.fn(), ...overrides }
  const result = render(<RefineModal {...props} />)
  return { ...result, onClose: props.onClose, onSubmit: props.onSubmit }
}

// --- Visibility -------------------------------------------------------------

describe('RefineModal visibility', () => {
  it('renders nothing when open=false', () => {
    const { container } = renderModal({ open: false })
    expect(container.firstChild).toBeNull()
  })

  it('renders when open=true', () => {
    renderModal()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })
})

// --- Continue mode ----------------------------------------------------------

describe('RefineModal continue mode', () => {
  it('shows title "Refine again"', () => {
    renderModal()
    const el = screen.getByRole('dialog').querySelector('[data-modal-title]')
    expect(el?.textContent).toBe('Refine again')
  })

  it('shows subtitle with Round N+1', () => {
    renderModal({ parentRoundDepth: 1 })
    const el = screen.getByRole('dialog').querySelector('[data-modal-subtitle]')
    expect(el?.textContent).toContain('Round 2')
  })

  it('shows single textarea with continue-mode placeholder', () => {
    renderModal()
    const textarea = screen.getByRole('textbox', { name: /what is changed/i })
    expect(textarea).toBeInTheDocument()
    expect((textarea as HTMLTextAreaElement).placeholder).toContain('What is changed about this idea?')
  })

  it('does not show label input in continue mode', () => {
    renderModal()
    expect(screen.queryByLabelText(/label this branch/i)).toBeNull()
  })

  it('shows "Refine" as primary button label', () => {
    renderModal()
    expect(screen.getByRole('button', { name: /^refine$/i })).toBeInTheDocument()
  })

  it('Refine button is disabled when textarea is empty', () => {
    renderModal()
    expect(screen.getByRole('button', { name: /^refine$/i })).toBeDisabled()
  })

  it('Refine button is disabled when textarea has only whitespace', () => {
    renderModal()
    const textarea = screen.getByRole('textbox', { name: /what is changed/i })
    fireEvent.change(textarea, { target: { value: '   ' } })
    expect(screen.getByRole('button', { name: /^refine$/i })).toBeDisabled()
  })

  it('Refine button enables when textarea has non-whitespace content', () => {
    renderModal()
    const textarea = screen.getByRole('textbox', { name: /what is changed/i })
    fireEvent.change(textarea, { target: { value: 'now mobile' } })
    expect(screen.getByRole('button', { name: /^refine$/i })).not.toBeDisabled()
  })

  it('calls onSubmit with { contextText } on Refine click', () => {
    const { onSubmit } = renderModal()
    const textarea = screen.getByRole('textbox', { name: /what is changed/i })
    fireEvent.change(textarea, { target: { value: 'now mobile' } })
    fireEvent.click(screen.getByRole('button', { name: /^refine$/i }))
    expect(onSubmit).toHaveBeenCalledOnce()
    expect(onSubmit).toHaveBeenCalledWith({ contextText: 'now mobile' })
  })

  it('does not include branchLabel key in continue-mode submit', () => {
    const { onSubmit } = renderModal()
    const textarea = screen.getByRole('textbox', { name: /what is changed/i })
    fireEvent.change(textarea, { target: { value: 'now mobile' } })
    fireEvent.click(screen.getByRole('button', { name: /^refine$/i }))
    const arg = (onSubmit as ReturnType<typeof vi.fn>).mock.calls[0][0]
    expect('branchLabel' in arg).toBe(false)
  })
})

// --- Branch mode ------------------------------------------------------------

describe('RefineModal branch mode', () => {
  it('shows title "⑂ Branch alternative"', () => {
    renderModal({ mode: 'branch' })
    const el = screen.getByRole('dialog').querySelector('[data-modal-title]')
    expect(el?.textContent).toBe('⑂ Branch alternative')
  })

  it('shows subtitle with "Forking from Round N"', () => {
    renderModal({ mode: 'branch', parentRoundDepth: 2 })
    const el = screen.getByRole('dialog').querySelector('[data-modal-subtitle]')
    expect(el?.textContent).toContain('Forking from Round 2')
  })

  it('includes parentBranchLabel in subtitle when provided', () => {
    renderModal({ mode: 'branch', parentRoundDepth: 1, parentBranchLabel: 'mobile-first' })
    const el = screen.getByRole('dialog').querySelector('[data-modal-subtitle]')
    expect(el?.textContent).toContain('mobile-first')
  })

  it('shows optional branch label input', () => {
    renderModal({ mode: 'branch' })
    expect(screen.getByLabelText(/label this branch/i)).toBeInTheDocument()
  })

  it('shows context textarea with branch-mode placeholder', () => {
    renderModal({ mode: 'branch' })
    const textarea = screen.getByLabelText(/what is different/i)
    expect((textarea as HTMLTextAreaElement).placeholder).toContain('Describe the alternative')
  })

  it('shows "Branch" as primary button label', () => {
    renderModal({ mode: 'branch' })
    expect(screen.getByRole('button', { name: /^branch$/i })).toBeInTheDocument()
  })

  it('Branch button disabled when context textarea empty', () => {
    renderModal({ mode: 'branch' })
    expect(screen.getByRole('button', { name: /^branch$/i })).toBeDisabled()
  })

  it('calls onSubmit with branchLabel and contextText when both filled', () => {
    const { onSubmit } = renderModal({ mode: 'branch' })
    fireEvent.change(screen.getByLabelText(/label this branch/i), { target: { value: 'mobile-first' } })
    fireEvent.change(screen.getByLabelText(/what is different/i), { target: { value: 'focus on mobile' } })
    fireEvent.click(screen.getByRole('button', { name: /^branch$/i }))
    expect(onSubmit).toHaveBeenCalledWith({ branchLabel: 'mobile-first', contextText: 'focus on mobile' })
  })

  it('omits branchLabel when label input is blank', () => {
    const { onSubmit } = renderModal({ mode: 'branch' })
    fireEvent.change(screen.getByLabelText(/what is different/i), { target: { value: 'focus on mobile' } })
    fireEvent.click(screen.getByRole('button', { name: /^branch$/i }))
    const arg = (onSubmit as ReturnType<typeof vi.fn>).mock.calls[0][0]
    expect('branchLabel' in arg).toBe(false)
    expect(arg.contextText).toBe('focus on mobile')
  })

  it('omits branchLabel when label input is only whitespace', () => {
    const { onSubmit } = renderModal({ mode: 'branch' })
    fireEvent.change(screen.getByLabelText(/label this branch/i), { target: { value: '   ' } })
    fireEvent.change(screen.getByLabelText(/what is different/i), { target: { value: 'something' } })
    fireEvent.click(screen.getByRole('button', { name: /^branch$/i }))
    const arg = (onSubmit as ReturnType<typeof vi.fn>).mock.calls[0][0]
    expect('branchLabel' in arg).toBe(false)
  })
})

// --- Dismissal --------------------------------------------------------------

describe('RefineModal dismissal', () => {
  it('Cancel button calls onClose', () => {
    const { onClose } = renderModal()
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('Escape key calls onClose', () => {
    const { onClose } = renderModal()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('backdrop click calls onClose', () => {
    const { onClose, container } = renderModal()
    const backdrop = container.querySelector('[data-backdrop]')!
    fireEvent.click(backdrop)
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('clicking inside modal does not call onClose', () => {
    const { onClose } = renderModal()
    fireEvent.click(screen.getByRole('dialog'))
    expect(onClose).not.toHaveBeenCalled()
  })
})

// --- Cost line --------------------------------------------------------------

describe('RefineModal cost line', () => {
  it('renders cost line in continue mode', () => {
    const { container } = renderModal()
    const costLine = container.querySelector('[data-cost-line]')
    expect(costLine?.textContent).toBe('~10 min · ~$1.50 of Max tokens')
  })

  it('renders cost line in branch mode', () => {
    const { container } = renderModal({ mode: 'branch' })
    const costLine = container.querySelector('[data-cost-line]')
    expect(costLine?.textContent).toBe('~10 min · ~$1.50 of Max tokens')
  })
})

// --- Title truncation -------------------------------------------------------

describe('RefineModal title truncation', () => {
  it('truncates very long idea title to ~40 chars', () => {
    renderModal({ parentIdeaTitle: 'A'.repeat(50) })
    const el = screen.getByRole('dialog').querySelector('[data-modal-subtitle]')
    expect(el?.textContent?.length).toBeLessThan(80)
    expect(el?.textContent).toContain('…')
  })

  it('does not truncate short title', () => {
    renderModal({ parentIdeaTitle: 'Short title' })
    const el = screen.getByRole('dialog').querySelector('[data-modal-subtitle]')
    expect(el?.textContent).toContain('Short title')
    expect(el?.textContent).not.toContain('…')
  })
})
