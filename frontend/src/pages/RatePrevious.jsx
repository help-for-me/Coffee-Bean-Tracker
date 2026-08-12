import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AdvancedRatingToggle from '../components/AdvancedRatingToggle'
import ScoreAndNotesFields from '../components/ScoreAndNotesFields'
import { listEntries, addRating } from '../api'
import { emptyAdvancedRating, ratingPayloadFromAdvanced } from '../utils/ratingPayload'

export default function RatePrevious() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [entries, setEntries] = useState([])
  const [selected, setSelected] = useState(null)
  const [score, setScore] = useState('')
  const [narrativeNotes, setNarrativeNotes] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [advanced, setAdvanced] = useState(emptyAdvancedRating)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const timeout = setTimeout(() => {
      listEntries({ q: query || undefined, limit: 20 })
        .then(setEntries)
        .catch(() => setEntries([]))
    }, 200)
    return () => clearTimeout(timeout)
  }, [query])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    if (score === '' || Number(score) < 0 || Number(score) > 10) {
      setError('Score must be between 0 and 10.')
      return
    }
    setSubmitting(true)
    try {
      await addRating(selected.id, {
        score: Number(score),
        narrative_notes: narrativeNotes.trim() || null,
        ...ratingPayloadFromAdvanced(advanced),
      })
      navigate('/history')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (!selected) {
    return (
      <div className="mx-auto max-w-md p-6 pb-24">
        <h1 className="mb-4 text-lg font-semibold text-gray-900">Rate a Previous Bean</h1>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search roaster or bean name..."
          className="mb-4 w-full rounded-md border border-gray-300 px-3 py-2"
        />
        {entries.length === 0 ? (
          <p className="text-sm text-gray-500">No entries yet — log one from Home first.</p>
        ) : (
          <ul className="divide-y divide-gray-200">
            {entries.map((entry) => (
              <li key={entry.id}>
                <button
                  type="button"
                  onClick={() => setSelected(entry)}
                  className="flex w-full items-center justify-between py-3 text-left"
                >
                  <span className="font-medium text-gray-900">
                    {entry.roaster} — {entry.bean_name}
                  </span>
                  <span className="text-sm text-purple-700">
                    {entry.latest_score ?? <span className="text-xs font-medium text-gray-400">Not yet rated</span>}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-md p-6 pb-24">
      <button
        type="button"
        onClick={() => setSelected(null)}
        className="mb-4 block text-sm text-purple-700"
      >
        ← Choose a different bean
      </button>
      <h1 className="mb-1 text-lg font-semibold text-gray-900">
        {selected.roaster} — {selected.bean_name}
      </h1>
      <p className="mb-4 text-sm text-gray-500">
        {selected.latest_score == null ? 'Rate it' : 'Rate it again'}
      </p>

      <ScoreAndNotesFields
        score={score}
        onScore={(e) => setScore(e.target.value)}
        narrativeNotes={narrativeNotes}
        onNarrativeNotes={(e) => setNarrativeNotes(e.target.value)}
      />

      <AdvancedRatingToggle
        show={showAdvanced}
        onToggle={() => setShowAdvanced((v) => !v)}
        value={advanced}
        onChange={setAdvanced}
      />

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-lg bg-purple-700 px-6 py-3 text-lg font-medium text-white disabled:opacity-50"
      >
        {submitting ? 'Saving...' : 'Save rating'}
      </button>
    </form>
  )
}
