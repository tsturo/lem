import Database from 'better-sqlite3'
import type { RunRow, LibraryItem } from '../shared/types'

const CREATE_RUNS_TABLE = `
  CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    idea TEXT NOT NULL,
    status TEXT NOT NULL,
    verdict TEXT,
    workspace_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )
`

const CREATE_IDEAS_TABLE = `
  CREATE TABLE IF NOT EXISTS ideas (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    created_at  INTEGER NOT NULL
  )
`

const ADD_WORKSPACE_PATH_COL = `
  ALTER TABLE runs ADD COLUMN workspace_path TEXT NOT NULL DEFAULT ''
`

const ADD_IDEA_ID_COL = `ALTER TABLE runs ADD COLUMN idea_id TEXT REFERENCES ideas(id)`
const ADD_PARENT_RUN_ID_COL = `ALTER TABLE runs ADD COLUMN parent_run_id TEXT REFERENCES runs(run_id)`
const ADD_BRANCH_LABEL_COL = `ALTER TABLE runs ADD COLUMN branch_label TEXT`
const ADD_ROUND_DEPTH_COL = `ALTER TABLE runs ADD COLUMN round_depth INTEGER NOT NULL DEFAULT 1`

const CREATE_IDX_CREATED_AT = `CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC)`
const CREATE_IDX_IDEA_ID = `CREATE INDEX IF NOT EXISTS idx_runs_idea_id ON runs(idea_id)`
const CREATE_IDX_PARENT_RUN_ID = `CREATE INDEX IF NOT EXISTS idx_runs_parent_run_id ON runs(parent_run_id)`

interface DbRow {
  run_id: string
  idea: string
  status: string
  verdict: string | null
  workspace_path: string
  created_at: string
  updated_at: string
}

export class LibraryDB {
  private db: Database.Database
  private closed = false

  constructor(dbPath: string) {
    this.db = new Database(dbPath)
    this.db.pragma('journal_mode = WAL')
    this.db.exec(CREATE_RUNS_TABLE)
    this.db.exec(CREATE_IDEAS_TABLE)
    this.db.exec(CREATE_IDX_CREATED_AT)
    try {
      this.db.exec(ADD_WORKSPACE_PATH_COL)
    } catch {
      // column already exists on existing DBs, ignore
    }
    try {
      this.db.exec(ADD_IDEA_ID_COL)
    } catch {
      // column already exists
    }
    try {
      this.db.exec(ADD_PARENT_RUN_ID_COL)
    } catch {
      // column already exists
    }
    try {
      this.db.exec(ADD_BRANCH_LABEL_COL)
    } catch {
      // column already exists
    }
    try {
      this.db.exec(ADD_ROUND_DEPTH_COL)
    } catch {
      // column already exists
    }
    this.db.exec(CREATE_IDX_IDEA_ID)
    this.db.exec(CREATE_IDX_PARENT_RUN_ID)
  }

  upsert(row: RunRow): void {
    this.db
      .prepare(
        `INSERT OR REPLACE INTO runs (run_id, idea, status, verdict, workspace_path, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
      )
      .run(row.runId, row.idea, row.status, row.verdict ?? null, row.workspacePath, row.createdAt, row.updatedAt)
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
      workspacePath: r.workspace_path,
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
