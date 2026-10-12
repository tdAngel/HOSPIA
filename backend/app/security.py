import hashlib
import secrets
from datetime import timedelta

import bcrypt
import jwt

from .config import settings
from .models import utcnow


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(settings.bcrypt_rounds)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode())
    except ValueError:
        return False


# Hash ficticio para que el tiempo de respuesta sea similar cuando el correo no existe
DUMMY_HASH = hash_password("contrasena-ficticia-Aa1")


def crear_access_token(usuario_id: int, rol: str) -> str:
    exp = utcnow() + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": str(usuario_id), "rol": rol, "exp": exp}, settings.secret_key, algorithm="HS256")


def decodificar_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=["HS256"])


def generar_token_reset() -> tuple[str, str]:
    """Devuelve (token_para_el_correo, hash_para_guardar_en_bd)."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
