from sqlalchemy.orm import Session

from .models import Bitacora


def registrar(db: Session, accion: str, usuario_id: int | None = None, entidad: str | None = None,
              entidad_id: int | None = None, detalle: dict | None = None, ip: str | None = None) -> None:
    """RNF-008: agrega un registro a la bitácora (el commit lo hace quien llama)."""
    db.add(Bitacora(usuario_id=usuario_id, accion=accion, entidad=entidad,
                    entidad_id=entidad_id, detalle=detalle, ip=ip))
