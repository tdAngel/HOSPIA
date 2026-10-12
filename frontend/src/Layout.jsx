import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from './auth.jsx'

const MENU = {
  paciente: [['/', 'Inicio'], ['/agendar', 'Agendar cita'], ['/mis-citas', 'Mis citas'], ['/perfil', 'Mi perfil']],
  recepcion: [['/', 'Inicio'], ['/agendar', 'Disponibilidad']],
}

export default function Layout() {
  const { usuario, logout } = useAuth()
  const items = MENU[usuario.rol] || [['/', 'Inicio']]
  return (
    <>
      <header className="barra">
        <div className="barra-in">
          <span className="marca">HOSP<span>IA</span></span>
          <nav>{items.map(([ruta, texto]) => <NavLink key={ruta} to={ruta} end={ruta === '/'}>{texto}</NavLink>)}</nav>
          <button className="salir" onClick={logout}>Salir</button>
        </div>
      </header>
      <div className="contenido"><Outlet /></div>
    </>
  )
}
