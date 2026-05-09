import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 90_000,
  globalTimeout: 180_000,
  use: {
    actionTimeout: 30_000,
  },
  workers: 1,
  retries: 0,
  reporter: [['list']],
  outputDir: 'test-results',
})
