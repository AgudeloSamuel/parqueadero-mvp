from datetime import datetime
from importlib.util import find_spec
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
from app.infrastructure import db, eventos, lectores
from app.infrastructure.seguridad import emitir_token
from app.main import app

RUTA = "/api/v1/carril/entrada/imagen"
BOGOTA = ZoneInfo("America/Bogota")


@pytest.fixture
def motor(tmp_path, monkeypatch):
    motor = create_engine(f"sqlite:///{tmp_path / 'camara.db'}")
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
    monkeypatch.setenv("LECTOR_PLACAS", "camara")
    monkeypatch.setattr(carril, "ahora_bogota", lambda: datetime(2026, 11, 25, 10, tzinfo=BOGOTA))
    token = emitir_token(Usuario("operador", "", Rol.OPERADOR))
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as cliente:
        yield cliente


def capturar(cliente, texto=None):
    imagen = Image.new("RGB", (520, 160), "white")
    if texto:
        ImageDraw.Draw(imagen).text(
            (42, 35), texto, fill="black", font=ImageFont.load_default(size=90)
        )
    contenido = BytesIO()
    imagen.save(contenido, format="PNG")
    return cliente.post(
        RUTA, data={"sede_id": 3}, files={"imagen": ("captura.png", contenido.getvalue(), "image/png")}
    )


def configurar_easyocr(monkeypatch, *lecturas):
    class MotorOCRDePrueba:
        def readtext(self, imagen, **opciones):
            assert imagen.startswith(b"\x89PNG")
            return [(None, texto, confianza) for texto, confianza in lecturas]

    monkeypatch.setattr(lectores, "motor_easyocr", MotorOCRDePrueba)


def comprobar_evento(motor, datos, placa, barrera, numero_cobros):
    with Session(motor) as sesion:
        evento, = sesion.scalars(select(db.EventoDB)).all()
        cobros = sesion.scalars(select(db.CobroDB)).all()
        assert (evento.id, evento.tipo, evento.placa, evento.barrera) == (
            datos["evento_id"], "ENTRADA", placa, barrera
        )
        assert (evento.sede_id, evento.confianza, evento.tipo_vehiculo, evento.motivo) == (
            3, datos["confianza"], datos["tipo_vehiculo"], datos["motivo"]
        )
        assert len(cobros) == numero_cobros


def test_foto_normaliza_placa_y_continua_con_hu02(cliente, motor, monkeypatch):
    configurar_easyocr(monkeypatch, ("AB-12", 0.99), (" abc-123 ", 0.95))
    respuesta = capturar(cliente, "ABC123")
    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert (datos["placa"], datos["tipo_vehiculo"], datos["confianza"]) == ("ABC123", "CARRO", 0.95)
    assert datos["cobro"]["valor"] == 3850
    comprobar_evento(motor, datos, "ABC123", "ABIERTA", 1)


@pytest.mark.parametrize("lecturas", [(), (("AB-12", 0.99),)])
def test_foto_sin_placa_valida_queda_pendiente(cliente, motor, monkeypatch, lecturas):
    configurar_easyocr(monkeypatch, *lecturas)
    monkeypatch.setenv("UMBRAL_CONFIANZA", "0")
    respuesta = capturar(cliente)
    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert datos["placa"] is None and datos["tipo_vehiculo"] is None
    assert datos["confianza"] == 0
    assert datos["motivo"] == "No se encontró una placa válida en la imagen"
    comprobar_evento(motor, datos, None, "PENDIENTE_VALIDACION", 0)


def test_lectura_con_confianza_baja_queda_pendiente(cliente, motor, monkeypatch):
    configurar_easyocr(monkeypatch, ("ABC12A", 0.79))
    respuesta = capturar(cliente, "ABC12A")
    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert (datos["confianza"], datos["tipo_vehiculo"]) == (0.79, "MOTO")
    comprobar_evento(motor, datos, "ABC12A", "PENDIENTE_VALIDACION", 0)


def test_fuera_de_horario_tiene_prioridad_incluso_sin_placa(cliente, motor, monkeypatch):
    configurar_easyocr(monkeypatch)
    monkeypatch.setattr(carril, "ahora_bogota", lambda: datetime(2026, 11, 25, 2, tzinfo=BOGOTA))
    respuesta = capturar(cliente)
    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert datos["motivo"] == "Parqueadero cerrado"
    comprobar_evento(motor, datos, None, "CERRADA", 0)


def test_modo_simulador_desactiva_la_camara_y_conserva_la_api_json(cliente, motor, monkeypatch):
    monkeypatch.setenv("LECTOR_PLACAS", "simulador")
    assert isinstance(lectores.FabricaLector.crear(), lectores.LectorSimulado)
    assert capturar(cliente, "ABC123").status_code == 409
    respuesta = cliente.post(
        "/api/v1/carril/entrada", json={"placa": "ABC123", "sede_id": 3, "confianza": 0.95}
    )
    assert respuesta.status_code == 201, respuesta.text
    comprobar_evento(motor, respuesta.json(), "ABC123", "ABIERTA", 1)


@pytest.mark.skipif(find_spec("easyocr") is None, reason="EasyOCR se instala en Docker")
@pytest.mark.parametrize("texto", ["ABC123", None], ids=["placa", "sin-placa"])
def test_easyocr_real(cliente, motor, texto):
    respuesta = capturar(cliente, texto)
    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    if texto is None:
        assert datos["placa"] is None
        comprobar_evento(motor, datos, None, "PENDIENTE_VALIDACION", 0)
    else:
        assert (datos["placa"], datos["tipo_vehiculo"]) == ("ABC123", "CARRO")
        assert 0.80 < datos["confianza"] <= 1
        comprobar_evento(motor, datos, "ABC123", "ABIERTA", 1)
