import Database from 'better-sqlite3'
import type { RunRow, RunGroup, LibraryItem, Idea } from '../shared/types'

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
  idea_id: string | null
  parent_run_id: string | null
  branch_label: string | null
  round_depth: number
}

interface IdeaDbRow {
  id: string
  title: string
  created_at: number
}

function statusToGroup(status: string): RunGroup {
  if (status === 'running') return 'active'
  if (status === 'completed') return 'done'
  return 'archive'
}

function rowToRunRow(r: DbRow): RunRow {
  return {
    runId: r.run_id,
    idea: r.idea,
    verdict: r.verdict as RunRow['verdict'],
    status: r.status as RunRow['status'],
    group: statusToGroup(r.status),
    workspacePath: r.workspace_path,
    createdAt: r.created_at,
    updatedAt: r.updated_at,
    ideaId: r.idea_id ?? undefined,
    parentRunId: r.parent_run_id,
    branchLabel: r.branch_label,
    roundDepth: r.round_depth,
  }
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
        `INSERT INTO runs (run_id, idea, status, verdict, workspace_path, created_at, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?)
         ON CONFLICT (run_id) DO UPDATE SET
           idea = excluded.idea,
           status = excluded.status,
           verdict = excluded.verdict,
           workspace_path = excluded.workspace_path,
           created_at = excluded.created_at,
           updated_at = excluded.updated_at`,
      )
      .run(row.runId, row.idea, row.status, row.verdict ?? null, row.workspacePath ?? '', row.createdAt, row.updatedAt)
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

  getRunById(runId: string): RunRow | null {
    const row = this.db
      .prepare(`SELECT * FROM runs WHERE run_id = ?`)
      .get(runId) as DbRow | undefined
    return row ? rowToRunRow(row) : null
  }

  createIdea(args: { id: string; title: string; createdAt: number }): void {
    this.db
      .prepare(`INSERT INTO ideas (id, title, created_at) VALUES (?, ?, ?)`)
      .run(args.id, args.title, args.createdAt)
  }

  listIdeas(): Idea[] {
    const rows = this.db
      .prepare(`SELECT * FROM ideas ORDER BY created_at DESC`)
      .all() as IdeaDbRow[]
    return rows.map(r => ({ id: r.id, title: r.title, createdAt: r.created_at }))
  }

  getRoundsForIdea(ideaId: string): RunRow[] {
    const rows = this.db
      .prepare(`SELECT * FROM runs WHERE idea_id = ? ORDER BY round_depth ASC, created_at ASC`)
      .all(ideaId) as DbRow[]
    return rows.map(rowToRunRow)
  }

  getRunDag(ideaId: string): RunRow[] {
    return this.getRoundsForIdea(ideaId)
  }

  renameIdea(ideaId: string, newTitle: string): void {
    if (newTitle.length < 1 || newTitle.length > 200) {
      throw new Error(`title must be 1–200 characters, got ${newTitle.length}`)
    }
    this.db
      .prepare(`UPDATE ideas SET title = ? WHERE id = ?`)
      .run(newTitle, ideaId)
  }

  setBranchLabel(runId: string, label: string | null): void {
    this.db
      .prepare(`UPDATE runs SET branch_label = ? WHERE run_id = ?`)
      .run(label, runId)
  }

  linkRunToIdea(
    runId: string,
    args: { ideaId: string; parentRunId: string | null; branchLabel: string | null; roundDepth: number },
  ): void {
    this.db
      .prepare(
        `UPDATE runs SET idea_id = ?, parent_run_id = ?, branch_label = ?, round_depth = ? WHERE run_id = ?`,
      )
      .run(args.ideaId, args.parentRunId, args.branchLabel, args.roundDepth, runId)
  }

  runInTransaction<T>(fn: () => T): T {
    return this.db.transaction(fn)()
  }

  close(): void {
    if (this.closed) return
    this.closed = true
    this.db.close()
  }
}
