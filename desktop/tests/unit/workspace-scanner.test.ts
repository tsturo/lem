// @vitest-environment node
import { describe, it, expect, afterEach, vi, beforeEach } from 'vitest'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import { LibraryDB } from '../../src/main/library-db'
import { scanWorkspaces, readRunMeta } from '../../src/main/workspace-scanner'

function makeRunDir(
  base: string,
  runId: string,
  opts: {
    idea?: string
    status?: string
    startedAt?: number
    parentRunId?: string
    branchLabel?: string
  } = {},
): string {
  const runDir = join(base, runId)
  mkdirSync(join(runDir, 'meta'), { recursive: true })
  const state = {
    run_id: runId,
    status: opts.status ?? 'completed',
    started_at: opts.startedAt ?? Math.floor(Date.now() / 1000),
    last_event_at: Math.floor(Date.now() / 1000),
  }
  writeFileSync(join(runDir, 'meta', 'state.json'), JSON.stringify(state))
  if (opts.idea) {
    writeFileSync(join(runDir, 'idea.md'), `# Idea\n\n${opts.idea}\n`)
  }
  if (opts.parentRunId) {
    writeFileSync(join(runDir, 'meta', 'parent_run_id'), opts.parentRunId)
  }
  if (opts.branchLabel) {
    writeFileSync(join(runDir, 'meta', 'branch_label'), opts.branchLabel)
  }
  return runDir
}

describe('workspace-scanner backfill', () => {
  const dbs: LibraryDB[] = []
  const tmpDirs: string[] = []

  function openDb(): LibraryDB {
    const db = new LibraryDB(':memory:')
    dbs.push(db)
    return db
  }

  function makeTmpDir(): string {
    const dir = mkdtempSync(join(tmpdir(), 'lem-scanner-test-'))
    tmpDirs.push(dir)
    return dir
  }

  afterEach(() => {
    for (const db of dbs.splice(0)) {
      try { db.close() } catch { /* ignore */ }
    }
    for (const dir of tmpDirs.splice(0)) {
      try { rmSync(dir, { recursive: true, force: true }) } catch { /* ignore */ }
    }
  })

  it('empty runs dir → no ideas, no errors', () => {
    const db = openDb()
    const runsDir = makeTmpDir()
    const count = scanWorkspaces(db, runsDir)
    expect(count).toBe(0)
    expect(db.listIdeas()).toHaveLength(0)
  })

  it('3 isolated legacy runs → 3 ideas each with round_depth=1', () => {
    const db = openDb()
    const runsDir = makeTmpDir()
    makeRunDir(runsDir, 'run-a', { idea: 'Idea A', startedAt: 1000 })
    makeRunDir(runsDir, 'run-b', { idea: 'Idea B', startedAt: 2000 })
    makeRunDir(runsDir, 'run-c', { idea: 'Idea C', startedAt: 3000 })

    scanWorkspaces(db, runsDir)

    const ideas = db.listIdeas()
    expect(ideas).toHaveLength(3)

    for (const runId of ['run-a', 'run-b', 'run-c']) {
      const row = db.getRunById(runId)
      expect(row).not.toBeNull()
      expect(row!.ideaId).toBeTruthy()
      expect(row!.roundDepth).toBe(1)
      expect(row!.parentRunId).toBeNull()
    }
  })

  it('linear chain (run1 → run2 → run3) → 1 idea, round_depth 1/2/3', () => {
    const db = openDb()
    const runsDir = makeTmpDir()
    makeRunDir(runsDir, 'run1', { idea: 'The idea', startedAt: 1000 })
    makeRunDir(runsDir, 'run2', { idea: 'The idea r2', startedAt: 2000, parentRunId: 'run1' })
    makeRunDir(runsDir, 'run3', { idea: 'The idea r3', startedAt: 3000, parentRunId: 'run2' })

    scanWorkspaces(db, runsDir)

    const ideas = db.listIdeas()
    expect(ideas).toHaveLength(1)

    const r1 = db.getRunById('run1')!
    const r2 = db.getRunById('run2')!
    const r3 = db.getRunById('run3')!

    expect(r1.roundDepth).toBe(1)
    expect(r2.roundDepth).toBe(2)
    expect(r3.roundDepth).toBe(3)

    expect(r2.ideaId).toBe(r1.ideaId)
    expect(r3.ideaId).toBe(r1.ideaId)

    expect(r2.parentRunId).toBe('run1')
    expect(r3.parentRunId).toBe('run2')
  })

  it('2 branches off run1 → 1 idea, run2a and run2b both round_depth=2', () => {
    const db = openDb()
    const runsDir = makeTmpDir()
    makeRunDir(runsDir, 'run1', { idea: 'Branch base', startedAt: 1000 })
    makeRunDir(runsDir, 'run2a', { idea: 'Branch A', startedAt: 2000, parentRunId: 'run1', branchLabel: 'mobile-first' })
    makeRunDir(runsDir, 'run2b', { idea: 'Branch B', startedAt: 3000, parentRunId: 'run1', branchLabel: 'enterprise' })

    scanWorkspaces(db, runsDir)

    const ideas = db.listIdeas()
    expect(ideas).toHaveLength(1)

    const r2a = db.getRunById('run2a')!
    const r2b = db.getRunById('run2b')!
    const r1 = db.getRunById('run1')!

    expect(r2a.roundDepth).toBe(2)
    expect(r2b.roundDepth).toBe(2)
    expect(r2a.ideaId).toBe(r1.ideaId)
    expect(r2b.ideaId).toBe(r1.ideaId)
    expect(r2a.branchLabel).toBe('mobile-first')
    expect(r2b.branchLabel).toBe('enterprise')
  })

  it('orphan (parent dir deleted) → becomes own root idea + warning logged', () => {
    const db = openDb()
    const runsDir = makeTmpDir()
    // run-deleted is NOT on disk
    makeRunDir(runsDir, 'run-orphan', { idea: 'Orphaned idea', startedAt: 1000, parentRunId: 'run-deleted' })

    const stderrSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true)
    scanWorkspaces(db, runsDir)
    const warnCalls = (stderrSpy.mock.calls as unknown[]).flat().join(' ')
    stderrSpy.mockRestore()

    const ideas = db.listIdeas()
    expect(ideas).toHaveLength(1)

    const orphan = db.getRunById('run-orphan')!
    expect(orphan.ideaId).toBeTruthy()
    expect(orphan.roundDepth).toBe(1)
    expect(orphan.parentRunId).toBeNull()

    expect(warnCalls).toMatch(/run-orphan/)
    expect(warnCalls).toMatch(/run-deleted/)
  })

  it('idempotency — scan twice produces no new ideas or changes', () => {
    const db = openDb()
    const runsDir = makeTmpDir()
    makeRunDir(runsDir, 'run-x', { idea: 'Stable idea', startedAt: 1000 })
    makeRunDir(runsDir, 'run-y', { idea: 'Another idea', startedAt: 2000 })

    scanWorkspaces(db, runsDir)
    const ideasAfterFirst = db.listIdeas()
    const xAfterFirst = db.getRunById('run-x')!
    const yAfterFirst = db.getRunById('run-y')!

    scanWorkspaces(db, runsDir)
    const ideasAfterSecond = db.listIdeas()
    const xAfterSecond = db.getRunById('run-x')!
    const yAfterSecond = db.getRunById('run-y')!

    expect(ideasAfterSecond).toHaveLength(ideasAfterFirst.length)
    expect(xAfterSecond.ideaId).toBe(xAfterFirst.ideaId)
    expect(yAfterSecond.ideaId).toBe(yAfterFirst.ideaId)
    expect(xAfterSecond.roundDepth).toBe(xAfterFirst.roundDepth)
    expect(yAfterSecond.roundDepth).toBe(yAfterFirst.roundDepth)
  })

  it('cycle A→B→A — both left unlinked after cap + warnings logged', () => {
    const db = openDb()
    const runsDir = makeTmpDir()
    // A points to B, B points to A: a true cycle
    makeRunDir(runsDir, 'run-A', { idea: 'Cycle A', startedAt: 1000, parentRunId: 'run-B' })
    makeRunDir(runsDir, 'run-B', { idea: 'Cycle B', startedAt: 2000, parentRunId: 'run-A' })

    const stderrSpy = vi.spyOn(process.stderr, 'write').mockImplementation(() => true)
    scanWorkspaces(db, runsDir)
    const warnCalls = (stderrSpy.mock.calls as unknown[]).flat().join(' ')
    stderrSpy.mockRestore()

    // Neither run should have an idea_id since both are in a cycle
    const rA = db.getRunById('run-A')!
    const rB = db.getRunById('run-B')!
    expect(rA.ideaId).toBeFalsy()
    expect(rB.ideaId).toBeFalsy()

    expect(warnCalls).toMatch(/run-A|run-B/)
  })

  describe('readRunMeta', () => {
    it('returns empty object when meta files are absent', () => {
      const dir = makeTmpDir()
      mkdirSync(join(dir, 'meta'), { recursive: true })
      expect(readRunMeta(dir)).toEqual({})
    })

    it('reads parent_run_id and branch_label when present', () => {
      const dir = makeTmpDir()
      mkdirSync(join(dir, 'meta'), { recursive: true })
      writeFileSync(join(dir, 'meta', 'parent_run_id'), 'parent-123\n')
      writeFileSync(join(dir, 'meta', 'branch_label'), 'mobile-focus\n')
      const meta = readRunMeta(dir)
      expect(meta.parentRunId).toBe('parent-123')
      expect(meta.branchLabel).toBe('mobile-focus')
    })

    it('handles missing meta directory gracefully', () => {
      const dir = makeTmpDir()
      expect(() => readRunMeta(dir)).not.toThrow()
      expect(readRunMeta(dir)).toEqual({})
    })
  })
})
