const BREW_STYLES = ['Pour Over', 'Espresso', 'French Press', 'Cafe-made', 'Other']
const REPURCHASE_OPTIONS = ['yes', 'no', 'maybe']

export default function AdvancedRatingFields({ value, onChange }) {
  const set = (key) => (e) => onChange({ ...value, [key]: e.target.value })

  return (
    <div className="mb-4 grid grid-cols-2 gap-3 rounded-md border border-gray-200 p-3">
      <div>
        <label className="block text-xs text-gray-600">Acidity</label>
        <input
          type="number"
          min="0"
          max="10"
          step="0.5"
          value={value.acidityScore}
          onChange={set('acidityScore')}
          className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-600">Body</label>
        <input
          type="number"
          min="0"
          max="10"
          step="0.5"
          value={value.bodyScore}
          onChange={set('bodyScore')}
          className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
        />
      </div>
      <div>
        <label className="block text-xs text-gray-600">Sweetness</label>
        <input
          type="number"
          min="0"
          max="10"
          step="0.5"
          value={value.sweetnessScore}
          onChange={set('sweetnessScore')}
          className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1 text-sm"
        />
      </div>
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
