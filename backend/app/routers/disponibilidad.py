from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import require_roles
from ..models import RolUsuario, Usuario
from ..schemas import DisponibilidadOut, SlotOut
from ..services import agenda

router = APIRouter(prefix="/api/disponibilidad", tags=["Disponibilidad"])


@router.get("", response_model=list[DisponibilidadOut])
def consultar_disponibilidad(
        fecha: date, dias: int = Query(1, ge=1, le=14), especialidad_id: int | None = None,
        medico_id: int | None = None, db: Session = Depends(get_db),
        _: Usuario = Depends(require_roles(RolUsuario.PACIENTE, RolUsuario.RECEPCION))):
    """RF-004: horarios libres filtrando por especialidad, médico y fecha (hasta 14 días desde `fecha`)."""
    if not especialidad_id and not medico_id:
        raise HTTPException(400, "Indica una especialidad o un médico.")
    hoy = agenda.hoy_local()
    if fecha < hoy:
        raise HTTPException(400, "La fecha no puede ser anterior a hoy.")
    if (fecha - hoy).days > settings.dias_max_agenda:
        raise HTTPException(400, f"Solo se puede consultar hasta {settings.dias_max_agenda} días hacia adelante.")

    return [DisponibilidadOut(
        fecha=r["fecha"], medico_id=r["medico"].id, medico_nombre=r["medico"].nombre_completo,
        consultorio=r["medico"].consultorio,
        horarios=[SlotOut(inicio=i, fin=f) for i, f in r["horarios"]])
        for r in agenda.consultar(db, fecha, dias, especialidad_id, medico_id)]
