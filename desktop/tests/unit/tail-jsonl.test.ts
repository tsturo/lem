// @vitest-environment node
import { describe, it, expect, afterEach } from 'vitest'
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import { tailJsonl } from '../../src/main/tail-jsonl'

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function waitFor(condition: () => boolean, timeoutMs = 3000, intervalMs = 20): Promise<void> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (condition()) return
    await sleep(intervalMs)
  }
  throw new Error('waitFor timed out')
}

describe('tailJsonl', () => {
  const cleanups: (() => void)[] = []
  const tmpFiles: string[] = []

  afterEach(() => {
    for (const cleanup of cleanups.splice(0)) cleanup()
    for (const f of tmpFiles.splice(0)) {
      try { fs.unlinkSync(f) } catch { /* ignore */ }
    }
  })

  it('reads existing lines from a file', () => {
    const filePath = path.join(os.tmpdir(), `lem-tail-${Date.now()}.jsonl`)
    fs.writeFileSync(filePath, '{"a":1}\n{"b":2}\n')
    tmpFiles.push(filePath)

    const lines: string[] = []
    const cleanup = tailJsonl(filePath, line => lines.push(line))
    cleanups.push(cleanup)

    expect(lines).toEqual(['{"a":1}', '{"b":2}'])
  })

  it('buffers partial lines until newline arrives', async () => {
    const filePath = path.join(os.tmpdir(), `lem-tail-${Date.now()}.jsonl`)
    fs.writeFileSync(filePath, '{"partial"')
    tmpFiles.push(filePath)

    const lines: string[] = []
    const cleanup = tailJsonl(filePath, line => lines.push(line))
    cleanups.push(cleanup)

    expect(lines).toHaveLength(0)

    fs.appendFileSync(filePath, ':true}\n')
    await waitFor(() => lines.length === 1)

    expect(lines[0]).toBe('{"partial":true}')
  })

  it('handles file creation after watch starts', async () => {
    const filePath = path.join(os.tmpdir(), `lem-tail-${Date.now()}.jsonl`)
    tmpFiles.push(filePath)

    const lines: string[] = []
    const cleanup = tailJsonl(filePath, line => lines.push(line))
    cleanups.push(cleanup)

    expect(lines).toHaveLength(0)

    await sleep(50)
    fs.writeFileSync(filePath, '{"created":true}\n')

    await waitFor(() => lines.length === 1)
    expect(lines[0]).toBe('{"created":true}')
  })
})
