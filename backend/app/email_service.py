import logging
import smtplib
from email.message import EmailMessage

from .config import settings

log = logging.getLogger("hospia.email")


def enviar_correo(destino: str, asunto: str, texto: str, html: str | None = None) -> bool:
    """Envía por SMTP. Sin SMTP configurado, imprime el correo en consola (desarrollo)."""
    if not settings.smtp_host:
        log.warning("\n--- CORREO (modo consola) ---\nPara: %s\nAsunto: %s\n\n%s\n-----------------------------",
                    destino, asunto, texto)
        return True
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, destino, asunto
    msg.set_content(texto)
    if html:
        msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as s:
            if settings.smtp_user:
                s.starttls()
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        return True
    except Exception:  # nunca exponer fallos de correo al usuario
        log.exception("No se pudo enviar el correo a %s", destino)
        return False


def enviar_restablecimiento(destino: str, nombre: str, enlace: str) -> None:
    minutos = settings.reset_token_minutes
    texto = (f"Hola {nombre},\n\nRecibimos una solicitud para restablecer tu contraseña de HOSPIA.\n"
             f"Abre este enlace (vigente {minutos} minutos, un solo uso):\n{enlace}\n\n"
             "Si no fuiste tú, ignora este mensaje: tu contraseña no cambiará.")
    html = (f"<p>Hola {nombre},</p><p>Recibimos una solicitud para restablecer tu contraseña de HOSPIA.</p>"
            f'<p><a href="{enlace}">Restablecer mi contraseña</a></p>'
            f"<p>El enlace es vigente por {minutos} minutos y de un solo uso.</p>"
            "<p>Si no fuiste tú, ignora este mensaje: tu contraseña no cambiará.</p>")
    enviar_correo(destino, "HOSPIA – Restablecer contraseña", texto, html)


DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_legible(dt) -> str:
    return f"{DIAS[dt.weekday()]} {dt.day} de {MESES[dt.month - 1]} de {dt.year}"


def enviar_confirmacion_cita(destino: str, nombre: str, folio: str, medico: str, especialidad: str,
                             consultorio: str | None, inicio) -> bool:
    cuando, hora = fecha_legible(inicio), inicio.strftime("%H:%M")
    lugar = f"\nConsultorio: {consultorio}" if consultorio else ""
    texto = (f"Hola {nombre},\n\nTu cita fue agendada con éxito.\n\nFolio: {folio}\nMédico: {medico}\n"
             f"Especialidad: {especialidad}\nFecha: {cuando}\nHora: {hora}{lugar}\n\n"
             "Llega 10 minutos antes. Si no puedes asistir, cancela tu cita desde HOSPIA para liberar el horario.")
    filas = "".join(f"<tr><td><b>{k}</b></td><td>{v}</td></tr>" for k, v in [
        ("Folio", folio), ("Médico", medico), ("Especialidad", especialidad), ("Fecha", cuando), ("Hora", hora)]
        + ([("Consultorio", consultorio)] if consultorio else []))
    html = (f"<p>Hola {nombre},</p><p>Tu cita fue agendada con éxito.</p><table cellpadding='6'>{filas}</table>"
            "<p>Llega 10 minutos antes. Si no puedes asistir, cancela tu cita desde HOSPIA.</p>")
    return enviar_correo(destino, f"HOSPIA – Confirmación de cita {folio}", texto, html)
