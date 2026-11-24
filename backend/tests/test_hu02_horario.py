from datetime import datetime
from pathlib import Path
from secrets import token_hex
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api import carril
from app.application.generar_cobro import ServicioCobro
from app.application.registrar_ingreso import Decision, ValidarHorario
from app.domain.ingreso import LecturaPlaca
from app.domain.usuario import Rol, Usuario
from app.infrastructure import db, eventos
from app.infrastructure.seguridad import emitir_token
from app.main import app

BOGOTA = ZoneInfo("America/Bogota")
RUTA = "/api/v1/carril/entrada"
LECTURA = LecturaPlaca("ABC123", 0.95, 1)


def a_las(hora: int, minuto: int, segundo: int = 0) -> datetime:
    return datetime(2026, 11, 23, hora, minuto, segundo, tzinfo=BOGOTA)


@pytest.mark.parametrize(
    "momento",
    [
        a_las(4, 0),
        a_las(10, 30),
        a_las(17, 29),
        a_las(17, 30),
        a_las(23, 59, 59).replace(microsecond=999_999),
    ],
)
def test_dentro_del_horario_deja_pasar(momento):
    assert ValidarHorario()(LECTURA, momento) is None


@pytest.mark.parametrize("momento", [a_las(0, 0), a_las(2, 0), a_las(3, 59, 59)])
def test_fuera_del_horario_cierra_la_barrera(momento):
    assert ValidarHorario()(LECTURA, momento) == Decision("CERRADA", "Parqueadero cerrado")


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
    token = emitir_token(Usuario("operador", "", Rol.OPERADOR))
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as cliente:
        yield cliente


def test_ingreso_con_parqueadero_cerrado(cliente, motor, monkeypatch):
    monkeypatch.setattr(carril, "ahora_bogota", lambda: a_las(2, 0))

    def fallar_si_genera_cobro(*args):
        pytest.fail("Un ingreso fuera de horario no debe llamar al servicio de cobro")

    monkeypatch.setattr(ServicioCobro, "generar_o_reutilizar", fallar_si_genera_cobro)

    respuesta = cliente.post(RUTA, json={"placa": "ABC123", "confianza": 0.95, "sede_id": 1})

    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert (datos["barrera"], datos["motivo"]) == ("CERRADA", "Parqueadero cerrado")
    assert "cobro" not in datos
    with Session(motor) as sesion:
        evento, = sesion.scalars(select(db.EventoDB)).all()
    assert (evento.barrera, evento.motivo) == ("CERRADA", "Parqueadero cerrado")


def test_horario_se_revisa_antes_que_la_confianza(cliente, monkeypatch):
    monkeypatch.setattr(carril, "ahora_bogota", lambda: a_las(3, 0))

    respuesta = cliente.post(RUTA, json={"placa": "ABC123", "confianza": 0.10, "sede_id": 1})

    assert respuesta.json()["barrera"] == "CERRADA"


def test_demo_carril_carga(cliente):
    respuesta = cliente.get("/demo/carril")
    assert respuesta.status_code == 200
    assert "Carril de entrada" in respuesta.text
