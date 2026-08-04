import { useEffect, useState } from 'react'
import MonthlyTrendChart from '../components/MonthlyTrendChart'
import RepurchasedList from '../components/RepurchasedList'
import ScoreByProcessChart from '../components/ScoreByProcessChart'
import { getInsights } from '../api'

export default function Insights() {
  const [insights, setInsights] = useState(null)
  const [error, setError] = useState(null)
  const [window_, setWindow] = useState('all_time')

  useEffect(() => {
    getInsights()
      .then((data) => {
        setInsights(data)
        setWindow(data.recent_window.applicable ? 'recent' : 'all_time')
      })
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="p-6 text-sm text-red-600">{error}</div>
  if (!insights) return <div className="p-6 text-sm text-gray-500">Loading...</div>

  const byProcess = insights.by_process[window_]
  const mostRepurchased = insights.most_repurchased[window_]

  return (
    <div className="mx-auto max-w-md p-6 pb-24">
      <h1 className="mb-4 text-lg font-semibold text-gray-900">Insights</h1>

      <h2 className="mb-2 text-sm font-semibold text-gray-900">Score by month</h2>
      <div className="mb-6 rounded-md border border-gray-200 p-3">
        <MonthlyTrendChart data={insights.monthly_trend} />
      </div>

      {insights.recent_window.applicable && (
        <div className="mb-4 flex gap-2">
          {['recent', 'all_time'].map((w) => (
            <button
              key={w}
              type="button"
              onClick={() => setWindow(w)}
              className={`flex-1 rounded-md border px-3 py-2 text-sm font-medium ${
                window_ === w ? 'border-purple-700 bg-purple-700 text-white' : 'border-gray-300 text-gray-700'
              }`}
            >
              {w === 'recent' ? 'Recent' : 'All time'}
            </button>
          ))}
        </div>
      )}

      <h2 className="mb-2 text-sm font-semibold text-gray-900">Score by process</h2>
      <div className="mb-6 rounded-md border border-gray-200 p-3">
        <ScoreByProcessChart data={byProcess} />
      </div>

      <h2 className="mb-2 text-sm font-semibold text-gray-900">Most repurchased</h2>
      <RepurchasedList data={mostRepurchased} />
    </div>
  )
}
