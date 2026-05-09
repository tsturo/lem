import { type IpcMain, dialog, shell } from 'electron'
import { spawn } from 'child_process'
import { IPC } from '../shared/ipc-channels'
import { detectClaude } from './claude-detect'

export function registerClaudeHandlers(ipcMain: IpcMain): void {
  ipcMain.handle(IPC.CLAUDE_DETECT, () => detectClaude())

  ipcMain.handle(IPC.SHELL_OPEN_EXTERNAL, (_event, url: string) => {
    const parsed = new URL(url)
    if (!['http:', 'https:', 'mailto:'].includes(parsed.protocol)) {
      throw new Error(`Refusing to open URL with scheme ${parsed.protocol}`)
    }
    return shell.openExternal(url)
  })

  ipcMain.handle(IPC.CLAUDE_PICK_PATH, async () => {
    const { filePaths } = await dialog.showOpenDialog({
      properties: ['openFile'],
      title: 'Select Claude binary',
    })
    return filePaths[0] ?? null
  })

  ipcMain.handle(IPC.CLAUDE_LOGIN, async () => {
    const validatedPath = await detectClaude()
    if (!validatedPath) throw new Error('No validated claude binary found')
    spawn(validatedPath, ['/login'], {
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
