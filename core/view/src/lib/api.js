const DEFAULT_API_BASE = 'http://127.0.0.1:8000'

export const API_BASE = import.meta.env.VITE_DB_API_BASE || DEFAULT_API_BASE

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
  })

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    const message = typeof payload === 'string' ? payload : payload?.detail || payload?.message || '请求失败'
    throw new Error(message)
  }

  return payload
}

export function getTeams() {
  return request('/teams')
}

export function getTeam(teamName) {
  return request(`/teams/${encodeURIComponent(teamName)}`)
}

export function getPetBaseAttrs(petName) {
  return request(`/pets/${encodeURIComponent(petName)}/base-attrs`)
}

export function importTeam(text) {
  return request('/teams/import', {
    method: 'POST',
    body: JSON.stringify({ text })
  })
}

export function setTeamMemberAttributes(teamName, petName, stats) {
  return request(`/teams/${encodeURIComponent(teamName)}/pets/${encodeURIComponent(petName)}/attributes`, {
    method: 'POST',
    body: JSON.stringify(stats)
  })
}
