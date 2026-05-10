import type { IpcMain } from 'electron'
import { IPC } from '../../shared/ipc-channels'
import type { Idea, RunRow, RefineRequest, RefineResponse } from '../../shared/types'
import type { LibraryDB } from '../library-db'
import type { OrchestratorBridge } from '../orchestrator-bridge'

const ID_RE = /^[A-Za-z0-9_-]+$/

function validateId(value: unknown, field: string): string {
  if (typeof value !== 'string' || value.length === 0 || value.length > 64 || !ID_RE.test(value)) {
    throw new Error(`invalid ${field}: must be a non-empty string ≤64 chars matching /^[A-Za-z0-9_-]+$/`)
  }
  return value
}

function validateTitle(value: unknown): string {
  if (typeof value !== 'string' || value.length < 1 || value.length > 200) {
    throw new Error('invalid newTitle: must be a string of length 1–200')
  }
  return value
}

function validateLabel(value: unknown, field: string): string | null {
  if (value === null) return null
  if (typeof value !== 'string') throw new Error(`invalid ${field}: must be string or null`)
  if (value.length === 0) throw new Error(`invalid ${field}: use null instead of empty string`)
  if (value.length > 64 || !ID_RE.test(value)) {
    throw new Error(`invalid ${field}: must be ≤64 chars matching /^[A-Za-z0-9_-]+$/`)
  }
  return value
}

function validateRefineRequest(value: unknown): RefineRequest {
  if (typeof value !== 'object' || value === null) {
    throw new Error('invalid request: expected object')
  }
  const req = value as Record<string, unknown>

  if (typeof req['idea'] !== 'string' || req['idea'].length < 1 || req['idea'].length > 2000) {
    throw new Error('invalid idea: must be a string of length 1–2000')
  }
  if (req['parentRunId'] !== undefined) {
    validateId(req['parentRunId'], 'parentRunId')
  }
  if (req['branchLabel'] !== undefined) {
    validateLabel(req['branchLabel'], 'branchLabel')
  }
  if (req['contextText'] !== undefined) {
    if (typeof req['contextText'] !== 'string' || req['contextText'].length > 8000) {
      throw new Error('invalid contextText: must be a string ≤8000 chars')
    }
  }

  return {
    idea: req['idea'] as string,
    parentRunId: req['parentRunId'] as string | undefined,
    branchLabel: req['branchLabel'] as string | undefined,
    contextText: req['contextText'] as string | undefined,
  }
}

export function registerIdeasHandlers(
  ipcMain: IpcMain,
  deps: { db: LibraryDB; bridge: OrchestratorBridge },
): void {
  const { db, bridge } = deps

  ipcMain.handle(IPC.IDEAS_LIST, (): Idea[] => db.listIdeas())

  ipcMain.handle(IPC.IDEAS_GET_ROUNDS, (_event, ideaId: unknown): RunRow[] =>
    db.getRoundsForIdea(validateId(ideaId, 'ideaId')),
  )

  ipcMain.handle(IPC.IDEAS_GET_DAG, (_event, ideaId: unknown): RunRow[] =>
    db.getRunDag(validateId(ideaId, 'ideaId')),
  )

  ipcMain.handle(IPC.IDEAS_RENAME, (_event, ideaId: unknown, newTitle: unknown): void => {
    db.renameIdea(validateId(ideaId, 'ideaId'), validateTitle(newTitle))
  })

  ipcMain.handle(
    IPC.RUNS_REFINE,
    async (_event, req: unknown): Promise<RefineResponse> => {
      const validated = validateRefineRequest(req)
      const { runId } = await bridge.spawnRefine(validated)
      return { runId }
    },
  )

  ipcMain.handle(IPC.RUNS_SET_BRANCH_LABEL, (_event, runId: unknown, label: unknown): void => {
    db.setBranchLabel(validateId(runId, 'runId'), validateLabel(label, 'label'))
  })
}
