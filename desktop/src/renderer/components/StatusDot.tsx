import type { Status } from '../../shared/types'

const STATUS_COLOR: Record<Status, string> = {
  running:   'var(--t-status-success)',
  completed: 'var(--t-status-success)',
  queued:    'var(--t-status-muted)',
  failed:    'var(--t-status-error)',
  archived:  'var(--t-status-muted)',
}

interface StatusDotProps {
  status: Status
}

export default function StatusDot({ status }: StatusDotProps) {
  const isRunning = status === 'running'
  return (
    <span
      data-status={status}
      style={{
        display: 'inline-block',
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: STATUS_COLOR[status],
        flexShrink: 0,
        animation: isRunning ? 't-pulse 1.4s ease-in-out infinite' : undefined,
      }}
    />
  )
}
