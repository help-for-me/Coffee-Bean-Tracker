import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listEntries } from '../api'
import { beanProfileDisplayName } from '../utils/beanProfileDisplay'

const ENTRY_TYPE_OPTIONS = [
  { value: '', label: 'All types' },
  { value: 'bag', label: 'Bag' },
  { value: 'cafe_cup', label: 'Cafe' },
]

const SORT_OPTIONS = [
  { value: 'date_desc', label: 'Newest first' },
  { value: 'date_asc', label: 'Oldest first' },
  { value: 'score_desc', label: 'Highest score first' },
  { value: 'score_asc', label: 'Lowest score first' },
]

export default function History() {
  const [entries, setEntries] = useState(null)
  const [error, setError] = useState(null)
  const [entryType, setEntryType] = useState('')
  const [sort, setSort] = useState('date_desc')

  useEffect(() => {
    listEntries({ entryType: entryType || undefined, sort })
      .then(setEntries)
      .catch((e) => setError(e.message))
  }, [entryType, sort])

  if (error) return <div className="p-6 text-sm text-red-600">{error}</div>

  return (
    <div className="p-6 pb-24">
      <h1 className="mb-4 text-lg font-semibold text-gray-900">History</h1>

      <div className="mb-4 flex gap-2">
        <select
          value={entryType}
          onChange={(e) => setEntryType(e.target.value)}
          className="flex-1 rounded-md border border-gray-300 px-2 py-1.5 text-sm text-gray-700"
          aria-label="Filter by entry type"
        >
          {ENTRY_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="flex-1 rounded-md border border-gray-300 px-2 py-1.5 text-sm text-gray-700"
          aria-label="Sort entries"
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {!entries ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-gray-500">No entries yet.</p>
      ) : (
        <ul className="divide-y divide-gray-200">
          {entries.map((entry) => (
            <li key={entry.id}>
              <Link
                to={`/entries/${entry.id}`}
                className="flex items-center justify-between py-3"
              >
                <div>
                  <p className="font-medium text-gray-900">
                    <span className="mr-2 rounded bg-gray-100 px-1.5 py-0.5 text-xs font-medium text-gray-600">
                      {entry.entry_type === 'bag' ? 'Bag' : 'Cafe'}
                    </span>
                    {beanProfileDisplayName(entry, entry.extraction_status)}
                  </p>
                  <p className="text-xs text-gray-500">
                    {entry.entry_date ?? entry.date_entered.slice(0, 10)}
                    {entry.extraction_status === 'pending' ? ' · processing…' : ''}
                  </p>
                </div>
                <span className="text-sm font-semibold text-purple-700">
                  {entry.latest_score ?? <span className="text-xs font-medium text-gray-400">Not yet rated</span>}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
