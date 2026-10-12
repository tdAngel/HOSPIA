from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import Bitacora, PasswordResetToken, Usuario, utcnow

VALIDO = {
    "nombre_completo": "Ana María Pérez López", "fecha_nacimiento": "1992-04-10",
    "correo": "Ana.Perez@Correo.com", "telefono": "477 123 4567", "contrasena": "Segura123",
    "acepta_aviso_privacidad": True, "acepta_notificaciones_movil": True,
}


def registrar(client, **cambios):
    return client.post("/api/auth/registro", json={**VALIDO, **cambios})


def login(client, correo="ana.perez@correo.com", contrasena="Segura123"):
    return client.post("/api/auth/login", json={"correo": correo, "contrasena": contrasena})


# ---------------- RF-001
def test_registro_exitoso_normaliza_y_cifra(client):
    r = registrar(client)
    assert r.status_code == 201
    assert r.json()["correo"] == "ana.perez@correo.com" and r.json()["rol"] == "paciente"
    with client.session_factory() as db:
        u = db.scalar(select(Usuario))
        assert u.password_hash.startswith("$2") and "Segura123" not in u.password_hash   # RNF-005
        assert u.paciente.telefono == "4771234567"
        assert u.paciente.acepta_aviso_privacidad and u.paciente.version_aviso               # RD-001
        assert db.scalar(select(Bitacora).where(Bitacora.accion == "registro_paciente"))      # RNF-008


def test_correo_unico(client):
    assert registrar(client).status_code == 201
    r = registrar(client, correo="ANA.PEREZ@correo.com")
    assert r.status_code == 409


def test_aviso_privacidad_obligatorio(client):
    r = registrar(client, acepta_aviso_privacidad=False)
    assert r.status_code == 422 and "acepta_aviso_privacidad" in r.json()["errores"]


@pytest.mark.parametrize("campo,valor", [
    ("contrasena", "corta1A"), ("contrasena", "sinmayusculas1"), ("contrasena", "SinNumeros"),
    ("telefono", "12345"), ("correo", "no-es-correo"), ("nombre_completo", "Ana"),
    ("fecha_nacimiento", "2999-01-01"), ("fecha_nacimiento", "no-fecha"),
])
def test_validaciones_registro(client, campo, valor):
    r = registrar(client, **{campo: valor})
    assert r.status_code == 422 and campo in r.json()["errores"]


def test_campos_obligatorios(client):
    r = client.post("/api/auth/registro", json={})
    assert r.status_code == 422 and "correo" in r.json()["errores"]


# ---------------- RF-002
def test_login_y_me(client):
    registrar(client)
    r = login(client)
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["nombre_completo"] == "Ana María Pérez López"
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_login_credenciales_incorrectas_mensaje_generico(client):
    registrar(client)
    a = login(client, contrasena="Incorrecta1")
    b = login(client, correo="noexiste@correo.com")
    assert a.status_code == b.status_code == 401 and a.json()["detail"] == b.json()["detail"]


def test_bloqueo_por_intentos_fallidos(client):
    registrar(client)
    for _ in range(5):
        assert login(client, contrasena="Incorrecta1").status_code == 401
    assert login(client).status_code == 429          # aun con la contraseña correcta
    with client.session_factory() as db:
        u = db.scalar(select(Usuario))
        u.bloqueado_hasta = utcnow() - timedelta(seconds=1)
        db.commit()
    assert login(client).status_code == 200


def test_cuenta_inactiva(client):
    registrar(client)
    with client.session_factory() as db:
        db.scalar(select(Usuario)).activo = False
        db.commit()
    assert login(client).status_code == 403


def test_flujo_restablecer_contrasena(client, monkeypatch):
    registrar(client)
    enlaces = []
    monkeypatch.setattr("app.routers.auth.enviar_restablecimiento", lambda d, n, e: enlaces.append(e))

    r = client.post("/api/auth/olvide-contrasena", json={"correo": "ana.perez@correo.com"})
    r2 = client.post("/api/auth/olvide-contrasena", json={"correo": "nadie@correo.com"})
    assert r.status_code == r2.status_code == 200 and r.json() == r2.json()   # sin enumeración
    assert len(enlaces) == 1
    token = enlaces[0].split("token=")[1]

    assert client.post("/api/auth/restablecer-contrasena",
                       json={"token": token, "nueva_contrasena": "debil"}).status_code == 422
    ok = client.post("/api/auth/restablecer-contrasena", json={"token": token, "nueva_contrasena": "NuevaClave9"})
    assert ok.status_code == 200
    assert login(client).status_code == 401 and login(client, contrasena="NuevaClave9").status_code == 200
    # un solo uso
    assert client.post("/api/auth/restablecer-contrasena",
                       json={"token": token, "nueva_contrasena": "OtraClave99"}).status_code == 400


def test_token_expirado_o_invalido(client, monkeypatch):
    registrar(client)
    enlaces = []
    monkeypatch.setattr("app.routers.auth.enviar_restablecimiento", lambda d, n, e: enlaces.append(e))
    client.post("/api/auth/olvide-contrasena", json={"correo": "ana.perez@correo.com"})
    token = enlaces[0].split("token=")[1]
    with client.session_factory() as db:
        t = db.scalar(select(PasswordResetToken))
        t.expira_en = utcnow() - timedelta(minutes=1)
        db.commit()
    assert client.post("/api/auth/restablecer-contrasena",
                       json={"token": token, "nueva_contrasena": "NuevaClave9"}).status_code == 400
    assert client.post("/api/auth/restablecer-contrasena",
                       json={"token": "inventado", "nueva_contrasena": "NuevaClave9"}).status_code == 400


def test_nuevo_enlace_invalida_el_anterior(client, monkeypatch):
    registrar(client)
    enlaces = []
    monkeypatch.setattr("app.routers.auth.enviar_restablecimiento", lambda d, n, e: enlaces.append(e))
    for _ in range(2):
        client.post("/api/auth/olvide-contrasena", json={"correo": "ana.perez@correo.com"})
    viejo, nuevo = (e.split("token=")[1] for e in enlaces)
    assert client.post("/api/auth/restablecer-contrasena",
                       json={"token": viejo, "nueva_contrasena": "NuevaClave9"}).status_code == 400
    assert client.post("/api/auth/restablecer-contrasena",
                       json={"token": nuevo, "nueva_contrasena": "NuevaClave9"}).status_code == 200
