// @vitest-environment node
import { describe, it, expect, afterEach } from 'vitest'
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

  function openDb(): LibraryDB {
    const db = new LibraryDB(':memory:')
    dbs.push(db)
    return db
  }

  afterEach(() => {
    for (const db of dbs.splice(0)) {
      try { db.close() } catch { /* ignore */ }
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
})
