import { create } from 'zustand'
import type { Settings } from '../../shared/types'

interface SettingsState extends Settings {
  setTheme: (theme: Settings['theme']) => Promise<void>
  load: () => Promise<void>
}

export const useSettings = create<SettingsState>((set, get) => ({
  theme: 'auto',
  claudePath: undefined,

  setTheme: async (theme) => {
    set({ theme })
    const current = await window.lem.settings.get()
    await window.lem.settings.set({ ...current, theme })
  },

  load: async () => {
    const settings = await window.lem.settings.get()
    set(settings)
  },
}))
