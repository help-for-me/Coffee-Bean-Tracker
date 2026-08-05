import { useRef, useState } from 'react'
import { downloadDataExport, importDataExport } from '../api'

export default function Export() {
  const fileInputRef = useRef(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  const handleDownload = async () => {
    setBusy(true)
    setError(null)
    try {
      await downloadDataExport()
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

    const proceed = window.confirm(
      'Restoring from a backup file replaces every entry, rating, and photo record currently in the app. This cannot be undone. Continue?'
    )
    if (!proceed) return

    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const text = await file.text()
      const data = JSON.parse(text)
      const counts = await importDataExport(data)
      setResult(counts)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md p-6 pb-24">
      <h1 className="mb-4 text-lg font-semibold text-gray-900">Export</h1>
      <p className="mb-4 text-sm text-gray-500">
        CSV, XLSX, and GitHub backup export arrive in milestone 1.1.0 - not built yet.
      </p>

      <div className="mb-4 rounded-md border border-gray-200 p-3">
        <h2 className="text-sm font-semibold text-gray-900">Full data backup (JSON)</h2>
        <p className="mt-1 text-xs text-gray-500">
          Downloads everything in the app - every bean profile, entry, rating, and photo record -
          exactly as stored. For restoring or moving to a new install, not for opening in a
          spreadsheet (see CSV/XLSX above for that).
        </p>
        <button
          type="button"
          onClick={handleDownload}
          disabled={busy}
          className="mt-2 rounded-md border border-purple-700 px-3 py-1 text-xs font-medium text-purple-700 disabled:opacity-50"
        >
          {busy ? 'Working...' : 'Download backup'}
        </button>
      </div>

      <div className="mb-4 rounded-md border border-gray-200 p-3">
        <h2 className="text-sm font-semibold text-gray-900">Restore from backup</h2>
        <p className="mt-1 text-xs text-gray-500">
          Replaces everything currently in the app with the contents of the chosen backup file.
          Photo files themselves aren't included in the backup - only the records pointing at
          them, so the photos/ folder needs to be carried over separately if you're moving to a
          new install.
        </p>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={busy}
          className="mt-2 rounded-md border border-red-600 px-3 py-1 text-xs font-medium text-red-600 disabled:opacity-50"
        >
          {busy ? 'Working...' : 'Choose backup file...'}
        </button>
        <input ref={fileInputRef} type="file" accept="application/json" onChange={handleFileChosen} className="hidden" />
        {result && (
          <p className="mt-2 text-xs text-green-700">
            Restored: {result.entries} entries, {result.ratings} ratings, {result.photos} photo records.
          </p>
        )}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  )
}
