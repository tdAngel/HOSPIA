import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { Alerta, Campo } from '../components.jsx'
import { fmtFecha } from '../utils.js'

export default function Perfil() {
  const { refrescar } = useAuth()
  const [perfil, setPerfil] = useState(null)
  const [f, setF] = useState(null)
  const [errores, setErrores] = useState({})
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')
  const [enviando, setEnviando] = useState(false)

  function cargar(p) { setPerfil(p); setF({ telefono: p.telefono, correo: p.correo, acepta_notificaciones_movil: p.acepta_notificaciones_movil, contrasena_actual: '' }) }
  useEffect(() => { api('/pacientes/me').then(cargar).catch((e) => setError(e.message)) }, [])

  if (!perfil) return <><Alerta>{error}</Alerta>{!error && <p className="sub">Cargando…</p>}</>
  const cambiaCorreo = f.correo.trim().toLowerCase() !== perfil.correo
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  async function guardar(e) {
    e.preventDefault()
    setError(''); setOk(''); setErrores({}); setEnviando(true)
    try {
      const body = { telefono: f.telefono, acepta_notificaciones_movil: f.acepta_notificaciones_movil }
      if (cambiaCorreo) { body.correo = f.correo; body.contrasena_actual = f.contrasena_actual }
      cargar(await api('/pacientes/me', { method: 'PATCH', body }))
      await refrescar()
      setOk('Tus datos fueron actualizados.')
    } catch (err) {
      setErrores(err.errores || {})
      setError(Object.keys(err.errores || {}).length ? 'Revisa los campos marcados.' : err.message)
    } finally { setEnviando(false) }
  }

  return (
    <>
      <h1>Mi perfil</h1>
      <section className="panel"><dl>
        <dt>Nombre</dt><dd>{perfil.nombre_completo}</dd>
        <dt>Fecha de nacimiento</dt><dd>{fmtFecha(perfil.fecha_nacimiento + 'T00:00')}</dd>
      </dl></section>

      <section className="panel">
        <h2>Datos de contacto</h2>
        <Alerta tipo="ok">{ok}</Alerta><Alerta>{error}</Alerta>
        <form onSubmit={guardar} noValidate>
          <Campo etiqueta="Correo electrónico" type="email" value={f.correo} onChange={set('correo')} error={errores.correo} />
          {cambiaCorreo && <Campo etiqueta="Contraseña actual (necesaria para cambiar el correo)" type="password"
            value={f.contrasena_actual} onChange={set('contrasena_actual')} autoComplete="current-password" />}
          <Campo etiqueta="Teléfono celular" type="tel" inputMode="numeric" value={f.telefono} onChange={set('telefono')}
                 error={errores.telefono} ayuda="10 dígitos" />
          <label className="check"><input type="checkbox" checked={f.acepta_notificaciones_movil} onChange={set('acepta_notificaciones_movil')} />
            <span>Autorizo recibir recordatorios por SMS o WhatsApp.</span></label>
          <button disabled={enviando}>{enviando ? 'Guardando…' : 'Guardar cambios'}</button>
        </form>
      </section>
    </>
  )
}
