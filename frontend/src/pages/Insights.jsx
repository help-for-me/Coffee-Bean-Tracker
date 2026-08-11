import { useEffect, useState } from 'react'
import MonthlyTrendChart from '../components/MonthlyTrendChart'
import NarrativeSummary from '../components/NarrativeSummary'
import RankedScoreChart from '../components/RankedScoreChart'
import RepurchasedList from '../components/RepurchasedList'
import { getInsights } from '../api'

// Each attribute the "Favourite ___" chart can switch to. brew_style is new
// in 1.2.0, alongside the brew-method slicer below - the same ratings.
// brew_style field, previously collected but unused for insights.
const ATTRIBUTES = [
  { key: 'by_tasting_note', label: 'Tasting notes', labelKey: 'note', emptyMessage: 'No printed tasting notes on rated entries yet.' },
  { key: 'by_origin_country', label: 'Origin countries', labelKey: 'origin_country', emptyMessage: 'No known origin country on rated entries yet.' },
  { key: 'by_process', label: 'Processes', labelKey: 'process', emptyMessage: 'No rated entries with a known process yet.' },
  { key: 'by_brew_style', label: 'Brew methods', labelKey: 'brew_style', emptyMessage: 'No rated entries with a known brew method yet.' },
]

const BREW_STYLES = ['Pour Over', 'Espresso', 'French Press', 'Cafe-made', 'Other']

export default function Insights() {
  const [insights, setInsights] = useState(null)
  const [error, setError] = useState(null)
  const [window_, setWindow] = useState('all_time')
  const [attribute, setAttribute] = useState('by_tasting_note')
  const [brewStyle, setBrewStyle] = useState('')

  useEffect(() => {
    let isFirstLoad = true
    const load = () => {
      getInsights(brewStyle || undefined)
        .then((data) => {
          setInsights(data)
          // Only pick a default toggle position on the very first load - a
          // background refresh shouldn't yank the user back to "Recent"
          // if they'd deliberately switched to "All time".
          if (isFirstLoad) {
            setWindow(data.recent_window.applicable ? 'recent' : 'all_time')
            isFirstLoad = false
          }
        })
        .catch((e) => setError(e.message))
    }

    load()
    // Coming back to this tab (e.g. after adding a coffee elsewhere) should
    // show current numbers, not whatever was loaded when the page first
    // opened - the charts are cheap to refetch (no AI cost, unlike the
    // narrative summary below, which stays manual-refresh only).
    const onVisible = () => {
      if (document.visibilityState === 'visible') load()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [brewStyle])

  if (error) return <div className="p-6 text-sm text-red-600">{error}</div>
  if (!insights) return <div className="p-6 text-sm text-gray-500">Loading...</div>

  const mostRepurchased = insights.most_repurchased[window_]
  const activeAttribute = ATTRIBUTES.find((a) => a.key === attribute)
  const attributeRanking = insights[attribute][window_]
  // Slicing "brew methods" by a single brew method would just collapse the
  // chart to that one row - the slicer only makes sense against the other
  // three attributes.
  const brewSlicerApplies = attribute !== 'by_brew_style'

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

      <h2 className="mb-2 text-sm font-semibold text-gray-900">Insights summary</h2>
      <NarrativeSummary window={window_} />

      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-gray-900">Favourite</h2>
        <select
          value={attribute}
          onChange={(e) => setAttribute(e.target.value)}
          className="rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-700"
          aria-label="Choose which attribute to rank"
        >
          {ATTRIBUTES.map((a) => (
            <option key={a.key} value={a.key}>
              {a.label}
            </option>
          ))}
        </select>
      </div>
      {brewSlicerApplies && (
        <select
          value={brewStyle}
          onChange={(e) => setBrewStyle(e.target.value)}
          className="mb-2 w-full rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-700"
          aria-label="Filter by brew method"
        >
          <option value="">All brew methods</option>
          {BREW_STYLES.map((style) => (
            <option key={style} value={style}>
              When brewed as {style}
            </option>
          ))}
        </select>
      )}
      <div className="mb-1 rounded-md border border-gray-200 p-3">
        <RankedScoreChart
          data={attributeRanking.items}
          labelKey={activeAttribute.labelKey}
          emptyMessage={activeAttribute.emptyMessage}
          ariaLabel={`Average score by ${activeAttribute.label.toLowerCase()}`}
        />
      </div>
      <p className="mb-6 text-xs text-gray-500">
        {attributeRanking.items.length > 0 ? attributeRanking.significance.message : ' '}
      </p>

      <h2 className="mb-2 text-sm font-semibold text-gray-900">Most repurchased</h2>
      <RepurchasedList data={mostRepurchased} />
    </div>
  )
}
