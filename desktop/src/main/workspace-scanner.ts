import { existsSync, readFileSync, readdirSync, statSync } from 'fs'
import { homedir } from 'os'
import { join } from 'path'
import type { LibraryDB } from './library-db'
import type { RunRow, RunStatus, Verdict } from '../shared/types'

interface SynthesisFrontmatter {
  recommendation?: string
  idea_one_liner?: string
}

interface RunStateJson {
  run_id?: string
  status?: string
  started_at?: number
  last_event_at?: number
}

const STATUS_MAP: Record<string, RunStatus> = {
  running: 'running',
  completed: 'completed',
  failed: 'failed',
  archived: 'archived',
}

function lemRunsDir(): string {
  if (process.env['LEM_RUNS_DIR']) return process.env['LEM_RUNS_DIR']
  const xdg = process.env['XDG_DATA_HOME']
  if (xdg) return join(xdg, 'lem', 'runs')
  return join(homedir(), '.local', 'share', 'lem', 'runs')
}

function safeReadJson(path: string): RunStateJson | null {
  try {
    return JSON.parse(readFileSync(path, 'utf-8'))
  } catch {
    return null
  }
}

function safeReadText(path: string): string | null {
  try {
    return readFileSync(path, 'utf-8')
  } catch {
    return null
  }
}

function extractFrontmatter(text: string): SynthesisFrontmatter {
  if (!text.startsWith('---\n')) return {}
  const lines = text.split('\n')
  const out: SynthesisFrontmatter = {}
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]
    if (line === '---') break
    const m = line.match(/^(recommendation|idea_one_liner):\s*"?([^"]*)"?\s*$/)
    if (m) {
      const key = m[1] as keyof SynthesisFrontmatter
      out[key] = m[2]
    }
  }
  return out
}

function recommendationToVerdict(rec?: string): Verdict | null {
  if (!rec) return null
  const lower = rec.toLowerCase()
  if (lower.includes("don't build") || lower.includes('skip') || lower.includes('do not build')) {
    return 'skip'
  }
  if (lower.includes('build')) return 'build'
  if (lower.includes('insufficient') || lower.includes('unsure')) return 'unsure'
  return null
}

function readIdea(workspacePath: string): string {
  const ideaPath = join(workspacePath, 'idea.md')
  const text = safeReadText(ideaPath)
  if (!text) return ''
  // idea.md typically starts with `# Idea` heading; skip headings entirely
  // and return the first non-blank prose line.
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    if (line.startsWith('#')) continue
    return line
  }
  return ''
}

function readSynthesis(workspacePath: string): SynthesisFrontmatter {
  const synthPath = join(workspacePath, 'meta', 'synthesis.md')
  const text = safeReadText(synthPath)
  if (!text) return {}
  return extractFrontmatter(text)
}

function readState(workspacePath: string): RunStateJson | null {
  return safeReadJson(join(workspacePath, 'meta', 'state.json'))
}

function isoFromUnixSeconds(seconds: number | undefined, fallback: string): string {
  if (!seconds) return fallback
  return new Date(seconds * 1000).toISOString()
}

function workspaceToRunRow(workspacePath: string, runId: string): RunRow | null {
  const state = readState(workspacePath)
  if (!state) {
    // No state.json — workspace is too partial to import.
    return null
  }

  const synth = readSynthesis(workspacePath)
  const idea = synth.idea_one_liner || readIdea(workspacePath) || runId
  const status = STATUS_MAP[state.status ?? ''] ?? 'failed'
  const verdict = recommendationToVerdict(synth.recommendation)

  let stat
  try {
    stat = statSync(workspacePath)
  } catch {
    return null
  }

  const createdAt = isoFromUnixSeconds(state.started_at, stat.birthtime.toISOString())
  const updatedAt = isoFromUnixSeconds(state.last_event_at, stat.mtime.toISOString())

  return {
    runId,
    idea,
    verdict,
    status,
    group: status === 'running' ? 'active' : status === 'archived' ? 'archive' : 'done',
    workspacePath,
    createdAt,
    updatedAt,
  }
}

export function scanWorkspaces(db: LibraryDB, runsDir: string = lemRunsDir()): number {
  if (!existsSync(runsDir)) return 0

  let imported = 0
  let entries: string[] = []
  try {
    entries = readdirSync(runsDir)
  } catch {
    return 0
  }

  for (const entry of entries) {
    if (entry.startsWith('.')) continue
    const workspacePath = join(runsDir, entry)
    try {
      if (!statSync(workspacePath).isDirectory()) continue
    } catch {
      continue
    }

    const row = workspaceToRunRow(workspacePath, entry)
    if (!row) continue

    db.upsert(row)
    imported++
  }

  return imported
}
