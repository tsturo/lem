import { test, expect, _electron as electron } from '@playwright/test'
import type { ElectronApplication, Page } from '@playwright/test'
import { DatabaseSync } from 'node:sqlite'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'fs'
import { join, resolve } from 'path'
import { tmpdir } from 'os'

const IDEA = 'a productivity app for remote teams'
const STUB_IDEA_ID = 'stub-idea-cont-001'
const STUB_RUN_ID = 'stub-run-cont-001'
const SCREENSHOT_DIR = resolve(__dirname, '..', '..', 'screenshots', 'refine-again')
const APP_MAIN = resolve(__dirname, '..', '..', 'out', 'main', 'index.js')

function createTestUserDataDir(): string {
  const dir = mkdtempSync(join(tmpdir(), 'lem-e2e-continue-'))

  writeFileSync(
    join(dir, 'settings.json'),
    JSON.stringify({ theme: 'auto', claudePath: '/usr/bin/env' }),
  )

  const db = new DatabaseSync(join(dir, 'library.db'))
  db.exec('PRAGMA journal_mode = WAL')
  db.exec(`
    CREATE TABLE IF NOT EXISTS ideas (
      id          TEXT PRIMARY KEY,
      title       TEXT NOT NULL,
      created_at  INTEGER NOT NULL
    )
  `)
  db.exec(`
    CREATE TABLE IF NOT EXISTS runs (
      run_id        TEXT PRIMARY KEY,
      idea          TEXT NOT NULL,
      status        TEXT NOT NULL,
      verdict       TEXT,
      workspace_path TEXT NOT NULL DEFAULT '',
      created_at    TEXT NOT NULL,
      updated_at    TEXT NOT NULL,
      idea_id       TEXT REFERENCES ideas(id),
      parent_run_id TEXT REFERENCES runs(run_id),
      branch_label  TEXT,
      round_depth   INTEGER NOT NULL DEFAULT 1
    )
  `)
  db.exec('CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC)')
  db.exec('CREATE INDEX IF NOT EXISTS idx_runs_idea_id ON runs (idea_id)')

  const now = new Date().toISOString()
  const ideaCreatedAt = Math.floor(Date.now() / 1000)

  db.prepare('INSERT INTO ideas (id, title, created_at) VALUES (?, ?, ?)').run(
    STUB_IDEA_ID, IDEA, ideaCreatedAt,
  )
  db.prepare(`
    INSERT INTO runs
      (run_id, idea, status, verdict, workspace_path, created_at, updated_at,
       idea_id, parent_run_id, branch_label, round_depth)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(STUB_RUN_ID, IDEA, 'completed', 'build', '', now, now, STUB_IDEA_ID, null, null, 1)

  db.close()
  return dir
}

async function snap(page: Page, name: string): Promise<void> {
  await page.screenshot({ path: join(SCREENSHOT_DIR, name) })
}

test.describe('Feature A continue-flow — refine again (stubbed)', () => {
  let electronApp: ElectronApplication
  let page: Page
  let testDir: string

  test.beforeAll(async () => {
    testDir = createTestUserDataDir()
    mkdirSync(SCREENSHOT_DIR, { recursive: true })

    electronApp = await electron.launch({
      args: [APP_MAIN, `--user-data-dir=${testDir}`],
      env: { ...process.env, LEM_DESKTOP_STUB_RUN: '1' },
    })

    page = await electronApp.firstWindow()
    await page.waitForLoadState('domcontentloaded')
  })

  test.afterAll(async () => {
    await electronApp?.close()
    if (testDir) rmSync(testDir, { recursive: true, force: true })
  })

  test('sidebar -> brief -> refine-again modal -> theater -> 2-round brief -> pill navigation', async () => {
    // Step 3: Sidebar renders the idea; 1-round idea has NO badge
    const ideaRow = page.locator('aside button', { hasText: IDEA })
    await expect(ideaRow).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('aside').getByText(/\xb7\d+/)).not.toBeVisible()

    // Step 4: Click idea row -> Brief loads
    await ideaRow.click()
    await page.waitForSelector('[data-brief]', { timeout: 10_000 })
    await snap(page, '01-idea-selected.png')

    // Step 5: TimelineStrip renders with exactly 1 verdict pill
    await expect(page.locator('[data-timeline-strip]')).toBeVisible()
    await expect(page.locator('button[data-pill]')).toHaveCount(1)
    await expect(page.locator('button[data-pill][data-round="1"]')).toBeVisible()

    // Step 6: Click 'Refine again' main button
    await page.click('[data-refine-again-button] [data-main]')

    // Step 7: Modal opens -- assert title and subtitle
    await page.waitForSelector('[role="dialog"]', { timeout: 5_000 })
    await expect(page.locator('[data-modal-title]')).toContainText('Refine again')
    await expect(page.locator('[data-modal-subtitle]')).toContainText('Round 2 of')

    await snap(page, '02-modal-open.png')

    // Step 8: Type new context in the textarea
    await page.fill(
      'textarea[aria-label="What is changed about this idea?"]',
      'now mobile-first with comments',
    )

    // Step 9: Click Refine submit -> modal closes
    await page.getByRole('button', { name: 'Refine', exact: true }).click()
    await page.waitForSelector('[role="dialog"]', { state: 'hidden', timeout: 5_000 })
    await snap(page, '03-modal-submit.png')

    // Step 10: App navigates to Theater for the new run
    await page.waitForSelector('[data-state="queued"]', { timeout: 10_000 })
    await expect(page.locator('[data-state="queued"]').first()).toBeVisible()
    await snap(page, '04-theater.png')

    // Step 11: Wait for stub-run completion (replaySpeed=60 => ~5s wall time)
    await page.waitForSelector('[data-state="active"]', { timeout: 15_000 })
    await page.waitForSelector('[data-state="active"]', { state: 'detached', timeout: 30_000 })

    // Step 12: Brief reloads -- TimelineStrip shows TWO pills (round 1 and round 2)
    await page.waitForSelector('[data-brief]', { timeout: 10_000 })
    await expect(page.locator('[data-timeline-strip]')).toBeVisible()
    await expect(page.locator('button[data-pill]')).toHaveCount(2)
    await expect(page.locator('button[data-pill][data-round="1"]')).toBeVisible()
    await expect(page.locator('button[data-pill][data-round="2"]')).toBeVisible()
    await snap(page, '05-brief-2-rounds.png')

    // Step 13: Sidebar auto-refreshes -- idea shows badge and 2 expanded round rows
    await expect(page.locator('aside').getByText('\xb72')).toBeVisible({ timeout: 5_000 })
    await expect(page.locator('aside').locator('span', { hasText: /^Round \d$/ })).toHaveCount(2)

    // Step 14: Click round 1 pill -> Brief updates to round 1 as current
    await page.click('button[data-pill][data-round="1"]')
    await expect(page.locator('button[data-pill][data-round="1"][data-current="true"]')).toBeVisible()
    await snap(page, '06-round-1-active.png')

    // Step 15: Click round 2 pill -> Brief updates to round 2 as current
    await page.click('button[data-pill][data-round="2"]')
    await expect(page.locator('button[data-pill][data-round="2"][data-current="true"]')).toBeVisible()
    await snap(page, '07-round-2-active.png')
  })
})
