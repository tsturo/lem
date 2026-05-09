import { app, BrowserWindow, shell, ipcMain } from 'electron'
import { join } from 'path'
import { registerAllHandlers } from './ipc-register'
import { registerClaudeHandlers } from './claude-ipc'
import { LibraryDB } from './library-db'
import { registerLibraryHandlers } from './library-ipc'

const db = new LibraryDB(join(app.getPath('userData'), 'library.db'))

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

  if (process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'))
  }

  return win
}

app.whenReady().then(() => {
  registerAllHandlers(ipcMain)
  registerClaudeHandlers(ipcMain)
  registerLibraryHandlers(ipcMain, db)
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
