import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Alerta, Campo, Tarjeta } from '../components.jsx'
import { useAuth } from '../auth.jsx'

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const { state } = useLocation()
  const [f, setF] = useState({ correo: '', contrasena: '' })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError(''); setEnviando(true)
    try { await login(f.correo, f.contrasena); nav('/') }
    catch (err) { setError(err.message) }
    finally { setEnviando(false) }
  }

  return (
    <Tarjeta titulo="Iniciar sesión" subtitulo="Accede a tu cuenta para gestionar tus citas.">
      <Alerta tipo="ok">{state?.mensaje}</Alerta>
      <Alerta>{error}</Alerta>
      <form onSubmit={enviar} noValidate>
        <Campo etiqueta="Correo electrónico" type="email" autoComplete="username" value={f.correo}
               onChange={(e) => setF({ ...f, correo: e.target.value })} required />
        <Campo etiqueta="Contraseña" type="password" autoComplete="current-password" value={f.contrasena}
               onChange={(e) => setF({ ...f, contrasena: e.target.value })} required />
        <button disabled={enviando}>{enviando ? 'Ingresando…' : 'Ingresar'}</button>
      </form>
      <p className="enlaces"><Link to="/olvide-contrasena">¿Olvidaste tu contraseña?</Link></p>
      <p className="enlaces">¿Aún no tienes cuenta? <Link to="/registro">Regístrate</Link></p>
    </Tarjeta>
  )
}
