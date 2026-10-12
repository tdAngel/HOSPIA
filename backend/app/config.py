from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Base de datos: SQLite para desarrollo rápido, PostgreSQL en docker/producción
    database_url: str = "sqlite:///./hospia.db"

    # Seguridad
    secret_key: str = "cambia-esto-en-produccion-usa-una-cadena-larga-y-aleatoria"
    access_token_minutes: int = 60
    reset_token_minutes: int = 30
    bcrypt_rounds: int = 12                 # RNF-005
    max_intentos_fallidos: int = 5
    bloqueo_minutos: int = 15

    # Aplicación
    frontend_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173"
    version_aviso_privacidad: str = "2026-01"   # RD-001

    # Agenda
    zona_horaria: str = "America/Mexico_City"   # hora local del hospital
    anticipacion_minima_min: int = 60           # no se agenda con menos de 1 h de anticipación
    dias_max_agenda: int = 60                   # horizonte máximo para agendar

    # Correo (SMTP). Si smtp_host está vacío, el correo se imprime en consola.
    smtp_host: str = ""
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "HOSPIA <no-reply@hospia.local>"


settings = Settings()
