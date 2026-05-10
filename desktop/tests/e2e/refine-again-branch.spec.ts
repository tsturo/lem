import { test, expect, _electron as electron } from '@playwright/test'
import type { ElectronApplication, Page } from '@playwright/test'
import { DatabaseSync } from 'node:sqlite'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'fs'
import { join, resolve } from 'path'
import { tmpdir } from 'os'

const IDEA         = 'a task-management app for remote teams'
const IDEA_ID      = 'stub-idea-branch-001'
const RUN_1_ID     = 'stub-branch-r1-001'
const RUN_2_ID     = 'stub-branch-r2-001'
const SCREENSHOT_DIR = resolve(__dirname, '..', '..', 'screenshots')
const APP_MAIN       = resolve(__dirname, '..', '..', 'out', 'main', 'index.js')

function seedDb(dir: string): void {
  const db = new DatabaseSync(join(dir, 'library.db'))
  db.exec('PRAGMA journal_mode = WAL')
  db.exec(`
    CREATE TABLE IF NOT EXISTS ideas (
      id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at INTEGER NOT NULL
    )
  `)
  db.exec(`
    CREATE TABLE IF NOT EXISTS runs (
      run_id TEXT PRIMARY KEY, idea TEXT NOT NULL, status TEXT NOT NULL,
      verdict TEXT, workspace_path TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL, idea_id TEXT REFERENCES ideas(id),
      parent_run_id TEXT REFERENCES runs(run_id), branch_label TEXT,
      round_depth INTEGER NOT NULL DEFAULT 1
    )
  `)
  db.exec('CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC)')
  db.exec('CREATE INDEX IF NOT EXISTS idx_runs_idea_id ON runs (idea_id)')
  const now   = new Date().toISOString()
  const epoch = Math.floor(Date.now() / 1000)
  db.prepare('INSERT INTO ideas (id, title, created_at) VALUES (?, ?, ?)').run(IDEA_ID, IDEA, epoch)
  db.prepare(`INSERT INTO runs (run_id, idea, status, verdict, workspace_path,
    created_at, updated_at, idea_id, parent_run_id, branch_label, round_depth)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(
    RUN_1_ID, IDEA, 'completed', 'skip', '', now, now, IDEA_ID, null, null, 1,
  )
  db.prepare(`INSERT INTO runs (run_id, idea, status, verdict, workspace_path,
    created_at, updated_at, idea_id, parent_run_id, branch_label, round_depth)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(
    RUN_2_ID, IDEA, 'completed', 'build', '', now, now, IDEA_ID, RUN_1_ID, null, 2,
  )
  db.close()
}

function createTestDir(): string {
  const dir = mkdtempSync(join(tmpdir(), 'lem-e2e-branch-'))
  writeFileSync(join(dir, 'settings.json'), JSON.stringify({ theme: 'auto', claudePath: '/usr/bin/env' }))
  seedDb(dir)
  return dir
}

async function snap(page: Page, name: string): Promise<void> {
  await page.screenshot({ path: join(SCREENSHOT_DIR, name) })
}

test.describe('Feature A branch flow — stacked threads, 2 verdicts', () => {
  let electronApp: ElectronApplication
  let page: Page
  let testDir: string

  test.beforeAll(async () => {
    testDir = createTestDir()
    mkdirSync(SCREENSHOT_DIR, { recursive: true })
    electronApp = await electron.launch({
      args: [APP_MAIN, '--user-data-dir=' + testDir],
      env: { ...process.env, LEM_DESKTOP_STUB_RUN: '1' },
    })
    page = await electronApp.firstWindow()
    await page.waitForLoadState('domcontentloaded')
  })

  test.afterAll(async () => {
    await electronApp?.close()
    if (testDir) rmSync(testDir, { recursive: true, force: true })
  })

  test('branch alternative — labeled branch produces stacked-threads timeline', async () => {
    // 1. Navigate to the idea — opens Brief for Round 2 (latest by default)
    const ideaBtn = page.locator('aside button', { hasText: IDEA })
    await expect(ideaBtn).toBeVisible({ timeout: 10_000 })
    await ideaBtn.click()
    await page.waitForSelector('[data-brief]', { timeout: 8_000 })
    await snap(page, 'branch-01-brief-r2.png')

    // 2. Open the chevron dropdown on RefineAgainButton
    await page.click('[data-chevron]')
    await expect(page.locator('[data-menu]')).toBeVisible()
    await expect(page.locator('[data-menu-item="branch"]')).toBeVisible()
    await snap(page, 'branch-02-menu-open.png')

    // 3. Click Branch alternative — modal opens
    await page.click('[data-menu-item="branch"]')
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 4_000 })
    await expect(page.locator('[data-modal-title]')).toHaveText('⑂ Branch alternative')
    await expect(page.locator('[data-modal-subtitle]')).toContainText('Forking from Round 2')
    await snap(page, 'branch-03-modal-open.png')

    // 4. Fill label and context
    await page.fill('#refine-branch-label', 'mobile')
    await page.fill('#refine-context', 'iOS-only first, no web companion')

    // 5. Click Branch submit — modal closes
    await page.getByRole('button', { name: 'Branch' }).click()
    await expect(page.locator('[role="dialog"]')).not.toBeVisible({ timeout: 4_000 })
    await snap(page, 'branch-04-modal-submitted.png')

    // 6. App navigates to Theater for the new stub run
    await page.waitForSelector('[data-state="active"]', { timeout: 10_000 })
    await expect(page.locator('[data-state="done"]').first()).toBeVisible()
    await snap(page, 'branch-05-theater.png')

    // 7. Wait for stub-run completion (~30 s at replay-speed 10)
    await page.waitForSelector('[data-state="active"]', { state: 'detached', timeout: 55_000 })

    // 8. Brief reloads — assert STACKED THREADS layout, not a single linear row
    await page.waitForSelector('[data-brief]', { timeout: 8_000 })
    const strip = page.locator('[data-timeline-strip]')
    await expect(strip).toBeVisible()
    const threadRows = page.locator('[data-timeline-row]')
    await expect(threadRows).toHaveCount(2)
    await expect(page.locator('[data-timeline-row="main"]')).toBeVisible()
    await expect(page.locator('[data-timeline-row="branch"]')).toBeVisible()
    await snap(page, 'branch-06-stacked-threads.png')

    // 9. Branch pill carries the stub-run verdict color (BUILD)
    const branchPill = page
      .locator('[data-timeline-row="branch"] [data-pill]:not([data-placeholder="true"])')
      .last()
    await expect(branchPill).toHaveAttribute('data-verdict', 'BUILD')

    // 10. Branch label 'mobile' is visible on the branch thread
    await expect(page.locator('[data-branch-label]')).toContainText('mobile')

    // 11. Click main R2 pill — it becomes current
    const mainR2Pill = page.locator(
      '[data-timeline-row="main"] [data-pill][data-round="2"]',
    )
    await mainR2Pill.click()
    await expect(mainR2Pill).toHaveAttribute('data-current', 'true')
    await snap(page, 'branch-07-r2-active.png')

    // 12. Click branch pill — Brief switches to branch deliverables
    await branchPill.click()
    await expect(branchPill).toHaveAttribute('data-current', 'true')
    await expect(mainR2Pill).toHaveAttribute('data-current', 'false')
    await snap(page, 'branch-08-branch-active.png')

    // 13. Sidebar shows *3 (3 rounds total) and *2 (2 leaf branches)
    await expect(page.locator('aside').getByText('·3')).toBeVisible({ timeout: 5_000 })
    await expect(page.locator('aside').getByText('⑂2')).toBeVisible()
    await snap(page, 'branch-09-sidebar-badges.png')
  })

  test('branch with empty label — fallback stub-label appears', async () => {
    // Navigate to the idea to get the latest round in Brief
    const ideaBtn = page.locator('aside button', { hasText: IDEA })
    await ideaBtn.click()
    await page.waitForSelector('[data-brief]', { timeout: 8_000 })

    // Open branch modal
    await page.click('[data-chevron]')
    await expect(page.locator('[data-menu-item="branch"]')).toBeVisible()
    await page.click('[data-menu-item="branch"]')
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 4_000 })

    // Leave label blank, fill context only
    await page.fill('#refine-context', 'enterprise focus, no consumer tier')
    await page.getByRole('button', { name: 'Branch' }).click()
    await expect(page.locator('[role="dialog"]')).not.toBeVisible({ timeout: 4_000 })

    // Wait for stub run to complete
    await page.waitForSelector('[data-state="active"]', { timeout: 10_000 })
    await page.waitForSelector('[data-state="active"]', { state: 'detached', timeout: 55_000 })

    // Brief reloads — fallback label 'stub-label' appears on the branch thread
    await page.waitForSelector('[data-brief]', { timeout: 8_000 })
    await expect(
      page.locator('[data-branch-label]').filter({ hasText: 'stub-label' }),
    ).toBeVisible({ timeout: 5_000 })
    await snap(page, 'branch-10-fallback-label.png')
  })
})
