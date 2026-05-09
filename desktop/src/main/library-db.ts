import Database from 'better-sqlite3'
import type { RunRow, LibraryItem } from '../shared/types'

const CREATE_TABLE = `
  CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    idea TEXT NOT NULL,
    status TEXT NOT NULL,
    verdict TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )
`

const CREATE_INDEX = `
  CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC)
`

interface DbRow {
  run_id: string
  idea: string
  status: string
  verdict: string | null
  created_at: string
  updated_at: string
}

export class LibraryDB {
  private db: Database.Database
  private closed = false

  constructor(dbPath: string) {
    this.db = new Database(dbPath)
    this.db.pragma('journal_mode = WAL')
    this.db.exec(CREATE_TABLE)
    this.db.exec(CREATE_INDEX)
  }

  upsert(row: RunRow): void {
    this.db
      .prepare(
        `INSERT OR REPLACE INTO runs (run_id, idea, status, verdict, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?)`,
      )
      .run(row.runId, row.idea, row.status, row.verdict ?? null, row.createdAt, row.updatedAt)
  }

  list(): LibraryItem[] {
    const rows = this.db
      .prepare(`SELECT * FROM runs ORDER BY created_at DESC LIMIT 100`)
      .all() as DbRow[]

    return rows.map(r => ({
      runId: r.run_id,
      idea: r.idea,
      verdict: r.verdict as LibraryItem['verdict'],
      status: r.status as LibraryItem['status'],
      createdAt: r.created_at,
      updatedAt: r.updated_at,
    }))
  }

  close(): void {
    if (this.closed) return
    this.closed = true
    this.db.close()
  }
}
