import { execFileSync, spawn } from 'child_process'
import { homedir } from 'os'
import { join } from 'path'

function validateBinary(binaryPath: string): Promise<boolean> {
  return new Promise((resolve) => {
    const proc = spawn(binaryPath, ['--version'])
    const timer = setTimeout(() => {
      proc.kill()
      resolve(false)
    }, 5000)
    proc.on('close', (code) => {
      clearTimeout(timer)
      resolve(code === 0)
    })
    proc.on('error', () => {
      clearTimeout(timer)
      resolve(false)
    })
  })
}

function buildCandidatePaths(): string[] {
  const home = homedir()
  const paths: string[] = []

  try {
    const which = execFileSync('which', ['claude'], { encoding: 'utf8' }).trim()
    if (which) paths.push(which)
  } catch { /* not on PATH */ }

  paths.push(
    '/opt/homebrew/bin/claude',
    '/usr/local/bin/claude',
    join(home, '.local/bin/claude'),
    join(home, '.claude/local/claude'),
  )

  try {
    const npmRoot = execFileSync('npm', ['root', '-g'], { encoding: 'utf8' }).trim()
    if (npmRoot) paths.push(join(npmRoot, '../.bin/claude'))
  } catch { /* npm not available or no global root */ }

  return paths
}

export async function detectClaude(candidatePaths?: string[]): Promise<string | null> {
  const envBin = process.env['LEM_CLAUDE_BIN']
  if (envBin) {
    return (await validateBinary(envBin)) ? envBin : null
  }

  const candidates = candidatePaths ?? buildCandidatePaths()
  for (const p of candidates) {
    if (await validateBinary(p)) return p
  }
  return null
}
