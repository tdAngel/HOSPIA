from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import audit
from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..email_service import enviar_restablecimiento
from ..models import Paciente, PasswordResetToken, RolUsuario, Usuario, utcnow
from ..schemas import (LoginIn, MensajeOut, OlvideContrasenaIn, RegistroIn,
                       RestablecerContrasenaIn, TokenOut, UsuarioOut)
from ..security import (DUMMY_HASH, crear_access_token, generar_token_reset, hash_password,
                        hash_token, verify_password)

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])

MSG_CREDENCIALES = "Correo o contraseña incorrectos."
MSG_FORGOT = "Si el correo está registrado, te enviamos un enlace para restablecer tu contraseña."


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


# ------------------------------------------------------------------ RF-001
@router.post("/registro", response_model=UsuarioOut, status_code=201)
def registro(datos: RegistroIn, request: Request, db: Session = Depends(get_db)):
    if db.scalar(select(Usuario.id).where(Usuario.correo == datos.correo)):
        raise HTTPException(409, "Ya existe una cuenta registrada con ese correo electrónico.")

    usuario = Usuario(correo=datos.correo, password_hash=hash_password(datos.contrasena),
                      nombre_completo=datos.nombre_completo, rol=RolUsuario.PACIENTE)
    usuario.paciente = Paciente(
        fecha_nacimiento=datos.fecha_nacimiento, telefono=datos.telefono,
        acepta_aviso_privacidad=True, fecha_aceptacion_aviso=utcnow(),
        version_aviso=settings.version_aviso_privacidad,
        acepta_notificaciones_movil=datos.acepta_notificaciones_movil)
    db.add(usuario)
    try:
        db.flush()
        audit.registrar(db, "registro_paciente", usuario.id, "usuarios", usuario.id,
                        {"aviso": settings.version_aviso_privacidad}, _ip(request))
        db.commit()
    except IntegrityError:   # carrera entre dos registros simultáneos con el mismo correo
        db.rollback()
        raise HTTPException(409, "Ya existe una cuenta registrada con ese correo electrónico.")
    return usuario


# ------------------------------------------------------------------ RF-002
@router.post("/login", response_model=TokenOut)
def login(datos: LoginIn, request: Request, db: Session = Depends(get_db)):
    ahora = utcnow()
    usuario = db.scalar(select(Usuario).where(Usuario.correo == datos.correo.strip().lower()))

    if usuario and usuario.bloqueado_hasta and usuario.bloqueado_hasta > ahora:
        minutos = int((usuario.bloqueado_hasta - ahora).total_seconds() // 60) + 1
        raise HTTPException(429, f"Cuenta bloqueada temporalmente por intentos fallidos. Intenta en {minutos} min.")

    valido = verify_password(datos.contrasena, usuario.password_hash if usuario else DUMMY_HASH)
    if not usuario or not valido:
        if usuario:
            usuario.intentos_fallidos += 1
            if usuario.intentos_fallidos >= settings.max_intentos_fallidos:
                usuario.bloqueado_hasta = ahora + timedelta(minutes=settings.bloqueo_minutos)
                usuario.intentos_fallidos = 0
        audit.registrar(db, "login_fallido", usuario.id if usuario else None,
                        detalle={"correo": datos.correo[:254]}, ip=_ip(request))
        db.commit()
        raise HTTPException(401, MSG_CREDENCIALES)

    if not usuario.activo:
        audit.registrar(db, "login_cuenta_inactiva", usuario.id, ip=_ip(request))
        db.commit()
        raise HTTPException(403, "Tu cuenta está desactivada. Contacta al hospital.")

    usuario.intentos_fallidos, usuario.bloqueado_hasta, usuario.ultimo_acceso = 0, None, ahora
    audit.registrar(db, "login", usuario.id, ip=_ip(request))
    db.commit()
    return TokenOut(access_token=crear_access_token(usuario.id, usuario.rol.value), usuario=usuario)


@router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(get_current_user)):
    return usuario


@router.post("/olvide-contrasena", response_model=MensajeOut)
def olvide_contrasena(datos: OlvideContrasenaIn, request: Request, tareas: BackgroundTasks,
                      db: Session = Depends(get_db)):
    usuario = db.scalar(select(Usuario).where(Usuario.correo == datos.correo.strip().lower()))
    if usuario and usuario.activo:
        # invalida enlaces anteriores sin usar
        db.execute(update(PasswordResetToken)
                   .where(PasswordResetToken.usuario_id == usuario.id, PasswordResetToken.usado.is_(False))
                   .values(usado=True))
        token, token_hash = generar_token_reset()
        db.add(PasswordResetToken(usuario_id=usuario.id, token_hash=token_hash,
                                  expira_en=utcnow() + timedelta(minutes=settings.reset_token_minutes)))
        audit.registrar(db, "solicitud_reset_password", usuario.id, ip=_ip(request))
        db.commit()
        enlace = f"{settings.frontend_url}/restablecer?token={token}"
        tareas.add_task(enviar_restablecimiento, usuario.correo, usuario.nombre_completo, enlace)
    # Respuesta idéntica exista o no el correo (evita enumeración de usuarios)
    return MensajeOut(mensaje=MSG_FORGOT)


@router.post("/restablecer-contrasena", response_model=MensajeOut)
def restablecer_contrasena(datos: RestablecerContrasenaIn, request: Request, db: Session = Depends(get_db)):
    registro_token = db.scalar(select(PasswordResetToken).where(
        PasswordResetToken.token_hash == hash_token(datos.token)))
    if (not registro_token or registro_token.usado or registro_token.expira_en < utcnow()):
        raise HTTPException(400, "El enlace no es válido o ya expiró. Solicita uno nuevo.")
    usuario = db.get(Usuario, registro_token.usuario_id)
    if not usuario or not usuario.activo:
        raise HTTPException(400, "El enlace no es válido o ya expiró. Solicita uno nuevo.")

    usuario.password_hash = hash_password(datos.nueva_contrasena)
    usuario.intentos_fallidos, usuario.bloqueado_hasta = 0, None
    registro_token.usado = True
    audit.registrar(db, "reset_password", usuario.id, ip=_ip(request))
    db.commit()
    return MensajeOut(mensaje="Tu contraseña fue actualizada. Ya puedes iniciar sesión.")
