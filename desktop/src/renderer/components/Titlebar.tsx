import { BrandMark } from './BrandMark'

export function Titlebar() {
  return (
    <div
      className="h-9 flex items-center justify-center bg-surface border-b border-border shrink-0"
      style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
    >
      <div className="flex items-center gap-1.5">
        <BrandMark size="14px" />
        <span
          className="text-text-2"
          style={{ fontSize: 13, fontFamily: 'var(--t-font)', fontWeight: 500 }}
        >
          lem · by tonale
        </span>
      </div>
    </div>
  )
}
