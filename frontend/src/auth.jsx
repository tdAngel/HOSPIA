import { createContext, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from './api.js'

const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(!!getToken())

  useEffect(() => {
    if (!getToken()) return
    api('/auth/me').then(setUsuario).catch(() => setToken(null)).finally(() => setCargando(false))
  }, [])

  async function login(correo, contrasena) {
    const data = await api('/auth/login', { method: 'POST', body: { correo, contrasena } })
    setToken(data.access_token)
    setUsuario(data.usuario)
  }
  const logout = () => { setToken(null); setUsuario(null) }
  const refrescar = () => api('/auth/me').then(setUsuario)

  return <Ctx.Provider value={{ usuario, cargando, login, logout, refrescar }}>{children}</Ctx.Provider>
}
