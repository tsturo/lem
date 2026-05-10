import type { Settings, LibraryItem, Idea, RunRow, RefineRequest, RefineResponse } from '../shared/types'
import type { LogLine, ProgressEvent } from '../types/lem-events'
import type { BriefData } from '../main/workspace-reader'

declare global {
  interface Window {
    lem: {
      settings: {
        get(): Promise<Settings>
        set(settings: Settings): Promise<void>
      }
      claude: {
        detect(): Promise<string | null>
        pickPath(): Promise<string | null>
        login(claudePath: string): Promise<void>
      }
      shell: {
        openExternal(url: string): Promise<void>
        openFile?(): Promise<string | null>
      }
      library: {
        list(): Promise<LibraryItem[]>
      }
      ideas: {
        list(): Promise<Idea[]>
        getRounds(ideaId: string): Promise<RunRow[]>
        getDag(ideaId: string): Promise<RunRow[]>
        rename(ideaId: string, newTitle: string): Promise<void>
      }
      run: {
        start(args: { idea: string; stub?: boolean; replaySpeed?: number }): Promise<string>
        cancel(runId: string): Promise<void>
        onEvent(
          callback: (event: ProgressEvent | { kind: string; [key: string]: unknown }) => void,
        ): () => void
        onLog(callback: (logLine: LogLine) => void): () => void
        refine(req: RefineRequest): Promise<RefineResponse>
        setBranchLabel(runId: string, label: string | null): Promise<void>
      }
      workspace: {
        readBrief(workspacePath: string): Promise<BriefData>
      }
    }
  }
}
