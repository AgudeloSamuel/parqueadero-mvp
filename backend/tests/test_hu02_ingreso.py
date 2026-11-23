import shutil
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from secrets import token_hex
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api import carril
from app.domain.usuario import Rol, Usuario
from app.infrastructure import db, eventos
from app.infrastructure.seguridad import emitir_token
from app.main import app

RUTA = "/api/v1/carril/entrada"
ENTRADA = {"placa": "ABC123", "confianza": 0.95, "sede_id": 1}
HORA_ABIERTO = datetime(2026, 11, 23, 10, 0, tzinfo=ZoneInfo("America/Bogota"))


@pytest.fixture
def motor(tmp_path, monkeypatch):
    motor = create_engine(f"sqlite:///{tmp_path / 'eventos.db'}")
    monkeypatch.setattr(db, "motor_db", lambda: motor)
    monkeypatch.setattr(eventos, "motor_db", lambda: motor)
    try:
        config = Path(__file__).resolve().parents[1] / "alembic.ini"
        command.upgrade(Config(str(config)), "head")
        yield motor
    finally:
        motor.dispose()


@pytest.fixture
def cliente(monkeypatch, motor):
    monkeypatch.setenv("JWT_SECRET", token_hex(32))
    monkeypatch.setenv("UMBRAL_CONFIANZA", "0.80")
    monkeypatch.setattr(carril, "ahora_bogota", lambda: HORA_ABIERTO)
    token = emitir_token(Usuario("operador", "", Rol.OPERADOR))
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as cliente:
        yield cliente


def filas_eventos(motor):
    with Session(motor) as sesion:
        return sesion.scalars(select(db.EventoDB)).all()


@pytest.mark.parametrize(
    ("placa", "normalizada", "tipo"),
    [
        ("ABC123", "ABC123", "CARRO"),
        (" aBc - 123 ", "ABC123", "CARRO"),
        ("xyz-12a", "XYZ12A", "MOTO"),
    ],
)
def test_registra_entrada_y_abre_barrera(cliente, motor, placa, normalizada, tipo):
    respuesta = cliente.post(RUTA, json={**ENTRADA, "placa": placa})

    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert datos["barrera"] == "ABIERTA"
    assert datos["tipo_evento"] == "ENTRADA"
    assert datos["tipo_vehiculo"] == tipo
    assert datos["placa"] == normalizada
    fecha_hora = datetime.fromisoformat(datos["fecha_hora"])
    assert fecha_hora.utcoffset() == timedelta(hours=-5)
    evento, = filas_eventos(motor)
    assert evento.id == datos["evento_id"]
    assert (evento.tipo, evento.placa, evento.confianza, evento.sede_id) == (
        "ENTRADA", normalizada, 0.95, 1
    )
    assert evento.fecha_hora is not None


def test_placa_invalida_no_crea_evento(cliente, motor):
    respuesta = cliente.post(RUTA, json={**ENTRADA, "placa": "AB-12"})
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detail": "Formato de placa inválido"}
    assert filas_eventos(motor) == []


@pytest.mark.parametrize("confianza", [-0.01, 1.01])
def test_confianza_fuera_de_rango_no_crea_evento(cliente, motor, confianza):
    respuesta = cliente.post(RUTA, json={**ENTRADA, "confianza": confianza})
    assert respuesta.status_code == 422
    assert filas_eventos(motor) == []


@pytest.mark.parametrize(
    ("confianza", "barrera"), [(0, "PENDIENTE_VALIDACION"), (0.80, "ABIERTA"), (1, "ABIERTA")]
)
def test_umbrales_de_confianza(cliente, motor, confianza, barrera):
    respuesta = cliente.post(RUTA, json={**ENTRADA, "confianza": confianza})
    assert respuesta.status_code == 201
    assert respuesta.json()["barrera"] == barrera
    evento, = filas_eventos(motor)
    assert (evento.confianza, evento.barrera) == (confianza, barrera)


def test_carril_exige_token_de_operador(cliente, motor):
    with TestClient(app) as anonimo:
        assert anonimo.post(RUTA, json=ENTRADA).status_code == 401
    token = emitir_token(Usuario("admin", "", Rol.ADMIN))
    respuesta = cliente.post(RUTA, json=ENTRADA, headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 403
    assert filas_eventos(motor) == []


def test_imagen_invalida_no_crea_evento(cliente, motor):
    respuesta = cliente.post(
        f"{RUTA}/imagen",
        data={"sede_id": 1},
        files={"imagen": ("placa.png", b"imagen invalida", "image/png")},
    )
    assert respuesta.status_code == 422
    assert filas_eventos(motor) == []


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract se instala en Docker")
def test_lee_placa_desde_imagen_y_guarda_confianza(cliente, motor):
    imagen = Image.new("RGB", (520, 150), "white")
    ImageDraw.Draw(imagen).text(
        (35, 30), "ABC123", fill="black", font=ImageFont.load_default(size=80)
    )
    contenido = BytesIO()
    imagen.save(contenido, format="PNG")

    respuesta = cliente.post(
        f"{RUTA}/imagen",
        data={"sede_id": 3},
        files={"imagen": ("foto.png", contenido.getvalue(), "image/png")},
    )

    assert respuesta.status_code == 201, respuesta.text
    lectura = respuesta.json()
    assert lectura["placa"] == "ABC123"
    assert 0 <= lectura["confianza"] <= 1
    evento, = filas_eventos(motor)
    assert (evento.placa, evento.sede_id, evento.confianza) == ("ABC123", 3, lectura["confianza"])
