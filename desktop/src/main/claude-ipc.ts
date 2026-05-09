import { type IpcMain, dialog, shell } from 'electron'
import { spawn } from 'child_process'
import { IPC } from '../shared/ipc-channels'
import { detectClaude } from './claude-detect'

export function registerClaudeHandlers(ipcMain: IpcMain): void {
  ipcMain.handle(IPC.CLAUDE_DETECT, () => detectClaude())

  ipcMain.handle(IPC.SHELL_OPEN_EXTERNAL, (_event, url: string) => {
    shell.openExternal(url)
  })

  ipcMain.handle(IPC.CLAUDE_PICK_PATH, async () => {
    const { filePaths } = await dialog.showOpenDialog({
      properties: ['openFile'],
      title: 'Select Claude binary',
    })
    return filePaths[0] ?? null
  })

  ipcMain.handle(IPC.CLAUDE_LOGIN, (_event, claudePath: string) => {
    spawn(claudePath, ['/login'], {
      detached: true,
      stdio: 'ignore',
    }).unref()
  })

  ipcMain.handle(IPC.SHELL_OPEN_FILE, async () => {
    const { filePaths } = await dialog.showOpenDialog({
      properties: ['openFile'],
      title: 'Attach a file',
      filters: [
        {
          name: 'Images & documents',
          extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'md', 'txt'],
        },
      ],
    })
    return filePaths[0] ?? null
  })
}
