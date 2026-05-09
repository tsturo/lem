// @vitest-environment node
import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'

vi.mock('child_process', () => ({
  execFileSync: vi.fn().mockReturnValue(''),
  spawn: vi.fn(),
}))

import * as childProcess from 'child_process'
import { detectClaude } from '../../src/main/claude-detect'

type SpawnMock = ReturnType<typeof vi.fn>

function makeProc(exitCode: number) {
  return {
    on: vi.fn((event: string, cb: (code: number) => void) => {
      if (event === 'close') setTimeout(() => cb(exitCode), 0)
    }),
    kill: vi.fn(),
  }
}

describe('detectClaude', () => {
  const spawnMock = childProcess.spawn as unknown as SpawnMock

  beforeEach(() => {
    delete process.env['LEM_CLAUDE_BIN']
  })

  afterEach(() => {
    vi.clearAllMocks()
    delete process.env['LEM_CLAUDE_BIN']
  })

  it('returns null when candidatePaths is empty', async () => {
    const result = await detectClaude([])
    expect(result).toBeNull()
    expect(spawnMock).not.toHaveBeenCalled()
  })

  it('returns path when LEM_CLAUDE_BIN is set to a valid executable', async () => {
    process.env['LEM_CLAUDE_BIN'] = '/custom/claude'
    spawnMock.mockReturnValue(makeProc(0))

    const result = await detectClaude()

    expect(result).toBe('/custom/claude')
    expect(spawnMock).toHaveBeenCalledWith('/custom/claude', ['--version'])
  })

  it('returns null when LEM_CLAUDE_BIN binary fails validation', async () => {
    process.env['LEM_CLAUDE_BIN'] = '/bad/claude'
    spawnMock.mockReturnValue(makeProc(1))

    const result = await detectClaude()

    expect(result).toBeNull()
  })

  it('validates binary with spawn and returns path on exit 0', async () => {
    spawnMock.mockReturnValue(makeProc(0))

    const result = await detectClaude(['/fake/claude'])

    expect(result).toBe('/fake/claude')
    expect(spawnMock).toHaveBeenCalledWith('/fake/claude', ['--version'])
  })

  it('skips candidates where spawn exits non-zero', async () => {
    spawnMock.mockReturnValueOnce(makeProc(1)).mockReturnValueOnce(makeProc(0))

    const result = await detectClaude(['/bad/claude', '/good/claude'])

    expect(result).toBe('/good/claude')
  })
})
