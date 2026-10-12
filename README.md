# HOSPIA – Fases 1 y 2: RF-001 a RF-005

Registro · Autenticación · Perfil e historial de citas · Consulta de disponibilidad · Agendar cita

## Stack tecnológico

| Capa | Tecnología | Por qué |
|---|---|---|
| Frontend | React 18 + Vite (SPA responsiva) | RNF-009; ecosistema amplio |
| Backend / API | Python 3.12 + FastAPI | Documentación OpenAPI automática (RF-017); validación con Pydantic; ideal para integrar IA |
| ORM / BD | SQLAlchemy 2 + **PostgreSQL 16** | Integridad transaccional; índices únicos parciales para evitar citas duplicadas (RD-003) |
| Seguridad | bcrypt, JWT (PyJWT), TLS en el despliegue | RNF-005, RNF-006, RNF-007 |
| Asistente IA (próximas fases) | Claude API (tool use) | RF-008 a RF-010 |
| Recordatorios (próximas fases) | APScheduler / Celery + Redis; Twilio (SMS/WhatsApp); SES/SendGrid (correo) | RF-015 |
| Infraestructura | Docker, nube (AWS/Azure) con monitoreo y respaldos automáticos | RNF-001, RNF-010, RNF-011 |

## Cómo ejecutarlo

### Opción A – Docker (recomendada)
```bash
docker compose up --build
```
- App: http://localhost:5173  ·  API/Swagger: http://localhost:8000/docs  ·  Correos de prueba: http://localhost:8025

### Opción B – Local sin Docker (SQLite)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py --reset                                  # crea tablas y datos de prueba
uvicorn app.main:app --reload                           # http://localhost:8000/docs

cd ../frontend && npm install && npm run dev            # http://localhost:5173
```
Sin SMTP configurado, el correo de restablecimiento aparece **en la consola del backend**.

### Pruebas automáticas
```bash
cd backend && pytest -v        # 40 pruebas de RF-001 a RF-005
```

## Cuentas de prueba (contraseña de todas: `Hospia2026`)

| Rol | Correo |
|---|---|
| Administrador | admin@hospia.mx |
| Recepción | recepcion1@hospia.mx, recepcion2@hospia.mx |
| Médicos | dr.hernandez@hospia.mx, dra.castillo@hospia.mx, dr.vargas@hospia.mx, dra.ibarra@hospia.mx, dra.luna@hospia.mx, dr.soto@hospia.mx |
| Pacientes | paciente1@correo.com … paciente4@correo.com |
| Paciente **desactivado** (probar 403) | inactivo@correo.com |

Datos adicionales cargados: 6 especialidades, 6 médicos con horarios L-V (30 min por cita), un bloqueo por vacaciones,
8 citas en todos los estados (programada, cancelada, reprogramada, atendida, no asistió), una notificación y una
conversación derivada a recepción.

## Endpoints implementados

| Método | Ruta | Requisito |
|---|---|---|
| POST | `/api/auth/registro` | RF-001, RD-001, RD-004 |
| POST | `/api/auth/login` | RF-002 |
| GET | `/api/auth/me` | RF-002 |
| POST | `/api/auth/olvide-contrasena` | RF-002 |
| POST | `/api/auth/restablecer-contrasena` | RF-002 |
| GET | `/api/pacientes/me` | RF-003 (ver perfil) |
| PATCH | `/api/pacientes/me` | RF-003 (actualizar teléfono, correo, preferencia SMS/WhatsApp) |
| GET | `/api/citas/mis-citas?estado=` | RF-003 (historial de citas) |
| GET | `/api/citas/{id}` | RF-003 / RF-005 (detalle; solo citas propias) |
| GET | `/api/especialidades`, `/api/medicos?especialidad_id=` | Catálogo para los filtros de RF-004 |
| GET | `/api/disponibilidad?fecha=&dias=&especialidad_id=&medico_id=` | RF-004 (paciente y recepción) |
| POST | `/api/citas` | RF-005, RD-003 |

## Cómo probar las funcionalidades 3 a 5

1. Entra como `paciente1@correo.com` (contraseña `Hospia2026`) → **Agendar cita**.
2. Elige *Medicina General*: verás 7 días de horarios. El de **10:00 de mañana con el Dr. Hernández no aparece** porque ya existe una cita en el seed.
3. Elige *Cardiología* y una fecha de la próxima semana: **no hay horarios** (el Dr. Vargas está de vacaciones, bloqueo cargado en el seed).
4. Pulsa un horario → **Confirmar cita**. Verás la pantalla de confirmación con el folio; el correo llega a Mailpit (http://localhost:8025) o a la consola del backend.
5. **Mis citas** muestra el historial con todos los estados (hay citas atendidas, no asistió, cancelada y reprogramada) y permite filtrar.
6. **Mi perfil**: cambia teléfono o preferencia de SMS/WhatsApp. Para cambiar el correo se pide la contraseña actual.
7. Para ver la vista de recepción (solo consulta, sin botón de agendar): entra con `recepcion1@hospia.mx`.
8. Para probar el choque de horarios: abre dos sesiones (dos pacientes) y agenda el mismo horario; la segunda recibe el aviso de que ya no está disponible y la lista se actualiza.

## Decisiones de diseño relevantes

- **RF-004:** la disponibilidad se **calcula en cada consulta** (horarios de atención − bloqueos − citas vigentes − horas pasadas), por lo que siempre está actualizada. No se ofrecen horarios con menos de 1 h de anticipación ni a más de 60 días (configurable en `config.py`). La zona horaria del hospital es `America/Mexico_City`.
- **RF-005:** el horario se valida contra la agenda real del médico (no se puede inventar una hora), el índice único parcial de la BD evita el doble agendamiento aun con dos peticiones simultáneas, y se guarda historial de estado, notificación de correo (pendiente → enviada/fallida) y bitácora. El folio tiene formato `HOS-000123`.
- **RF-003:** un paciente solo puede ver sus propias citas (las ajenas responden 404).
- **RNF-007:** disponibilidad accesible para paciente y recepción; agendar, historial y perfil solo para paciente.

- **RF-001:** correo único (índice único + validación + manejo de carrera), aviso de privacidad obligatorio con fecha y versión guardadas (RD-001), consentimiento opcional de SMS/WhatsApp (RD-004), el rol se fuerza a *paciente* (nadie puede auto-registrarse como administrador).
- **RF-002:** contraseña con bcrypt; JWT de 60 min; mensajes genéricos (no revela si el correo existe); bloqueo de 15 min tras 5 intentos fallidos; el enlace de restablecimiento es aleatorio, se guarda **solo su hash SHA-256**, expira en 30 min, es de un solo uso e invalida los anteriores.
- **RNF-007:** `deps.require_roles(...)` listo para proteger los siguientes endpoints por rol.
- **RNF-008:** cada registro, login (exitoso o fallido) y restablecimiento queda en la tabla `bitacora`.
- **RD-003:** índice único parcial en `citas (medico_id, inicio)` para citas vigentes, a nivel de base de datos.

## Base de datos (`db/schema.sql` = DDL PostgreSQL completo)

```
usuarios ─┬─ pacientes ── citas ── historial_citas
          ├─ medicos ──┬─ medico_especialidad ── especialidades
          │            ├─ horarios_atencion      citas ── notificaciones
          │            └─ bloqueos_agenda
          ├─ password_reset_tokens
          ├─ conversaciones ── mensajes   (asistente IA / derivación)
          └─ bitacora
```
Ya están todas las tablas del proyecto (RF-001 a RF-017). Hasta esta fase se usan `usuarios`, `pacientes`,
`password_reset_tokens`, `bitacora`, `especialidades`, `medicos`, `medico_especialidad`, `horarios_atencion`,
`bloqueos_agenda`, `citas`, `historial_citas` y `notificaciones`.

## Pendiente para producción
Guardar el JWT en cookie `HttpOnly`, limitar peticiones por IP, HTTPS/TLS, cifrado en reposo (RNF-006), migraciones con Alembic, `SECRET_KEY` real.
