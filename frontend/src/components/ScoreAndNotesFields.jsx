// The score + notes inputs are identical on the New Entry and Rate a
// Previous Bean forms - this is the one shared copy both pages render.
export default function ScoreAndNotesFields({ score, onScore, narrativeNotes, onNarrativeNotes }) {
  return (
    <>
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700">Score (0-10)</label>
        <input
          type="number"
          min="0"
          max="10"
          step="0.5"
          value={score}
          onChange={onScore}
          required
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700">Notes (optional)</label>
        <input
          value={narrativeNotes}
          onChange={onNarrativeNotes}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
          placeholder="Chocolatey, bright finish..."
        />
      </div>
    </>
  )
}
