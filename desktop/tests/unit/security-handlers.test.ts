// @vitest-environment node
import { describe, it, expect, vi, beforeAll } from 'vitest'

type WillNavigateHandler = (event: { preventDefault: () => void }, url: string) => void
type WebContentsCreatedHandler = (event: unknown, contents: MockWebContents) => void

interface MockWebContents {
  on: ReturnType<typeof vi.fn>
  setWindowOpenHandler: ReturnType<typeof vi.fn>
}

// --- Captured state (filled during module load + whenReady trigger) ---
let whenReadyCb: (() => void) | null = null
let mainWindowWillNavigateHandler: WillNavigateHandler | null = null
let webContentsCreatedHandler: WebContentsCreatedHandler | null = null

const mockShellOpenExternal = vi.fn()

const mockMainWebContents: MockWebContents = {
  on: vi.fn((event: string, handler: WillNavigateHandler) => {
    if (event === 'will-navigate') {
      mainWindowWillNavigateHandler = handler
    }
  }),
  setWindowOpenHandler: vi.fn(),
}

const mockWin = {
  webContents: mockMainWebContents,
  once: vi.fn(),
  loadURL: vi.fn(),
  loadFile: vi.fn(),
}

const MockBrowserWindow = vi.fn(function () {
  return mockWin
})
;(MockBrowserWindow as unknown as { getAllWindows: ReturnType<typeof vi.fn> }).getAllWindows = vi.fn(
  () => [],
)

const mockApp = {
  getPath: vi.fn(() => '/tmp'),
  on: vi.fn((event: string, handler: WebContentsCreatedHandler) => {
    if (event === 'web-contents-created') {
      webContentsCreatedHandler = handler
    }
  }),
  whenReady: vi.fn(() => ({
    then: (cb: () => void) => {
      whenReadyCb = cb
      return { catch: vi.fn() }
    },
  })),
  quit: vi.fn(),
}

vi.mock('electron', () => ({
  app: mockApp,
  BrowserWindow: MockBrowserWindow,
  shell: { openExternal: mockShellOpenExternal },
  ipcMain: { handle: vi.fn() },
}))

vi.mock('../../src/main/ipc-register', () => ({ registerAllHandlers: vi.fn() }))
vi.mock('../../src/main/claude-ipc', () => ({ registerClaudeHandlers: vi.fn() }))
vi.mock('../../src/main/library-db', () => ({
  LibraryDB: vi.fn(function (this: { close: () => void }) {
    this.close = vi.fn()
  }),
}))
vi.mock('../../src/main/library-ipc', () => ({ registerLibraryHandlers: vi.fn() }))
vi.mock('../../src/main/workspace-reader', () => ({ WorkspaceReader: vi.fn(function () {}) }))
vi.mock('../../src/main/workspace-ipc', () => ({ registerWorkspaceHandlers: vi.fn() }))

beforeAll(async () => {
  await import('../../src/main/index')
  whenReadyCb!()
})

describe('will-navigate handler in main window', () => {
  it('prevents BrowserWindow navigation', () => {
    const event = { preventDefault: vi.fn() }
    mainWindowWillNavigateHandler!(event, 'https://attacker.com')
    expect(event.preventDefault).toHaveBeenCalled()
  })

  it('routes http URLs to system browser', () => {
    const event = { preventDefault: vi.fn() }
    mockShellOpenExternal.mockClear()
    mainWindowWillNavigateHandler!(event, 'http://example.com')
    expect(mockShellOpenExternal).toHaveBeenCalledWith('http://example.com')
  })

  it('routes https URLs to system browser', () => {
    const event = { preventDefault: vi.fn() }
    mockShellOpenExternal.mockClear()
    mainWindowWillNavigateHandler!(event, 'https://example.com')
    expect(mockShellOpenExternal).toHaveBeenCalledWith('https://example.com')
  })

  it('does not open file: URLs in system browser', () => {
    const event = { preventDefault: vi.fn() }
    mockShellOpenExternal.mockClear()
    mainWindowWillNavigateHandler!(event, 'file:///etc/passwd')
    expect(mockShellOpenExternal).not.toHaveBeenCalled()
    expect(event.preventDefault).toHaveBeenCalled()
  })
})

describe('web-contents-created global lockdown', () => {
  function makeFreshContents(): MockWebContents {
    return { on: vi.fn(), setWindowOpenHandler: vi.fn() }
  }

  it('registers a will-navigate blocker on new webContents', () => {
    const contents = makeFreshContents()
    webContentsCreatedHandler!({}, contents)
    expect(contents.on).toHaveBeenCalledWith('will-navigate', expect.any(Function))
  })

  it('the will-navigate blocker calls preventDefault', () => {
    const contents = makeFreshContents()
    webContentsCreatedHandler!({}, contents)
    const [, blocker] = (contents.on as ReturnType<typeof vi.fn>).mock.calls.find(
      ([ev]: [string]) => ev === 'will-navigate',
    )!
    const mockEvent = { preventDefault: vi.fn() }
    blocker(mockEvent)
    expect(mockEvent.preventDefault).toHaveBeenCalled()
  })

  it('sets window open handler to deny on new webContents', () => {
    const contents = makeFreshContents()
    webContentsCreatedHandler!({}, contents)
    expect(contents.setWindowOpenHandler).toHaveBeenCalledWith(expect.any(Function))
    const [denyFn] = (contents.setWindowOpenHandler as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(denyFn()).toEqual({ action: 'deny' })
  })
})
