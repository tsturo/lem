// @vitest-environment node
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { EventEmitter } from 'events'
import * as path from 'path'
import * as fs from 'fs'

// ---------------------------------------------------------------------------
// Mock child_process.spawn before importing the module under test
// ---------------------------------------------------------------------------

class MockChildProcess extends EventEmitter {
  stdin = { on: vi.fn() }
  stdout = new EventEmitter()
  stderr = new EventEmitter()
  kill = vi.fn()
}

let mockChild: MockChildProcess

vi.mock('child_process', () => ({
  spawn: vi.fn(() => mockChild),
}))

// ---------------------------------------------------------------------------
// Import after mocking
// ---------------------------------------------------------------------------

import { OrchestratorBridge } from '../../src/main/orchestrator-bridge'
import { spawn } from 'child_process'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeEvent(overrides: Partial<Record<string, unknown>> = {}): Record<string, unknown> {
  return {
    kind: 'phase_start',
    phase_id: '0.5',
    roles: ['jtbd-extractor'],
    duration_s: 0,
    cost_usd: 0,
    success: true,
    timestamp: 1746784800,
    ...overrides,
  }
}

function jsonLine(obj: Record<string, unknown>): Buffer {
  return Buffer.from(JSON.stringify(obj) + '\n')
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('OrchestratorBridge', () => {
  let bridge: OrchestratorBridge

  beforeEach(() => {
    mockChild = new MockChildProcess()
    vi.clearAllMocks()
    bridge = new OrchestratorBridge()
  })

  afterEach(() => {
    bridge.destroy()
  })

  describe('real mode — stdout parsing', () => {
    it('parses a complete JSON line from stdout into a progress event', () => {
      const received: unknown[] = []
      bridge.on('event', (e) => received.push(e))

      bridge.start('test idea')

      mockChild.stdout.emit('data', jsonLine(makeEvent()))

      expect(received).toHaveLength(1)
      expect(received[0]).toMatchObject({ kind: 'phase_start', phase_id: '0.5' })
    })

    it('buffers a partial JSON line and emits only after the newline arrives', () => {
      const received: unknown[] = []
      bridge.on('event', (e) => received.push(e))

      bridge.start('test idea')

      const full = JSON.stringify(makeEvent({ phase_id: '0.6' }))
      const half = full.slice(0, Math.floor(full.length / 2))
      const rest = full.slice(Math.floor(full.length / 2)) + '\n'

      mockChild.stdout.emit('data', Buffer.from(half))
      expect(received).toHaveLength(0)

      mockChild.stdout.emit('data', Buffer.from(rest))
      expect(received).toHaveLength(1)
      expect((received[0] as Record<string, unknown>).phase_id).toBe('0.6')
    })

    it('handles multiple events in a single data chunk', () => {
      const received: unknown[] = []
      bridge.on('event', (e) => received.push(e))

      bridge.start('test idea')

      const chunk = Buffer.from(
        JSON.stringify(makeEvent({ phase_id: '1' })) + '\n' +
        JSON.stringify(makeEvent({ phase_id: '1.5' })) + '\n',
      )
      mockChild.stdout.emit('data', chunk)

      expect(received).toHaveLength(2)
      expect((received[0] as Record<string, unknown>).phase_id).toBe('1')
      expect((received[1] as Record<string, unknown>).phase_id).toBe('1.5')
    })

    it('silently ignores non-JSON stdout lines', () => {
      const received: unknown[] = []
      bridge.on('event', (e) => received.push(e))

      bridge.start('test idea')

      mockChild.stdout.emit('data', Buffer.from('not json at all\n'))
      expect(received).toHaveLength(0)
    })
  })

  describe('real mode — cancel', () => {
    it('sends SIGTERM to the child process when cancel is called', () => {
      bridge.start('test idea')
      bridge.cancel('run-123')

      expect(mockChild.kill).toHaveBeenCalledOnce()
      expect(mockChild.kill).toHaveBeenCalledWith('SIGTERM')
    })

    it('sends SIGKILL if the child is still alive after 10 s', async () => {
      vi.useFakeTimers()
      bridge.start('test idea')
      bridge.cancel('run-123')

      vi.advanceTimersByTime(10_000)

      expect(mockChild.kill).toHaveBeenCalledTimes(2)
      expect(mockChild.kill).toHaveBeenNthCalledWith(2, 'SIGKILL')

      vi.useRealTimers()
    })

    it('does not send SIGKILL if the child exits within the grace period', async () => {
      vi.useFakeTimers()
      bridge.start('test idea')
      bridge.cancel('run-123')

      // Child exits cleanly before the 10 s timer fires
      mockChild.emit('close', 0, null)

      vi.advanceTimersByTime(10_000)

      // SIGTERM only — SIGKILL must not have been sent
      expect(mockChild.kill).toHaveBeenCalledOnce()
      expect(mockChild.kill).toHaveBeenCalledWith('SIGTERM')

      vi.useRealTimers()
    })
  })

  describe('real mode — exit events', () => {
    it('emits auth_expired and exit when child exits with code 69', () => {
      const authExpiredCalls: unknown[] = []
      const exitCalls: unknown[] = []
      bridge.on('auth_expired', () => authExpiredCalls.push(true))
      bridge.on('exit', (info) => exitCalls.push(info))

      bridge.start('test idea')
      mockChild.emit('close', 69, null)

      expect(authExpiredCalls).toHaveLength(1)
      expect(exitCalls).toHaveLength(1)
      expect((exitCalls[0] as Record<string, unknown>).code).toBe(69)
    })

    it('emits exit but not auth_expired for a normal exit code', () => {
      const authExpiredCalls: unknown[] = []
      const exitCalls: unknown[] = []
      bridge.on('auth_expired', () => authExpiredCalls.push(true))
      bridge.on('exit', (info) => exitCalls.push(info))

      bridge.start('test idea')
      mockChild.emit('close', 0, null)

      expect(authExpiredCalls).toHaveLength(0)
      expect(exitCalls).toHaveLength(1)
      expect((exitCalls[0] as Record<string, unknown>).code).toBe(0)
    })

    it('emits exit with an error when the child process errors', () => {
      const exitCalls: unknown[] = []
      bridge.on('exit', (info) => exitCalls.push(info))

      bridge.start('test idea')
      mockChild.emit('error', new Error('spawn failed'))

      expect(exitCalls).toHaveLength(1)
      const info = exitCalls[0] as Record<string, unknown>
      expect(info.error).toBeInstanceOf(Error)
    })

    it('passes detached: false to spawn to prevent orphan processes', () => {
      bridge.start('test idea')

      const spawnMock = spawn as ReturnType<typeof vi.fn>
      const opts = spawnMock.mock.calls[0][2] as Record<string, unknown>
      expect(opts.detached).toBeFalsy()
    })
  })

  describe('real mode — stderr capture', () => {
    it('captures stderr output and includes it in exit info on non-zero exit', () => {
      const exitCalls: unknown[] = []
      bridge.on('exit', (info) => exitCalls.push(info))

      bridge.start('test idea')

      mockChild.stderr.emit(
        'data',
        Buffer.from('Traceback (most recent call last):\n  File "app.py", line 1\nRuntimeError: crash\n'),
      )
      mockChild.emit('close', 1, null)

      expect(exitCalls).toHaveLength(1)
      const info = exitCalls[0] as Record<string, unknown>
      expect(typeof info.stderr).toBe('string')
      expect(info.stderr as string).toContain('RuntimeError: crash')
    })

    it('does not include stderr in exit info on successful exit', () => {
      const exitCalls: unknown[] = []
      bridge.on('exit', (info) => exitCalls.push(info))

      bridge.start('test idea')

      mockChild.stderr.emit('data', Buffer.from('some warning output\n'))
      mockChild.emit('close', 0, null)

      expect(exitCalls).toHaveLength(1)
      const info = exitCalls[0] as Record<string, unknown>
      expect(info.stderr).toBeUndefined()
    })

    it('bounds the rolling stderr buffer to 100 lines', () => {
      const exitCalls: unknown[] = []
      bridge.on('exit', (info) => exitCalls.push(info))

      bridge.start('test idea')

      const lines = Array.from({ length: 200 }, (_, i) => `line ${i}`).join('\n') + '\n'
      mockChild.stderr.emit('data', Buffer.from(lines))
      mockChild.emit('close', 1, null)

      expect(exitCalls).toHaveLength(1)
      const info = exitCalls[0] as Record<string, unknown>
      expect(typeof info.stderr).toBe('string')
      const captured = (info.stderr as string).split('\n')
      expect(captured.length).toBeLessThanOrEqual(100)
      // Rolling window keeps the last 100 lines (100–199)
      expect(captured[0]).toBe('line 100')
      expect(captured[captured.length - 1]).toBe('line 199')
    })

    it('includes stderr in exit info when the child process errors', () => {
      const exitCalls: unknown[] = []
      bridge.on('exit', (info) => exitCalls.push(info))

      bridge.start('test idea')

      mockChild.stderr.emit('data', Buffer.from('spawn error detail\n'))
      mockChild.emit('error', new Error('spawn failed'))

      expect(exitCalls).toHaveLength(1)
      const info = exitCalls[0] as Record<string, unknown>
      expect(info.stderr as string).toContain('spawn error detail')
    })
  })

  describe('stub mode', () => {
    const fixtureDir = path.join(__dirname, '..', 'fixtures')
    const fixturePath = path.join(fixtureDir, 'stub-events.jsonl')

    it('emits events in timestamp order', async () => {
      const received: Array<{ timestamp: number }> = []
      bridge.on('event', (e) => received.push(e as { timestamp: number }))

      bridge.start('test idea', { stub: true, replaySpeed: 1_000_000 })

      await new Promise<void>((resolve) => bridge.once('exit', () => resolve()))

      expect(received.length).toBeGreaterThan(0)
      for (let i = 1; i < received.length; i++) {
        expect(received[i].timestamp).toBeGreaterThanOrEqual(received[i - 1].timestamp)
      }
    })

    it('emits an exit event after all stub events are replayed', async () => {
      const exitInfo: unknown[] = []
      bridge.on('exit', (info) => exitInfo.push(info))

      bridge.start('test idea', { stub: true, replaySpeed: 1_000_000 })

      await new Promise<void>((resolve) => bridge.once('exit', () => resolve()))

      expect(exitInfo).toHaveLength(1)
      expect((exitInfo[0] as Record<string, unknown>).code).toBe(0)
    })

    it('emits all phases from the fixture', async () => {
      const phaseIds = new Set<string>()
      bridge.on('event', (e) => phaseIds.add((e as Record<string, unknown>).phase_id as string))

      bridge.start('test idea', { stub: true, replaySpeed: 1_000_000 })

      await new Promise<void>((resolve) => bridge.once('exit', () => resolve()))

      const expectedPhases = ['0', '0.5', '0.6', '1', '1.5', '2.1', '2.2', '2.3', '2.5', '3', '4']
      for (const phase of expectedPhases) {
        expect(phaseIds.has(phase), `phase ${phase} should be present`).toBe(true)
      }
    })

    it('emits exit with error if the stub file is missing', async () => {
      process.env['LEM_DESKTOP_STUB_EVENTS'] = '/nonexistent/path/stub-events.jsonl'

      const exitInfo: unknown[] = []
      bridge.on('exit', (info) => exitInfo.push(info))

      bridge.start('test idea', { stub: true })

      await new Promise<void>((resolve) => bridge.once('exit', () => resolve()))

      expect((exitInfo[0] as Record<string, unknown>).error).toBeInstanceOf(Error)

      delete process.env['LEM_DESKTOP_STUB_EVENTS']
    })

    it('does not call spawn in stub mode', () => {
      bridge.start('test idea', { stub: true, replaySpeed: 1_000_000 })
      expect(spawn).not.toHaveBeenCalled()
    })
  })
})
