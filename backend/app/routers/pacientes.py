from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..deps import require_roles
from ..models import RolUsuario, Usuario
from ..schemas import PerfilOut, PerfilUpdateIn
from ..security import verify_password

router = APIRouter(prefix="/api/pacientes", tags=["Perfil del paciente"])
solo_paciente = require_roles(RolUsuario.PACIENTE)


def _perfil(u: Usuario) -> PerfilOut:
    p = u.paciente
    return PerfilOut(nombre_completo=u.nombre_completo, correo=u.correo, fecha_nacimiento=p.fecha_nacimiento,
                     telefono=p.telefono, acepta_notificaciones_movil=p.acepta_notificaciones_movil)


@router.get("/me", response_model=PerfilOut)
def ver_perfil(usuario: Usuario = Depends(solo_paciente)):
    return _perfil(usuario)


@router.patch("/me", response_model=PerfilOut)
def actualizar_perfil(datos: PerfilUpdateIn, request: Request, db: Session = Depends(get_db),
                      usuario: Usuario = Depends(solo_paciente)):
    """RF-003: actualiza datos de contacto (teléfono, correo, preferencia de SMS/WhatsApp)."""
    cambios = []
    if datos.correo and datos.correo != usuario.correo:
        if not datos.contrasena_actual or not verify_password(datos.contrasena_actual, usuario.password_hash):
            raise HTTPException(400, "Para cambiar tu correo confirma tu contraseña actual correctamente.")
        if db.scalar(select(Usuario.id).where(Usuario.correo == datos.correo)):
            raise HTTPException(409, "Ya existe una cuenta registrada con ese correo electrónico.")
        usuario.correo = datos.correo
        cambios.append("correo")
    if datos.telefono is not None and datos.telefono != usuario.paciente.telefono:
        usuario.paciente.telefono = datos.telefono
        cambios.append("telefono")
    if (datos.acepta_notificaciones_movil is not None
            and datos.acepta_notificaciones_movil != usuario.paciente.acepta_notificaciones_movil):
        usuario.paciente.acepta_notificaciones_movil = datos.acepta_notificaciones_movil
        cambios.append("acepta_notificaciones_movil")
    if cambios:
        audit.registrar(db, "actualizar_perfil", usuario.id, "pacientes", usuario.paciente.id,
                        {"campos": cambios}, request.client.host if request.client else None)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Ya existe una cuenta registrada con ese correo electrónico.")
    return _perfil(usuario)
