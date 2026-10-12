import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { Alerta } from '../components.jsx'
import { fmtFecha, fmtHora, hoyISO } from '../utils.js'

export default function Agendar() {
  const { usuario } = useAuth()
  const nav = useNavigate()
  const puedeAgendar = usuario.rol === 'paciente'      // recepción solo consulta (RF-004)
  const [especialidades, setEsp] = useState([])
  const [medicos, setMed] = useState([])
  const [f, setF] = useState({ especialidad_id: '', medico_id: '', fecha: hoyISO() })
  const [resultados, setRes] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')
  const [sel, setSel] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [recarga, setRecarga] = useState(0)

  useEffect(() => { api('/especialidades').then(setEsp).catch((e) => setError(e.message)) }, [])

  useEffect(() => {
    setMed([])
    if (f.especialidad_id) api(`/medicos?especialidad_id=${f.especialidad_id}`).then(setMed).catch((e) => setError(e.message))
  }, [f.especialidad_id])

  // Consulta la disponibilidad (siempre en tiempo real) al cambiar cualquier filtro
  useEffect(() => {
    if (!f.especialidad_id || !f.fecha) { setRes(null); return }
    let vigente = true
    setCargando(true); setError('')
    const p = new URLSearchParams({ fecha: f.fecha, dias: 7, especialidad_id: f.especialidad_id })
    if (f.medico_id) p.set('medico_id', f.medico_id)
    api(`/disponibilidad?${p}`)
      .then((r) => vigente && setRes(r))
      .catch((e) => { if (vigente) { setError(e.message); setRes(null) } })
      .finally(() => vigente && setCargando(false))
    return () => { vigente = false }
  }, [f.especialidad_id, f.medico_id, f.fecha, recarga])

  const cambiar = (k) => (e) => setF({ ...f, [k]: e.target.value, ...(k === 'especialidad_id' ? { medico_id: '' } : {}) })
  const nombreEsp = especialidades.find((e) => String(e.id) === String(f.especialidad_id))?.nombre

  async function confirmar() {
    setEnviando(true); setError('')
    try {
      const c = await api('/citas', { method: 'POST',
        body: { medico_id: sel.medico_id, especialidad_id: Number(f.especialidad_id), inicio: sel.inicio } })
      nav(`/citas/${c.id}`, { state: { nueva: true } })
    } catch (e) {
      setSel(null); setError(e.message)
      if (e.status === 409) setRecarga((n) => n + 1)       // el horario se ocupó: refresca la lista
    } finally { setEnviando(false) }
  }

  const porDia = {}
  ;(resultados || []).forEach((r) => (porDia[r.fecha] ||= []).push(r))

  return (
    <>
      <h1>{puedeAgendar ? 'Agendar cita' : 'Consultar disponibilidad'}</h1>
      <p className="sub">Elige una especialidad y la fecha desde la cual quieres ver horarios (se muestran 7 días).</p>

      <section className="panel filtros">
        <label className="campo"><span>Especialidad *</span>
          <select value={f.especialidad_id} onChange={cambiar('especialidad_id')}>
            <option value="">Selecciona…</option>
            {especialidades.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
          </select></label>
        <label className="campo"><span>Médico</span>
          <select value={f.medico_id} onChange={cambiar('medico_id')} disabled={!f.especialidad_id}>
            <option value="">Cualquiera</option>
            {medicos.map((m) => <option key={m.id} value={m.id}>{m.nombre_completo}</option>)}
          </select></label>
        <label className="campo"><span>Fecha</span>
          <input type="date" value={f.fecha} min={hoyISO()} onChange={cambiar('fecha')} /></label>
      </section>

      <Alerta>{error}</Alerta>
      {!f.especialidad_id && <p className="sub">Selecciona una especialidad para ver los horarios.</p>}
      {cargando && <p className="sub">Buscando horarios…</p>}
      {resultados && !cargando && resultados.length === 0 && (
        <div className="panel"><p>No hay horarios disponibles en estos 7 días. Prueba con otra fecha u otro médico.</p></div>
      )}

      {!cargando && Object.entries(porDia).map(([dia, lista]) => (
        <section key={dia} className="dia">
          <h2>{fmtFecha(dia + 'T00:00')}</h2>
          {lista.map((r) => (
            <div key={r.medico_id} className="panel medico">
              <div><b>{r.medico_nombre}</b>{r.consultorio && <span className="sub"> · {r.consultorio}</span>}</div>
              <div className="slots">
                {r.horarios.map((h) => (
                  <button key={h.inicio} className="slot" disabled={!puedeAgendar}
                          onClick={() => setSel({ medico_id: r.medico_id, medico: r.medico_nombre, consultorio: r.consultorio, inicio: h.inicio })}>
                    {fmtHora(h.inicio)}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </section>
      ))}

      {sel && (
        <div className="modal-fondo" onClick={() => !enviando && setSel(null)}>
          <div className="modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <h2>Confirmar cita</h2>
            <dl>
              <dt>Especialidad</dt><dd>{nombreEsp}</dd>
              <dt>Médico</dt><dd>{sel.medico}</dd>
              <dt>Fecha</dt><dd>{fmtFecha(sel.inicio)}</dd>
              <dt>Hora</dt><dd>{fmtHora(sel.inicio)}</dd>
              {sel.consultorio && (<><dt>Consultorio</dt><dd>{sel.consultorio}</dd></>)}
            </dl>
            <div className="acciones">
              <button className="secundario" disabled={enviando} onClick={() => setSel(null)}>Cancelar</button>
              <button disabled={enviando} onClick={confirmar}>{enviando ? 'Agendando…' : 'Confirmar cita'}</button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
