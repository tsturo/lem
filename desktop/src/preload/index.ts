import { contextBridge, ipcRenderer } from 'electron'
import { IPC } from '../shared/ipc-channels'
import type { Settings, LibraryItem } from '../shared/types'
import type { BriefData } from '../main/workspace-reader'

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
    openFile: (): Promise<string | null> => ipcRenderer.invoke(IPC.SHELL_OPEN_FILE),
  },
  library: {
    list: (): Promise<LibraryItem[]> => ipcRenderer.invoke(IPC.LIBRARY_LIST),
  },
  run: {
    start(args: { idea: string; stub?: boolean; replaySpeed?: number }): Promise<string> {
      return ipcRenderer.invoke(IPC.RUN_START, args)
    },
    cancel(runId: string): Promise<void> {
      return ipcRenderer.invoke(IPC.RUN_CANCEL, runId)
    },
    onEvent(callback: (event: unknown) => void): () => void {
      const listener = (_e: Electron.IpcRendererEvent, data: unknown) => callback(data)
      ipcRenderer.on(IPC.RUN_EVENT, listener)
      return () => ipcRenderer.removeListener(IPC.RUN_EVENT, listener)
    },
    onLog(callback: (logLine: unknown) => void): () => void {
      const listener = (_e: Electron.IpcRendererEvent, data: unknown) => callback(data)
      ipcRenderer.on(IPC.RUN_LOG, listener)
      return () => ipcRenderer.removeListener(IPC.RUN_LOG, listener)
    },
  },
  workspace: {
    readBrief: (workspacePath: string): Promise<BriefData> =>
      ipcRenderer.invoke(IPC.WORKSPACE_READ_BRIEF, workspacePath),
  },
})
