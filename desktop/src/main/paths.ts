import * as os from 'os'
import * as path from 'path'

export function lemRunsDir(): string {
  const xdgDataHome = process.env['XDG_DATA_HOME']
  const dataHome = xdgDataHome || path.join(os.homedir(), '.local', 'share')
  return path.join(dataHome, 'lem', 'runs')
}
