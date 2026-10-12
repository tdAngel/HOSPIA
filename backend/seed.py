"""Datos de prueba. Uso:  python seed.py          (agrega si la BD está vacía)
                         python seed.py --reset  (borra todo y vuelve a cargar)"""
import sys
from datetime import date, datetime, time, timedelta

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal, engine
from app.models import (Base, BloqueoAgenda, Cita, CanalNotificacion, Conversacion, AutorMensaje,
                        Especialidad, EstadoCita, EstadoConversacion, EstadoNotificacion, HistorialCita,
                        HorarioAtencion, Medico, Mensaje, Notificacion, Paciente, RolUsuario,
                        TipoNotificacion, Usuario, utcnow)
from app.security import hash_password

PASSWORD = "Hospia2026"

if "--reset" in sys.argv:
    Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

db = SessionLocal()
if db.scalar(select(Usuario.id).limit(1)):
    print("La base de datos ya tiene datos. Usa --reset para recargar.")
    sys.exit(0)

pwd = hash_password(PASSWORD)


def usuario(correo, nombre, rol, activo=True):
    u = Usuario(correo=correo, nombre_completo=nombre, rol=rol, password_hash=pwd, activo=activo)
    db.add(u)
    return u


# ---- Personal
usuario("admin@hospia.mx", "Laura Méndez Ortega", RolUsuario.ADMINISTRADOR)
usuario("recepcion1@hospia.mx", "Carlos Ramírez Soto", RolUsuario.RECEPCION)
usuario("recepcion2@hospia.mx", "Ana Torres Vega", RolUsuario.RECEPCION)

# ---- Especialidades
esp = {n: Especialidad(nombre=n, descripcion=d) for n, d in [
    ("Medicina General", "Atención primaria y valoración inicial"),
    ("Pediatría", "Atención médica de bebés, niños y adolescentes"),
    ("Cardiología", "Corazón y sistema circulatorio"),
    ("Dermatología", "Piel, cabello y uñas"),
    ("Ginecología", "Salud de la mujer"),
    ("Traumatología", "Huesos, músculos y articulaciones"),
]}
db.add_all(esp.values())

# ---- Médicos (cada uno con usuario para iniciar sesión)
medicos_def = [
    ("dr.hernandez@hospia.mx", "Dr. Jorge Hernández Ruiz", "10234561", "Consultorio 101", ["Medicina General"], 0, 9, 14),
    ("dra.castillo@hospia.mx", "Dra. Mariana Castillo Lara", "10234562", "Consultorio 102", ["Pediatría", "Medicina General"], 0, 15, 19),
    ("dr.vargas@hospia.mx", "Dr. Roberto Vargas Peña", "10234563", "Consultorio 201", ["Cardiología"], 0, 10, 16),
    ("dra.ibarra@hospia.mx", "Dra. Sofía Ibarra Núñez", "10234564", "Consultorio 202", ["Dermatología"], 0, 9, 13),
    ("dra.luna@hospia.mx", "Dra. Patricia Luna Cortés", "10234565", "Consultorio 203", ["Ginecología"], 0, 11, 17),
    ("dr.soto@hospia.mx", "Dr. Andrés Soto Mejía", "10234566", "Consultorio 301", ["Traumatología"], 0, 8, 12),
]
medicos = []
for correo, nombre, cedula, cons, especs, _, h_ini, h_fin in medicos_def:
    u = usuario(correo, nombre, RolUsuario.MEDICO)
    m = Medico(usuario=u, nombre_completo=nombre, cedula_profesional=cedula, consultorio=cons,
               especialidades=[esp[e] for e in especs])
    for dia in range(0, 5):                                  # lunes a viernes
        m.horarios.append(HorarioAtencion(dia_semana=dia, hora_inicio=time(h_ini), hora_fin=time(h_fin),
                                          duracion_cita_min=30))
    medicos.append(m)
db.add_all(medicos)

# Dra. Ibarra también atiende sábados por la mañana
medicos[3].horarios.append(HorarioAtencion(dia_semana=5, hora_inicio=time(9), hora_fin=time(12), duracion_cita_min=30))
# Bloqueo: vacaciones del Dr. Vargas la próxima semana
lunes_prox = date.today() + timedelta(days=(7 - date.today().weekday()))
medicos[2].bloqueos.append(BloqueoAgenda(inicio=datetime.combine(lunes_prox, time(0)),
                                         fin=datetime.combine(lunes_prox + timedelta(days=4), time(23, 59)),
                                         motivo="Vacaciones"))

# ---- Pacientes
pacientes_def = [
    ("paciente1@correo.com", "María Fernanda López García", date(1990, 5, 14), "4771234501", True, True),
    ("paciente2@correo.com", "Juan Pablo Martínez Cruz", date(1985, 11, 2), "4771234502", True, False),
    ("paciente3@correo.com", "Sofía Guadalupe Rangel Díaz", date(2001, 3, 27), "4771234503", True, True),
    ("paciente4@correo.com", "Luis Alberto Pérez Mora", date(1972, 8, 19), "4771234504", True, False),
    ("inactivo@correo.com", "Cuenta Desactivada Prueba", date(1980, 1, 1), "4771234599", False, False),
]
pacientes = []
for correo, nombre, nac, tel, activo, movil in pacientes_def:
    u = usuario(correo, nombre, RolUsuario.PACIENTE, activo)
    p = Paciente(usuario=u, fecha_nacimiento=nac, telefono=tel, acepta_aviso_privacidad=True,
                 fecha_aceptacion_aviso=utcnow(), version_aviso=settings.version_aviso_privacidad,
                 acepta_notificaciones_movil=movil)
    pacientes.append(p)
db.add_all(pacientes)
db.flush()


# ---- Citas de ejemplo (todos los estados) con fechas relativas a hoy
def dia_habil(delta):
    d = date.today() + timedelta(days=delta)
    while d.weekday() > 4:
        d += timedelta(days=1)
    return d


def cita(n, pac, med, esp_nombre, dia, hora, estado, origen="web", cita_origen=None):
    ini = datetime.combine(dia, hora)
    c = Cita(folio=f"HOS-{n:06d}", paciente_id=pac.id, medico_id=med.id, especialidad_id=esp[esp_nombre].id,
             inicio=ini, fin=ini + timedelta(minutes=30), estado=estado, origen=origen,
             cita_origen_id=cita_origen.id if cita_origen else None)
    db.add(c)
    db.flush()
    db.add(HistorialCita(cita_id=c.id, estado_anterior=None, estado_nuevo="programada", comentario="Cita creada"))
    if estado != EstadoCita.PROGRAMADA:
        db.add(HistorialCita(cita_id=c.id, estado_anterior="programada", estado_nuevo=estado.value))
    return c


c1 = cita(1, pacientes[0], medicos[0], "Medicina General", dia_habil(-14), time(9, 0), EstadoCita.ATENDIDA)
cita(2, pacientes[0], medicos[2], "Cardiología", dia_habil(-7), time(10, 30), EstadoCita.NO_ASISTIO)
cita(3, pacientes[1], medicos[1], "Pediatría", dia_habil(-3), time(15, 30), EstadoCita.CANCELADA)
orig = cita(4, pacientes[2], medicos[3], "Dermatología", dia_habil(2), time(9, 30), EstadoCita.REPROGRAMADA)
nueva = cita(5, pacientes[2], medicos[3], "Dermatología", dia_habil(3), time(11, 0), EstadoCita.PROGRAMADA, cita_origen=orig)
cita(6, pacientes[0], medicos[0], "Medicina General", dia_habil(1), time(10, 0), EstadoCita.PROGRAMADA, "asistente_ia")
cita(7, pacientes[1], medicos[4], "Ginecología", dia_habil(4), time(12, 0), EstadoCita.PROGRAMADA, "recepcion")
cita(8, pacientes[3], medicos[5], "Traumatología", dia_habil(5), time(8, 30), EstadoCita.PROGRAMADA)

db.add(Notificacion(cita_id=nueva.id, canal=CanalNotificacion.CORREO, tipo=TipoNotificacion.RECORDATORIO,
                    estado=EstadoNotificacion.PENDIENTE, programada_para=nueva.inicio - timedelta(hours=24)))

# ---- Conversación derivada a recepción (RF-010)
conv = Conversacion(paciente_id=pacientes[3].id, estado=EstadoConversacion.DERIVADA)
conv.mensajes = [
    Mensaje(autor=AutorMensaje.PACIENTE, contenido="Hola, necesito una cita con urgencia para mi mamá"),
    Mensaje(autor=AutorMensaje.ASISTENTE, contenido="Entiendo. No puedo evaluar urgencias; te canalizo con recepción."),
]
db.add(conv)
db.commit()

print("Datos de prueba cargados.\n")
print(f"Contraseña de TODAS las cuentas de prueba: {PASSWORD}")
print("  admin@hospia.mx | recepcion1@hospia.mx | dr.hernandez@hospia.mx | paciente1@correo.com | inactivo@correo.com")
