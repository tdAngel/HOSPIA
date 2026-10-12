export function Tarjeta({ titulo, subtitulo, children }) {
  return (
    <main className="pantalla">
      <section className="tarjeta">
        <div className="marca">HOSP<span>IA</span></div>
        <h1>{titulo}</h1>
        {subtitulo && <p className="sub">{subtitulo}</p>}
        {children}
      </section>
    </main>
  )
}

export function Campo({ etiqueta, nombre, error, ayuda, ...props }) {
  return (
    <label className="campo">
      <span>{etiqueta}</span>
      <input name={nombre} aria-invalid={!!error} {...props} />
      {ayuda && !error && <small>{ayuda}</small>}
      {error && <small className="error">{error}</small>}
    </label>
  )
}

export const Alerta = ({ tipo = 'error', children }) => (children ? <div className={`alerta ${tipo}`} role="alert">{children}</div> : null)
