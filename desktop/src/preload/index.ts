import { contextBridge, ipcRenderer } from 'electron'
import { IPC } from '../shared/ipc-channels'
import type { Settings } from '../shared/types'

contextBridge.exposeInMainWorld('lem', {
  settings: {
    get: (): Promise<Settings> => ipcRenderer.invoke(IPC.SETTINGS_GET),
    set: (settings: Settings): Promise<void> => ipcRenderer.invoke(IPC.SETTINGS_SET, settings),
  },
  claude: {
    detect: (): Promise<string | null> => ipcRenderer.invoke(IPC.CLAUDE_DETECT),
    pickPath: (): Promise<string | null> => ipcRenderer.invoke(IPC.CLAUDE_PICK_PATH),
    login: (claudePath: string): Promise<void> => ipcRenderer.invoke(IPC.CLAUDE_LOGIN, claudePath),
  },
  shell: {
    openExternal: (url: string): Promise<void> => ipcRenderer.invoke(IPC.SHELL_OPEN_EXTERNAL, url),
  },
})
