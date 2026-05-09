import { create } from 'zustand'
import type { LibraryItem } from '../../shared/types'

interface LibraryState {
  items:      LibraryItem[]
  selectedId: string | null
  load():     Promise<void>
  select(id: string): void
}

export const useLibrary = create<LibraryState>((set) => ({
  items:      [],
  selectedId: null,

  async load() {
    const items = await window.lem.library.list()
    set({ items })
  },

  select(id) {
    set({ selectedId: id })
  },
}))
