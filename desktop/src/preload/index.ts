import { contextBridge, ipcRenderer } from 'electron'
import { IPC } from '../shared/ipc-channels'
import type { Settings } from '../shared/types'

contextBridge.exposeInMainWorld('lem', {
  settings: {
    get: (): Promise<Settings> => ipcRenderer.invoke(IPC.SETTINGS_GET),
    set: (settings: Settings): Promise<void> => ipcRenderer.invoke(IPC.SETTINGS_SET, settings),
  },
})
