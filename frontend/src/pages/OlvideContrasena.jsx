import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alerta, Campo, Tarjeta } from '../components.jsx'
import { api } from '../api.js'

export default function OlvideContrasena() {
  const [correo, setCorreo] = useState('')
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError(''); setMsg(''); setEnviando(true)
    try { setMsg((await api('/auth/olvide-contrasena', { method: 'POST', body: { correo } })).mensaje) }
    catch (err) { setError(err.message) }
    finally { setEnviando(false) }
  }

  return (
    <Tarjeta titulo="Restablecer contraseña" subtitulo="Te enviaremos un enlace al correo con el que te registraste.">
      <Alerta tipo="ok">{msg}</Alerta>
      <Alerta>{error}</Alerta>
      <form onSubmit={enviar} noValidate>
        <Campo etiqueta="Correo electrónico" type="email" value={correo} onChange={(e) => setCorreo(e.target.value)} required />
        <button disabled={enviando}>{enviando ? 'Enviando…' : 'Enviar enlace'}</button>
      </form>
      <p className="enlaces"><Link to="/login">Volver a iniciar sesión</Link></p>
    </Tarjeta>
  )
}
