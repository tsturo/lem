import type { Settings } from '../shared/types'

declare global {
  interface Window {
    lem: {
      settings: {
        get(): Promise<Settings>
        set(settings: Settings): Promise<void>
      }
    }
  }
}
