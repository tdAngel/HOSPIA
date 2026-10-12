const TOKEN_KEY = 'hospia_token'
export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY))

export async function api(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  if (getToken()) headers.Authorization = `Bearer ${getToken()}`
  let res
  try {
    res = await fetch(`/api${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined })
  } catch {
    throw Object.assign(new Error('No hay conexión con el servidor.'), { errores: {} })
  }
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const msg = typeof data?.detail === 'string' ? data.detail : 'Ocurrió un error inesperado.'
    throw Object.assign(new Error(msg), { status: res.status, errores: data?.errores || {} })
  }
  return data
}
