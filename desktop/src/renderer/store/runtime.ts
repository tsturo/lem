import { create } from 'zustand'
import type { PhaseSnapshot, ProgressEvent, RunSnapshot } from '../../types/lem-events'

const PHASE_ESTIMATES: Record<string, number> = {
  '0':   0,
  '0.5': 20,
  '0.6': 90,
  '1':   120,
  '1.5': 45,
  '2.1': 60,
  '2.2': 60,
  '2.3': 60,
  '2.5': 20,
  '3':   135,
  '4':   210,
}

const TOTAL_ESTIMATE_S = Object.values(PHASE_ESTIMATES).reduce((a, b) => a + b, 0)

const PHASE_ORDER = ['0', '0.5', '0.6', '1', '1.5', '2.1', '2.2', '2.3', '2.5', '3', '4']

function makeInitialPhases(): PhaseSnapshot[] {
  return PHASE_ORDER.map(id => ({ id, state: 'queued', roles: [] }))
}

function computeEta(phases: PhaseSnapshot[]): string | undefined {
  let consumedS = 0
  for (const phase of phases) {
    if (phase.state === 'done') {
      consumedS += phase.durationS ?? PHASE_ESTIMATES[phase.id] ?? 0
    }
  }
  const remainingS = Math.max(0, TOTAL_ESTIMATE_S - consumedS)
  if (remainingS <= 0) return undefined
  if (remainingS >= 60) return `${Math.round(remainingS / 60)}m`
  return `${remainingS}s`
}

interface RuntimeState {
  runs: Record<string, RunSnapshot>
  activeRunId: string | null
  initRun(runId: string): void
  onPhaseStart(runId: string, event: ProgressEvent): void
  onPhaseDone(runId: string, event: ProgressEvent): void
  onPhaseSkipped(runId: string, event: ProgressEvent): void
  onRoleDone(runId: string, phaseId: string, roleName: string, output: string): void
  failRun(runId: string): void
  setActiveRun(runId: string): void
}

export const useRuntime = create<RuntimeState>((set) => ({
  runs:        {},
  activeRunId: null,

  initRun(runId) {
    const phases = makeInitialPhases()
    set(s => ({
      runs: {
        ...s.runs,
        [runId]: {
          id:           runId,
          phases,
          currentPhase: 0,
          totalCost:    0,
          eta:          computeEta(phases),
          status:       'running',
        },
      },
      activeRunId: runId,
    }))
  },

  onPhaseStart(runId, event) {
    set(s => {
      const run = s.runs[runId]
      if (!run) return s
      const phases = run.phases.map(p =>
        p.id === event.phase_id
          ? {
              ...p,
              state: 'active' as const,
              roles: event.roles.map(name => ({ name, state: 'thinking' as const })),
            }
          : p,
      )
      const idx = PHASE_ORDER.indexOf(event.phase_id)
      return {
        runs: {
          ...s.runs,
          [runId]: {
            ...run,
            phases,
            currentPhase: idx >= 0 ? idx : run.currentPhase,
          },
        },
      }
    })
  },

  onPhaseDone(runId, event) {
    set(s => {
      const run = s.runs[runId]
      if (!run) return s
      const phases = run.phases.map(p =>
        p.id === event.phase_id
          ? {
              ...p,
              state:     'done' as const,
              durationS: event.duration_s,
              costUsd:   event.cost_usd,
              roles:     p.roles.map(r =>
                r.state === 'thinking' ? { ...r, state: 'done' as const } : r,
              ),
            }
          : p,
      )
      const totalCost = run.totalCost + event.cost_usd
      const status    = event.phase_id === '4' ? 'completed' as const : run.status
      return {
        runs: {
          ...s.runs,
          [runId]: { ...run, phases, totalCost, eta: computeEta(phases), status },
        },
      }
    })
  },

  onPhaseSkipped(runId, event) {
    set(s => {
      const run = s.runs[runId]
      if (!run) return s
      const phases = run.phases.map(p =>
        p.id === event.phase_id
          ? { ...p, state: 'done' as const, durationS: 0, costUsd: 0 }
          : p,
      )
      return {
        runs: {
          ...s.runs,
          [runId]: { ...run, phases, eta: computeEta(phases) },
        },
      }
    })
  },

  onRoleDone(runId, phaseId, roleName, output) {
    set(s => {
      const run = s.runs[runId]
      if (!run) return s
      const phases = run.phases.map(p =>
        p.id === phaseId
          ? {
              ...p,
              roles: p.roles.map(r =>
                r.name === roleName ? { ...r, state: 'done' as const, output } : r,
              ),
            }
          : p,
      )
      return { runs: { ...s.runs, [runId]: { ...run, phases } } }
    })
  },

  failRun(runId) {
    set(s => {
      const run = s.runs[runId]
      if (!run) return s
      return {
        runs: {
          ...s.runs,
          [runId]: { ...run, status: 'failed' as const, eta: undefined },
        },
      }
    })
  },

  setActiveRun(runId) {
    set({ activeRunId: runId })
  },
}))

export { computeEta as _computeEtaForTest, TOTAL_ESTIMATE_S as _TOTAL_ESTIMATE_S }
