const ACCENT = '#7e22ce' // matches the app's existing purple-700 accent
const GRID = '#e5e7eb' // matches the app's existing border-gray-200
const LEFT_MARGIN = 108
const RIGHT_PADDING = 28
const CHART_WIDTH = 320
const BAR_HEIGHT = 18
const BAR_GAP = 10
const RADIUS = 4
const MAX_SCORE = 10

function barPath(x1, x2, y, height, radius) {
  const r = Math.min(radius, (x2 - x1) / 2, height / 2)
  return `M ${x1},${y} L ${x2 - r},${y} Q ${x2},${y} ${x2},${y + r} L ${x2},${y + height - r} Q ${x2},${y + height} ${x2 - r},${y + height} L ${x1},${y + height} Z`
}

export default function RankedScoreChart({ data, labelKey, emptyMessage, ariaLabel }) {
  if (data.length === 0) {
    return <p className="text-sm text-gray-500">{emptyMessage}</p>
  }

  const plotWidth = CHART_WIDTH - LEFT_MARGIN - RIGHT_PADDING
  const rowHeight = BAR_HEIGHT + BAR_GAP
  const height = data.length * rowHeight + 24
  const ticks = [0, 2, 4, 6, 8, 10]

  return (
    <svg viewBox={`0 0 ${CHART_WIDTH} ${height}`} width="100%" role="img" aria-label={ariaLabel}>
      {ticks.map((tick) => {
        const x = LEFT_MARGIN + (tick / MAX_SCORE) * plotWidth
        return (
          <g key={tick}>
            <line x1={x} y1={0} x2={x} y2={data.length * rowHeight} stroke={GRID} strokeWidth={1} />
            <text x={x} y={data.length * rowHeight + 16} fontSize={10} fill="#6b7280" textAnchor="middle">
              {tick}
            </text>
          </g>
        )
      })}
      {data.map((row, i) => {
        const label = row[labelKey]
        const y = i * rowHeight
        const barWidth = (row.avg_score / MAX_SCORE) * plotWidth
        return (
          <g key={label}>
            <text x={LEFT_MARGIN - 8} y={y + BAR_HEIGHT / 2 + 4} fontSize={11} fill="#374151" textAnchor="end">
              {label}
            </text>
            <path d={barPath(LEFT_MARGIN, LEFT_MARGIN + barWidth, y, BAR_HEIGHT, RADIUS)} fill={ACCENT}>
              <title>
                {label}: {row.avg_score.toFixed(1)} avg ({row.count} rating{row.count === 1 ? '' : 's'})
              </title>
            </path>
            <text x={LEFT_MARGIN + barWidth + 6} y={y + BAR_HEIGHT / 2 + 4} fontSize={11} fill="#374151">
              {row.avg_score.toFixed(1)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
