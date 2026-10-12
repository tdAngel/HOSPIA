from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import Especialidad, Medico, Usuario
from ..schemas import EspecialidadOut, MedicoOut

router = APIRouter(prefix="/api", tags=["Catálogo"])


@router.get("/especialidades", response_model=list[EspecialidadOut])
def especialidades(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    """Especialidades activas que tienen al menos un médico activo."""
    q = (select(Especialidad).join(Especialidad.medicos)
         .where(Especialidad.activa.is_(True), Medico.activo.is_(True)).order_by(Especialidad.nombre))
    return db.scalars(q).unique().all()


@router.get("/medicos", response_model=list[MedicoOut])
def medicos(especialidad_id: int | None = None, db: Session = Depends(get_db),
            _: Usuario = Depends(get_current_user)):
    q = select(Medico).where(Medico.activo.is_(True)).options(selectinload(Medico.especialidades))
    if especialidad_id:
        q = q.join(Medico.especialidades).where(Especialidad.id == especialidad_id)
    return db.scalars(q.order_by(Medico.nombre_completo)).unique().all()
