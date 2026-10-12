import uuid
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .. import audit
from ..database import get_db
from ..deps import require_roles
from ..email_service import enviar_confirmacion_cita
from ..models import (CanalNotificacion, Cita, EstadoCita, EstadoNotificacion, HistorialCita, Medico,
                      Notificacion, RolUsuario, TipoNotificacion, Usuario, utcnow)
from ..schemas import CitaCrearIn, CitaOut
from ..services import agenda

router = APIRouter(prefix="/api/citas", tags=["Citas"])
solo_paciente = require_roles(RolUsuario.PACIENTE)
MSG_OCUPADO = "El horario seleccionado ya no está disponible. Elige otro horario."


def _enviar_confirmacion(engine, notificacion_id: int, destino: str, nombre: str, folio: str, medico: str,
                         especialidad: str, consultorio, inicio):
    ok = enviar_confirmacion_cita(destino, nombre, folio, medico, especialidad, consultorio, inicio)
    with Session(engine) as s:
        n = s.get(Notificacion, notificacion_id)
        n.estado = EstadoNotificacion.ENVIADA if ok else EstadoNotificacion.FALLIDA
        n.enviada_en = utcnow() if ok else None
        s.commit()


@router.post("", response_model=CitaOut, status_code=201)
def agendar_cita(datos: CitaCrearIn, request: Request, tareas: BackgroundTasks, db: Session = Depends(get_db),
                 usuario: Usuario = Depends(solo_paciente)):
    """RF-005: agenda una cita en un horario disponible y envía la confirmación por correo."""
    medico = db.get(Medico, datos.medico_id)
    if not medico or not medico.activo:
        raise HTTPException(404, "El médico seleccionado no existe o no está disponible.")
    especialidad = next((e for e in medico.especialidades if e.id == datos.especialidad_id and e.activa), None)
    if not especialidad:
        raise HTTPException(400, "El médico no atiende la especialidad seleccionada.")

    # Validaciones de agenda: horario real del médico, sin bloqueo, sin cita previa, con anticipación
    if not agenda.horario_disponible(db, medico.id, especialidad.id, datos.inicio):
        raise HTTPException(409, MSG_OCUPADO)

    paciente = usuario.paciente
    cita = Cita(folio=uuid.uuid4().hex[:20], paciente_id=paciente.id, medico_id=medico.id,
                especialidad_id=especialidad.id, inicio=datos.inicio, estado=EstadoCita.PROGRAMADA, origen="web",
                fin=datos.inicio + timedelta(minutes=next(
                    (h.duracion_cita_min for h in medico.horarios if h.dia_semana == datos.inicio.weekday()
                     and h.hora_inicio <= datos.inicio.time() < h.hora_fin), 30)))
    db.add(cita)
    try:
        db.flush()                                    # el índice único parcial (RD-003) frena carreras
        cita.folio = f"HOS-{cita.id:06d}"
        db.add(HistorialCita(cita_id=cita.id, estado_nuevo=EstadoCita.PROGRAMADA.value,
                             usuario_id=usuario.id, comentario="Cita agendada"))
        notif = Notificacion(cita_id=cita.id, canal=CanalNotificacion.CORREO, tipo=TipoNotificacion.CONFIRMACION,
                             estado=EstadoNotificacion.PENDIENTE, programada_para=utcnow())
        db.add(notif)
        audit.registrar(db, "agendar_cita", usuario.id, "citas", cita.id,
                        {"folio": cita.folio, "medico_id": medico.id, "inicio": cita.inicio.isoformat()},
                        request.client.host if request.client else None)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, MSG_OCUPADO)

    tareas.add_task(_enviar_confirmacion, db.get_bind(), notif.id, usuario.correo, usuario.nombre_completo,
                    cita.folio, medico.nombre_completo, especialidad.nombre, medico.consultorio, cita.inicio)
    return cita


@router.get("/mis-citas", response_model=list[CitaOut])
def mis_citas(estado: EstadoCita | None = None, limite: int = Query(100, ge=1, le=200),
              db: Session = Depends(get_db), usuario: Usuario = Depends(solo_paciente)):
    """RF-003: historial de citas del paciente (más recientes primero)."""
    q = (select(Cita).where(Cita.paciente_id == usuario.paciente.id)
         .options(joinedload(Cita.medico), joinedload(Cita.especialidad))
         .order_by(Cita.inicio.desc()).limit(limite))
    if estado:
        q = q.where(Cita.estado == estado)
    return db.scalars(q).all()


@router.get("/{cita_id}", response_model=CitaOut)
def detalle_cita(cita_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(solo_paciente)):
    cita = db.scalar(select(Cita).where(Cita.id == cita_id, Cita.paciente_id == usuario.paciente.id)
                     .options(joinedload(Cita.medico), joinedload(Cita.especialidad)))
    if not cita:
        raise HTTPException(404, "Cita no encontrada.")      # 404 también si es de otro paciente
    return cita
