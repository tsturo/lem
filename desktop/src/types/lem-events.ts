export type ProgressEventKind = 'phase_start' | 'phase_done' | 'phase_skipped'

export interface ProgressEvent {
  kind: ProgressEventKind
  phase_id: string
  roles: string[]
  duration_s: number
  cost_usd: number
  success: boolean
  timestamp: number
}

export interface LogLine {
  ts: string
  event: string
  phase_id?: string
  role?: string
  message?: string
}

export interface RoleSnapshot {
  name: string
  state: 'thinking' | 'done'
  output?: string
}

export interface PhaseSnapshot {
  id: string
  state: 'done' | 'active' | 'queued'
  roles: RoleSnapshot[]
  durationS?: number
  costUsd?: number
  summary?: string
}

export interface RunSnapshot {
  id: string
  phases: PhaseSnapshot[]
  currentPhase: number
  totalCost: number
  eta?: string
  status: 'running' | 'completed' | 'failed'
}

export interface RunExitEvent {
  kind: 'run_exit'
  code: number | null
  signal: NodeJS.Signals | null
  error?: Error
  stderr?: string
}
