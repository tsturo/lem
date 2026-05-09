import { EventEmitter } from 'events'
import { spawn, ChildProcess } from 'child_process'
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import { tailJsonl } from './tail-jsonl'
import type { LogLine, ProgressEvent } from '../types/lem-events'

export interface StartOptions {
  stub?: boolean
  replaySpeed?: number
}

export interface ExitInfo {
  code: number | null
  signal: NodeJS.Signals | null
  error?: Error
  stderr?: string
}

function stubEventsPath(): string {
  return (
    process.env['LEM_DESKTOP_STUB_EVENTS'] ??
    path.join(__dirname, '..', '..', 'tests', 'fixtures', 'stub-events.jsonl')
  )
}

function lemRunsDir(): string {
  const xdgData =
    process.env['XDG_DATA_HOME'] ?? path.join(os.homedir(), '.local', 'share')
  return path.join(xdgData, 'lem', 'runs')
}

const STDERR_MAX_LINES = 100
const STDERR_MAX_BYTES = 64 * 1024

export class OrchestratorBridge extends EventEmitter {
  private child: ChildProcess | null = null
  private killTimer: ReturnType<typeof setTimeout> | null = null
  private logCleanup: (() => void) | null = null
  private stderrLines: string[] = []
  private stderrBytes = 0

  start(idea: string, options: StartOptions = {}): string {
    this._cleanup()
    const runId = `run-${Date.now()}`

    if (options.stub === true || process.env['LEM_DESKTOP_STUB_RUN'] === '1') {
      this._replayStub(options.replaySpeed ?? 10)
    } else {
      this._spawnLem(idea)
    }

    return runId
  }

  cancel(_runId: string): void {
    if (!this.child) return
    this.child.kill('SIGTERM')
    this.killTimer = setTimeout(() => {
      if (this.child) {
        this.child.kill('SIGKILL')
      }
      this.killTimer = null
    }, 10_000)
  }

  private _spawnLem(idea: string): void {
    this.stderrLines = []
    this.stderrBytes = 0

    const child = spawn('lem', ['refine', idea, '--json-events', '--skip-intake'], {
      stdio: ['pipe', 'pipe', 'pipe'],
      detached: false,
    })
    this.child = child

    child.stdin!.on('error', () => {})

    let stdoutBuf = ''
    child.stdout!.on('data', (chunk: Buffer) => {
      stdoutBuf += chunk.toString('utf8')
      const lines = stdoutBuf.split('\n')
      stdoutBuf = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.trim()) continue
        try {
          const event = JSON.parse(line) as ProgressEvent
          this.emit('event', event)
        } catch {
          // non-JSON line — ignore
        }
      }
    })

    let stderrBuf = ''
    child.stderr?.on('data', (chunk: Buffer) => {
      stderrBuf += chunk.toString('utf8')
      const lines = stderrBuf.split('\n')
      stderrBuf = lines.pop() ?? ''
      for (const line of lines) {
        const lineBytes = Buffer.byteLength(line, 'utf8') + 1
        this.stderrLines.push(line)
        this.stderrBytes += lineBytes
        while (this.stderrLines.length > STDERR_MAX_LINES || this.stderrBytes > STDERR_MAX_BYTES) {
          const removed = this.stderrLines.shift()
          if (removed !== undefined) {
            this.stderrBytes -= Buffer.byteLength(removed, 'utf8') + 1
          }
        }
      }
    })

    child.on('error', (err: Error) => {
      this._clearKillTimer()
      const stderr = this.stderrLines.length > 0 ? this.stderrLines.join('\n') : undefined
      const info: ExitInfo = { code: null, signal: null, error: err, stderr }
      this.emit('exit', info)
      this.child = null
    })

    child.on('close', (code: number | null, signal: NodeJS.Signals | null) => {
      this._clearKillTimer()
      if (code === 69) {
        this.emit('auth_expired')
      }
      const stderr =
        code !== 0 && this.stderrLines.length > 0 ? this.stderrLines.join('\n') : undefined
      const info: ExitInfo = { code, signal, stderr }
      this.emit('exit', info)
      this.child = null
    })

    this._watchForWorkspace()
  }

  private _watchForWorkspace(): void {
    const runsDir = lemRunsDir()

    const knownEntries = new Set<string>()
    try {
      for (const entry of fs.readdirSync(runsDir)) {
        knownEntries.add(entry)
      }
    } catch {
      // runs directory may not exist yet
    }

    let settled = false
    let dirWatcher: fs.FSWatcher | null = null

    const onNewEntry = (entry: string) => {
      if (settled || knownEntries.has(entry)) return
      knownEntries.add(entry)
      settled = true
      dirWatcher?.close()
      dirWatcher = null
      this._tailLog(path.join(runsDir, entry, 'meta', 'log.jsonl'))
    }

    try {
      fs.mkdirSync(runsDir, { recursive: true })
      dirWatcher = fs.watch(runsDir, (_event, filename) => {
        if (filename) onNewEntry(filename)
      })
      dirWatcher.on('error', () => {})
    } catch {
      // watch setup failed — log tailing unavailable
    }

    this.once('exit', () => {
      settled = true
      dirWatcher?.close()
      dirWatcher = null
    })
  }

  private _tailLog(logPath: string): void {
    this.logCleanup?.()
    this.logCleanup = tailJsonl(logPath, (line) => {
      try {
        const logLine = JSON.parse(line) as LogLine
        this.emit('log', logLine)
      } catch {
        // non-JSON log line — ignore
      }
    })
  }

  private _replayStub(replaySpeed: number): void {
    const filePath = stubEventsPath()
    let content: string
    try {
      content = fs.readFileSync(filePath, 'utf8')
    } catch {
      const info: ExitInfo = {
        code: 1,
        signal: null,
        error: new Error(`stub-events.jsonl not found: ${filePath}`),
      }
      setImmediate(() => this.emit('exit', info))
      return
    }

    const events: ProgressEvent[] = []
    for (const line of content.split('\n')) {
      if (!line.trim()) continue
      try {
        events.push(JSON.parse(line) as ProgressEvent)
      } catch {
        // skip malformed lines
      }
    }

    if (events.length === 0) {
      const info: ExitInfo = { code: 0, signal: null }
      setImmediate(() => this.emit('exit', info))
      return
    }

    const baseTs = events[0].timestamp
    const lastTs = events[events.length - 1].timestamp

    for (const event of events) {
      const delayMs = Math.round(((event.timestamp - baseTs) / replaySpeed) * 1000)
      setTimeout(() => this.emit('event', event), delayMs)
    }

    const exitDelayMs = Math.round(((lastTs - baseTs) / replaySpeed) * 1000) + 200
    setTimeout(() => {
      const info: ExitInfo = { code: 0, signal: null }
      this.emit('exit', info)
    }, exitDelayMs)
  }

  private _clearKillTimer(): void {
    if (this.killTimer !== null) {
      clearTimeout(this.killTimer)
      this.killTimer = null
    }
  }

  private _cleanup(): void {
    this._clearKillTimer()
    this.logCleanup?.()
    this.logCleanup = null
  }

  destroy(): void {
    this._cleanup()
    if (this.child) {
      this.child.kill('SIGKILL')
      this.child = null
    }
  }
}
