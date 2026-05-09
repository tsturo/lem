import type { IpcMain } from 'electron'
import { IPC } from '../shared/ipc-channels'
import type { LibraryDB } from './library-db'

export function registerLibraryHandlers(ipcMain: IpcMain, db: LibraryDB): void {
  ipcMain.handle(IPC.LIBRARY_LIST, () => db.list())
}
