import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { applyTheme } from '../../src/renderer/theme'

describe('applyTheme', () => {
  const attrs: Record<string, string> = {}
  const htmlEl = {
    setAttribute: (k: string, v: string) => {
      attrs[k] = v
    },
    getAttribute: (k: string) => attrs[k] ?? null,
  }

  beforeEach(() => {
    for (const k of Object.keys(attrs)) delete attrs[k]
    vi.stubGlobal('document', { documentElement: htmlEl })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sets data-theme=light', () => {
    applyTheme('light')
    expect(htmlEl.getAttribute('data-theme')).toBe('light')
  })

  it('sets data-theme=dark', () => {
    applyTheme('dark')
    expect(htmlEl.getAttribute('data-theme')).toBe('dark')
  })

  it('uses matchMedia result for auto', () => {
    vi.stubGlobal('window', {
      matchMedia: (q: string) => ({
        matches: q === '(prefers-color-scheme: dark)',
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    })
    applyTheme('auto')
    expect(htmlEl.getAttribute('data-theme')).toBe('dark')
  })
})
