// Base URL of the CollapseCast API. Set VITE_API_BASE_URL at build time (see .env.example).
export const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')

async function request(path, options) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, options)
  } catch {
    throw new Error(`Cannot reach the API at ${API_BASE}. Is the backend running?`)
  }
  if (!response.ok) {
    let detail = ''
    try {
      const body = await response.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new Error(`API error ${response.status}${detail ? `: ${detail}` : ''}`)
  }
  return response.json()
}

export const fetchSamples = () => request('/samples')

export const predict = (payload, signal) =>
  request('/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  })
