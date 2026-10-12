import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import RolUsuario, Usuario
from .security import decodificar_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db: Session = Depends(get_db)) -> Usuario:
    error = HTTPException(401, "Sesión inválida o expirada. Inicia sesión nuevamente.")
    if not cred:
        raise error
    try:
        payload = decodificar_token(cred.credentials)
    except jwt.PyJWTError:
        raise error
    usuario = db.get(Usuario, int(payload["sub"]))
    if not usuario or not usuario.activo:
        raise error
    return usuario


def require_roles(*roles: RolUsuario):
    """RNF-007: control de acceso por rol. Uso: Depends(require_roles(RolUsuario.ADMINISTRADOR))"""
    def checker(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(403, "No tienes permiso para realizar esta acción.")
        return usuario
    return checker
