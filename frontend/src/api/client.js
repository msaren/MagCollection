const TOKEN_KEY = 'magcollector_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

// Shared JSON request helper. Binary responses (file/thumbnail/page downloads) go
// through fetchBlob below instead, since they don't fit the parse-as-JSON assumption here.
async function request(path, { method = 'GET', body, headers = {} } = {}) {
  const token = getToken()
  const res = await fetch(`/api${path}`, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  })

  if (res.status === 204) return null

  const isJson = res.headers.get('content-type')?.includes('application/json')
  const data = isJson ? await res.json() : null

  if (!res.ok) {
    // FastAPI's HTTPException bodies are {"detail": "..."}; fall back to a generic
    // message for errors that never reach our handlers (e.g. a proxy 502).
    throw new ApiError(data?.detail || `Request failed (${res.status})`, res.status)
  }
  return data
}

export const api = {
  login: (username, password) => request('/auth/login', { method: 'POST', body: { username, password } }),
  me: () => request('/me'),
  updateTheme: (theme) => request('/me/theme', { method: 'PUT', body: { theme } }),

  collections: () => request('/collections'),
  collectionBrowse: (name, path = '') =>
    request(
      `/collections/${encodeURIComponent(name)}/browse${path ? `?path=${encodeURIComponent(path)}` : ''}`
    ),

  comicPages: (magazineId) => request(`/magazines/${magazineId}/pages`),

  // Used for magazine files, thumbnails, and comic pages: these need the auth header
  // (so they can't just be plain <img src="/api/...">) but return binary bodies, not JSON.
  async fetchBlob(path) {
    const token = getToken()
    const res = await fetch(`/api${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new ApiError(`Request failed (${res.status})`, res.status)
    return res.blob()
  },

  adminListUsers: () => request('/admin/users'),
  adminCreateUser: (user) => request('/admin/users', { method: 'POST', body: user }),
  adminUpdateUser: (id, fields) => request(`/admin/users/${id}`, { method: 'PUT', body: fields }),
  adminDeleteUser: (id) => request(`/admin/users/${id}`, { method: 'DELETE' }),

  adminScan: () => request('/admin/scan', { method: 'POST' }),
  adminRescanCovers: () => request('/admin/rescan-covers', { method: 'POST' }),
  adminListCollections: () => request('/admin/collections'),
  adminUpdateCollection: (name, fields) =>
    request(`/admin/collections/${encodeURIComponent(name)}`, { method: 'PUT', body: fields }),

  adminListMagazines: () => request('/admin/magazines'),
  adminUpdateMagazine: (id, fields) => request(`/admin/magazines/${id}`, { method: 'PUT', body: fields }),
}

export { ApiError }
