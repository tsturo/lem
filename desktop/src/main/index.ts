import { app, BrowserWindow, shell, ipcMain } from 'electron'
import { join } from 'path'
import { registerAllHandlers, bridge } from './ipc-register'
import { registerClaudeHandlers } from './claude-ipc'
import { LibraryDB } from './library-db'
import { registerLibraryHandlers } from './library-ipc'
import { scanWorkspaces } from './workspace-scanner'
import { WorkspaceReader } from './workspace-reader'
import { registerWorkspaceHandlers } from './workspace-ipc'
import { registerIdeasHandlers } from './ipc/ideas'

const db = new LibraryDB(join(app.getPath('userData'), 'library.db'))
const workspaceReader = new WorkspaceReader()

function createWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    show: false,
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 14, y: 12 },
    backgroundColor: '#ffffff',
    webPreferences: {
      sandbox: true,
      contextIsolation: true,
      preload: join(__dirname, '../preload/index.js'),
    },
  })

  win.once('ready-to-show', () => win.show())

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  win.webContents.on('will-navigate', (event, url) => {
    event.preventDefault()
    const parsed = new URL(url)
    if (['http:', 'https:'].includes(parsed.protocol)) {
      shell.openExternal(url)
    }
  })

  if (process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'))
  }

  return win
}

app.whenReady().then(() => {
  app.on('web-contents-created', (_event, contents) => {
    contents.on('will-navigate', (e) => e.preventDefault())
    contents.setWindowOpenHandler(() => ({ action: 'deny' }))
  })

  registerAllHandlers(ipcMain)
  registerClaudeHandlers(ipcMain)
  registerLibraryHandlers(ipcMain, db)
  registerWorkspaceHandlers(ipcMain, workspaceReader)
  registerIdeasHandlers(ipcMain, { db, bridge })

  // Populate library from on-disk workspaces (CLI runs, crashed runs, etc.).
  // This makes ALL past runs visible regardless of how they were started.
  try {
    const imported = scanWorkspaces(db)
    if (imported > 0) {
      console.log(`[lem] Imported ${imported} workspace(s) into library`)
    }
  } catch (err) {
    console.error('[lem] Workspace scan failed:', err)
  }

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => db.close())
process.on('exit', () => db.close())
