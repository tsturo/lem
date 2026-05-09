export interface Settings {
  theme: 'auto' | 'light' | 'dark'
  claudePath?: string
}

export type Verdict = 'build' | 'skip' | 'unsure'

export type Status = 'running' | 'completed' | 'failed' | 'queued' | 'archived'

export type RunGroup = 'active' | 'done' | 'archive'

export type RunStatus = 'running' | 'completed' | 'failed' | 'archived'

export interface LibraryItem {
  runId: string
  idea: string
  verdict: Verdict | null
  status: RunStatus
  createdAt: string
  updatedAt: string
}

export interface RunRow {
  runId: string
  idea: string
  verdict: Verdict | null
  status: RunStatus
  group: RunGroup
  createdAt: string
  updatedAt: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export interface ProgressEvent {
  runId: string
  phase: string
  role: string
  status: 'started' | 'completed' | 'failed'
  message: string
  timestamp: string
}
