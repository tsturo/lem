import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useLibrary } from '@/store/library'
import type { LibraryItem } from '../../src/shared/types'

const COMPLETED_ITEM: LibraryItem = {
  runId:     'run-abc',
  idea:      'A calendar app',
  verdict:   'build',
  status:    'completed',
  createdAt: '2026-05-09T10:00:00.000Z',
  updatedAt: '2026-05-09T10:30:00.000Z',
}

const RUNNING_ITEM: LibraryItem = {
  runId:     'run-def',
  idea:      'A todo list',
  verdict:   null,
  status:    'running',
  createdAt: '2026-05-09T11:00:00.000Z',
  updatedAt: '2026-05-09T11:05:00.000Z',
}

describe('useLibrary', () => {
  beforeEach(() => {
    useLibrary.setState({ items: [], selectedId: null })
    ;(window as unknown as { lem: unknown }).lem = {
      library: { list: vi.fn().mockResolvedValue([]) },
    }
  })

  it('starts with empty items and null selectedId', () => {
    const state = useLibrary.getState()
    expect(state.items).toEqual([])
    expect(state.selectedId).toBeNull()
  })

  it('load() populates items from window.lem.library.list', async () => {
    const { lem } = window as unknown as { lem: { library: { list: ReturnType<typeof vi.fn> } } }
    lem.library.list.mockResolvedValue([COMPLETED_ITEM])
    await useLibrary.getState().load()
    expect(useLibrary.getState().items).toEqual([COMPLETED_ITEM])
  })

  it('load() with empty server response leaves items empty', async () => {
    await useLibrary.getState().load()
    expect(useLibrary.getState().items).toEqual([])
  })

  it('load() replaces all existing items on subsequent calls', async () => {
    const { lem } = window as unknown as { lem: { library: { list: ReturnType<typeof vi.fn> } } }
    lem.library.list.mockResolvedValue([COMPLETED_ITEM, RUNNING_ITEM])
    await useLibrary.getState().load()
    expect(useLibrary.getState().items).toHaveLength(2)

    lem.library.list.mockResolvedValue([COMPLETED_ITEM])
    await useLibrary.getState().load()
    expect(useLibrary.getState().items).toHaveLength(1)
    expect(useLibrary.getState().items[0].runId).toBe('run-abc')
  })

  it('select() sets selectedId to the given runId', () => {
    useLibrary.getState().select('run-abc')
    expect(useLibrary.getState().selectedId).toBe('run-abc')
  })

  it('select() can be called multiple times, retaining the last id', () => {
    useLibrary.getState().select('run-abc')
    useLibrary.getState().select('run-def')
    expect(useLibrary.getState().selectedId).toBe('run-def')
  })
})
