"""Modelo de datos completo de HOSPIA (RF-001 a RF-017).
Las fechas se guardan en UTC (naive); las citas en hora local del hospital."""
from __future__ import annotations

import enum
from datetime import date, datetime, time, timezone
from typing import Optional

from sqlalchemy import (JSON, Boolean, Column, Date, DateTime, Enum, ForeignKey, Index,
                        Integer, SmallInteger, String, Table, Text, Time, UniqueConstraint, text)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RolUsuario(str, enum.Enum):
    PACIENTE = "paciente"
    RECEPCION = "recepcion"
    MEDICO = "medico"
    ADMINISTRADOR = "administrador"


class EstadoCita(str, enum.Enum):
    PROGRAMADA = "programada"
    CANCELADA = "cancelada"
    REPROGRAMADA = "reprogramada"
    ATENDIDA = "atendida"
    NO_ASISTIO = "no_asistio"


class CanalNotificacion(str, enum.Enum):
    CORREO = "correo"
    SMS = "sms"
    WHATSAPP = "whatsapp"


class TipoNotificacion(str, enum.Enum):
    CONFIRMACION = "confirmacion"
    RECORDATORIO = "recordatorio"
    CANCELACION = "cancelacion"
    REPROGRAMACION = "reprogramacion"


class EstadoNotificacion(str, enum.Enum):
    PENDIENTE = "pendiente"
    ENVIADA = "enviada"
    FALLIDA = "fallida"


class EstadoConversacion(str, enum.Enum):
    ACTIVA = "activa"
    DERIVADA = "derivada"
    CERRADA = "cerrada"


class AutorMensaje(str, enum.Enum):
    PACIENTE = "paciente"
    ASISTENTE = "asistente"
    RECEPCION = "recepcion"


def _enum(e):
    return Enum(e, native_enum=False, length=20, create_constraint=True,
                values_callable=lambda x: [m.value for m in x], validate_strings=True)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------- Usuarios (RF-001, RF-002)
class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    correo: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))               # bcrypt (RNF-005)
    nombre_completo: Mapped[str] = mapped_column(String(150))
    rol: Mapped[RolUsuario] = mapped_column(_enum(RolUsuario))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[Optional[datetime]] = mapped_column(DateTime)
    ultimo_acceso: Mapped[Optional[datetime]] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    paciente: Mapped[Optional["Paciente"]] = relationship(back_populates="usuario", uselist=False,
                                                          cascade="all, delete-orphan")
    medico: Mapped[Optional["Medico"]] = relationship(back_populates="usuario", uselist=False)


class Paciente(Base):
    __tablename__ = "pacientes"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), unique=True)
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    telefono: Mapped[str] = mapped_column(String(15))
    # RD-001: consentimiento expreso con evidencia
    acepta_aviso_privacidad: Mapped[bool] = mapped_column(Boolean)
    fecha_aceptacion_aviso: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    version_aviso: Mapped[str] = mapped_column(String(20))
    # RD-004: consentimiento para SMS / WhatsApp
    acepta_notificaciones_movil: Mapped[bool] = mapped_column(Boolean, default=False)

    usuario: Mapped[Usuario] = relationship(back_populates="paciente")
    citas: Mapped[list["Cita"]] = relationship(back_populates="paciente")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)       # SHA-256 del token
    expira_en: Mapped[datetime] = mapped_column(DateTime)
    usado: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------- Catálogos (RF-011, RF-012)
medico_especialidad = Table(
    "medico_especialidad", Base.metadata,
    Column("medico_id", ForeignKey("medicos.id", ondelete="CASCADE"), primary_key=True),
    Column("especialidad_id", ForeignKey("especialidades.id", ondelete="CASCADE"), primary_key=True),
)


class Especialidad(Base):
    __tablename__ = "especialidades"
    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(255))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    medicos: Mapped[list["Medico"]] = relationship(secondary=medico_especialidad, back_populates="especialidades")


class Medico(Base):
    __tablename__ = "medicos"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), unique=True)
    nombre_completo: Mapped[str] = mapped_column(String(150))
    cedula_profesional: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    consultorio: Mapped[Optional[str]] = mapped_column(String(30))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    usuario: Mapped[Optional[Usuario]] = relationship(back_populates="medico")
    especialidades: Mapped[list[Especialidad]] = relationship(secondary=medico_especialidad, back_populates="medicos")
    horarios: Mapped[list["HorarioAtencion"]] = relationship(back_populates="medico", cascade="all, delete-orphan")
    bloqueos: Mapped[list["BloqueoAgenda"]] = relationship(back_populates="medico", cascade="all, delete-orphan")


class HorarioAtencion(Base):
    __tablename__ = "horarios_atencion"
    __table_args__ = (UniqueConstraint("medico_id", "dia_semana", "hora_inicio"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    medico_id: Mapped[int] = mapped_column(ForeignKey("medicos.id", ondelete="CASCADE"), index=True)
    dia_semana: Mapped[int] = mapped_column(SmallInteger)                  # 0=lunes ... 6=domingo
    hora_inicio: Mapped[time] = mapped_column(Time)
    hora_fin: Mapped[time] = mapped_column(Time)
    duracion_cita_min: Mapped[int] = mapped_column(SmallInteger, default=30)
    medico: Mapped[Medico] = relationship(back_populates="horarios")


class BloqueoAgenda(Base):
    __tablename__ = "bloqueos_agenda"
    id: Mapped[int] = mapped_column(primary_key=True)
    medico_id: Mapped[int] = mapped_column(ForeignKey("medicos.id", ondelete="CASCADE"), index=True)
    inicio: Mapped[datetime] = mapped_column(DateTime)
    fin: Mapped[datetime] = mapped_column(DateTime)
    motivo: Mapped[str] = mapped_column(String(120))
    medico: Mapped[Medico] = relationship(back_populates="bloqueos")


# ---------------------------------------------------------------- Citas (RF-003 a RF-007, RF-013, RF-014)
class Cita(Base):
    __tablename__ = "citas"
    __table_args__ = (
        # RD-003: un médico no puede tener dos citas vigentes en el mismo horario
        Index("uq_cita_medico_horario_vigente", "medico_id", "inicio", unique=True,
              postgresql_where=text("estado IN ('programada','atendida')"),
              sqlite_where=text("estado IN ('programada','atendida')")),
        Index("ix_citas_paciente_inicio", "paciente_id", "inicio"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    folio: Mapped[str] = mapped_column(String(20), unique=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id"))
    medico_id: Mapped[int] = mapped_column(ForeignKey("medicos.id"))
    especialidad_id: Mapped[int] = mapped_column(ForeignKey("especialidades.id"))
    inicio: Mapped[datetime] = mapped_column(DateTime)
    fin: Mapped[datetime] = mapped_column(DateTime)
    estado: Mapped[EstadoCita] = mapped_column(_enum(EstadoCita), default=EstadoCita.PROGRAMADA)
    cita_origen_id: Mapped[Optional[int]] = mapped_column(ForeignKey("citas.id"))   # RF-007
    origen: Mapped[str] = mapped_column(String(20), default="web")                  # web | asistente_ia | recepcion | api
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    paciente: Mapped[Paciente] = relationship(back_populates="citas")
    medico: Mapped[Medico] = relationship()
    especialidad: Mapped[Especialidad] = relationship()
    historial: Mapped[list["HistorialCita"]] = relationship(back_populates="cita", cascade="all, delete-orphan")


class HistorialCita(Base):
    __tablename__ = "historial_citas"
    id: Mapped[int] = mapped_column(primary_key=True)
    cita_id: Mapped[int] = mapped_column(ForeignKey("citas.id", ondelete="CASCADE"), index=True)
    estado_anterior: Mapped[Optional[str]] = mapped_column(String(20))
    estado_nuevo: Mapped[str] = mapped_column(String(20))
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    comentario: Mapped[Optional[str]] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    cita: Mapped[Cita] = relationship(back_populates="historial")


# ---------------------------------------------------------------- Notificaciones (RF-015)
class Notificacion(Base):
    __tablename__ = "notificaciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    cita_id: Mapped[int] = mapped_column(ForeignKey("citas.id", ondelete="CASCADE"), index=True)
    canal: Mapped[CanalNotificacion] = mapped_column(_enum(CanalNotificacion))
    tipo: Mapped[TipoNotificacion] = mapped_column(_enum(TipoNotificacion))
    estado: Mapped[EstadoNotificacion] = mapped_column(_enum(EstadoNotificacion), default=EstadoNotificacion.PENDIENTE)
    programada_para: Mapped[datetime] = mapped_column(DateTime)
    enviada_en: Mapped[Optional[datetime]] = mapped_column(DateTime)
    respuesta_paciente: Mapped[Optional[str]] = mapped_column(String(10))   # confirma | cancela


# ---------------------------------------------------------------- Asistente IA (RF-008 a RF-010)
class Conversacion(Base):
    __tablename__ = "conversaciones"
    id: Mapped[int] = mapped_column(primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id", ondelete="CASCADE"), index=True)
    estado: Mapped[EstadoConversacion] = mapped_column(_enum(EstadoConversacion), default=EstadoConversacion.ACTIVA)
    atendida_por_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    mensajes: Mapped[list["Mensaje"]] = relationship(back_populates="conversacion", cascade="all, delete-orphan",
                                                     order_by="Mensaje.id")


class Mensaje(Base):
    __tablename__ = "mensajes"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversacion_id: Mapped[int] = mapped_column(ForeignKey("conversaciones.id", ondelete="CASCADE"), index=True)
    autor: Mapped[AutorMensaje] = mapped_column(_enum(AutorMensaje))
    contenido: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    conversacion: Mapped[Conversacion] = relationship(back_populates="mensajes")


# ---------------------------------------------------------------- Bitácora (RNF-008)
class Bitacora(Base):
    __tablename__ = "bitacora"
    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), index=True)
    accion: Mapped[str] = mapped_column(String(50), index=True)
    entidad: Mapped[Optional[str]] = mapped_column(String(50))
    entidad_id: Mapped[Optional[int]] = mapped_column(Integer)
    detalle: Mapped[Optional[dict]] = mapped_column(JSON)
    ip: Mapped[Optional[str]] = mapped_column(String(45))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
