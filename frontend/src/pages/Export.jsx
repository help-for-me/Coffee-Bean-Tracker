import { useEffect, useRef, useState } from 'react'
import {
  backupToGithub,
  downloadCsv,
  downloadDataExport,
  downloadXlsx,
  getExportStatus,
  importDataExport,
} from '../api'

function lastRunLine(last) {
  if (!last) return 'Never run.'
  const when = new Date(last.exported_at).toLocaleString()
  return last.status === 'success' ? `Last succeeded ${when}` : `Last failed ${when}`
}

export default function Export() {
  const fileInputRef = useRef(null)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(null)
  const [jsonBusy, setJsonBusy] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => {
    getExportStatus()
      .then(setStatus)
      .catch((e) => setError(e.message))
  }, [])

  const run = async (key, action) => {
    setBusy(key)
    setError(null)
    try {
      await action()
      setStatus(await getExportStatus())
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(null)
    }
  }

  const handleDownload = async () => {
    setJsonBusy(true)
    setError(null)
    try {
      await downloadDataExport()
    } catch (err) {
      setError(err.message)
    } finally {
      setJsonBusy(false)
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

    setJsonBusy(true)
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
      setJsonBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-md p-6 pb-24">
      <h1 className="mb-4 text-lg font-semibold text-gray-900">Export</h1>

      <div className="mb-4 rounded-md border border-gray-200 p-3">
        <h2 className="text-sm font-semibold text-gray-900">CSV</h2>
        <p className="mt-1 text-xs text-gray-500">
          A plain spreadsheet report, one row per rating. Always available, nothing saved on the
          server.
        </p>
        <button
          type="button"
          onClick={() => run('csv', downloadCsv)}
          disabled={busy === 'csv'}
          className="mt-2 rounded-md border border-purple-700 px-3 py-1 text-xs font-medium text-purple-700 disabled:opacity-50"
        >
          {busy === 'csv' ? 'Downloading...' : 'Download CSV'}
        </button>
      </div>

      <div className="mb-4 rounded-md border border-gray-200 p-3">
        <h2 className="text-sm font-semibold text-gray-900">XLSX</h2>
        <p className="mt-1 text-xs text-gray-500">
          Formatted report with Raw Data and Summary sheets.
          {status?.local_xlsx.enabled
            ? ' Also saves a copy on the server.'
            : ' Local server copy is off (LOCAL_XLSX_ENABLED).'}
        </p>
        {status?.local_xlsx.enabled && (
          <p className="mt-1 text-xs text-gray-400">{lastRunLine(status.local_xlsx.last)}</p>
        )}
        <button
          type="button"
          onClick={() => run('xlsx', downloadXlsx)}
          disabled={busy === 'xlsx'}
          className="mt-2 rounded-md border border-purple-700 px-3 py-1 text-xs font-medium text-purple-700 disabled:opacity-50"
        >
          {busy === 'xlsx' ? 'Downloading...' : 'Download XLSX'}
        </button>
      </div>

      <div className="mb-4 rounded-md border border-gray-200 p-3">
        <h2 className="text-sm font-semibold text-gray-900">GitHub backup</h2>
        {status?.github.enabled ? (
          <>
            <p className="mt-1 text-xs text-gray-500">Pushes the XLSX report to a separate private repo.</p>
            <p className="mt-1 text-xs text-gray-400">{lastRunLine(status.github.last)}</p>
            <button
              type="button"
              onClick={() => run('github', backupToGithub)}
              disabled={busy === 'github'}
              className="mt-2 rounded-md border border-purple-700 px-3 py-1 text-xs font-medium text-purple-700 disabled:opacity-50"
            >
              {busy === 'github' ? 'Backing up...' : 'Back up to GitHub'}
            </button>
          </>
        ) : (
          <p className="mt-1 text-xs text-gray-500">
            Not configured - set GITHUB_BACKUP_ENABLED, GITHUB_TOKEN, and GITHUB_REPO to turn this on.
          </p>
        )}
      </div>

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
          disabled={jsonBusy}
          className="mt-2 rounded-md border border-purple-700 px-3 py-1 text-xs font-medium text-purple-700 disabled:opacity-50"
        >
          {jsonBusy ? 'Working...' : 'Download backup'}
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
          disabled={jsonBusy}
          className="mt-2 rounded-md border border-red-600 px-3 py-1 text-xs font-medium text-red-600 disabled:opacity-50"
        >
          {jsonBusy ? 'Working...' : 'Choose backup file...'}
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
