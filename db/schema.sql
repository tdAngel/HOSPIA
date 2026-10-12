-- HOSPIA · esquema PostgreSQL (generado con backend/export_schema.py)

CREATE TABLE especialidades (
	id SERIAL NOT NULL, 
	nombre VARCHAR(80) NOT NULL, 
	descripcion VARCHAR(255), 
	activa BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (nombre)
);

CREATE TABLE usuarios (
	id SERIAL NOT NULL, 
	correo VARCHAR(254) NOT NULL, 
	password_hash VARCHAR(100) NOT NULL, 
	nombre_completo VARCHAR(150) NOT NULL, 
	rol VARCHAR(20) NOT NULL, 
	activo BOOLEAN NOT NULL, 
	intentos_fallidos INTEGER NOT NULL, 
	bloqueado_hasta TIMESTAMP WITHOUT TIME ZONE, 
	ultimo_acceso TIMESTAMP WITHOUT TIME ZONE, 
	creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT rolusuario CHECK (rol IN ('paciente', 'recepcion', 'medico', 'administrador'))
);

CREATE UNIQUE INDEX ix_usuarios_correo ON usuarios (correo);

CREATE TABLE bitacora (
	id SERIAL NOT NULL, 
	usuario_id INTEGER, 
	accion VARCHAR(50) NOT NULL, 
	entidad VARCHAR(50), 
	entidad_id INTEGER, 
	detalle JSON, 
	ip VARCHAR(45), 
	creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
);

CREATE INDEX ix_bitacora_accion ON bitacora (accion);

CREATE INDEX ix_bitacora_creado_en ON bitacora (creado_en);

CREATE INDEX ix_bitacora_usuario_id ON bitacora (usuario_id);

CREATE TABLE medicos (
	id SERIAL NOT NULL, 
	usuario_id INTEGER, 
	nombre_completo VARCHAR(150) NOT NULL, 
	cedula_profesional VARCHAR(20), 
	consultorio VARCHAR(30), 
	activo BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (usuario_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL, 
	UNIQUE (cedula_profesional)
);

CREATE TABLE pacientes (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	fecha_nacimiento DATE NOT NULL, 
	telefono VARCHAR(15) NOT NULL, 
	acepta_aviso_privacidad BOOLEAN NOT NULL, 
	fecha_aceptacion_aviso TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	version_aviso VARCHAR(20) NOT NULL, 
	acepta_notificaciones_movil BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (usuario_id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
);

CREATE TABLE password_reset_tokens (
	id SERIAL NOT NULL, 
	usuario_id INTEGER NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	expira_en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	usado BOOLEAN NOT NULL, 
	creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE, 
	UNIQUE (token_hash)
);

CREATE INDEX ix_password_reset_tokens_usuario_id ON password_reset_tokens (usuario_id);

CREATE TABLE bloqueos_agenda (
	id SERIAL NOT NULL, 
	medico_id INTEGER NOT NULL, 
	inicio TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	fin TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	motivo VARCHAR(120) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(medico_id) REFERENCES medicos (id) ON DELETE CASCADE
);

CREATE INDEX ix_bloqueos_agenda_medico_id ON bloqueos_agenda (medico_id);

CREATE TABLE citas (
	id SERIAL NOT NULL, 
	folio VARCHAR(20) NOT NULL, 
	paciente_id INTEGER NOT NULL, 
	medico_id INTEGER NOT NULL, 
	especialidad_id INTEGER NOT NULL, 
	inicio TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	fin TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	estado VARCHAR(20) NOT NULL, 
	cita_origen_id INTEGER, 
	origen VARCHAR(20) NOT NULL, 
	creada_en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (folio), 
	FOREIGN KEY(paciente_id) REFERENCES pacientes (id), 
	FOREIGN KEY(medico_id) REFERENCES medicos (id), 
	FOREIGN KEY(especialidad_id) REFERENCES especialidades (id), 
	CONSTRAINT estadocita CHECK (estado IN ('programada', 'cancelada', 'reprogramada', 'atendida', 'no_asistio')), 
	FOREIGN KEY(cita_origen_id) REFERENCES citas (id)
);

CREATE INDEX ix_citas_paciente_inicio ON citas (paciente_id, inicio);

CREATE UNIQUE INDEX uq_cita_medico_horario_vigente ON citas (medico_id, inicio) WHERE estado IN ('programada','atendida');

CREATE TABLE conversaciones (
	id SERIAL NOT NULL, 
	paciente_id INTEGER NOT NULL, 
	estado VARCHAR(20) NOT NULL, 
	atendida_por_id INTEGER, 
	creada_en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(paciente_id) REFERENCES pacientes (id) ON DELETE CASCADE, 
	CONSTRAINT estadoconversacion CHECK (estado IN ('activa', 'derivada', 'cerrada')), 
	FOREIGN KEY(atendida_por_id) REFERENCES usuarios (id) ON DELETE SET NULL
);

CREATE INDEX ix_conversaciones_paciente_id ON conversaciones (paciente_id);

CREATE TABLE horarios_atencion (
	id SERIAL NOT NULL, 
	medico_id INTEGER NOT NULL, 
	dia_semana SMALLINT NOT NULL, 
	hora_inicio TIME WITHOUT TIME ZONE NOT NULL, 
	hora_fin TIME WITHOUT TIME ZONE NOT NULL, 
	duracion_cita_min SMALLINT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (medico_id, dia_semana, hora_inicio), 
	FOREIGN KEY(medico_id) REFERENCES medicos (id) ON DELETE CASCADE
);

CREATE INDEX ix_horarios_atencion_medico_id ON horarios_atencion (medico_id);

CREATE TABLE medico_especialidad (
	medico_id INTEGER NOT NULL, 
	especialidad_id INTEGER NOT NULL, 
	PRIMARY KEY (medico_id, especialidad_id), 
	FOREIGN KEY(medico_id) REFERENCES medicos (id) ON DELETE CASCADE, 
	FOREIGN KEY(especialidad_id) REFERENCES especialidades (id) ON DELETE CASCADE
);

CREATE TABLE historial_citas (
	id SERIAL NOT NULL, 
	cita_id INTEGER NOT NULL, 
	estado_anterior VARCHAR(20), 
	estado_nuevo VARCHAR(20) NOT NULL, 
	usuario_id INTEGER, 
	comentario VARCHAR(255), 
	creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(cita_id) REFERENCES citas (id) ON DELETE CASCADE, 
	FOREIGN KEY(usuario_id) REFERENCES usuarios (id) ON DELETE SET NULL
);

CREATE INDEX ix_historial_citas_cita_id ON historial_citas (cita_id);

CREATE TABLE mensajes (
	id SERIAL NOT NULL, 
	conversacion_id INTEGER NOT NULL, 
	autor VARCHAR(20) NOT NULL, 
	contenido TEXT NOT NULL, 
	creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversacion_id) REFERENCES conversaciones (id) ON DELETE CASCADE, 
	CONSTRAINT autormensaje CHECK (autor IN ('paciente', 'asistente', 'recepcion'))
);

CREATE INDEX ix_mensajes_conversacion_id ON mensajes (conversacion_id);

CREATE TABLE notificaciones (
	id SERIAL NOT NULL, 
	cita_id INTEGER NOT NULL, 
	canal VARCHAR(20) NOT NULL, 
	tipo VARCHAR(20) NOT NULL, 
	estado VARCHAR(20) NOT NULL, 
	programada_para TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	enviada_en TIMESTAMP WITHOUT TIME ZONE, 
	respuesta_paciente VARCHAR(10), 
	PRIMARY KEY (id), 
	FOREIGN KEY(cita_id) REFERENCES citas (id) ON DELETE CASCADE, 
	CONSTRAINT canalnotificacion CHECK (canal IN ('correo', 'sms', 'whatsapp')), 
	CONSTRAINT tiponotificacion CHECK (tipo IN ('confirmacion', 'recordatorio', 'cancelacion', 'reprogramacion')), 
	CONSTRAINT estadonotificacion CHECK (estado IN ('pendiente', 'enviada', 'fallida'))
);

CREATE INDEX ix_notificaciones_cita_id ON notificaciones (cita_id);
