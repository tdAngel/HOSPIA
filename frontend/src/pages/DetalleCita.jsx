import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { Alerta } from '../components.jsx'
import { ESTADOS, fmtFecha, fmtHora } from '../utils.js'

export default function DetalleCita() {
  const { id } = useParams()
  const { state } = useLocation()
  const { usuario } = useAuth()
  const [cita, setCita] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => { api(`/citas/${id}`).then(setCita).catch((e) => setError(e.message)) }, [id])

  if (error) return <><Alerta>{error}</Alerta><Link to="/mis-citas">Volver a mis citas</Link></>
  if (!cita) return <p className="sub">Cargando…</p>

  return (
    <>
      {state?.nueva && (
        <Alerta tipo="ok">¡Cita agendada con éxito! Te enviamos la confirmación a <b>{usuario.correo}</b>.</Alerta>
      )}
      <h1>Cita {cita.folio}</h1>
      <section className="panel">
        <dl>
          <dt>Estado</dt><dd><span className={`badge ${cita.estado}`}>{ESTADOS[cita.estado]}</span></dd>
          <dt>Folio</dt><dd><b>{cita.folio}</b></dd>
          <dt>Médico</dt><dd>{cita.medico.nombre_completo}</dd>
          <dt>Especialidad</dt><dd>{cita.especialidad.nombre}</dd>
          <dt>Fecha</dt><dd>{fmtFecha(cita.inicio)}</dd>
          <dt>Hora</dt><dd>{fmtHora(cita.inicio)} – {fmtHora(cita.fin)}</dd>
          {cita.medico.consultorio && (<><dt>Consultorio</dt><dd>{cita.medico.consultorio}</dd></>)}
        </dl>
      </section>
      <p><Link to="/mis-citas">← Mis citas</Link> · <Link to="/agendar">Agendar otra cita</Link></p>
    </>
  )
}
