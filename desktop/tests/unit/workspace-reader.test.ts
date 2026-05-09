// @vitest-environment node
import { describe, it, expect } from 'vitest'
import * as path from 'path'
import * as fs from 'fs'
import * as os from 'os'
import { WorkspaceReader } from '../../src/main/workspace-reader'

const FIXTURE = path.resolve(__dirname, '../fixtures/sample-workspace')

describe('WorkspaceReader.readBrief — fixture workspace', () => {
  const reader = new WorkspaceReader()

  it('reads all 3 deliverables from fixture', () => {
    const data = reader.readBrief(FIXTURE)
    expect(data.deliverables.executiveSummary).toContain('Fast Calendar App')
    expect(data.deliverables.mvpPlan).toContain('Phase 1')
    expect(data.deliverables.risksAndRejectedPaths).toContain('Rejected Paths')
  })

  it('parses synthesis frontmatter correctly', () => {
    const data = reader.readBrief(FIXTURE)
    expect(data.verdict).toBe('Build')
    expect(data.confidence).toBe('High')
    expect(data.firstMilestone).toBe('MVP in 6 weeks')
  })

  it('computes wallClockMs from timeline.jsonl', () => {
    const data = reader.readBrief(FIXTURE)
    // first started_at=1746784800.0, last ended_at=1746785220.0 → diff=420s → 420000ms
    expect(data.wallClockMs).toBe(420000)
  })
})

describe('WorkspaceReader.readBrief — missing files', () => {
  const reader = new WorkspaceReader()

  it('returns placeholder body for missing deliverable file', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lem-ws-'))
    fs.mkdirSync(path.join(tmpDir, 'meta'), { recursive: true })
    fs.mkdirSync(path.join(tmpDir, 'deliverables'), { recursive: true })

    fs.writeFileSync(
      path.join(tmpDir, 'meta', 'synthesis.md'),
      '---\nrecommendation: Build\nconfidence: High\nfirst_milestone: Q1\n---\n',
    )
    // no deliverable files

    const data = reader.readBrief(tmpDir)
    expect(data.deliverables.executiveSummary).toBe('Not yet written')
    expect(data.deliverables.mvpPlan).toBe('Not yet written')
    expect(data.deliverables.risksAndRejectedPaths).toBe('Not yet written')

    fs.rmSync(tmpDir, { recursive: true })
  })

  it('returns null verdict when synthesis.md is missing', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lem-ws-'))
    fs.mkdirSync(path.join(tmpDir, 'meta'), { recursive: true })
    fs.mkdirSync(path.join(tmpDir, 'deliverables'), { recursive: true })

    const data = reader.readBrief(tmpDir)
    expect(data.verdict).toBeNull()
    expect(data.confidence).toBeNull()
    expect(data.firstMilestone).toBeNull()

    fs.rmSync(tmpDir, { recursive: true })
  })

  it('returns null wallClockMs when timeline.jsonl is missing', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lem-ws-'))
    fs.mkdirSync(path.join(tmpDir, 'meta'), { recursive: true })

    const data = reader.readBrief(tmpDir)
    expect(data.wallClockMs).toBeNull()

    fs.rmSync(tmpDir, { recursive: true })
  })
})
