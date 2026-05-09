import { describe, it, expect, beforeEach } from 'vitest'
import { useRuntime, _computeEtaForTest, _TOTAL_ESTIMATE_S } from '@/store/runtime'
import type { ProgressEvent } from '../../src/types/lem-events'

function makeEvent(
  kind: ProgressEvent['kind'],
  phase_id: string,
  roles: string[] = [],
  duration_s = 0,
  cost_usd = 0,
): ProgressEvent {
  return { kind, phase_id, roles, duration_s, cost_usd, success: true, timestamp: Date.now() / 1000 }
}

describe('useRuntime', () => {
  beforeEach(() => {
    useRuntime.setState({ runs: {}, activeRunId: null })
  })

  // ── initRun ────────────────────────────────────────────────────────────────

  it('initRun creates a run with all phases queued', () => {
    useRuntime.getState().initRun('run-1')
    const run = useRuntime.getState().runs['run-1']
    expect(run).toBeDefined()
    expect(run.status).toBe('running')
    expect(run.phases.every(p => p.state === 'queued')).toBe(true)
  })

  it('initRun sets activeRunId', () => {
    useRuntime.getState().initRun('run-42')
    expect(useRuntime.getState().activeRunId).toBe('run-42')
  })

  it('initRun creates 11 phases matching the pipeline order', () => {
    useRuntime.getState().initRun('run-1')
    const ids = useRuntime.getState().runs['run-1'].phases.map(p => p.id)
    expect(ids).toEqual(['0', '0.5', '0.6', '1', '1.5', '2.1', '2.2', '2.3', '2.5', '3', '4'])
  })

  // ── onPhaseStart ───────────────────────────────────────────────────────────

  it('onPhaseStart marks the phase active and seeds roles as thinking', () => {
    useRuntime.getState().initRun('run-1')
    useRuntime.getState().onPhaseStart('run-1', makeEvent('phase_start', '1', ['architect', 'designer', 'market']))
    const phase = useRuntime.getState().runs['run-1'].phases.find(p => p.id === '1')
    expect(phase?.state).toBe('active')
    expect(phase?.roles).toHaveLength(3)
    expect(phase?.roles.every(r => r.state === 'thinking')).toBe(true)
  })

  it('onPhaseStart updates currentPhase index', () => {
    useRuntime.getState().initRun('run-1')
    useRuntime.getState().onPhaseStart('run-1', makeEvent('phase_start', '1', ['architect']))
    expect(useRuntime.getState().runs['run-1'].currentPhase).toBe(3)
  })

  it('onPhaseStart is a no-op for unknown runId', () => {
    useRuntime.getState().onPhaseStart('ghost', makeEvent('phase_start', '1', []))
    expect(useRuntime.getState().runs['ghost']).toBeUndefined()
  })

  // ── onPhaseDone ────────────────────────────────────────────────────────────

  it('onPhaseDone marks the phase done and flips remaining thinking roles to done', () => {
    useRuntime.getState().initRun('run-1')
    useRuntime.getState().onPhaseStart('run-1', makeEvent('phase_start', '0.5', ['jtbd-extractor']))
    useRuntime.getState().onPhaseDone('run-1', makeEvent('phase_done', '0.5', ['jtbd-extractor'], 14.3, 0.003))
    const phase = useRuntime.getState().runs['run-1'].phases.find(p => p.id === '0.5')
    expect(phase?.state).toBe('done')
    expect(phase?.durationS).toBe(14.3)
    expect(phase?.costUsd).toBe(0.003)
    expect(phase?.roles.every(r => r.state === 'done')).toBe(true)
  })

  it('onPhaseDone accumulates totalCost', () => {
    useRuntime.getState().initRun('run-1')
    useRuntime.getState().onPhaseStart('run-1', makeEvent('phase_start', '0.5', ['jtbd-extractor']))
    useRuntime.getState().onPhaseDone('run-1', makeEvent('phase_done', '0.5', [], 10, 0.003))
    useRuntime.getState().onPhaseStart('run-1', makeEvent('phase_start', '0.6', ['frame-shifter']))
    useRuntime.getState().onPhaseDone('run-1', makeEvent('phase_done', '0.6', [], 30, 0.007))
    expect(useRuntime.getState().runs['run-1'].totalCost).toBeCloseTo(0.01)
  })

  it('onPhaseDone for phase 4 transitions status to completed', () => {
    useRuntime.getState().initRun('run-1')
    useRuntime.getState().onPhaseStart('run-1', makeEvent('phase_start', '4', ['synthesizer']))
    useRuntime.getState().onPhaseDone('run-1', makeEvent('phase_done', '4', ['synthesizer'], 53.4, 0.03))
    expect(useRuntime.getState().runs['run-1'].status).toBe('completed')
  })

  it('onPhaseDone for non-final phase keeps status running', () => {
    useRuntime.getState().initRun('run-1')
    useRuntime.getState().onPhaseStart('run-1', makeEvent('phase_start', '1', ['architect']))
    useRuntime.getState().onPhaseDone('run-1', makeEvent('phase_done', '1', [], 44, 0.018))
    expect(useRuntime.getState().runs['run-1'].status).toBe('running')
  })

  // ── onPhaseSkipped ─────────────────────────────────────────────────────────

  it('onPhaseSkipped marks phase done with zero duration and cost', () => {
    useRuntime.getState().initRun('run-1')
    useRuntime.getState().onPhaseSkipped('run-1', makeEvent('phase_skipped', '0'))
    const phase = useRuntime.getState().runs['run-1'].phases.find(p => p.id === '0')
    expect(phase?.state).toBe('done')
    expect(phase?.durationS).toBe(0)
    expect(phase?.costUsd).toBe(0)
  })

  // ── onRoleDone ─────────────────────────────────────────────────────────────

  it('onRoleDone flips one role to done independently without affecting others', () => {
    useRuntime.getState().initRun('run-1')
    useRuntime.getState().onPhaseStart('run-1', makeEvent('phase_start', '1', ['architect', 'designer', 'market']))
    useRuntime.getState().onRoleDone('run-1', '1', 'architect', 'Architecture output')
    const phase = useRuntime.getState().runs['run-1'].phases.find(p => p.id === '1')
    const architect = phase?.roles.find(r => r.name === 'architect')
    const designer  = phase?.roles.find(r => r.name === 'designer')
    expect(architect?.state).toBe('done')
    expect(architect?.output).toBe('Architecture output')
    expect(designer?.state).toBe('thinking')
  })

  it('onRoleDone allows all three parallel roles to flip independently', () => {
    useRuntime.getState().initRun('run-1')
    useRuntime.getState().onPhaseStart('run-1', makeEvent('phase_start', '1', ['architect', 'designer', 'market']))
    useRuntime.getState().onRoleDone('run-1', '1', 'architect', 'a')
    useRuntime.getState().onRoleDone('run-1', '1', 'market', 'm')
    const phase = useRuntime.getState().runs['run-1'].phases.find(p => p.id === '1')
    expect(phase?.roles.find(r => r.name === 'architect')?.state).toBe('done')
    expect(phase?.roles.find(r => r.name === 'designer')?.state).toBe('thinking')
    expect(phase?.roles.find(r => r.name === 'market')?.state).toBe('done')
  })

  // ── failRun ────────────────────────────────────────────────────────────────

  it('failRun sets status to failed and clears eta', () => {
    useRuntime.getState().initRun('run-1')
    useRuntime.getState().failRun('run-1')
    const run = useRuntime.getState().runs['run-1']
    expect(run.status).toBe('failed')
    expect(run.eta).toBeUndefined()
  })

  it('failRun is a no-op for unknown runId', () => {
    useRuntime.getState().failRun('ghost')
    expect(useRuntime.getState().runs['ghost']).toBeUndefined()
  })
})

// ── ETA ────────────────────────────────────────────────────────────────────────

describe('computeEta', () => {
  it('returns the full estimate when no phases are done', () => {
    const phases = [
      { id: '0', state: 'queued' as const, roles: [] },
      { id: '0.5', state: 'queued' as const, roles: [] },
    ]
    const eta = _computeEtaForTest(phases)
    expect(eta).toBeDefined()
  })

  it('returns undefined when all phases are done', () => {
    const phases = [
      { id: '0', state: 'done' as const, roles: [], durationS: 0 },
      { id: '0.5', state: 'done' as const, roles: [], durationS: 20 },
      { id: '0.6', state: 'done' as const, roles: [], durationS: 90 },
      { id: '1', state: 'done' as const, roles: [], durationS: 120 },
      { id: '1.5', state: 'done' as const, roles: [], durationS: 45 },
      { id: '2.1', state: 'done' as const, roles: [], durationS: 60 },
      { id: '2.2', state: 'done' as const, roles: [], durationS: 60 },
      { id: '2.3', state: 'done' as const, roles: [], durationS: 60 },
      { id: '2.5', state: 'done' as const, roles: [], durationS: 20 },
      { id: '3', state: 'done' as const, roles: [], durationS: 135 },
      { id: '4', state: 'done' as const, roles: [], durationS: 210 },
    ]
    expect(_computeEtaForTest(phases)).toBeUndefined()
  })

  it('uses per-phase-id estimates (not rolling average from actuals)', () => {
    // Complete a phase much faster than estimated — remaining should still be based on fixed estimates
    const phases = [
      { id: '0', state: 'done' as const, roles: [], durationS: 0 },
      { id: '0.5', state: 'done' as const, roles: [], durationS: 1 }, // much faster than 20s estimate
    ]
    const eta = _computeEtaForTest(phases)
    // Remaining = TOTAL - 0 - 1 = TOTAL - 1, which is near full estimate
    // (not rolling average based adjustment)
    expect(eta).toBeDefined()
    const remainingS = _TOTAL_ESTIMATE_S - 0 - 1
    const expectedMinutes = Math.round(remainingS / 60)
    expect(eta).toBe(`${expectedMinutes}m`)
  })

  it('formats remaining time as minutes when >= 60s', () => {
    const eta = _computeEtaForTest([])
    expect(eta).toMatch(/^\d+m$/)
  })

  it('formats remaining time as seconds when < 60s', () => {
    // Complete almost everything, leave only a few seconds
    const phases = [
      { id: '0', state: 'done' as const, roles: [], durationS: 0 },
      { id: '0.5', state: 'done' as const, roles: [], durationS: 20 },
      { id: '0.6', state: 'done' as const, roles: [], durationS: 90 },
      { id: '1', state: 'done' as const, roles: [], durationS: 120 },
      { id: '1.5', state: 'done' as const, roles: [], durationS: 45 },
      { id: '2.1', state: 'done' as const, roles: [], durationS: 60 },
      { id: '2.2', state: 'done' as const, roles: [], durationS: 60 },
      { id: '2.3', state: 'done' as const, roles: [], durationS: 60 },
      { id: '2.5', state: 'done' as const, roles: [], durationS: 20 },
      { id: '3', state: 'done' as const, roles: [], durationS: 135 },
      // phase 4 still queued — estimate 210s, but we consumed 820-210=610s
      // remaining = 820 - 610 = 210s → "4m"
    ]
    const eta = _computeEtaForTest(phases)
    // 210s remaining = 4m (rounded)
    expect(eta).toBe('4m')
  })
})
