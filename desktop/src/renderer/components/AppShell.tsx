import type { ReactNode } from 'react'
import { Titlebar } from './Titlebar'

interface AppShellProps {
  sidebar: ReactNode
  children: ReactNode
}

export function AppShell({ sidebar, children }: AppShellProps) {
  return (
    <div className="flex flex-col h-full">
      <Titlebar />
      <div className="flex flex-1 min-h-0">
        <aside
          className="bg-surface border-r border-border overflow-y-auto shrink-0"
          style={{ width: 232 }}
        >
          {sidebar}
        </aside>
        <main className="flex-1 min-w-0">
          {children}
        </main>
      </div>
    </div>
  )
}
