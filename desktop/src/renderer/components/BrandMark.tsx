interface BrandMarkProps {
  size?: string | number
  className?: string
}

const BAR_HEIGHTS = [35, 55, 75, 90, 100, 90, 75, 55, 35]
const BAR_OPACITIES = [0.55, 0.7, 0.85, 1, 1, 1, 0.85, 0.7, 0.55]

export function BrandMark({ size = '14px', className }: BrandMarkProps) {
  const sizeValue = typeof size === 'number' ? `${size}px` : size

  return (
    <span
      role="img"
      aria-label="Tonale"
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'flex-end',
        gap: '1px',
        width: sizeValue,
        height: sizeValue,
      }}
    >
      {BAR_HEIGHTS.map((heightPct, i) => (
        <span
          key={i}
          data-bar={i}
          style={{
            flex: 1,
            height: `${heightPct}%`,
            opacity: BAR_OPACITIES[i],
            background: 'var(--t-grad)',
            borderRadius: '1px 1px 0 0',
          }}
        />
      ))}
    </span>
  )
}
