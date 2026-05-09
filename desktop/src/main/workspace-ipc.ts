import type { IpcMain } from 'electron'
import { IPC } from '../shared/ipc-channels'
import type { WorkspaceReader } from './workspace-reader'

export function registerWorkspaceHandlers(ipcMain: IpcMain, reader: WorkspaceReader): void {
  ipcMain.handle(IPC.WORKSPACE_READ_BRIEF, (_event, workspacePath: string) =>
    reader.readBrief(workspacePath),
  )
}
