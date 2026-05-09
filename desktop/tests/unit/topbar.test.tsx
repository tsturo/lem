import { render, fireEvent } from '@testing-library/react'
import { Topbar } from '@/components/Topbar'
import { VerdictPill } from '@/components/VerdictPill'

describe('Topbar', () => {
  it('renders the title', () => {
    const { container } = render(<Topbar title="My idea" />)
    expect(container.querySelector('[data-title]')?.textContent).toBe('My idea')
  })

  it('renders the meta line when provided', () => {
    const { container } = render(<Topbar title="My idea" meta="Running… ~5 min remaining" />)
    expect(container.querySelector('[data-meta]')?.textContent).toBe('Running… ~5 min remaining')
  })

  it('omits the meta element when meta prop is absent', () => {
    const { container } = render(<Topbar title="My idea" />)
    expect(container.querySelector('[data-meta]')).toBeNull()
  })

  it('renders Stop and Workspace action buttons', () => {
    const { container } = render(<Topbar title="x" />)
    const buttons = container.querySelectorAll('[data-action-buttons] button')
    const actions = Array.from(buttons).map(b => b.getAttribute('data-action'))
    expect(actions).toContain('stop')
    expect(actions).toContain('workspace')
  })

  it('renders action buttons as IconButtons (32×32)', () => {
    const { container } = render(<Topbar title="x" />)
    const stopBtn = container.querySelector('[data-action="stop"]') as HTMLElement
    expect(stopBtn.style.width).toBe('32px')
    expect(stopBtn.style.height).toBe('32px')
  })

  it('calls onStop when Stop button is clicked', () => {
    const onStop = vi.fn()
    const { container } = render(<Topbar title="x" onStop={onStop} />)
    fireEvent.click(container.querySelector('[data-action="stop"]')!)
    expect(onStop).toHaveBeenCalledOnce()
  })

  it('calls onWorkspace when Workspace button is clicked', () => {
    const onWorkspace = vi.fn()
    const { container } = render(<Topbar title="x" onWorkspace={onWorkspace} />)
    fireEvent.click(container.querySelector('[data-action="workspace"]')!)
    expect(onWorkspace).toHaveBeenCalledOnce()
  })

  it('details button is hidden (display:none)', () => {
    const { container } = render(<Topbar title="x" />)
    const detailsBtn = container.querySelector('[data-action="details"]') as HTMLElement
    expect(detailsBtn.style.display).toBe('none')
  })

  it('accepts a ReactNode in rightSlot and renders it', () => {
    const { container } = render(
      <Topbar title="x" rightSlot={<VerdictPill verdict="build" />} />
    )
    const slot = container.querySelector('[data-right-slot]')
    expect(slot).not.toBeNull()
    expect(slot?.querySelector('[data-verdict]')?.getAttribute('data-verdict')).toBe('build')
  })

  it('omits the right-slot wrapper when rightSlot is not provided', () => {
    const { container } = render(<Topbar title="x" />)
    expect(container.querySelector('[data-right-slot]')).toBeNull()
  })

  it('passes detailsActive to the Details button', () => {
    const { container } = render(<Topbar title="x" detailsActive={true} />)
    const detailsBtn = container.querySelector('[data-action="details"]')
    expect(detailsBtn?.getAttribute('data-active')).toBe('true')
  })
})
