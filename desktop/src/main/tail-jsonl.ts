import * as fs from 'fs'
import * as path from 'path'

type CleanupFn = () => void

/**
 * Tails a JSONL file, calling onLine for each complete line received.
 * Buffers partial lines until a newline arrives.
 * Handles file-not-yet-created by watching the parent directory.
 * Uses FSEvents-safe directory watch to avoid coalescing issues on macOS.
 * Returns a cleanup function that stops watching.
 */
export function tailJsonl(filePath: string, onLine: (line: string) => void): CleanupFn {
  let offset = 0
  let buffer = ''
  let watcher: fs.FSWatcher | null = null

  function readChunk(): void {
    try {
      const stat = fs.statSync(filePath)
      if (stat.size <= offset) return

      const fd = fs.openSync(filePath, 'r')
      try {
        const length = stat.size - offset
        const buf = Buffer.alloc(length)
        const bytesRead = fs.readSync(fd, buf, 0, length, offset)
        offset += bytesRead
        buffer += buf.slice(0, bytesRead).toString('utf8')

        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (line.trim()) onLine(line)
        }
      } finally {
        fs.closeSync(fd)
      }
    } catch {
      // file not accessible yet or disappeared
    }
  }

  const dir = path.dirname(filePath)
  const basename = path.basename(filePath)

  // Read any existing content immediately before setting up the watch.
  readChunk()

  // Watch the parent directory — reliable on macOS FSEvents for both file
  // creation and modification events; avoids per-file kqueue unreliability.
  try {
    watcher = fs.watch(dir, (_event, filename) => {
      if (filename === basename) readChunk()
    })
    watcher.on('error', () => { /* ignore */ })
  } catch {
    // watch setup failed (e.g. parent dir does not exist)
  }

  return () => {
    watcher?.close()
    watcher = null
  }
}
