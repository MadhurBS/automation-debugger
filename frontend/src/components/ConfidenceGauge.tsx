interface Props {
  value: number   // 0–100
  size?: number
}

export default function ConfidenceGauge({ value, size = 120 }: Props) {
  const cx = size / 2
  const cy = size / 2
  const r = (size * 0.38)
  const strokeWidth = size * 0.08

  // Arc from 210° to 330° (240° sweep)
  const startAngle = 210
  const sweepAngle = 240
  const endAngle = startAngle + (sweepAngle * value) / 100

  const toRad = (deg: number) => (deg * Math.PI) / 180
  const arcX = (ang: number) => cx + r * Math.cos(toRad(ang))
  const arcY = (ang: number) => cy + r * Math.sin(toRad(ang))

  const bgEnd = startAngle + sweepAngle
  const bgPath = `M ${arcX(startAngle)} ${arcY(startAngle)} A ${r} ${r} 0 1 1 ${arcX(bgEnd - 0.01)} ${arcY(bgEnd - 0.01)}`

  const fillLargeArc = sweepAngle * value / 100 > 180 ? 1 : 0
  const fillPath = value > 0
    ? `M ${arcX(startAngle)} ${arcY(startAngle)} A ${r} ${r} 0 ${fillLargeArc} 1 ${arcX(endAngle)} ${arcY(endAngle)}`
    : ''

  const color = value >= 80 ? '#16a34a' : value >= 60 ? '#ca8a04' : value >= 40 ? '#ea580c' : '#dc2626'

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size * 0.75} viewBox={`0 0 ${size} ${size}`} style={{ overflow: 'visible' }}>
        {/* Background arc */}
        <path d={bgPath} fill="none" stroke="#e5e7eb" strokeWidth={strokeWidth} strokeLinecap="round" />
        {/* Fill arc */}
        {fillPath && (
          <path d={fillPath} fill="none" stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" />
        )}
        {/* Center value */}
        <text x={cx} y={cy + 4} textAnchor="middle" fontSize={size * 0.18} fontWeight="700" fill="#1f2328">
          {value}%
        </text>
        <text x={cx} y={cy + size * 0.16} textAnchor="middle" fontSize={size * 0.1} fill="#57606a">
          confidence
        </text>
      </svg>
    </div>
  )
}
