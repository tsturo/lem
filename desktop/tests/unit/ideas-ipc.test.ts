// @vitest-environment node
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { registerIdeasHandlers } from '../../src/main/ipc/ideas'
import type { Idea, RunRow } from '../../src/shared/types'

function makeIpcMain() {
  const handlers: Record<string, (...args: unknown[]) => unknown> = {}
  return {
    handle: vi.fn((channel: string, handler: (...args: unknown[]) => unknown) => {
      handlers[channel] = handler
    }),
    invoke: async (channel: string, ...args: unknown[]) => handlers[channel]?.({}, ...args),
  }
}

function makeDb() {
  return {
    listIdeas: vi.fn((): Idea[] => []),
    getRoundsForIdea: vi.fn((_id: string): RunRow[] => []),
    getRunDag: vi.fn((_id: string): RunRow[] => []),
    renameIdea: vi.fn(),
    setBranchLabel: vi.fn(),
  }
}

function makeBridge() {
  return {
    spawnRefine: vi.fn(),
  }
}

describe('ideas IPC handlers', () => {
  let ipcMain: ReturnType<typeof makeIpcMain>
  let db: ReturnType<typeof makeDb>
  let bridge: ReturnType<typeof makeBridge>

  beforeEach(() => {
    ipcMain = makeIpcMain()
    db = makeDb()
    bridge = makeBridge()
    registerIdeasHandlers(ipcMain as never, { db: db as never, bridge: bridge as never })
  })

  describe('ideas:list', () => {
    it('returns listIdeas result', async () => {
      const ideas: Idea[] = [{ id: 'idea-1', title: 'My idea', createdAt: 1234 }]
      db.listIdeas.mockReturnValue(ideas)
      const result = await ipcMain.invoke('ideas:list')
      expect(result).toEqual(ideas)
      expect(db.listIdeas).toHaveBeenCalled()
    })
  })

  describe('ideas:get-rounds', () => {
    it('returns rounds for a valid ideaId', async () => {
      const rows: RunRow[] = [
        {
          runId: 'r-1',
          idea: 'test',
          verdict: null,
          status: 'completed',
          group: 'done',
          workspacePath: '',
          createdAt: '',
          updatedAt: '',
        },
      ]
      db.getRoundsForIdea.mockReturnValue(rows)
      const result = await ipcMain.invoke('ideas:get-rounds', 'idea-abc')
      expect(result).toEqual(rows)
      expect(db.getRoundsForIdea).toHaveBeenCalledWith('idea-abc')
    })

    it('rejects invalid ideaId with bad characters (a/b)', async () => {
      await expect(ipcMain.invoke('ideas:get-rounds', 'a/b')).rejects.toThrow('invalid ideaId')
    })

    it('rejects ideaId longer than 64 chars', async () => {
      await expect(ipcMain.invoke('ideas:get-rounds', 'a'.repeat(65))).rejects.toThrow('invalid ideaId')
    })

    it('rejects empty ideaId', async () => {
      await expect(ipcMain.invoke('ideas:get-rounds', '')).rejects.toThrow('invalid ideaId')
    })

    it('rejects non-string ideaId', async () => {
      await expect(ipcMain.invoke('ideas:get-rounds', 123)).rejects.toThrow('invalid ideaId')
    })
  })

  describe('ideas:get-dag', () => {
    it('returns DAG for a valid ideaId', async () => {
      const rows: RunRow[] = []
      db.getRunDag.mockReturnValue(rows)
      const result = await ipcMain.invoke('ideas:get-dag', 'idea-xyz')
      expect(result).toEqual(rows)
      expect(db.getRunDag).toHaveBeenCalledWith('idea-xyz')
    })

    it('rejects invalid ideaId (path traversal attempt)', async () => {
      await expect(ipcMain.invoke('ideas:get-dag', '../etc/passwd')).rejects.toThrow('invalid ideaId')
    })
  })

  describe('ideas:rename', () => {
    it('calls renameIdea with valid inputs', async () => {
      await ipcMain.invoke('ideas:rename', 'idea-1', 'New Title')
      expect(db.renameIdea).toHaveBeenCalledWith('idea-1', 'New Title')
    })

    it('rejects invalid ideaId', async () => {
      await expect(ipcMain.invoke('ideas:rename', 'bad/id', 'Title')).rejects.toThrow('invalid ideaId')
    })

    it('rejects empty newTitle', async () => {
      await expect(ipcMain.invoke('ideas:rename', 'idea-1', '')).rejects.toThrow('invalid newTitle')
    })

    it('rejects newTitle longer than 200 chars', async () => {
      await expect(ipcMain.invoke('ideas:rename', 'idea-1', 'x'.repeat(201))).rejects.toThrow(
        'invalid newTitle',
      )
    })

    it('rejects non-string newTitle', async () => {
      await expect(ipcMain.invoke('ideas:rename', 'idea-1', null)).rejects.toThrow('invalid newTitle')
    })
  })

  describe('runs:refine', () => {
    it('calls spawnRefine and returns { runId }', async () => {
      const mockChild = {}
      bridge.spawnRefine.mockResolvedValue({ runId: 'r-123', child: mockChild })
      const result = await ipcMain.invoke('runs:refine', { idea: 'My new product idea' })
      expect(bridge.spawnRefine).toHaveBeenCalledWith({ idea: 'My new product idea' })
      expect(result).toEqual({ runId: 'r-123' })
    })

    it('passes optional fields through to spawnRefine', async () => {
      bridge.spawnRefine.mockResolvedValue({ runId: 'r-456', child: {} })
      const req = {
        idea: 'Iterate on this',
        parentRunId: 'run-parent',
        branchLabel: 'branch-A',
        contextText: 'some context',
      }
      await ipcMain.invoke('runs:refine', req)
      expect(bridge.spawnRefine).toHaveBeenCalledWith(req)
    })

    it('rejects when idea is missing', async () => {
      await expect(ipcMain.invoke('runs:refine', {})).rejects.toThrow('invalid idea')
    })

    it('rejects when idea exceeds 2000 chars', async () => {
      await expect(
        ipcMain.invoke('runs:refine', { idea: 'x'.repeat(2001) }),
      ).rejects.toThrow('invalid idea')
    })

    it('rejects when parentRunId fails the id regex', async () => {
      await expect(
        ipcMain.invoke('runs:refine', { idea: 'valid idea', parentRunId: 'bad/id' }),
      ).rejects.toThrow('invalid parentRunId')
    })

    it('rejects when contextText exceeds 8000 chars', async () => {
      await expect(
        ipcMain.invoke('runs:refine', { idea: 'valid idea', contextText: 'x'.repeat(8001) }),
      ).rejects.toThrow('invalid contextText')
    })

    it('rejects when request is not an object', async () => {
      await expect(ipcMain.invoke('runs:refine', 'not-an-object')).rejects.toThrow('invalid request')
    })
  })

  describe('runs:set-branch-label', () => {
    it('calls setBranchLabel with a valid label', async () => {
      await ipcMain.invoke('runs:set-branch-label', 'run-abc', 'feature-x')
      expect(db.setBranchLabel).toHaveBeenCalledWith('run-abc', 'feature-x')
    })

    it('calls setBranchLabel with null (clear label)', async () => {
      await ipcMain.invoke('runs:set-branch-label', 'run-abc', null)
      expect(db.setBranchLabel).toHaveBeenCalledWith('run-abc', null)
    })

    it('rejects invalid runId (regex fail)', async () => {
      await expect(ipcMain.invoke('runs:set-branch-label', 'run/bad', 'label')).rejects.toThrow(
        'invalid runId',
      )
    })

    it('rejects empty string label (use null instead)', async () => {
      await expect(ipcMain.invoke('runs:set-branch-label', 'run-abc', '')).rejects.toThrow(
        'invalid label',
      )
    })

    it('rejects label longer than 64 chars', async () => {
      await expect(
        ipcMain.invoke('runs:set-branch-label', 'run-abc', 'a'.repeat(65)),
      ).rejects.toThrow('invalid label')
    })

    it('rejects non-string, non-null label', async () => {
      await expect(ipcMain.invoke('runs:set-branch-label', 'run-abc', 42)).rejects.toThrow(
        'invalid label',
      )
    })
  })
})
