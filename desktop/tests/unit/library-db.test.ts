// @vitest-environment node
import { describe, it, expect, afterEach } from 'vitest'
import { mkdtempSync, rmSync } from 'fs'
import { tmpdir } from 'os'
import { join } from 'path'
import Database from 'better-sqlite3'
import { LibraryDB } from '../../src/main/library-db'
import type { RunRow } from '../../src/shared/types'

function makeRow(overrides: Partial<RunRow> = {}): RunRow {
  return {
    runId: 'run-1',
    idea: 'Test idea',
    verdict: null,
    status: 'running',
    group: 'active',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  }
}

describe('LibraryDB', () => {
  const dbs: LibraryDB[] = []
  const tmpDirs: string[] = []

  function openDb(): LibraryDB {
    const db = new LibraryDB(':memory:')
    dbs.push(db)
    return db
  }

  function makeTmpDb(): { path: string; lib: LibraryDB } {
    const dir = mkdtempSync(join(tmpdir(), 'lem-test-'))
    tmpDirs.push(dir)
    const path = join(dir, 'library.db')
    const lib = new LibraryDB(path)
    dbs.push(lib)
    return { path, lib }
  }

  afterEach(() => {
    for (const db of dbs.splice(0)) {
      try { db.close() } catch { /* ignore */ }
    }
    for (const dir of tmpDirs.splice(0)) {
      try { rmSync(dir, { recursive: true, force: true }) } catch { /* ignore */ }
    }
  })

  it('upserts a run and lists it', () => {
    const db = openDb()
    const row = makeRow({ runId: 'run-abc', idea: 'My app idea', verdict: 'build', status: 'completed' })
    db.upsert(row)

    const items = db.list()
    expect(items).toHaveLength(1)
    expect(items[0].runId).toBe('run-abc')
    expect(items[0].idea).toBe('My app idea')
    expect(items[0].verdict).toBe('build')
    expect(items[0].status).toBe('completed')
  })

  it('upsert replaces existing row with same runId', () => {
    const db = openDb()
    db.upsert(makeRow({ runId: 'run-1', status: 'running', verdict: null }))
    db.upsert(makeRow({ runId: 'run-1', status: 'completed', verdict: 'skip' }))

    const items = db.list()
    expect(items).toHaveLength(1)
    expect(items[0].status).toBe('completed')
    expect(items[0].verdict).toBe('skip')
  })

  it('groups items correctly (active/done/archive based on status)', () => {
    const db = openDb()
    const now = Date.now()

    db.upsert(makeRow({ runId: 'r1', status: 'running', group: 'active', createdAt: new Date(now + 3).toISOString() }))
    db.upsert(makeRow({ runId: 'r2', status: 'completed', group: 'done', createdAt: new Date(now + 2).toISOString() }))
    db.upsert(makeRow({ runId: 'r3', status: 'failed', group: 'archive', createdAt: new Date(now + 1).toISOString() }))
    db.upsert(makeRow({ runId: 'r4', status: 'archived', group: 'archive', createdAt: new Date(now).toISOString() }))

    const items = db.list()
    expect(items).toHaveLength(4)

    const byId = Object.fromEntries(items.map(i => [i.runId, i]))
    expect(byId['r1'].status).toBe('running')
    expect(byId['r2'].status).toBe('completed')
    expect(byId['r3'].status).toBe('failed')
    expect(byId['r4'].status).toBe('archived')
  })

  it('handles missing verdict gracefully', () => {
    const db = openDb()
    db.upsert(makeRow({ runId: 'run-noverd', verdict: null }))

    const items = db.list()
    expect(items).toHaveLength(1)
    expect(items[0].verdict).toBeNull()
  })

  it('LIMIT works — insert 200 rows, list returns 100', () => {
    const db = openDb()
    const base = Date.now()

    for (let i = 0; i < 200; i++) {
      db.upsert(makeRow({
        runId: `run-${i}`,
        createdAt: new Date(base + i).toISOString(),
      }))
    }

    const items = db.list()
    expect(items).toHaveLength(100)
  })

  describe('ideas + DAG methods (LEM-44)', () => {
    it('createIdea + listIdeas roundtrip — 3 ideas returned DESC by createdAt', () => {
      const db = openDb()
      const base = Date.now()

      db.createIdea({ id: 'idea-1', title: 'First',  createdAt: base + 1 })
      db.createIdea({ id: 'idea-2', title: 'Second', createdAt: base + 3 })
      db.createIdea({ id: 'idea-3', title: 'Third',  createdAt: base + 2 })

      const ideas = db.listIdeas()
      expect(ideas).toHaveLength(3)
      expect(ideas.map(i => i.id)).toEqual(['idea-2', 'idea-3', 'idea-1'])
    })

    it('createIdea throws on duplicate id', () => {
      const db = openDb()
      db.createIdea({ id: 'dup', title: 'Original', createdAt: Date.now() })
      expect(() => db.createIdea({ id: 'dup', title: 'Duplicate', createdAt: Date.now() })).toThrow()
    })

    it('linkRunToIdea: getRoundsForIdea returns the run under the right idea_id', () => {
      const db = openDb()
      db.createIdea({ id: 'idea-x', title: 'X', createdAt: Date.now() })
      db.upsert(makeRow({ runId: 'run-link', status: 'running' }))
      db.linkRunToIdea('run-link', { ideaId: 'idea-x', parentRunId: null, branchLabel: null, roundDepth: 1 })

      const rounds = db.getRoundsForIdea('idea-x')
      expect(rounds).toHaveLength(1)
      expect(rounds[0].runId).toBe('run-link')
      expect(rounds[0].ideaId).toBe('idea-x')
    })

    it('getRoundsForIdea sorts by round_depth ASC then created_at ASC', () => {
      const db = openDb()
      const base = Date.now()
      db.createIdea({ id: 'idea-y', title: 'Y', createdAt: base })

      db.upsert(makeRow({ runId: 'r-d2-early', createdAt: new Date(base + 1).toISOString() }))
      db.upsert(makeRow({ runId: 'r-d1',       createdAt: new Date(base + 2).toISOString() }))
      db.upsert(makeRow({ runId: 'r-d2-late',  createdAt: new Date(base + 3).toISOString() }))

      db.linkRunToIdea('r-d2-early', { ideaId: 'idea-y', parentRunId: null, branchLabel: null, roundDepth: 2 })
      db.linkRunToIdea('r-d1',       { ideaId: 'idea-y', parentRunId: null, branchLabel: null, roundDepth: 1 })
      db.linkRunToIdea('r-d2-late',  { ideaId: 'idea-y', parentRunId: null, branchLabel: null, roundDepth: 2 })

      const rounds = db.getRoundsForIdea('idea-y')
      expect(rounds.map(r => r.runId)).toEqual(['r-d1', 'r-d2-early', 'r-d2-late'])
    })

    it('renameIdea changes the title', () => {
      const db = openDb()
      db.createIdea({ id: 'idea-r', title: 'Old', createdAt: Date.now() })
      db.renameIdea('idea-r', 'New')
      const ideas = db.listIdeas()
      expect(ideas[0].title).toBe('New')
    })

    it('renameIdea throws on empty title', () => {
      const db = openDb()
      db.createIdea({ id: 'idea-e', title: 'Valid', createdAt: Date.now() })
      expect(() => db.renameIdea('idea-e', '')).toThrow()
    })

    it('renameIdea throws on title longer than 200 chars', () => {
      const db = openDb()
      db.createIdea({ id: 'idea-long', title: 'Valid', createdAt: Date.now() })
      expect(() => db.renameIdea('idea-long', 'x'.repeat(201))).toThrow()
    })

    it('setBranchLabel sets and clears the label', () => {
      const db = openDb()
      db.upsert(makeRow({ runId: 'run-bl' }))
      db.setBranchLabel('run-bl', 'foo')

      db.createIdea({ id: 'idea-bl', title: 'BL', createdAt: Date.now() })
      db.linkRunToIdea('run-bl', { ideaId: 'idea-bl', parentRunId: null, branchLabel: 'foo', roundDepth: 1 })

      const rounds = db.getRoundsForIdea('idea-bl')
      expect(rounds[0].branchLabel).toBe('foo')

      db.setBranchLabel('run-bl', null)
      const rounds2 = db.getRoundsForIdea('idea-bl')
      expect(rounds2[0].branchLabel).toBeNull()
    })
  })

  describe('schema migrations (LEM-38)', () => {
    it('fresh DB has ideas table, 4 new run columns, and both indexes', () => {
      const { path, lib } = makeTmpDb()
      lib.close()
      dbs.pop()

      const raw = new Database(path)
      try {
        const runCols = (raw.prepare('PRAGMA table_info(runs)').all() as Array<{ name: string }>).map(r => r.name)
        expect(runCols).toContain('idea_id')
        expect(runCols).toContain('parent_run_id')
        expect(runCols).toContain('branch_label')
        expect(runCols).toContain('round_depth')

        const ideaCols = (raw.prepare('PRAGMA table_info(ideas)').all() as Array<{ name: string }>).map(r => r.name)
        expect(ideaCols).toContain('id')
        expect(ideaCols).toContain('title')
        expect(ideaCols).toContain('created_at')

        const indexes = (
          raw
            .prepare("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='runs'")
            .all() as Array<{ name: string }>
        ).map(r => r.name)
        expect(indexes).toContain('idx_runs_idea_id')
        expect(indexes).toContain('idx_runs_parent_run_id')
      } finally {
        raw.close()
      }
    })

    it('migrating a partially-migrated DB (one column already added) succeeds', () => {
      const dir = mkdtempSync(join(tmpdir(), 'lem-partial-'))
      tmpDirs.push(dir)
      const path = join(dir, 'partial.db')

      const raw = new Database(path)
      try {
        raw.prepare(`CREATE TABLE runs (
          run_id TEXT PRIMARY KEY,
          idea TEXT NOT NULL,
          status TEXT NOT NULL,
          verdict TEXT,
          workspace_path TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )`).run()
        raw.prepare(`CREATE TABLE ideas (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          created_at INTEGER NOT NULL
        )`).run()
        raw.prepare('ALTER TABLE runs ADD COLUMN idea_id TEXT REFERENCES ideas(id)').run()
      } finally {
        raw.close()
      }

      expect(() => {
        const lib2 = new LibraryDB(path)
        dbs.push(lib2)
      }).not.toThrow()
    })

    it('migration is idempotent — opening LibraryDB twice on same file causes no errors', () => {
      const { path, lib } = makeTmpDb()
      lib.close()
      dbs.pop()

      expect(() => {
        const lib2 = new LibraryDB(path)
        lib2.close()
      }).not.toThrow()
    })
  })
})
