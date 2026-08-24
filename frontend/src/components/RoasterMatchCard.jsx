import { useRef, useState } from 'react'
import { confirmEnrichmentCandidate, reprocessEnrichment, submitManualEnrichmentUrl, uploadEnrichmentSource } from '../api'

const STATUS_LABEL = {
  pending: 'Looking it up...',
  needs_review: "Not sure which page matches - pick one below, or none",
  confirmed: 'Matched',
  no_match: 'No match found',
  failed: 'Lookup failed',
}

// Entry Detail's counterpart to the "Re-run AI extraction" block - this one
// covers 1.9.0's roaster-website lookup instead of the photo-label one.
// beanProfile.enrichment is null until a lookup has ever been attempted
// (see crud.maybe_start_enrichment), in which case this renders nothing.
export default function RoasterMatchCard({ beanProfile, onChanged }) {
  const [contextText, setContextText] = useState('')
  const [showContext, setShowContext] = useState(false)
  const [manualUrl, setManualUrl] = useState('')
  const [showFoundIt, setShowFoundIt] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const enrichment = beanProfile.enrichment
  if (!enrichment) return null

  const handleConfirm = async (candidate) => {
    setBusy(true)
    setError(null)
    try {
      await confirmEnrichmentCandidate(beanProfile.id, candidate.url, candidate.title)
      await onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const handleReprocess = async () => {
    setBusy(true)
    setError(null)
    try {
      await reprocessEnrichment(beanProfile.id, contextText.trim())
      setShowContext(false)
      setContextText('')
      await onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const handleSubmitManualUrl = async () => {
    setBusy(true)
    setError(null)
    try {
      await submitManualEnrichmentUrl(beanProfile.id, manualUrl.trim())
      setShowFoundIt(false)
      setManualUrl('')
      await onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const handleFileChosen = async (e) => {
    const file = e.target.files[0]
    e.target.value = '' // lets the same file be picked again later
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      await uploadEnrichmentSource(beanProfile.id, file)
      setShowFoundIt(false)
      await onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const reprocessLabel = enrichment.status === 'needs_review' ? 'None of these' : 'Reprocess'

  return (
    <div className="mb-4 rounded-md border border-gray-200 p-3 text-sm">
      <p>
        <span className="text-gray-500">Roaster website match: </span>
        <span className="font-medium">{STATUS_LABEL[enrichment.status] ?? enrichment.status}</span>
      </p>

      {enrichment.status === 'confirmed' && enrichment.source_url && (
        <p className="mt-1 truncate">
          <a href={enrichment.source_url} target="_blank" rel="noreferrer" className="text-purple-700">
            {enrichment.source_url}
          </a>
        </p>
      )}

      {enrichment.status === 'needs_review' && (
        <ul className="mt-2 space-y-2">
          {enrichment.candidates.map((candidate) => (
            <li key={candidate.url} className="rounded border border-gray-200 p-2">
              <p className="font-medium">{candidate.title}</p>
              <p className="truncate text-xs text-gray-500">{candidate.url}</p>
              {candidate.snippet && <p className="mt-1 text-xs text-gray-500">{candidate.snippet}</p>}
              <button
                type="button"
                onClick={() => handleConfirm(candidate)}
                disabled={busy}
                className="mt-2 rounded-md border border-purple-700 px-2 py-1 text-xs font-medium text-purple-700 disabled:opacity-50"
              >
                This is it
              </button>
            </li>
          ))}
        </ul>
      )}

      {enrichment.status === 'pending' && (
        <p className="mt-1 text-xs text-gray-500">
          This runs in the background - refresh in a few seconds to see the result.
        </p>
      )}

      {enrichment.status !== 'pending' && (
        <div className="mt-2 flex flex-wrap gap-4">
          {!showContext ? (
            <button type="button" onClick={() => setShowContext(true)} className="text-xs font-medium text-purple-700">
              {reprocessLabel}
            </button>
          ) : (
            <div className="w-full">
              <label className="mb-1 block text-xs text-gray-600">
                Anything that would help find the right page? (optional)
              </label>
              <input
                value={contextText}
                onChange={(e) => setContextText(e.target.value)}
                placeholder="e.g. it's their subscription-only &quot;Floodwater&quot; label"
                className="mb-2 w-full rounded-md border border-gray-300 px-2 py-1 text-xs"
              />
              <div className="flex gap-3">
                <button type="button" onClick={() => setShowContext(false)} className="text-xs font-medium text-gray-500">
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleReprocess}
                  disabled={busy}
                  className="text-xs font-medium text-purple-700 disabled:opacity-50"
                >
                  {busy ? 'Searching...' : 'Search again'}
                </button>
              </div>
            </div>
          )}

          {!showFoundIt ? (
            <button type="button" onClick={() => setShowFoundIt(true)} className="text-xs font-medium text-purple-700">
              I found it myself
            </button>
          ) : (
            <div className="w-full">
              <label className="mb-1 block text-xs text-gray-600">Paste the product page URL</label>
              <input
                value={manualUrl}
                onChange={(e) => setManualUrl(e.target.value)}
                placeholder="https://roaster.example/products/this-bean"
                className="mb-2 w-full rounded-md border border-gray-300 px-2 py-1 text-xs"
              />
              <div className="mb-2 flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowFoundIt(false)}
                  className="text-xs font-medium text-gray-500"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSubmitManualUrl}
                  disabled={busy || !manualUrl.trim()}
                  className="text-xs font-medium text-purple-700 disabled:opacity-50"
                >
                  {busy ? 'Fetching...' : 'Use this page'}
                </button>
              </div>
              <p className="mb-1 text-xs text-gray-500">Or upload a screenshot or PDF with the roaster's info:</p>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={busy}
                className="rounded-md border border-purple-700 px-2 py-1 text-xs font-medium text-purple-700 disabled:opacity-50"
              >
                {busy ? 'Uploading...' : 'Choose file...'}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,application/pdf"
                onChange={handleFileChosen}
                className="hidden"
              />
            </div>
          )}
        </div>
      )}

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  )
}
