import type { IpcMain } from 'electron'
import { IPC } from '../shared/ipc-channels'
import type { Settings } from '../shared/types'
import { readSettings, writeSettings } from './settings'

export function registerAllHandlers(ipcMain: IpcMain): void {
  ipcMain.handle(IPC.SETTINGS_GET, () => readSettings())
  ipcMain.handle(IPC.SETTINGS_SET, (_event, settings: Settings) => {
    writeSettings(settings)
  })
}
