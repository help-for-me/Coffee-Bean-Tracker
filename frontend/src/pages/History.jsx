import { useEffect, useState } from 'react'
import { listEntries } from '../api'

export default function History() {
  const [entries, setEntries] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    listEntries().then(setEntries).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="p-6 text-sm text-red-600">{error}</div>
  if (!entries) return <div className="p-6 text-sm text-gray-500">Loading...</div>

  return (
    <div className="p-6 pb-24">
      <h1 className="mb-4 text-lg font-semibold text-gray-900">History</h1>
      {entries.length === 0 ? (
        <p className="text-sm text-gray-500">No entries yet.</p>
      ) : (
        <ul className="divide-y divide-gray-200">
          {entries.map((entry) => (
            <li key={entry.id} className="flex items-center justify-between py-3">
              <div>
                <p className="font-medium text-gray-900">
                  {entry.entry_type === 'bag' ? '📦' : '☕'} {entry.roaster} — {entry.bean_name}
                </p>
                <p className="text-xs text-gray-500">
                  {entry.entry_date ?? entry.date_entered.slice(0, 10)}
                  {entry.extraction_status === 'pending' ? ' · processing…' : ''}
                </p>
              </div>
              <span className="text-sm font-semibold text-purple-700">
                {entry.latest_score ?? '—'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
