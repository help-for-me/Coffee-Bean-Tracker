import { useEffect, useState } from 'react'
import Field from '../components/Field'
import { getSettings, updateSettings } from '../api'

export default function Settings() {
  const [settings, setSettings] = useState(null)
  const [form, setForm] = useState(null)
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getSettings()
      .then((data) => {
        setSettings(data)
        setForm(data)
      })
      .catch((e) => setError(e.message))
  }, [])

  const handleSave = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      const updated = await updateSettings({
        recent_window_months: Number(form.recent_window_months),
        recent_window_count: Number(form.recent_window_count),
        extraction_custom_instructions: form.extraction_custom_instructions,
        narrative_custom_instructions: form.narrative_custom_instructions,
      })
      setSettings(updated)
      setForm(updated)
      setSaved(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (error && !settings) return <div className="p-6 text-sm text-red-600">{error}</div>
  if (!form) return <div className="p-6 text-sm text-gray-500">Loading...</div>

  return (
    <div className="mx-auto max-w-md p-6 pb-24">
      <h1 className="mb-4 text-lg font-semibold text-gray-900">Settings</h1>

      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <h2 className="mb-1 text-sm font-semibold text-gray-900">Insights "Recent" window</h2>
          <p className="mb-2 text-xs text-gray-500">
            Insights shows a "Recent" toggle once you have enough history for it to mean something -
            both of these must be met before it appears.
          </p>
          <div className="flex gap-2">
            <Field
              label="Months back"
              type="number"
              value={form.recent_window_months}
              onChange={(e) => setForm({ ...form, recent_window_months: e.target.value })}
            />
            <Field
              label="Minimum ratings"
              type="number"
              value={form.recent_window_count}
              onChange={(e) => setForm({ ...form, recent_window_count: e.target.value })}
            />
          </div>
        </div>

        <div>
          <h2 className="mb-1 text-sm font-semibold text-gray-900">Extraction instructions</h2>
          <p className="mb-2 text-xs text-gray-500">
            Plain-English additions to how photos are read (e.g. "always exclude bilingual packaging
            text"). Added alongside the built-in extraction rules, not a replacement for them.
          </p>
          <textarea
            value={form.extraction_custom_instructions}
            onChange={(e) => setForm({ ...form, extraction_custom_instructions: e.target.value })}
            rows={3}
            maxLength={2000}
            className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
          />
        </div>

        <div>
          <h2 className="mb-1 text-sm font-semibold text-gray-900">Insights summary instructions</h2>
          <p className="mb-2 text-xs text-gray-500">
            Plain-English additions to how the AI-generated Insights summary is written (e.g. "keep it
            to one sentence").
          </p>
          <textarea
            value={form.narrative_custom_instructions}
            onChange={(e) => setForm({ ...form, narrative_custom_instructions: e.target.value })}
            rows={3}
            maxLength={2000}
            className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {saved && !error && <p className="text-sm text-green-700">Saved.</p>}

        <button
          type="submit"
          disabled={saving}
          className="rounded-md border border-purple-700 bg-purple-700 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save settings'}
        </button>
      </form>
    </div>
  )
}
