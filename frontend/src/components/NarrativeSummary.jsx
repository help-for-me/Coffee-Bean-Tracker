import { useEffect, useState } from 'react'
import { generateNarrative, getNarrative } from '../api'

export default function NarrativeSummary({ window: windowType }) {
  const [narrative, setNarrative] = useState(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const load = (silent = false) => {
      if (!silent) setLoading(true)
      setError(null)
      getNarrative(windowType)
        .then(setNarrative)
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false))
    }

    load()
    // A cached read, not a new AI generation - safe to quietly refresh
    // when the tab regains focus, so a summary generated elsewhere (or
    // just the "Generated ..." timestamp) doesn't go stale while this
    // page sits open in the background.
    const onVisible = () => {
      if (document.visibilityState === 'visible') load(true)
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [windowType])

  const handleGenerate = async () => {
    setGenerating(true)
    setError(null)
    try {
      setNarrative(await generateNarrative(windowType))
    } catch (err) {
      setError(err.message)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="mb-6 rounded-md border border-gray-200 p-3">
      {loading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : narrative ? (
        <>
          <p className="text-sm text-gray-900">{narrative.summary_text}</p>
          <p className="mt-2 text-xs text-gray-400">
            Generated {new Date(narrative.generated_at).toLocaleString()}
          </p>
        </>
      ) : (
        <p className="text-sm text-gray-500">No summary generated yet.</p>
      )}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <button
        type="button"
        onClick={handleGenerate}
        disabled={generating || loading}
        className="mt-2 rounded-md border border-purple-700 px-3 py-1 text-xs font-medium text-purple-700 disabled:opacity-50"
      >
        {generating ? 'Generating...' : narrative ? 'Regenerate summary' : 'Generate summary'}
      </button>
    </div>
  )
}
