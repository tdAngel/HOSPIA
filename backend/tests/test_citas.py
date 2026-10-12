from datetime import date, datetime, time, timedelta

import pytest

from app.models import (BloqueoAgenda, Bitacora, Cita, Especialidad, EstadoCita, HorarioAtencion, Medico,
                        Notificacion, EstadoNotificacion)
from app.services.agenda import hoy_local
from sqlalchemy import select


def siguiente_dia_semana(dia_semana: int, minimo_dias: int = 3) -> date:
    d = hoy_local() + timedelta(days=minimo_dias)
    while d.weekday() != dia_semana:
        d += timedelta(days=1)
    return d


LUNES = siguiente_dia_semana(0)        # lunes de al menos 3 días en el futuro


@pytest.fixture()
def datos(client):
    """Cardiología con 1 médico (L-V 09:00-11:00, citas de 30 min = 4 lugares) y otro médico inactivo."""
    with client.session_factory() as db:
        card, derm = Especialidad(nombre="Cardiología"), Especialidad(nombre="Dermatología")
        m = Medico(nombre_completo="Dr. Vargas", consultorio="201", especialidades=[card])
        m.horarios = [HorarioAtencion(dia_semana=d, hora_inicio=time(9), hora_fin=time(11), duracion_cita_min=30)
                      for d in range(5)]
        inactivo = Medico(nombre_completo="Dr. Inactivo", activo=False, especialidades=[card])
        inactivo.horarios = [HorarioAtencion(dia_semana=0, hora_inicio=time(9), hora_fin=time(10))]
        db.add_all([card, derm, m, inactivo])
        db.commit()
        return {"medico_id": m.id, "esp_id": card.id, "derm_id": derm.id}


def registrar_y_login(client, correo="paciente@correo.com", telefono="4771234567"):
    client.post("/api/auth/registro", json={
        "nombre_completo": "Paciente Prueba Uno", "fecha_nacimiento": "1990-01-01", "correo": correo,
        "telefono": telefono, "contrasena": "Segura123", "acepta_aviso_privacidad": True})
    t = client.post("/api/auth/login", json={"correo": correo, "contrasena": "Segura123"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


def disponibilidad(client, h, **params):
    return client.get("/api/disponibilidad", params=params, headers=h)


def agendar(client, h, datos, hora=time(9), dia=LUNES):
    return client.post("/api/citas", headers=h, json={
        "medico_id": datos["medico_id"], "especialidad_id": datos["esp_id"],
        "inicio": datetime.combine(dia, hora).isoformat()})


# ---------------- RF-004
def test_disponibilidad_por_especialidad(client, datos):
    h = registrar_y_login(client)
    r = disponibilidad(client, h, fecha=LUNES.isoformat(), especialidad_id=datos["esp_id"])
    assert r.status_code == 200
    assert len(r.json()) == 1 and r.json()[0]["medico_nombre"] == "Dr. Vargas"      # el inactivo no aparece
    horas = [s["inicio"][11:16] for s in r.json()[0]["horarios"]]
    assert horas == ["09:00", "09:30", "10:00", "10:30"]


def test_disponibilidad_filtra_medico_y_rango(client, datos):
    h = registrar_y_login(client)
    r = disponibilidad(client, h, fecha=LUNES.isoformat(), dias=7, medico_id=datos["medico_id"])
    assert len(r.json()) == 5                          # lunes a viernes; sin sábado ni domingo
    assert disponibilidad(client, h, fecha=LUNES.isoformat(), especialidad_id=datos["derm_id"]).json() == []


def test_disponibilidad_validaciones(client, datos):
    h = registrar_y_login(client)
    assert disponibilidad(client, h, fecha=LUNES.isoformat()).status_code == 400          # sin filtro
    ayer = (hoy_local() - timedelta(days=1)).isoformat()
    assert disponibilidad(client, h, fecha=ayer, especialidad_id=datos["esp_id"]).status_code == 400
    assert client.get("/api/disponibilidad?fecha=2026-01-01&especialidad_id=1").status_code == 401


def test_disponibilidad_excluye_bloqueos_y_ocupados(client, datos):
    h = registrar_y_login(client)
    with client.session_factory() as db:
        db.add(BloqueoAgenda(medico_id=datos["medico_id"], motivo="Congreso",
                             inicio=datetime.combine(LUNES, time(9, 30)), fin=datetime.combine(LUNES, time(10, 0))))
        db.commit()
    assert agendar(client, h, datos, time(10, 30)).status_code == 201
    horas = [s["inicio"][11:16] for s in disponibilidad(
        client, h, fecha=LUNES.isoformat(), especialidad_id=datos["esp_id"]).json()[0]["horarios"]]
    assert horas == ["09:00", "10:00"]          # 09:30 bloqueado, 10:30 ocupado


def test_disponibilidad_hoy_no_ofrece_horas_pasadas(client, datos):
    h = registrar_y_login(client)
    with client.session_factory() as db:
        for hh in db.scalars(select(HorarioAtencion)).all():
            hh.hora_inicio, hh.hora_fin = time(0, 0), time(23, 30)        # horario de todo el día
        db.commit()
    r = disponibilidad(client, h, fecha=hoy_local().isoformat(), medico_id=datos["medico_id"]).json()
    from app.services.agenda import ahora_local
    limite = ahora_local() + timedelta(minutes=60)
    assert all(datetime.fromisoformat(s["inicio"]) >= limite for x in r for s in x["horarios"])


# ---------------- RF-005
def test_agendar_cita_exitoso(client, datos, monkeypatch):
    enviados = []
    monkeypatch.setattr("app.routers.citas.enviar_confirmacion_cita",
                        lambda *a: enviados.append(a) or True)
    h = registrar_y_login(client)
    r = agendar(client, h, datos)
    assert r.status_code == 201
    c = r.json()
    assert c["folio"].startswith("HOS-") and c["estado"] == "programada"
    assert c["medico"]["nombre_completo"] == "Dr. Vargas" and c["especialidad"]["nombre"] == "Cardiología"
    assert c["fin"][11:16] == "09:30"
    # correo con folio, médico, especialidad, fecha y hora
    assert len(enviados) == 1 and enviados[0][2] == c["folio"] and enviados[0][0] == "paciente@correo.com"
    with client.session_factory() as db:
        assert db.scalar(select(Notificacion)).estado == EstadoNotificacion.ENVIADA
        assert db.scalar(select(Bitacora).where(Bitacora.accion == "agendar_cita"))
    # el horario deja de estar disponible
    horas = [s["inicio"][11:16] for s in disponibilidad(
        client, h, fecha=LUNES.isoformat(), especialidad_id=datos["esp_id"]).json()[0]["horarios"]]
    assert "09:00" not in horas


def test_no_permite_doble_agendamiento_mismo_horario(client, datos):
    h1 = registrar_y_login(client)
    h2 = registrar_y_login(client, "otro@correo.com", "4779998888")
    assert agendar(client, h1, datos).status_code == 201
    assert agendar(client, h2, datos).status_code == 409           # RD-003
    assert agendar(client, h1, datos).status_code == 409           # mismo paciente, mismo médico y hora


def test_cancelada_libera_horario(client, datos):
    h = registrar_y_login(client)
    cita_id = agendar(client, h, datos).json()["id"]
    with client.session_factory() as db:
        db.get(Cita, cita_id).estado = EstadoCita.CANCELADA
        db.commit()
    assert agendar(client, h, datos).status_code == 201


@pytest.mark.parametrize("hora,dia", [(time(8), LUNES), (time(11), LUNES), (time(9, 15), LUNES),
                                      (time(9), LUNES + timedelta(days=5)),                 # sábado
                                      (time(9), hoy_local() - timedelta(days=1)),            # pasado
                                      (time(9), hoy_local() + timedelta(days=400))])         # muy lejano
def test_horarios_invalidos(client, datos, hora, dia):
    h = registrar_y_login(client)
    assert agendar(client, h, datos, hora, dia).status_code == 409


def test_agendar_validaciones_de_catalogo(client, datos):
    h = registrar_y_login(client)
    base = {"inicio": datetime.combine(LUNES, time(9)).isoformat()}
    assert client.post("/api/citas", headers=h, json={**base, "medico_id": 999, "especialidad_id": datos["esp_id"]}).status_code == 404
    assert client.post("/api/citas", headers=h, json={**base, "medico_id": datos["medico_id"], "especialidad_id": datos["derm_id"]}).status_code == 400
    assert client.post("/api/citas", headers=h, json={"medico_id": datos["medico_id"], "especialidad_id": datos["esp_id"],
                                                      "inicio": "2030-01-01T09:00:00Z"}).status_code == 422
    assert client.post("/api/citas", json={**base, "medico_id": 1, "especialidad_id": 1}).status_code == 401


# ---------------- RF-003
def test_historial_y_filtro_por_estado(client, datos):
    h = registrar_y_login(client)
    c1 = agendar(client, h, datos, time(9)).json()
    agendar(client, h, datos, time(9, 30))
    with client.session_factory() as db:
        db.get(Cita, c1["id"]).estado = EstadoCita.CANCELADA
        db.commit()
    todas = client.get("/api/citas/mis-citas", headers=h).json()
    assert len(todas) == 2 and todas[0]["inicio"] > todas[1]["inicio"]
    assert {"folio", "inicio", "medico", "especialidad", "estado"} <= set(todas[0])
    canceladas = client.get("/api/citas/mis-citas?estado=cancelada", headers=h).json()
    assert [c["id"] for c in canceladas] == [c1["id"]]
    assert client.get("/api/citas/mis-citas?estado=inventado", headers=h).status_code == 422


def test_un_paciente_no_ve_citas_de_otro(client, datos):
    h1 = registrar_y_login(client)
    h2 = registrar_y_login(client, "otro@correo.com", "4779998888")
    cita_id = agendar(client, h1, datos).json()["id"]
    assert client.get("/api/citas/mis-citas", headers=h2).json() == []
    assert client.get(f"/api/citas/{cita_id}", headers=h2).status_code == 404
    assert client.get(f"/api/citas/{cita_id}", headers=h1).status_code == 200


def test_perfil_ver_y_actualizar(client, datos):
    h = registrar_y_login(client)
    p = client.get("/api/pacientes/me", headers=h).json()
    assert p["telefono"] == "4771234567" and p["correo"] == "paciente@correo.com"
    r = client.patch("/api/pacientes/me", headers=h, json={"telefono": "477 555 0000", "acepta_notificaciones_movil": True})
    assert r.status_code == 200 and r.json()["telefono"] == "4775550000" and r.json()["acepta_notificaciones_movil"] is True
    assert client.patch("/api/pacientes/me", headers=h, json={"telefono": "123"}).status_code == 422


def test_cambiar_correo_requiere_contrasena_y_unicidad(client, datos):
    h = registrar_y_login(client)
    registrar_y_login(client, "ocupado@correo.com", "4779998888")
    assert client.patch("/api/pacientes/me", headers=h, json={"correo": "nuevo@correo.com"}).status_code == 400
    assert client.patch("/api/pacientes/me", headers=h, json={"correo": "nuevo@correo.com", "contrasena_actual": "Mala1234"}).status_code == 400
    assert client.patch("/api/pacientes/me", headers=h, json={"correo": "OCUPADO@correo.com", "contrasena_actual": "Segura123"}).status_code == 409
    ok = client.patch("/api/pacientes/me", headers=h, json={"correo": "Nuevo@Correo.com", "contrasena_actual": "Segura123"})
    assert ok.status_code == 200 and ok.json()["correo"] == "nuevo@correo.com"
    assert client.post("/api/auth/login", json={"correo": "nuevo@correo.com", "contrasena": "Segura123"}).status_code == 200


def test_control_de_acceso_por_rol(client, datos):
    from app.models import RolUsuario, Usuario
    registrar_y_login(client)
    with client.session_factory() as db:
        db.scalar(select(Usuario)).rol = RolUsuario.RECEPCION
        db.commit()
    t = client.post("/api/auth/login", json={"correo": "paciente@correo.com", "contrasena": "Segura123"}).json()["access_token"]
    h = {"Authorization": f"Bearer {t}"}
    assert client.get("/api/disponibilidad", params={"fecha": LUNES.isoformat(), "especialidad_id": datos["esp_id"]}, headers=h).status_code == 200   # recepción sí consulta
    assert client.post("/api/citas", headers=h, json={"medico_id": 1, "especialidad_id": 1, "inicio": "2030-01-01T09:00:00"}).status_code == 403
    assert client.get("/api/pacientes/me", headers=h).status_code == 403
    assert client.get("/api/especialidades", headers=h).status_code == 200


def test_catalogo(client, datos):
    h = registrar_y_login(client)
    esp = client.get("/api/especialidades", headers=h).json()
    assert [e["nombre"] for e in esp] == ["Cardiología"]       # Dermatología no tiene médicos activos
    med = client.get(f"/api/medicos?especialidad_id={datos['esp_id']}", headers=h).json()
    assert [m["nombre_completo"] for m in med] == ["Dr. Vargas"]
