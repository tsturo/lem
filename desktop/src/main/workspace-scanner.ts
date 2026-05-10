import { existsSync, readFileSync, readdirSync, statSync } from 'fs'
import { randomBytes } from 'crypto'
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

const CROCKFORD = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'
const MAX_LINK_PASSES = 10

function generateUlid(timestamp = Date.now()): string {
  let t = timestamp
  const timeChars = new Array<string>(10)
  for (let i = 9; i >= 0; i--) {
    timeChars[i] = CROCKFORD[t & 0x1f]!
    t = Math.floor(t / 32)
  }

  const randBuf = randomBytes(10)
  const randChars = new Array<string>(16)
  let bits = 0
  let bitsLeft = 0
  let byteIdx = 0
  for (let i = 0; i < 16; i++) {
    while (bitsLeft < 5) {
      bits = (bits << 8) | (randBuf[byteIdx++] ?? 0)
      bitsLeft += 8
    }
    bitsLeft -= 5
    randChars[i] = CROCKFORD[(bits >> bitsLeft) & 0x1f]!
  }

  return timeChars.join('') + randChars.join('')
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

export function readRunMeta(runDir: string): { parentRunId?: string; branchLabel?: string } {
  const result: { parentRunId?: string; branchLabel?: string } = {}
  const parentText = safeReadText(join(runDir, 'meta', 'parent_run_id'))
  if (parentText) {
    const trimmed = parentText.trim()
    if (trimmed) result.parentRunId = trimmed
  }
  const labelText = safeReadText(join(runDir, 'meta', 'branch_label'))
  if (labelText) {
    const trimmed = labelText.trim()
    if (trimmed) result.branchLabel = trimmed
  }
  return result
}

function workspaceToRunRow(workspacePath: string, runId: string): RunRow | null {
  const state = readState(workspacePath)
  if (!state) {
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

function warn(msg: string): void {
  process.stderr.write(`[workspace-scanner] WARN: ${msg}\n`)
}

function isoToEpochSeconds(iso: string): number {
  const ms = Date.parse(iso)
  return isNaN(ms) ? Math.floor(Date.now() / 1000) : Math.floor(ms / 1000)
}

export function scanWorkspaces(db: LibraryDB, runsDir: string = lemRunsDir()): number {
  if (!existsSync(runsDir)) return 0

  let entries: string[] = []
  try {
    entries = readdirSync(runsDir)
  } catch {
    return 0
  }

  // Collect candidate run dirs, keyed by run ID.
  const runDirs = new Map<string, string>() // runId → workspacePath
  for (const entry of entries) {
    if (entry.startsWith('.')) continue
    const workspacePath = join(runsDir, entry)
    try {
      if (!statSync(workspacePath).isDirectory()) continue
    } catch {
      continue
    }
    runDirs.set(entry, workspacePath)
  }

  let imported = 0

  db.runInTransaction(() => {
    // PASS 1: upsert run rows for any run not yet in DB (or update non-idea fields).
    // Collect unlinked run IDs and their parent_run_id from disk.
    const unlinked = new Set<string>()
    const parentFromMeta = new Map<string, string | undefined>() // runId → parentRunId (undefined = root)
    const branchFromMeta = new Map<string, string | undefined>()

    for (const [runId, workspacePath] of runDirs) {
      const existingRow = db.getRunById(runId)

      if (existingRow?.ideaId) {
        // Already fully linked — skip entirely.
        continue
      }

      // Upsert the basic run data (preserves idea_id if already set via ON CONFLICT logic).
      const row = workspaceToRunRow(workspacePath, runId)
      if (!row) continue

      db.upsert(row)
      imported++

      // Read meta files to determine parentage.
      const meta = readRunMeta(workspacePath)
      parentFromMeta.set(runId, meta.parentRunId)
      branchFromMeta.set(runId, meta.branchLabel)
      unlinked.add(runId)
    }

    // PASS 2: iteratively link unlinked runs to ideas.
    // Each iteration resolves runs whose parent is either missing (root) or already linked.
    // Runs in cycles or with unresolvable parents are left unlinked after MAX_LINK_PASSES.
    for (let pass = 0; pass < MAX_LINK_PASSES && unlinked.size > 0; pass++) {
      const resolvedThisPass: string[] = []

      for (const runId of unlinked) {
        const parentRunId = parentFromMeta.get(runId)

        if (!parentRunId) {
          // Root run: create a new idea.
          const run = db.getRunById(runId)
          if (!run) continue
          const newIdeaId = generateUlid()
          db.createIdea({ id: newIdeaId, title: run.idea, createdAt: isoToEpochSeconds(run.createdAt) })
          db.linkRunToIdea(runId, { ideaId: newIdeaId, parentRunId: null, branchLabel: null, roundDepth: 1 })
          resolvedThisPass.push(runId)
          continue
        }

        const parent = db.getRunById(parentRunId)

        if (!parent) {
          // Parent dir was deleted — treat as orphaned root.
          warn(`run ${runId} references missing parent ${parentRunId}; treating as root idea`)
          const run = db.getRunById(runId)
          if (!run) continue
          const newIdeaId = generateUlid()
          db.createIdea({ id: newIdeaId, title: run.idea, createdAt: isoToEpochSeconds(run.createdAt) })
          db.linkRunToIdea(runId, { ideaId: newIdeaId, parentRunId: null, branchLabel: null, roundDepth: 1 })
          resolvedThisPass.push(runId)
          continue
        }

        if (!parent.ideaId) {
          // Parent exists but is not yet linked — defer to next pass.
          continue
        }

        // Parent is linked: link this run as a child.
        const branchLabel = branchFromMeta.get(runId) ?? null
        const roundDepth = (parent.roundDepth ?? 1) + 1
        db.linkRunToIdea(runId, {
          ideaId: parent.ideaId,
          parentRunId: parentRunId,
          branchLabel: branchLabel ?? null,
          roundDepth,
        })
        resolvedThisPass.push(runId)
      }

      for (const id of resolvedThisPass) unlinked.delete(id)

      if (resolvedThisPass.length === 0) break
    }

    if (unlinked.size > 0) {
      for (const runId of unlinked) {
        warn(`run ${runId} could not be linked (possible cycle or unresolvable chain); leaving unlinked`)
      }
    }
  })

  return imported
}
