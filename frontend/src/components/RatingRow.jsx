import { useState } from 'react'
import AdvancedRatingFields from './AdvancedRatingFields'
import { advancedFromRating, ratingPayloadFromAdvanced } from '../utils/ratingPayload'

export default function RatingRow({ rating, onSave, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [score, setScore] = useState(rating.score)
  const [narrativeNotes, setNarrativeNotes] = useState(rating.narrative_notes ?? '')
  const [advanced, setAdvanced] = useState(() => advancedFromRating(rating))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const startEditing = () => {
    setScore(rating.score)
    setNarrativeNotes(rating.narrative_notes ?? '')
    setAdvanced(advancedFromRating(rating))
    setError(null)
    setEditing(true)
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      await onSave({
        score: Number(score),
        narrative_notes: narrativeNotes.trim() || null,
        ...ratingPayloadFromAdvanced(advanced),
      })
      setEditing(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = () => {
    if (window.confirm('Delete this rating?')) {
      onDelete()
    }
  }

  if (editing) {
    return (
      <li className="p-3 text-sm">
        <label className="block text-xs text-gray-600">Score (0-10)</label>
        <input
          type="number"
          min="0"
          max="10"
          step="0.5"
          value={score}
          onChange={(e) => setScore(e.target.value)}
          className="mt-1 mb-2 w-full rounded-md border border-gray-300 px-2 py-1"
        />
        <label className="block text-xs text-gray-600">Notes</label>
        <input
          value={narrativeNotes}
          onChange={(e) => setNarrativeNotes(e.target.value)}
          className="mt-1 mb-2 w-full rounded-md border border-gray-300 px-2 py-1"
        />
        <AdvancedRatingFields value={advanced} onChange={setAdvanced} />
        {error && <p className="mb-2 text-red-600">{error}</p>}
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="text-xs font-medium text-purple-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button type="button" onClick={() => setEditing(false)} className="text-xs font-medium text-gray-500">
            Cancel
          </button>
        </div>
      </li>
    )
  }

  return (
    <li className="p-3 text-sm">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-purple-700">{rating.score}</span>
        <div className="flex items-center gap-3">
          <span className="text-gray-500">{rating.date_entered.slice(0, 10)}</span>
          <button type="button" onClick={startEditing} className="text-xs font-medium text-purple-700">
            Edit
          </button>
          <button type="button" onClick={handleDelete} className="text-xs font-medium text-red-600">
            Delete
          </button>
        </div>
      </div>
      {rating.narrative_notes && <p className="mt-1">{rating.narrative_notes}</p>}
      {(rating.acidity_score || rating.body_score || rating.sweetness_score) && (
        <p className="mt-1 text-gray-500">
          {rating.acidity_score ? `Acidity ${rating.acidity_score} ` : ''}
          {rating.body_score ? `Body ${rating.body_score} ` : ''}
          {rating.sweetness_score ? `Sweetness ${rating.sweetness_score}` : ''}
        </p>
      )}
      {rating.brew_style && <p className="text-gray-500">{rating.brew_style}</p>}
      {rating.repurchase && <p className="text-gray-500">Repurchase: {rating.repurchase}</p>}
    </li>
  )
}
