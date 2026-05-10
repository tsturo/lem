import type { IpcMain } from 'electron'
import { BrowserWindow } from 'electron'
import { IPC } from '../shared/ipc-channels'
import type { Settings } from '../shared/types'
import { readSettings, writeSettings } from './settings'
import { OrchestratorBridge } from './orchestrator-bridge'
import { registerOrchestratorHandlers } from './orchestrator-ipc'

export const bridge = new OrchestratorBridge()

export function registerAllHandlers(ipcMain: IpcMain): void {
  ipcMain.handle(IPC.SETTINGS_GET, () => readSettings())
  ipcMain.handle(IPC.SETTINGS_SET, (_event, settings: Settings) => {
    writeSettings(settings)
  })
  registerOrchestratorHandlers(ipcMain, bridge, () => BrowserWindow.getAllWindows()[0] ?? null)
}
