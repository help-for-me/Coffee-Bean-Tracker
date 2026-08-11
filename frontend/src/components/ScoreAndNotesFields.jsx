// The score + notes inputs are identical on the New Entry and Rate a
// Previous Bean forms - this is the one shared copy both pages render.
// scoreOptional: New Entry allows saving a bag with no score yet ("log it
// now, rate later" - e.g. before it's been brewed); Rate a Previous Bean
// always requires one, since adding a rating is the entire point of it.
export default function ScoreAndNotesFields({ score, onScore, narrativeNotes, onNarrativeNotes, scoreOptional = false }) {
  return (
    <>
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700">
          Score (0-10){scoreOptional ? ' - optional, rate later if you prefer' : ''}
        </label>
        <input
          type="number"
          min="0"
          max="10"
          step="0.5"
          value={score}
          onChange={onScore}
          required={!scoreOptional}
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
