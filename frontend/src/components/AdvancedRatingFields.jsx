const BREW_STYLES = ['Pour Over', 'Espresso', 'French Press', 'Cafe-made', 'Other']
const REPURCHASE_OPTIONS = ['yes', 'no', 'maybe']
// The three 0-10 sliders below (Acidity, Body, Sweetness) are identical
// except for label and which field they edit, so they're generated from
// this list instead of repeating the same input three times.
const SCORE_FIELDS = [
  { key: 'acidityScore', label: 'Acidity' },
  { key: 'bodyScore', label: 'Body' },
  { key: 'sweetnessScore', label: 'Sweetness' },
]

export default function AdvancedRatingFields({ value, onChange }) {
  const set = (key) => (e) => onChange({ ...value, [key]: e.target.value })

  return (
    <div className="mb-4 grid grid-cols-2 gap-3 rounded-md border border-gray-200 p-3">
      {SCORE_FIELDS.map(({ key, label }) => (
        <div key={key}>
          <label className="block text-xs text-gray-600">{label}</label>
          <input
            type="number"
            min="0"
            max="10"
            step="0.5"
            value={value[key]}
            onChange={set(key)}
            className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
          />
        </div>
      ))}
      <div>
        <label className="block text-xs text-gray-600">Brew style</label>
        <select
          value={value.brewStyle}
          onChange={set('brewStyle')}
          className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
        >
          <option value="">-</option>
          {BREW_STYLES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>
      <div className="col-span-2">
        <label className="block text-xs text-gray-600">Repurchase?</label>
        <div className="mt-1 flex gap-2">
          {REPURCHASE_OPTIONS.map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => onChange({ ...value, repurchase: v })}
              className={`rounded-md border px-3 py-1 text-sm ${
                value.repurchase === v
                  ? 'border-purple-700 bg-purple-700 text-white'
                  : 'border-gray-300 text-gray-700'
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
