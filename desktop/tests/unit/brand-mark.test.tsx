import { render } from '@testing-library/react'
import { BrandMark } from '@/components/BrandMark'

describe('BrandMark', () => {
  it('renders 9 bars via [data-bar] attribute', () => {
    const { container } = render(<BrandMark />)
    const bars = container.querySelectorAll('[data-bar]')
    expect(bars).toHaveLength(9)
  })

  it('center bar is taller than outermost bar', () => {
    const { container } = render(<BrandMark />)
    const bars = container.querySelectorAll('[data-bar]')
    const centerBar = bars[4] as HTMLElement
    const outerBar = bars[0] as HTMLElement
    const centerHeight = parseFloat(centerBar.style.height)
    const outerHeight = parseFloat(outerBar.style.height)
    expect(centerHeight).toBeGreaterThan(outerHeight)
  })

  it('accepts size prop and applies it', () => {
    const { container } = render(<BrandMark size="42px" />)
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.style.width).toBe('42px')
    expect(wrapper.style.height).toBe('42px')
  })
})
