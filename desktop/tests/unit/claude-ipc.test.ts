// @vitest-environment node
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('electron', () => ({
  dialog: { showOpenDialog: vi.fn() },
  shell: { openExternal: vi.fn() },
}))

vi.mock('child_process', () => ({
  spawn: vi.fn(),
}))

vi.mock('../../src/main/claude-detect', () => ({
  detectClaude: vi.fn(),
}))

import * as childProcess from 'child_process'
import * as claudeDetect from '../../src/main/claude-detect'
import { registerClaudeHandlers } from '../../src/main/claude-ipc'

type SpawnMock = ReturnType<typeof vi.fn>
type DetectMock = ReturnType<typeof vi.fn>

function makeIpcMain() {
  const handlers: Record<string, (...args: unknown[]) => unknown> = {}
  return {
    handle: vi.fn((channel: string, handler: (...args: unknown[]) => unknown) => {
      handlers[channel] = handler
    }),
    invoke: (channel: string, ...args: unknown[]) => handlers[channel]?.({}, ...args),
  }
}

describe('CLAUDE_LOGIN IPC handler', () => {
  const spawnMock = childProcess.spawn as unknown as SpawnMock
  const detectMock = claudeDetect.detectClaude as unknown as DetectMock

  beforeEach(() => {
    vi.clearAllMocks()
    spawnMock.mockReturnValue({ unref: vi.fn() })
  })

  it('spawns the validated path from detectClaude, ignoring any renderer-supplied path', async () => {
    detectMock.mockResolvedValue('/opt/homebrew/bin/claude')
    const ipcMain = makeIpcMain()
    registerClaudeHandlers(ipcMain as never)

    await ipcMain.invoke('claude:login', '/tmp/evil-binary')

    expect(detectMock).toHaveBeenCalled()
    expect(spawnMock).toHaveBeenCalledWith('/opt/homebrew/bin/claude', ['/login'], expect.any(Object))
    expect(spawnMock).not.toHaveBeenCalledWith('/tmp/evil-binary', expect.anything(), expect.anything())
  })

  it('rejects arbitrary unauthorized paths by never spawning them', async () => {
    detectMock.mockResolvedValue('/usr/local/bin/claude')
    const ipcMain = makeIpcMain()
    registerClaudeHandlers(ipcMain as never)

    for (const evilPath of ['/bin/bash', '/tmp/evil', '/usr/bin/python3']) {
      vi.clearAllMocks()
      spawnMock.mockReturnValue({ unref: vi.fn() })
      detectMock.mockResolvedValue('/usr/local/bin/claude')

      await ipcMain.invoke('claude:login', evilPath)

      expect(spawnMock).not.toHaveBeenCalledWith(evilPath, expect.anything(), expect.anything())
      expect(spawnMock).toHaveBeenCalledWith('/usr/local/bin/claude', ['/login'], expect.any(Object))
    }
  })

  it('throws when detectClaude returns null (no valid claude binary)', async () => {
    detectMock.mockResolvedValue(null)
    const ipcMain = makeIpcMain()
    registerClaudeHandlers(ipcMain as never)

    await expect(ipcMain.invoke('claude:login')).rejects.toThrow('No validated claude binary found')
    expect(spawnMock).not.toHaveBeenCalled()
  })

  it('spawns with detached: true and stdio: ignore', async () => {
    detectMock.mockResolvedValue('/opt/homebrew/bin/claude')
    const ipcMain = makeIpcMain()
    registerClaudeHandlers(ipcMain as never)

    await ipcMain.invoke('claude:login')

    expect(spawnMock).toHaveBeenCalledWith(
      '/opt/homebrew/bin/claude',
      ['/login'],
      { detached: true, stdio: 'ignore' },
    )
  })
})
