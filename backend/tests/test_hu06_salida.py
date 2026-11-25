from datetime import datetime
from pathlib import Path
from secrets import token_hex
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api import carril
from app.domain.usuario import Rol, Usuario
from app.infrastructure import db, eventos
from app.infrastructure.entradas import ultima_entrada_sin_salida
from app.infrastructure.seguridad import emitir_token
from app.main import app

ENTRADA = "/api/v1/carril/entrada"
SALIDA = "/api/v1/carril/salida"
BOGOTA = ZoneInfo("America/Bogota")


@pytest.fixture
def motor(tmp_path, monkeypatch):
    motor = create_engine(f"sqlite:///{tmp_path / 'salidas.db'}")
    monkeypatch.setattr(db, "motor_db", lambda: motor)
    monkeypatch.setattr(eventos, "motor_db", lambda: motor)
    try:
        config = Path(__file__).resolve().parents[1] / "alembic.ini"
        command.upgrade(Config(str(config)), "head")
        yield motor
    finally:
        motor.dispose()


@pytest.fixture
def fijar_hora(monkeypatch):
    def fijar(dia, hora):
        momento = datetime(2026, 11, dia, hora, tzinfo=BOGOTA)
        monkeypatch.setattr(carril, "ahora_bogota", lambda: momento)

    fijar(25, 10)
    return fijar


@pytest.fixture
def cliente(monkeypatch, motor, fijar_hora):
    monkeypatch.setenv("JWT_SECRET", token_hex(32))
    token = emitir_token(Usuario("operador", "", Rol.OPERADOR))
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as cliente:
        yield cliente


def entrar(cliente, placa="ABC123"):
    respuesta = cliente.post(ENTRADA, json={"placa": placa, "sede_id": 1, "confianza": 0.95})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json().get("cobro")


def pagar(cliente, cobro_id):
    respuesta = cliente.post(
        f"/api/v1/cobros/{cobro_id}/pagos",
        headers={"Idempotency-Key": "pago-hu06-01"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def comprobar_salida(cliente, motor, placa, barrera, motivo):
    respuesta = cliente.post(SALIDA, json={"placa": placa, "sede_id": 1})
    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert (datos["tipo_evento"], datos["barrera"], datos["motivo"]) == (
        "SALIDA", barrera, motivo
    )
    with Session(motor) as sesion:
        evento = sesion.get(db.EventoDB, datos["evento_id"])
        assert (evento.tipo, evento.barrera, evento.motivo) == ("SALIDA", barrera, motivo)
        assert (evento.placa, evento.sede_id) == (datos["placa"], 1)
        assert evento.fecha_hora is not None
    return datos


def test_cobro_pagado_abre_y_permite_reingreso_sin_otro_cobro(cliente, motor, fijar_hora):
    cobro = entrar(cliente)
    pago = pagar(cliente, cobro["id"])
    assert pago["pase_hasta"].startswith("2026-11-25T23:59:59")
    fijar_hora(25, 11)
    salida = comprobar_salida(cliente, motor, " abc-123 ", "ABIERTA", "Pago verificado")
    assert salida["placa"] == "ABC123"
    assert ultima_entrada_sin_salida("ABC123", 1) is None
    fijar_hora(25, 19)
    reingreso = entrar(cliente)
    assert (reingreso["id"], reingreso["valor"], reingreso["estado"]) == (
        cobro["id"], 3850, "PAGADO"
    )
    with Session(motor) as sesion:
        assert sesion.scalar(select(func.count()).select_from(db.CobroDB)) == 1


def test_moto_sin_cobro_abre(cliente, motor):
    assert entrar(cliente, "ABC12D") is None
    comprobar_salida(cliente, motor, "ABC12D", "ABIERTA", "Sin cobro")
    assert ultima_entrada_sin_salida("ABC12D", 1) is None


def test_pendiente_bloquea_incluso_si_se_reintenta_despues_de_medianoche(
    cliente, motor, fijar_hora
):
    entrar(cliente)
    fijar_hora(26, 1)
    for _ in range(2):
        comprobar_salida(cliente, motor, "ABC123", "CERRADA", "Pago pendiente: $3.850")
    assert ultima_entrada_sin_salida("ABC123", 1).date().isoformat() == "2026-11-25"


def test_pagado_el_dia_de_ingreso_puede_salir_despues_de_medianoche(cliente, motor, fijar_hora):
    cobro = entrar(cliente)
    pagar(cliente, cobro["id"])
    fijar_hora(26, 1)
    comprobar_salida(cliente, motor, "ABC123", "ABIERTA", "Pago verificado")


def test_cobro_anulado_no_abre(cliente, motor):
    cobro = entrar(cliente)
    with Session(motor) as sesion, sesion.begin():
        sesion.get(db.CobroDB, cobro["id"]).estado = "ANULADO"
    comprobar_salida(cliente, motor, "ABC123", "CERRADA", "Cobro anulado")


def test_formato_invalido_no_registra_movimiento(cliente, motor):
    respuesta = cliente.post(SALIDA, json={"placa": "AB-12", "sede_id": 1})
    assert respuesta.status_code == 422
    with Session(motor) as sesion:
        assert sesion.scalar(select(func.count()).select_from(db.EventoDB)) == 0
