from pathlib import Path
from secrets import token_hex

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine

from app.api.dependencias import obtener_busqueda_usuarios
from app.domain.usuario import Rol, Usuario
from app.infrastructure import crear_usuario, db
from app.infrastructure.seguridad import hash_password, verificar_password
from app.main import app

LOGIN = "/api/v1/auth/login"
PASSWORD = "clave de prueba"


@pytest.fixture(scope="module")
def password_hash():
    return hash_password(PASSWORD)


@pytest.fixture
def secreto(monkeypatch):
    clave = token_hex(32)
    monkeypatch.setenv("JWT_SECRET", clave)
    return clave


@pytest.fixture
def client(secreto, password_hash, monkeypatch):
    usuarios = {
        "admin": Usuario("admin", password_hash, Rol.ADMIN),
        "operador": Usuario("operador", password_hash, Rol.OPERADOR),
    }
    monkeypatch.setitem(
        app.dependency_overrides, obtener_busqueda_usuarios, lambda: usuarios.get
    )
    with TestClient(app) as cliente:
        yield cliente


def iniciar_sesion(client, username, password=PASSWORD):
    return client.post(LOGIN, json={"username": username, "password": password})


@pytest.mark.parametrize(("username", "rol"), [("admin", "ADMIN"), ("operador", "OPERADOR")])
def test_login_devuelve_token_con_rol(client, secreto, username, rol):
    respuesta = iniciar_sesion(client, username)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["rol"] == rol
    token = jwt.decode(datos["access_token"], secreto, algorithms=["HS256"])
    assert token["sub"] == username
    assert token["rol"] == rol
    assert "exp" in token


@pytest.mark.parametrize(
    ("username", "password"),
    [("admin", "incorrecta"), ("inexistente", PASSWORD), ("admin", "ñ" * 37)],
)
def test_credenciales_invalidas(client, username, password):
    respuesta = iniciar_sesion(client, username, password)
    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "Usuario o contraseña incorrectos"}


@pytest.mark.parametrize("ruta", ["/admin/acceso", "/admin/tarifas", "/consultas/acceso"])
def test_operador_no_puede_abrir_zonas_administrativas(client, ruta):
    token = iniciar_sesion(client, "operador").json()["access_token"]
    respuesta = client.get(f"/api/v1{ruta}", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 403


@pytest.mark.parametrize("ruta", ["/admin/acceso", "/consultas/acceso"])
def test_admin_puede_abrir_administracion_y_consultas(client, ruta):
    token = iniciar_sesion(client, "admin").json()["access_token"]
    respuesta = client.get(f"/api/v1{ruta}", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 200


@pytest.mark.parametrize("exp", [1, None])
def test_rechaza_token_vencido_o_sin_expiracion(client, secreto, exp):
    datos = {"sub": "admin", "rol": "ADMIN"}
    if exp is not None:
        datos["exp"] = exp
    token = jwt.encode(datos, secreto, algorithm="HS256")
    respuesta = client.get("/api/v1/admin/acceso", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 401


def test_sin_token_devuelve_401(client):
    assert client.get("/api/v1/admin/acceso").status_code == 401


def test_crear_usuario_guarda_hash_bcrypt(tmp_path, monkeypatch):
    motor = create_engine(f"sqlite:///{tmp_path / 'pruebas.db'}")
    try:
        monkeypatch.setattr(db, "motor_db", lambda: motor)
        monkeypatch.setattr(crear_usuario, "motor_db", lambda: motor)
        config = Path(__file__).resolve().parents[1] / "alembic.ini"
        command.upgrade(Config(str(config)), "head")
        monkeypatch.setattr("sys.argv", ["crear_usuario", "admin", "ADMIN"])
        monkeypatch.setattr(crear_usuario, "getpass", lambda _: PASSWORD)

        crear_usuario.main()

        usuario = db.buscar_usuario("admin")
        assert usuario.rol == Rol.ADMIN
        assert usuario.password_hash.startswith("$2b$")
        assert verificar_password(PASSWORD, usuario.password_hash)
    finally:
        motor.dispose()
