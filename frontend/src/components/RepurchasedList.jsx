const TREND_SYMBOL = { up: '▲', down: '▼', flat: '—' }

export default function RepurchasedList({ data }) {
  if (data.length === 0) {
    return <p className="text-sm text-gray-500">No beans purchased more than once yet.</p>
  }

  return (
    <ul className="divide-y divide-gray-200 rounded-md border border-gray-200 text-sm">
      {data.map((item) => (
        <li key={`${item.roaster}-${item.bean_name}`} className="flex items-center justify-between p-3">
          <div>
            <p className="font-medium text-gray-900">
              {item.roaster} — {item.bean_name}
            </p>
            <p className="text-xs text-gray-500">
              {item.entry_count} entries · {item.avg_score.toFixed(1)} avg
            </p>
          </div>
          <span className="text-gray-500" title={`Trend: ${item.trend}`} aria-label={`Trend: ${item.trend}`}>
            {TREND_SYMBOL[item.trend]}
          </span>
        </li>
      ))}
    </ul>
  )
}
