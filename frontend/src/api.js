const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Request failed: ${response.status}`)
  }
  return response.json()
}

export function autocompleteBeanProfiles(query) {
  const params = new URLSearchParams({ q: query })
  return request(`/bean-profiles/autocomplete?${params}`)
}

export function createEntry(data) {
  return request('/entries', { method: 'POST', body: JSON.stringify(data) })
}

export function listEntries({ q, limit } = {}) {
  const params = new URLSearchParams()
  if (q) params.set('q', q)
  if (limit) params.set('limit', limit)
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
