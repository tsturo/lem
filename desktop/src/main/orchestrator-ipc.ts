import type { IpcMain, BrowserWindow } from 'electron'
import { OrchestratorBridge, ExitInfo } from './orchestrator-bridge'
import { IPC } from '../shared/ipc-channels'
import type { LogLine, ProgressEvent } from '../types/lem-events'

export function registerOrchestratorHandlers(
  ipcMain: IpcMain,
  bridge: OrchestratorBridge,
  getWindow: () => BrowserWindow | null,
): void {
  let cleanupRun: (() => void) | null = null

  ipcMain.handle(
    IPC.RUN_START,
    (_event, args: { idea: string; stub?: boolean; replaySpeed?: number }) => {
      cleanupRun?.()
      cleanupRun = null

      const win = getWindow()
      const runId = bridge.start(args.idea, {
        stub: args.stub,
        replaySpeed: args.replaySpeed,
      })

      function onEvent(event: ProgressEvent): void {
        win?.webContents.send(IPC.RUN_EVENT, event)
      }
      function onLog(logLine: LogLine): void {
        win?.webContents.send(IPC.RUN_LOG, logLine)
      }
      function onExit(info: ExitInfo): void {
        win?.webContents.send(IPC.RUN_EVENT, { kind: 'run_exit', ...info })
      }
      function onAuthExpired(): void {
        win?.webContents.send(IPC.RUN_EVENT, { kind: 'auth_expired' })
      }

      bridge.on('event', onEvent)
      bridge.on('log', onLog)
      bridge.on('exit', onExit)
      bridge.on('auth_expired', onAuthExpired)

      cleanupRun = () => {
        bridge.off('event', onEvent)
        bridge.off('log', onLog)
        bridge.off('exit', onExit)
        bridge.off('auth_expired', onAuthExpired)
      }

      return runId
    },
  )

  ipcMain.handle(IPC.RUN_CANCEL, (_event, runId: string) => {
    bridge.cancel(runId)
  })
}
