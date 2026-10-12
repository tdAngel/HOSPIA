import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { fmtFecha, fmtHora } from '../utils.js'

const ROLES = { paciente: 'Paciente', recepcion: 'Recepción', medico: 'Médico', administrador: 'Administrador' }

export default function Inicio() {
  const { usuario } = useAuth()
  const [proxima, setProxima] = useState(undefined)

  useEffect(() => {
    if (usuario.rol !== 'paciente') return
    api('/citas/mis-citas?estado=programada').then((cs) => {
      const futuras = cs.filter((c) => c.inicio >= new Date().toISOString().slice(0, 16)).sort((a, b) => a.inicio.localeCompare(b.inicio))
      setProxima(futuras[0] || null)
    }).catch(() => setProxima(null))
  }, [usuario.rol])

  return (
    <>
      <h1>Hola, {usuario.nombre_completo.split(' ')[0]}</h1>
      <p className="sub">{ROLES[usuario.rol]} · {usuario.correo}</p>

      {usuario.rol === 'paciente' && (
        <>
          <section className="panel">
            <h2>Tu próxima cita</h2>
            {proxima === undefined ? <p className="sub">Cargando…</p> : proxima ? (
              <p>
                <b>{fmtFecha(proxima.inicio)}</b> a las <b>{fmtHora(proxima.inicio)}</b><br />
                {proxima.medico.nombre_completo} · {proxima.especialidad.nombre}<br />
                <Link to={`/citas/${proxima.id}`}>Ver detalle ({proxima.folio})</Link>
              </p>
            ) : <p className="sub">No tienes citas programadas.</p>}
          </section>
          <div className="accesos">
            <Link to="/agendar" className="acceso"><b>Agendar una cita</b><span>Busca horarios disponibles</span></Link>
            <Link to="/mis-citas" className="acceso"><b>Mis citas</b><span>Consulta tu historial</span></Link>
            <Link to="/perfil" className="acceso"><b>Mi perfil</b><span>Actualiza tus datos de contacto</span></Link>
          </div>
        </>
      )}
      {usuario.rol === 'recepcion' && (
        <div className="accesos"><Link to="/agendar" className="acceso"><b>Consultar disponibilidad</b><span>Horarios por especialidad, médico y fecha</span></Link></div>
      )}
      {!['paciente', 'recepcion'].includes(usuario.rol) && <p className="sub">Tus herramientas se habilitarán en las siguientes fases del proyecto.</p>}
    </>
  )
}
