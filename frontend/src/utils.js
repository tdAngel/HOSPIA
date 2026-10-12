const pad = (n) => String(n).padStart(2, '0')

// Las fechas del servidor vienen en hora local del hospital, sin zona horaria: se interpretan tal cual.
export function parseLocal(s) {
  const [d, t = '00:00'] = s.split('T')
  const [y, m, dd] = d.split('-').map(Number)
  const [h, mi] = t.split(':').map(Number)
  return new Date(y, m - 1, dd, h, mi)
}
export const fmtFecha = (s, opts = {}) =>
  parseLocal(s).toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', ...opts })
export const fmtHora = (s) => parseLocal(s).toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', hour12: false })
export const hoyISO = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` }

export const ESTADOS = { programada: 'Programada', cancelada: 'Cancelada', reprogramada: 'Reprogramada',
                         atendida: 'Atendida', no_asistio: 'No asistió' }
