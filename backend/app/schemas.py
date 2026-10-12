import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from .models import RolUsuario


def validar_contrasena(v: str) -> str:
    if len(v) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    if len(v.encode("utf-8")) > 72:
        raise ValueError("La contraseña es demasiado larga (máximo 72 bytes).")
    if not (re.search(r"[a-z]", v) and re.search(r"[A-Z]", v) and re.search(r"\d", v)):
        raise ValueError("La contraseña debe incluir mayúsculas, minúsculas y números.")
    return v


def normalizar_telefono(v: str) -> str:
    digitos = re.sub(r"[\s\-().]", "", v)
    digitos = re.sub(r"^\+?52", "", digitos) if len(re.sub(r"\D", "", digitos)) > 10 else digitos
    if not re.fullmatch(r"\d{10}", digitos):
        raise ValueError("Ingresa un celular válido de 10 dígitos.")
    return digitos


class RegistroIn(BaseModel):
    nombre_completo: str
    fecha_nacimiento: date
    correo: EmailStr
    telefono: str
    contrasena: str
    acepta_aviso_privacidad: bool
    acepta_notificaciones_movil: bool = False   # RD-004 (opcional)

    @field_validator("nombre_completo")
    @classmethod
    def _nombre(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 5 or len(v.split(" ")) < 2:
            raise ValueError("Ingresa tu nombre completo (nombre y apellido).")
        if len(v) > 150:
            raise ValueError("El nombre es demasiado largo.")
        return v

    @field_validator("fecha_nacimiento")
    @classmethod
    def _fecha(cls, v: date) -> date:
        hoy = date.today()
        if v >= hoy:
            raise ValueError("La fecha de nacimiento debe ser anterior a hoy.")
        if (hoy.year - v.year) > 120:
            raise ValueError("La fecha de nacimiento no es válida.")
        return v

    @field_validator("correo")
    @classmethod
    def _correo(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("telefono")
    @classmethod
    def _telefono(cls, v: str) -> str:
        return normalizar_telefono(v)

    @field_validator("contrasena")
    @classmethod
    def _pwd(cls, v: str) -> str:
        return validar_contrasena(v)

    @field_validator("acepta_aviso_privacidad")
    @classmethod
    def _aviso(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Debes aceptar el aviso de privacidad para crear tu cuenta.")
        return v


class LoginIn(BaseModel):
    correo: str
    contrasena: str


class OlvideContrasenaIn(BaseModel):
    correo: str


class RestablecerContrasenaIn(BaseModel):
    token: str
    nueva_contrasena: str

    @field_validator("nueva_contrasena")
    @classmethod
    def _pwd(cls, v: str) -> str:
        return validar_contrasena(v)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre_completo: str
    correo: str
    rol: RolUsuario


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


class MensajeOut(BaseModel):
    mensaje: str


# ------------------------------------------------------------ Catálogo / agenda / citas
class EspecialidadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    descripcion: Optional[str] = None


class MedicoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre_completo: str
    consultorio: Optional[str] = None
    especialidades: list[EspecialidadOut]


class MedicoResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre_completo: str
    consultorio: Optional[str] = None


class EspecialidadResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class SlotOut(BaseModel):
    inicio: datetime
    fin: datetime


class DisponibilidadOut(BaseModel):
    fecha: date
    medico_id: int
    medico_nombre: str
    consultorio: Optional[str] = None
    horarios: list[SlotOut]


class CitaCrearIn(BaseModel):
    medico_id: int
    especialidad_id: int
    inicio: datetime

    @field_validator("inicio")
    @classmethod
    def _sin_zona(cls, v: datetime) -> datetime:
        if v.tzinfo is not None:
            raise ValueError("Envía la fecha y hora local, sin zona horaria.")
        return v


class CitaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    folio: str
    estado: str
    inicio: datetime
    fin: datetime
    origen: str
    medico: MedicoResumen
    especialidad: EspecialidadResumen

    @field_validator("estado", mode="before")
    @classmethod
    def _estado(cls, v):
        return getattr(v, "value", v)


class PerfilOut(BaseModel):
    nombre_completo: str
    correo: str
    fecha_nacimiento: date
    telefono: str
    acepta_notificaciones_movil: bool


class PerfilUpdateIn(BaseModel):
    telefono: Optional[str] = None
    correo: Optional[EmailStr] = None
    acepta_notificaciones_movil: Optional[bool] = None
    contrasena_actual: Optional[str] = None      # obligatoria solo si cambia el correo

    @field_validator("telefono")
    @classmethod
    def _tel(cls, v):
        return normalizar_telefono(v) if v is not None else v

    @field_validator("correo")
    @classmethod
    def _correo(cls, v):
        return v.strip().lower() if v else v
