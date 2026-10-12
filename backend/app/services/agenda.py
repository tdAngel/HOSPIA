"""Cálculo de disponibilidad (RF-004). Todo se calcula al consultar, por lo que siempre
refleja el estado actual: horarios de atención, bloqueos (RF-012) y citas vigentes (RD-003)."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..models import Cita, EstadoCita, Especialidad, Medico

ESTADOS_QUE_OCUPAN = (EstadoCita.PROGRAMADA, EstadoCita.ATENDIDA)


def ahora_local() -> datetime:
    return datetime.now(ZoneInfo(settings.zona_horaria)).replace(tzinfo=None)


def hoy_local() -> date:
    return ahora_local().date()


def _slots_del_dia(medico: Medico, dia: date) -> list[tuple[datetime, datetime]]:
    slots = []
    for h in medico.horarios:
        if h.dia_semana != dia.weekday():
            continue
        paso = timedelta(minutes=h.duracion_cita_min)
        ini, fin_turno = datetime.combine(dia, h.hora_inicio), datetime.combine(dia, h.hora_fin)
        while ini + paso <= fin_turno:
            slots.append((ini, ini + paso))
            ini += paso
    return sorted(slots)


def consultar(db: Session, fecha: date, dias: int = 1, especialidad_id: int | None = None,
              medico_id: int | None = None) -> list[dict]:
    """Devuelve [{fecha, medico, horarios:[(inicio, fin)]}] solo con días/médicos que tengan lugares."""
    q = (select(Medico).where(Medico.activo.is_(True))
         .options(selectinload(Medico.horarios), selectinload(Medico.bloqueos)))
    if especialidad_id:
        q = q.join(Medico.especialidades).where(Especialidad.id == especialidad_id, Especialidad.activa.is_(True))
    if medico_id:
        q = q.where(Medico.id == medico_id)
    medicos = db.scalars(q.order_by(Medico.nombre_completo)).unique().all()
    if not medicos:
        return []

    inicio_rango = datetime.combine(fecha, datetime.min.time())
    fin_rango = inicio_rango + timedelta(days=dias)
    ocupados = set(db.execute(
        select(Cita.medico_id, Cita.inicio).where(
            Cita.medico_id.in_([m.id for m in medicos]), Cita.inicio >= inicio_rango,
            Cita.inicio < fin_rango, Cita.estado.in_(ESTADOS_QUE_OCUPAN))).all())

    ahora = ahora_local()
    limite_min = ahora + timedelta(minutes=settings.anticipacion_minima_min)
    limite_max = ahora + timedelta(days=settings.dias_max_agenda)

    resultados = []
    for i in range(dias):
        dia = fecha + timedelta(days=i)
        for m in medicos:
            libres = [(ini, fin) for ini, fin in _slots_del_dia(m, dia)
                      if limite_min <= ini <= limite_max
                      and (m.id, ini) not in ocupados
                      and not any(ini < b.fin and fin > b.inicio for b in m.bloqueos)]
            if libres:
                resultados.append({"fecha": dia, "medico": m, "horarios": libres})
    return resultados


def horario_disponible(db: Session, medico_id: int, especialidad_id: int, inicio: datetime) -> bool:
    res = consultar(db, inicio.date(), 1, especialidad_id=especialidad_id, medico_id=medico_id)
    return any(ini == inicio for r in res for ini, _ in r["horarios"])
