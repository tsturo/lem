import { app } from 'electron'
import { readFileSync, writeFileSync, renameSync } from 'fs'
import { join } from 'path'
import type { Settings } from '../shared/types'

const DEFAULTS: Settings = { theme: 'auto' }

function settingsPath(): string {
  return join(app.getPath('userData'), 'settings.json')
}

export function readSettings(): Settings {
  try {
    const raw = readFileSync(settingsPath(), 'utf8')
    return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch {
    return { ...DEFAULTS }
  }
}

export function writeSettings(settings: Settings): void {
  const path = settingsPath()
  const tmp = `${path}.tmp`
  writeFileSync(tmp, JSON.stringify(settings, null, 2), 'utf8')
  renameSync(tmp, path)
}
