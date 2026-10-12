import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import Layout from './Layout.jsx'
import Login from './pages/Login.jsx'
import Registro from './pages/Registro.jsx'
import OlvideContrasena from './pages/OlvideContrasena.jsx'
import RestablecerContrasena from './pages/RestablecerContrasena.jsx'
import Inicio from './pages/Inicio.jsx'
import Agendar from './pages/Agendar.jsx'
import MisCitas from './pages/MisCitas.jsx'
import DetalleCita from './pages/DetalleCita.jsx'
import Perfil from './pages/Perfil.jsx'

function Protegida({ children }) {
  const { usuario, cargando } = useAuth()
  if (cargando) return <p className="centro">Cargando…</p>
  return usuario ? children : <Navigate to="/login" replace />
}

function SoloRoles({ roles, children }) {
  const { usuario } = useAuth()
  return roles.includes(usuario.rol) ? children : <Navigate to="/" replace />
}

export default function App() {
  const paciente = ['paciente']
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/registro" element={<Registro />} />
      <Route path="/olvide-contrasena" element={<OlvideContrasena />} />
      <Route path="/restablecer" element={<RestablecerContrasena />} />
      <Route element={<Protegida><Layout /></Protegida>}>
        <Route path="/" element={<Inicio />} />
        <Route path="/agendar" element={<SoloRoles roles={['paciente', 'recepcion']}><Agendar /></SoloRoles>} />
        <Route path="/mis-citas" element={<SoloRoles roles={paciente}><MisCitas /></SoloRoles>} />
        <Route path="/citas/:id" element={<SoloRoles roles={paciente}><DetalleCita /></SoloRoles>} />
        <Route path="/perfil" element={<SoloRoles roles={paciente}><Perfil /></SoloRoles>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
