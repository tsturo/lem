import { test, expect, _electron as electron } from '@playwright/test'
import type { ElectronApplication, Page } from '@playwright/test'
import { DatabaseSync } from 'node:sqlite'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'fs'
import { join, resolve } from 'path'
import { tmpdir } from 'os'

const APP_MAIN = resolve(__dirname, '..', '..', 'out', 'main', 'index.js')

const RUN_A      = 'run-legacy-a'
const RUN_B      = 'run-legacy-b'
const RUN_C      = 'run-legacy-c'
const RUN_PARENT = 'run-linked-parent'
const RUN_CHILD  = 'run-linked-child'
const RUN_ORPHAN = 'run-orphan'

type IdeaShape  = { id: string; title: string; createdAt: number }
type RoundShape = { runId: string; roundDepth: number; parentRunId: string | null; verdict: string | null }

function makeRunDir(
  runsDir: string,
  runId: string,
  opts: { idea: string; verdict: string; parentRunId?: string },
): void {
  const meta = join(runsDir, runId, 'meta')
  mkdirSync(meta, { recursive: true })
  const ts = Math.floor(Date.now() / 1000)
  writeFileSync(
    join(meta, 'state.json'),
    JSON.stringify({ run_id: runId, status: 'completed', started_at: ts - 3600, last_event_at: ts - 60 }),
  )
  writeFileSync(join(runsDir, runId, 'idea.md'), opts.idea)
  writeFileSync(
    join(meta, 'synthesis.md'),
    `---\nrecommendation: ${opts.verdict}\nidea_one_liner: ${opts.idea}\n---\n`,
  )
  if (opts.parentRunId) {
    writeFileSync(join(meta, 'parent_run_id'), opts.parentRunId)
  }
}

function createFixtures(): { userDataDir: string; runsDir: string } {
  const userDataDir = mkdtempSync(join(tmpdir(), 'lem-bf-data-'))
  const runsDir     = mkdtempSync(join(tmpdir(), 'lem-bf-runs-'))

  writeFileSync(
    join(userDataDir, 'settings.json'),
    JSON.stringify({ theme: 'auto', claudePath: '/usr/bin/env' }),
  )

  // Pre-seed with OLD schema — no ideas table, no idea_id column.
  // This simulates runs created by a prior app version that predates the ideas table.
  const db = new DatabaseSync(join(userDataDir, 'library.db'))
  db.exec('PRAGMA journal_mode = WAL')
  db.exec(`
    CREATE TABLE runs (
      run_id        TEXT PRIMARY KEY,
      idea          TEXT NOT NULL,
      status        TEXT NOT NULL,
      verdict       TEXT,
      workspace_path TEXT NOT NULL DEFAULT '',
      created_at    TEXT NOT NULL,
      updated_at    TEXT NOT NULL
    )
  `)
  db.exec('CREATE INDEX idx_runs_created_at ON runs (created_at DESC)')

  const now = new Date().toISOString()
  const ins = db.prepare(
    'INSERT INTO runs (run_id, idea, status, verdict, workspace_path, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
  )
  ins.run(RUN_A,      'idea A',      'completed', 'build', '', now, now)
  ins.run(RUN_B,      'idea B',      'completed', 'skip',  '', now, now)
  ins.run(RUN_C,      'idea C',      'completed', 'build', '', now, now)
  ins.run(RUN_PARENT, 'parent idea', 'completed', 'build', '', now, now)
  ins.run(RUN_CHILD,  'parent idea', 'completed', 'skip',  '', now, now)
  ins.run(RUN_ORPHAN, 'orphan idea', 'completed', 'build', '', now, now)
  db.close()

  // On-disk run directories (workspace-scanner reads these)
  makeRunDir(runsDir, RUN_A,      { idea: 'idea A',      verdict: 'build' })
  makeRunDir(runsDir, RUN_B,      { idea: 'idea B',      verdict: 'skip' })
  makeRunDir(runsDir, RUN_C,      { idea: 'idea C',      verdict: 'build' })
  makeRunDir(runsDir, RUN_PARENT, { idea: 'parent idea', verdict: 'build' })
  makeRunDir(runsDir, RUN_CHILD,  { idea: 'parent idea', verdict: 'skip', parentRunId: RUN_PARENT })
  makeRunDir(runsDir, RUN_ORPHAN, { idea: 'orphan idea', verdict: 'build', parentRunId: 'run-missing' })

  return { userDataDir, runsDir }
}

async function launchApp(
  dirs: { userDataDir: string; runsDir: string },
): Promise<{ app: ElectronApplication; page: Page }> {
  const app = await electron.launch({
    args: [APP_MAIN, `--user-data-dir=${dirs.userDataDir}`],
    env: { ...process.env, LEM_RUNS_DIR: dirs.runsDir },
  })
  const page = await app.firstWindow()
  await page.waitForLoadState('domcontentloaded')
  await page.locator('aside').locator('text=idea A').waitFor({ timeout: 15_000 })
  return { app, page }
}

test.describe('backfill — legacy runs on startup', () => {
  let electronApp: ElectronApplication
  let page: Page
  let dirs: { userDataDir: string; runsDir: string }

  test.beforeAll(async () => {
    dirs = createFixtures()
    ;({ app: electronApp, page } = await launchApp(dirs))
  })

  test.afterAll(async () => {
    await electronApp?.close()
    rmSync(dirs.userDataDir, { recursive: true, force: true })
    rmSync(dirs.runsDir,     { recursive: true, force: true })
  })

  test('3 legacy runs each become a separate 1-round idea', async () => {
    await expect(page.locator('aside').getByText('idea A')).toBeVisible()
    await expect(page.locator('aside').getByText('idea B')).toBeVisible()
    await expect(page.locator('aside').getByText('idea C')).toBeVisible()

    const ideas = await page.evaluate((): Promise<IdeaShape[]> => (window as any).lem.ideas.list())
    const basic = ideas.filter(i => ['idea A', 'idea B', 'idea C'].includes(i.title))
    expect(basic).toHaveLength(3)

    for (const idea of basic) {
      const rounds = await page.evaluate(
        (id): Promise<RoundShape[]> => (window as any).lem.ideas.getRounds(id),
        idea.id,
      )
      expect(rounds).toHaveLength(1)
      expect(rounds[0].roundDepth).toBe(1)
    }

    // Verdict pills: A and C → build, B → skip
    const ideaA = basic.find(i => i.title === 'idea A')!
    const ideaB = basic.find(i => i.title === 'idea B')!
    const ideaC = basic.find(i => i.title === 'idea C')!
    const [rA] = await page.evaluate((id): Promise<RoundShape[]> => (window as any).lem.ideas.getRounds(id), ideaA.id)
    const [rB] = await page.evaluate((id): Promise<RoundShape[]> => (window as any).lem.ideas.getRounds(id), ideaB.id)
    const [rC] = await page.evaluate((id): Promise<RoundShape[]> => (window as any).lem.ideas.getRounds(id), ideaC.id)
    expect(rA.verdict).toBe('build')
    expect(rB.verdict).toBe('skip')
    expect(rC.verdict).toBe('build')

    // No round (·N) or branch (⑂N) badges — single-round ideas never render them
    for (const title of ['idea A', 'idea B', 'idea C']) {
      const btn = page.locator('aside button').filter({ hasText: title }).first()
      await expect(btn).not.toContainText('·')
      await expect(btn).not.toContainText('⑂')
    }
  })

  test('clicking a 1-round idea opens Brief with a single timeline pill at depth 1', async () => {
    await page.locator('aside button').filter({ hasText: 'idea A' }).first().click()
    await page.waitForSelector('[data-brief]', { timeout: 5_000 })
    await page.waitForSelector('[data-timeline-wrapper]', { timeout: 5_000 })

    // A single-round idea uses the linear view; no placeholder pills are rendered
    const pills = page.locator('[data-pill]')
    await expect(pills).toHaveCount(1)
    await expect(pills.first()).toHaveAttribute('data-round', '1')
    await expect(pills.first()).toHaveAttribute('data-current', 'true')
  })

  test('idempotency: second startup yields same idea count with no duplicates', async () => {
    const before = await page.evaluate((): Promise<IdeaShape[]> => (window as any).lem.ideas.list())
    const countBefore = before.length

    await electronApp.close()
    ;({ app: electronApp, page } = await launchApp(dirs))

    const after = await page.evaluate((): Promise<IdeaShape[]> => (window as any).lem.ideas.list())
    expect(after).toHaveLength(countBefore)
  })

  test('linked runs: parent + child form a single idea with 2 rounds', async () => {
    const ideas = await page.evaluate((): Promise<IdeaShape[]> => (window as any).lem.ideas.list())
    const parentIdea = ideas.find(i => i.title === 'parent idea')
    expect(parentIdea).toBeDefined()

    const rounds = await page.evaluate(
      (id): Promise<RoundShape[]> => (window as any).lem.ideas.getRounds(id),
      parentIdea!.id,
    )
    expect(rounds).toHaveLength(2)
    const depths = rounds.map(r => r.roundDepth).sort((a, b) => a - b)
    expect(depths).toEqual([1, 2])
  })

  test('orphan: run whose parent is absent becomes a standalone root idea', async () => {
    const ideas = await page.evaluate((): Promise<IdeaShape[]> => (window as any).lem.ideas.list())
    const orphanIdea = ideas.find(i => i.title === 'orphan idea')
    expect(orphanIdea).toBeDefined()

    const rounds = await page.evaluate(
      (id): Promise<RoundShape[]> => (window as any).lem.ideas.getRounds(id),
      orphanIdea!.id,
    )
    expect(rounds).toHaveLength(1)
    expect(rounds[0].roundDepth).toBe(1)
    expect(rounds[0].parentRunId).toBeNull()
  })
})
