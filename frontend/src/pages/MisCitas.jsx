import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { Alerta } from '../components.jsx'
import { ESTADOS, fmtFecha, fmtHora } from '../utils.js'

export default function MisCitas() {
  const [estado, setEstado] = useState('')
  const [citas, setCitas] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setCitas(null); setError('')
    api(`/citas/mis-citas${estado ? `?estado=${estado}` : ''}`).then(setCitas).catch((e) => setError(e.message))
  }, [estado])

  return (
    <>
      <h1>Mis citas</h1>
      <label className="campo filtro-estado"><span>Filtrar por estado</span>
        <select value={estado} onChange={(e) => setEstado(e.target.value)}>
          <option value="">Todas</option>
          {Object.entries(ESTADOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select></label>
      <Alerta>{error}</Alerta>
      {citas === null && !error && <p className="sub">Cargando…</p>}
      {citas?.length === 0 && <div className="panel"><p>No hay citas para mostrar. <Link to="/agendar">Agenda tu primera cita</Link></p></div>}
      <div className="lista-citas">
        {citas?.map((c) => (
          <Link key={c.id} to={`/citas/${c.id}`} className="panel cita">
            <div className="cita-fecha"><b>{fmtFecha(c.inicio, { weekday: 'short', year: undefined })}</b><span>{fmtHora(c.inicio)}</span></div>
            <div className="cita-datos"><b>{c.medico.nombre_completo}</b><span>{c.especialidad.nombre}</span><small>{c.folio}</small></div>
            <span className={`badge ${c.estado}`}>{ESTADOS[c.estado]}</span>
          </Link>
        ))}
      </div>
    </>
  )
}
