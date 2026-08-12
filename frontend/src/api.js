const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
// Every backend route lives under /api (see backend/main.py) so it never
// collides with one of the frontend's own page paths - both this helper
// and photoUrl() below need the prefix, since photoUrl() builds a URL
// directly for an <img>/<a> tag instead of going through request().
const API_PREFIX = '/api'

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${API_PREFIX}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Request failed: ${response.status}`)
  }
  if (response.status === 204) return null
  return response.json()
}

export function autocompleteBeanProfiles(query) {
  const params = new URLSearchParams({ q: query })
  return request(`/bean-profiles/autocomplete?${params}`)
}

export function createEntry(data, photos = []) {
  const formData = new FormData()
  formData.append('data', JSON.stringify(data))
  photos.forEach((file) => formData.append('photos', file))
  // No Content-Type header here on purpose - the browser sets the correct
  // multipart boundary itself when the body is a FormData instance.
  return request('/entries', { method: 'POST', body: formData, headers: {} })
}

export function listEntries({ q, limit, entryType, sort } = {}) {
  const params = new URLSearchParams()
  if (q) params.set('q', q)
  if (limit) params.set('limit', limit)
  if (entryType) params.set('entry_type', entryType)
  if (sort) params.set('sort', sort)
  const qs = params.toString()
  return request(`/entries${qs ? `?${qs}` : ''}`)
}

export function getEntry(id) {
  return request(`/entries/${id}`)
}

export function addRating(entryId, data) {
  return request(`/entries/${entryId}/ratings`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function getInsights(brewStyle) {
  const params = new URLSearchParams()
  if (brewStyle) params.set('brew_style', brewStyle)
  const qs = params.toString()
  return request(`/insights${qs ? `?${qs}` : ''}`)
}

export function getNarrative(window_) {
  const params = new URLSearchParams({ window: window_ })
  return request(`/insights/narrative?${params}`)
}

export function generateNarrative(window_) {
  const params = new URLSearchParams({ window: window_ })
  return request(`/insights/narrative?${params}`, { method: 'POST' })
}

export function photoUrl(photoId) {
  return `${BASE_URL}${API_PREFIX}/photos/${photoId}`
}

export function reextractEntry(id) {
  return request(`/entries/${id}/reextract`, { method: 'POST' })
}

export function updateEntry(id, data) {
  return request(`/entries/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function deleteEntry(id) {
  return request(`/entries/${id}`, { method: 'DELETE' })
}

export function updateRating(entryId, ratingId, data) {
  return request(`/entries/${entryId}/ratings/${ratingId}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function deleteRating(entryId, ratingId) {
  return request(`/entries/${entryId}/ratings/${ratingId}`, { method: 'DELETE' })
}

async function downloadFile(path, options = {}) {
  const response = await fetch(`${BASE_URL}${API_PREFIX}${path}`, options)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Request failed: ${response.status}`)
  }
  const blob = await response.blob()
  const match = (response.headers.get('Content-Disposition') ?? '').match(/filename="?([^"]+)"?/)
  const filename = match ? match[1] : 'export'
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function downloadCsv() {
  return downloadFile('/exports/csv')
}

export function downloadXlsx() {
  return downloadFile('/exports/xlsx', { method: 'POST' })
}

export function getExportStatus() {
  return request('/exports/status')
}

export function backupToGithub() {
  return request('/exports/github', { method: 'POST' })
}
