import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Alerta, Campo, Tarjeta } from '../components.jsx'
import { api } from '../api.js'

const inicial = { nombre_completo: '', fecha_nacimiento: '', correo: '', telefono: '', contrasena: '',
                  confirmar: '', acepta_aviso_privacidad: false, acepta_notificaciones_movil: false }

export default function Registro() {
  const nav = useNavigate()
  const [f, setF] = useState(inicial)
  const [errores, setErrores] = useState({})
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  async function enviar(e) {
    e.preventDefault()
    setError('')
    if (f.contrasena !== f.confirmar) return setErrores({ confirmar: 'Las contraseñas no coinciden.' })
    setErrores({}); setEnviando(true)
    try {
      const { confirmar, ...body } = f
      await api('/auth/registro', { method: 'POST', body })
      nav('/login', { state: { mensaje: '¡Cuenta creada! Ahora puedes iniciar sesión.' } })
    } catch (err) {
      setErrores(err.errores || {})
      setError(err.status === 409 ? err.message : Object.keys(err.errores || {}).length ? 'Revisa los campos marcados.' : err.message)
    } finally { setEnviando(false) }
  }

  return (
    <Tarjeta titulo="Crear cuenta de paciente" subtitulo="Agenda y consulta tus citas médicas en línea.">
      <Alerta>{error}</Alerta>
      <form onSubmit={enviar} noValidate>
        <Campo etiqueta="Nombre completo" value={f.nombre_completo} onChange={set('nombre_completo')}
               error={errores.nombre_completo} autoComplete="name" required />
        <Campo etiqueta="Fecha de nacimiento" type="date" value={f.fecha_nacimiento} onChange={set('fecha_nacimiento')}
               max={new Date().toISOString().slice(0, 10)} error={errores.fecha_nacimiento} required />
        <Campo etiqueta="Correo electrónico" type="email" value={f.correo} onChange={set('correo')}
               error={errores.correo} autoComplete="email" required />
        <Campo etiqueta="Teléfono celular" type="tel" inputMode="numeric" value={f.telefono} onChange={set('telefono')}
               error={errores.telefono} ayuda="10 dígitos" autoComplete="tel" required />
        <Campo etiqueta="Contraseña" type="password" value={f.contrasena} onChange={set('contrasena')}
               error={errores.contrasena} ayuda="Mínimo 8 caracteres, con mayúsculas, minúsculas y números."
               autoComplete="new-password" required />
        <Campo etiqueta="Confirmar contraseña" type="password" value={f.confirmar} onChange={set('confirmar')}
               error={errores.confirmar} autoComplete="new-password" required />

        <label className="check">
          <input type="checkbox" checked={f.acepta_aviso_privacidad} onChange={set('acepta_aviso_privacidad')} />
          <span>He leído y acepto el <a href="#aviso" onClick={(e) => { e.preventDefault(); alert('Aviso de privacidad: tus datos personales y de salud se usarán únicamente para la gestión de tus citas médicas.') }}>aviso de privacidad</a>. *</span>
        </label>
        {errores.acepta_aviso_privacidad && <small className="error">{errores.acepta_aviso_privacidad}</small>}
        <label className="check">
          <input type="checkbox" checked={f.acepta_notificaciones_movil} onChange={set('acepta_notificaciones_movil')} />
          <span>Autorizo recibir recordatorios por SMS o WhatsApp (opcional).</span>
        </label>

        <button disabled={enviando}>{enviando ? 'Creando cuenta…' : 'Crear cuenta'}</button>
      </form>
      <p className="enlaces">¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link></p>
    </Tarjeta>
  )
}
