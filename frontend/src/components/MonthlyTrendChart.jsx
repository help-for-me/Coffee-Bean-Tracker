const ACCENT = '#7e22ce' // matches the app's existing purple-700 accent
const GRID = '#e5e7eb' // matches the app's existing border-gray-200
const CHART_WIDTH = 320
const CHART_HEIGHT = 160
const LEFT_MARGIN = 24
const RIGHT_PADDING = 32
const TOP_PADDING = 12
const BOTTOM_MARGIN = 24
const MAX_SCORE = 10

export default function MonthlyTrendChart({ data }) {
  if (data.length === 0) {
    return <p className="text-sm text-gray-500">No ratings logged yet.</p>
  }

  const plotWidth = CHART_WIDTH - LEFT_MARGIN - RIGHT_PADDING
  const plotHeight = CHART_HEIGHT - TOP_PADDING - BOTTOM_MARGIN
  const ticks = [0, 2, 4, 6, 8, 10]

  const xFor = (i) => (data.length === 1 ? LEFT_MARGIN + plotWidth / 2 : LEFT_MARGIN + (i / (data.length - 1)) * plotWidth)
  const yFor = (score) => TOP_PADDING + plotHeight - (score / MAX_SCORE) * plotHeight

  const linePath = data.map((row, i) => `${i === 0 ? 'M' : 'L'} ${xFor(i)},${yFor(row.avg_score)}`).join(' ')
  const last = data[data.length - 1]

  return (
    <svg viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} width="100%" role="img" aria-label="Average score by month">
      {ticks.map((tick) => (
        <line
          key={tick}
          x1={LEFT_MARGIN}
          y1={yFor(tick)}
          x2={CHART_WIDTH - RIGHT_PADDING}
          y2={yFor(tick)}
          stroke={GRID}
          strokeWidth={1}
        />
      ))}
      <path d={linePath} fill="none" stroke={ACCENT} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      {data.map((row, i) => (
        <circle key={row.month} cx={xFor(i)} cy={yFor(row.avg_score)} r={4} fill={ACCENT} stroke="white" strokeWidth={2}>
          <title>
            {row.month}: {row.avg_score.toFixed(1)} avg ({row.count} rating{row.count === 1 ? '' : 's'})
          </title>
        </circle>
      ))}
      <text x={xFor(data.length - 1)} y={yFor(last.avg_score) - 10} fontSize={11} fill="#374151" textAnchor="end">
        {last.avg_score.toFixed(1)}
      </text>
      {data.map((row, i) => (
        <text key={row.month} x={xFor(i)} y={CHART_HEIGHT - 6} fontSize={9} fill="#6b7280" textAnchor="middle">
          {row.month.slice(2)}
        </text>
      ))}
    </svg>
  )
}
