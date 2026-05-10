/// <reference types="vitest/globals" />
import { render, fireEvent, act } from '@testing-library/react'
import { RefineAgainButton } from './RefineAgainButton'

function renderBtn(props?: Partial<React.ComponentProps<typeof RefineAgainButton>>) {
  const onContinue = vi.fn()
  const onBranch   = vi.fn()
  const result = render(
    <RefineAgainButton onContinue={onContinue} onBranch={onBranch} {...props} />
  )
  return { ...result, onContinue, onBranch }
}

// --- Main click ---------------------------------------------------------------

describe('RefineAgainButton — main click', () => {
  it('calls onContinue once and not onBranch when main is clicked', () => {
    const { container, onContinue, onBranch } = renderBtn()
    fireEvent.click(container.querySelector('[data-main]')!)
    expect(onContinue).toHaveBeenCalledOnce()
    expect(onBranch).not.toHaveBeenCalled()
  })
})

// --- Chevron opens menu -------------------------------------------------------

describe('RefineAgainButton — chevron opens menu', () => {
  it('opens the menu when chevron is clicked', () => {
    const { container } = renderBtn()
    expect(container.querySelector('[role=menu]')).toBeNull()
    fireEvent.click(container.querySelector('[data-chevron]')!)
    expect(container.querySelector('[role=menu]')).not.toBeNull()
  })

  it('shows both menu items when open', () => {
    const { container } = renderBtn()
    fireEvent.click(container.querySelector('[data-chevron]')!)
    expect(container.querySelector('[data-menu-item="continue"]')).not.toBeNull()
    expect(container.querySelector('[data-menu-item="branch"]')).not.toBeNull()
  })
})

// --- Menu item clicks ---------------------------------------------------------

describe('RefineAgainButton — menu item clicks', () => {
  it('clicking "Continue this thread" calls onContinue and closes menu', () => {
    const { container, onContinue } = renderBtn()
    fireEvent.click(container.querySelector('[data-chevron]')!)
    fireEvent.click(container.querySelector('[data-menu-item="continue"]')!)
    expect(onContinue).toHaveBeenCalledOnce()
    expect(container.querySelector('[role=menu]')).toBeNull()
  })

  it('clicking "Branch alternative" calls onBranch once and closes menu', () => {
    const { container, onBranch } = renderBtn()
    fireEvent.click(container.querySelector('[data-chevron]')!)
    fireEvent.click(container.querySelector('[data-menu-item="branch"]')!)
    expect(onBranch).toHaveBeenCalledOnce()
    expect(container.querySelector('[role=menu]')).toBeNull()
  })
})

// --- Outside click closes menu ------------------------------------------------

describe('RefineAgainButton — outside click', () => {
  it('closes the menu on outside mousedown without firing any callback', () => {
    const { container, onContinue, onBranch } = renderBtn()
    fireEvent.click(container.querySelector('[data-chevron]')!)
    expect(container.querySelector('[role=menu]')).not.toBeNull()

    act(() => {
      fireEvent.mouseDown(document.body)
    })

    expect(container.querySelector('[role=menu]')).toBeNull()
    expect(onContinue).not.toHaveBeenCalled()
    expect(onBranch).not.toHaveBeenCalled()
  })
})

// --- Escape key ---------------------------------------------------------------

describe('RefineAgainButton — Escape key', () => {
  it('closes the menu when Escape is pressed', () => {
    const { container } = renderBtn()
    fireEvent.click(container.querySelector('[data-chevron]')!)
    expect(container.querySelector('[role=menu]')).not.toBeNull()

    act(() => {
      fireEvent.keyDown(document, { key: 'Escape' })
    })

    expect(container.querySelector('[role=menu]')).toBeNull()
  })
})

// --- Disabled state -----------------------------------------------------------

describe('RefineAgainButton — disabled', () => {
  it('main click is a no-op when disabled', () => {
    const { container, onContinue } = renderBtn({ disabled: true })
    fireEvent.click(container.querySelector('[data-main]')!)
    expect(onContinue).not.toHaveBeenCalled()
  })

  it('chevron click does not open menu when disabled', () => {
    const { container } = renderBtn({ disabled: true })
    fireEvent.click(container.querySelector('[data-chevron]')!)
    expect(container.querySelector('[role=menu]')).toBeNull()
  })
})
