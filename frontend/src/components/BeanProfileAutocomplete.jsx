import { useEffect, useRef, useState } from 'react'
import { autocompleteBeanProfiles } from '../api'

export default function BeanProfileAutocomplete({ roaster, beanName, onRoaster, onBeanName, onSelect }) {
  const [suggestions, setSuggestions] = useState([])
  const [open, setOpen] = useState(false)
  const debounceRef = useRef(null)

  const query = `${roaster} ${beanName}`.trim()

  useEffect(() => {
    if (!query) {
      setSuggestions([])
      return undefined
    }
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      autocompleteBeanProfiles(query)
        .then(setSuggestions)
        .catch(() => setSuggestions([]))
    }, 200)
    return () => clearTimeout(debounceRef.current)
  }, [query])

  return (
    <div className="grid grid-cols-2 gap-2">
      <div>
        <label className="block text-sm font-medium text-gray-700">Roaster</label>
        <input
          value={roaster}
          onChange={(e) => {
            onRoaster(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
          placeholder="e.g. Stumptown"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700">Bean name</label>
        <input
          value={beanName}
          onChange={(e) => {
            onBeanName(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
          placeholder="e.g. Hair Bender"
        />
      </div>
      {open && suggestions.length > 0 && (
        <ul className="col-span-2 -mt-1 rounded-md border border-gray-200 bg-white shadow-sm">
          {suggestions.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                onClick={() => {
                  onSelect(s)
                  setOpen(false)
                }}
                className="block w-full px-3 py-2 text-left text-sm hover:bg-gray-50"
              >
                {s.roaster} — {s.bean_name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
