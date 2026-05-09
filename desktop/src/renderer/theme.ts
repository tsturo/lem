import type { Settings } from '../shared/types'

export function applyTheme(pref: Settings['theme']): void {
  const resolved =
    pref === 'auto'
      ? window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      : pref
  document.documentElement.setAttribute('data-theme', resolved)
}

export function watchSystemTheme(pref: Settings['theme']): () => void {
  if (pref !== 'auto') return () => {}
  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  const handler = () => applyTheme('auto')
  mq.addEventListener('change', handler)
  return () => mq.removeEventListener('change', handler)
}
