import type { Settings } from '../shared/types'
import type { LogLine, ProgressEvent } from '../types/lem-events'

declare global {
  interface Window {
    lem: {
      settings: {
        get(): Promise<Settings>
        set(settings: Settings): Promise<void>
      }
      run: {
        start(args: { idea: string; stub?: boolean; replaySpeed?: number }): Promise<string>
        cancel(runId: string): Promise<void>
        onEvent(
          callback: (event: ProgressEvent | { kind: string; [key: string]: unknown }) => void,
        ): () => void
        onLog(callback: (logLine: LogLine) => void): () => void
      }
    }
  }
}
