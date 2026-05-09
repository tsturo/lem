import * as fs from 'fs'
import * as path from 'path'
import { parse as parseYaml } from 'yaml'
import { lemRunsDir } from './paths'

export interface BriefData {
  verdict: string | null
  confidence: string | null
  firstMilestone: string | null
  deliverables: {
    executiveSummary: string | null
    mvpPlan: string | null
    risksAndRejectedPaths: string | null
  }
  wallClockMs: number | null
}

function assertInsideRunsDir(workspacePath: string, runsDir: string): void {
  let resolvedRuns: string
  try {
    resolvedRuns = fs.realpathSync(runsDir)
  } catch {
    resolvedRuns = path.resolve(runsDir)
  }

  let resolvedWorkspace: string
  try {
    resolvedWorkspace = fs.realpathSync(workspacePath)
  } catch {
    throw new Error(`Path traversal blocked: '${workspacePath}' cannot be resolved`)
  }

  const prefix = resolvedRuns.endsWith(path.sep) ? resolvedRuns : resolvedRuns + path.sep
  if (!resolvedWorkspace.startsWith(prefix)) {
    throw new Error(`Path traversal blocked: '${workspacePath}' is outside lem runs directory`)
  }
}

function readFileSafe(filePath: string): string | null {
  try {
    return fs.readFileSync(filePath, 'utf-8')
  } catch {
    return null
  }
}

function parseFrontmatter(content: string): Record<string, unknown> {
  const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/)
  if (!match) return {}
  try {
    const parsed = parseYaml(match[1])
    return typeof parsed === 'object' && parsed !== null ? (parsed as Record<string, unknown>) : {}
  } catch {
    return {}
  }
}

function extractBody(content: string): string {
  const match = content.match(/^---\r?\n[\s\S]*?\r?\n---\r?\n([\s\S]*)$/)
  return match ? match[1] : content
}

function readWallClockMs(workspacePath: string): number | null {
  const timelinePath = path.join(workspacePath, 'meta', 'timeline.jsonl')
  const raw = readFileSafe(timelinePath)
  if (!raw) return null

  const lines = raw.split('\n').filter(l => l.trim() !== '')
  if (lines.length === 0) return null

  try {
    const first = JSON.parse(lines[0]) as Record<string, unknown>
    const last = JSON.parse(lines[lines.length - 1]) as Record<string, unknown>
    const startedAt = typeof first['started_at'] === 'number' ? first['started_at'] : null
    const endedAt = typeof last['ended_at'] === 'number' ? last['ended_at'] : null
    if (startedAt === null || endedAt === null) return null
    return Math.round((endedAt - startedAt) * 1000)
  } catch {
    return null
  }
}

export class WorkspaceReader {
  private readonly runsDir: string

  constructor(runsDir?: string) {
    this.runsDir = runsDir ?? lemRunsDir()
  }

  readBrief(workspacePath: string): BriefData {
    assertInsideRunsDir(workspacePath, this.runsDir)
    const synthesisRaw = readFileSafe(path.join(workspacePath, 'meta', 'synthesis.md'))
    let verdict: string | null = null
    let confidence: string | null = null
    let firstMilestone: string | null = null

    if (synthesisRaw !== null) {
      const fm = parseFrontmatter(synthesisRaw)
      verdict = typeof fm['recommendation'] === 'string' ? fm['recommendation'] : null
      confidence = typeof fm['confidence'] === 'string' ? fm['confidence'] : null
      firstMilestone = typeof fm['first_milestone'] === 'string' ? fm['first_milestone'] : null
    }

    const PLACEHOLDER = 'Not yet written'

    const readDeliverable = (name: string): string | null => {
      const raw = readFileSafe(path.join(workspacePath, 'deliverables', name))
      if (raw === null) return PLACEHOLDER
      return extractBody(raw)
    }

    return {
      verdict,
      confidence,
      firstMilestone,
      deliverables: {
        executiveSummary: readDeliverable('executive-summary.md'),
        mvpPlan: readDeliverable('mvp-plan.md'),
        risksAndRejectedPaths: readDeliverable('risks-and-rejected-paths.md'),
      },
      wallClockMs: readWallClockMs(workspacePath),
    }
  }
}
