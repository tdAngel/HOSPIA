import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Alerta, Campo, Tarjeta } from '../components.jsx'
import { api } from '../api.js'

export default function RestablecerContrasena() {
  const [params] = useSearchParams()
  const token = params.get('token') || ''
  const nav = useNavigate()
  const [f, setF] = useState({ nueva: '', confirmar: '' })
  const [errores, setErrores] = useState({})
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError('')
    if (f.nueva !== f.confirmar) return setErrores({ confirmar: 'Las contraseñas no coinciden.' })
    setErrores({}); setEnviando(true)
    try {
      const r = await api('/auth/restablecer-contrasena', { method: 'POST', body: { token, nueva_contrasena: f.nueva } })
      nav('/login', { state: { mensaje: r.mensaje } })
    } catch (err) {
      setErrores({ nueva: err.errores?.nueva_contrasena })
      if (!err.errores?.nueva_contrasena) setError(err.message)
    } finally { setEnviando(false) }
  }

  if (!token) return <Tarjeta titulo="Enlace inválido"><Alerta>Falta el token de restablecimiento.</Alerta>
    <p className="enlaces"><Link to="/olvide-contrasena">Solicitar un nuevo enlace</Link></p></Tarjeta>

  return (
    <Tarjeta titulo="Nueva contraseña" subtitulo="Elige una contraseña segura para tu cuenta.">
      <Alerta>{error}</Alerta>
      <form onSubmit={enviar} noValidate>
        <Campo etiqueta="Nueva contraseña" type="password" value={f.nueva} onChange={(e) => setF({ ...f, nueva: e.target.value })}
               error={errores.nueva} ayuda="Mínimo 8 caracteres, con mayúsculas, minúsculas y números." autoComplete="new-password" required />
        <Campo etiqueta="Confirmar contraseña" type="password" value={f.confirmar} onChange={(e) => setF({ ...f, confirmar: e.target.value })}
               error={errores.confirmar} autoComplete="new-password" required />
        <button disabled={enviando}>{enviando ? 'Guardando…' : 'Guardar contraseña'}</button>
      </form>
    </Tarjeta>
  )
}
