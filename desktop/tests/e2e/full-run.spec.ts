import { test, expect, _electron as electron } from '@playwright/test'
import type { ElectronApplication, Page } from '@playwright/test'
import { DatabaseSync } from 'node:sqlite'
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'fs'
import { join, resolve } from 'path'
import { tmpdir } from 'os'

const IDEA = 'a calendar app for parents and kids'
const STUB_IDEA_ID = 'stub-idea-001'
const STUB_RUN_ID = 'stub-completed-001'
const SCREENSHOT_DIR = resolve(__dirname, '..', '..', 'screenshots')
const APP_MAIN = resolve(__dirname, '..', '..', 'out', 'main', 'index.js')

function createTestUserDataDir(): string {
  const dir = mkdtempSync(join(tmpdir(), 'lem-e2e-'))

  // Pre-seed settings.json so the app skips the loading-spinner check on claudePath
  writeFileSync(join(dir, 'settings.json'), JSON.stringify({ theme: 'auto', claudePath: '/usr/bin/env' }))

  // Pre-seed library.db with a completed 'build' run linked to an idea row.
  // The Sidebar now renders ideas at top level and resolves rounds via the ideas table,
  // so both the ideas and runs tables must be populated and linked.
  // Uses node:sqlite (built-in, no native ABI) so this setup code works regardless of
  // whether better-sqlite3 is compiled for Electron or host Node.js.
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
  db.prepare(
    'INSERT INTO ideas (id, title, created_at) VALUES (?, ?, ?)',
  ).run(STUB_IDEA_ID, IDEA, ideaCreatedAt)
  db.prepare(
    `INSERT INTO runs
       (run_id, idea, status, verdict, workspace_path, created_at, updated_at,
        idea_id, parent_run_id, branch_label, round_depth)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  ).run(STUB_RUN_ID, IDEA, 'completed', 'build', '', now, now, STUB_IDEA_ID, null, null, 1)
  db.close()

  return dir
}

async function snap(page: Page, name: string): Promise<void> {
  await page.screenshot({ path: join(SCREENSHOT_DIR, name) })
}

test.describe('full run — stubbed orchestrator', () => {
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

  test('intake -> chat -> confirm -> theater -> brief', async () => {
    // 1. Assert app launches with sidebar and intake screen
    await page.waitForSelector('[data-screen="intake-input"]', { timeout: 15_000 })
    await expect(page.locator('[data-screen="intake-input"]')).toBeVisible()
    await expect(page.getByRole('button', { name: '+ New idea' })).toBeVisible()
    await snap(page, '01-intake.png')

    // 2. Click "+ New idea" (ensures intake state is fresh)
    await page.getByRole('button', { name: '+ New idea' }).click()

    // 3. Type the idea
    await page.fill('textarea[aria-label="Your idea"]', IDEA)

    // 4. Click "Refine my idea ->"
    await page.getByRole('button', { name: /Refine my idea/i }).click()

    // Chat screen opens with first clarifying question
    await page.waitForSelector('[data-message="assistant"]', { timeout: 5_000 })
    await snap(page, '02-chat.png')

    // 5. Answer each of the 3 clarifying questions with a one-word answer + Enter
    for (let i = 0; i < 3; i++) {
      await page.waitForSelector('textarea[data-input]', { timeout: 5_000 })
      await page.fill('textarea[data-input]', 'yes')
      await page.keyboard.press('Enter')
    }

    // 6. ConfirmationCard appears after all questions answered
    await page.waitForSelector('[data-screen="confirmation"]', { timeout: 5_000 })
    await snap(page, '03-confirmation.png')

    // 7. Click "Start analysis" to launch the stub run
    await page.click('[data-action="start-analysis"]')

    // 8. Theater shows -- assert step rail has done, active, and queued segments
    await page.waitForSelector('[data-state="active"]', { timeout: 10_000 })
    await expect(page.locator('[data-state="done"]').first()).toBeVisible()
    await expect(page.locator('[data-state="active"]').first()).toBeVisible()
    await expect(page.locator('[data-state="queued"]').first()).toBeVisible()
    await snap(page, '04-theater.png')

    // 9. Wait for all 9 phases to complete (~30 s with stub at replay-speed 10).
    // Theater unmounts when phase 4 finishes, so data-state="active" detaches.
    await page.waitForSelector('[data-state="active"]', { state: 'detached', timeout: 55_000 })

    // 10. The pre-seeded completed run is visible in the sidebar -- click it to open Brief
    const sidebarItem = page.locator('aside button', { hasText: IDEA })
    await expect(sidebarItem).toBeVisible({ timeout: 5_000 })
    await sidebarItem.click()

    // 11. Brief shows with verdict pill for "build"
    await page.waitForSelector('[data-brief]', { timeout: 5_000 })
    await expect(page.locator('[data-verdict="build"]')).toBeVisible()
    await snap(page, '05-brief.png')

    // 12. Click through all 3 tabs and assert each becomes active
    await page.click('[data-tab="exec"]')
    await expect(page.locator('[data-tab="exec"][data-active="true"]')).toBeVisible()

    await page.click('[data-tab="mvp"]')
    await expect(page.locator('[data-tab="mvp"][data-active="true"]')).toBeVisible()

    await page.click('[data-tab="risks"]')
    await expect(page.locator('[data-tab="risks"][data-active="true"]')).toBeVisible()
  })
})
