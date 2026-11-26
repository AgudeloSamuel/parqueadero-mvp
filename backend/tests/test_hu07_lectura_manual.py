from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from secrets import token_hex
from threading import Barrier
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api import carril
from app.domain.usuario import Rol, Usuario
from app.infrastructure import db, lectores
from app.infrastructure.seguridad import emitir_token
from app.main import app

RUTA = "/api/v1/carril"
BOGOTA = ZoneInfo("America/Bogota")
AHORA = datetime(2026, 11, 26, 10, tzinfo=BOGOTA)


@pytest.fixture
def motor(tmp_path, monkeypatch):
    motor = create_engine(f"sqlite:///{tmp_path / 'hu07.db'}")
    monkeypatch.setattr(db, "motor_db", lambda: motor)
    try:
        config = Path(__file__).resolve().parents[1] / "alembic.ini"
        command.upgrade(Config(str(config)), "head")
        yield motor
    finally:
        motor.dispose()


@pytest.fixture
def cliente(monkeypatch, motor):
    monkeypatch.setenv("JWT_SECRET", token_hex(32))
    monkeypatch.delenv("UMBRAL_CONFIANZA", raising=False)
    monkeypatch.setattr(carril, "ahora_bogota", lambda: AHORA)
    token = emitir_token(Usuario("operador_turno", "", Rol.OPERADOR))
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as cliente:
        yield cliente


def ingresar(cliente, confianza=0.60, placa="ABC123", sede_id=1):
    respuesta = cliente.post(
        f"{RUTA}/entrada", json={"placa": placa, "confianza": confianza, "sede_id": sede_id}
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def validar(cliente, evento_id, placa, headers=None):
    return cliente.post(
        f"{RUTA}/eventos/{evento_id}/validar", json={"placa": placa}, headers=headers
    )


def test_confirma_lectura_baja_y_registra_al_operador_del_token(cliente, motor, monkeypatch):
    pendiente = ingresar(cliente)
    assert pendiente["barrera"] == "PENDIENTE_VALIDACION"
    assert pendiente["lectura_manual"] is False
    assert "cobro" not in pendiente
    assert cliente.get(f"{RUTA}/pendientes?sede_id=2").json() == []
    lecturas = cliente.get(f"{RUTA}/pendientes?sede_id=1").json()
    assert [(l["evento_id"], l["placa"], l["confianza"]) for l in lecturas] == [
        (pendiente["evento_id"], "ABC123", 0.60)
    ]

    momento_validacion = AHORA.replace(hour=11)
    monkeypatch.setattr(carril, "ahora_bogota", lambda: momento_validacion)
    respuesta = validar(cliente, pendiente["evento_id"], "ABC123")
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert (datos["evento_id"], datos["barrera"], datos["confianza"]) == (
        pendiente["evento_id"], "ABIERTA", 0.60
    )
    assert datos["lectura_manual"] is True
    assert datos["validada_por"] == "operador_turno"
    assert datos["validada_en"] == momento_validacion.isoformat()
    assert datos["cobro"]["valor"] == 3850
    assert cliente.get(f"{RUTA}/pendientes").json() == []

    with Session(motor) as sesion:
        evento, = sesion.scalars(select(db.EventoDB)).all()
        assert evento.lectura_manual and evento.validada_por == "operador_turno"
        assert (evento.fecha_hora.hour, evento.validada_en.hour) == (10, 11)
    assert cliente.get(f"{RUTA}/cupos?sede_id=1").json()[0]["ocupados"] == 1


def test_corrige_placa_e_identifica_tipo_definitivo(cliente, motor):
    pendiente = ingresar(cliente)
    respuesta = validar(cliente, pendiente["evento_id"], " abc-12a ")
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert (datos["placa_leida"], datos["placa"], datos["tipo_vehiculo"]) == ("ABC123", "ABC12A", "MOTO")
    assert datos["cobro"] is None
    with Session(motor) as sesion:
        evento = sesion.get(db.EventoDB, pendiente["evento_id"])
        assert (evento.placa_leida, evento.placa) == ("ABC123", "ABC12A")


def test_placa_invalida_se_rechaza_y_mantiene_el_evento_pendiente(cliente, motor):
    pendiente = ingresar(cliente)
    respuesta = validar(cliente, pendiente["evento_id"], "AB-12")
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == "Formato de placa inválido"
    with Session(motor) as sesion:
        evento = sesion.get(db.EventoDB, pendiente["evento_id"])
        assert evento.barrera == "PENDIENTE_VALIDACION"
        assert not evento.lectura_manual and evento.validada_por is None
        assert sesion.scalar(select(db.CobroDB)) is None


def test_respeta_umbral_por_defecto_y_configurado(cliente, monkeypatch):
    assert ingresar(cliente, confianza=0.80)["barrera"] == "ABIERTA"
    monkeypatch.setenv("UMBRAL_CONFIANZA", "0.90")
    assert ingresar(cliente, confianza=0.89, placa="ABC124")["barrera"] == "PENDIENTE_VALIDACION"
    assert ingresar(cliente, confianza=0.90, placa="ABC125")["barrera"] == "ABIERTA"


def test_permiso_y_evento_inexistente_o_ya_validado(cliente):
    pendiente = ingresar(cliente)
    token_admin = emitir_token(Usuario("admin", "", Rol.ADMIN))
    assert validar(
        cliente, pendiente["evento_id"], "ABC123", {"Authorization": f"Bearer {token_admin}"}
    ).status_code == 403
    assert validar(cliente, 9999, "ABC123").status_code == 404
    assert validar(cliente, pendiente["evento_id"], "ABC123").status_code == 200
    assert validar(cliente, pendiente["evento_id"], "ABC124").status_code == 409


def test_confirmaciones_simultaneas_resuelven_el_evento_una_vez(cliente, motor):
    pendiente = ingresar(cliente)
    inicio = Barrier(2)

    def confirmar(placa):
        inicio.wait(timeout=5)
        return validar(cliente, pendiente["evento_id"], placa).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(confirmar, ["ABC123", "ABC124"])) == [200, 409]
    with Session(motor) as sesion:
        assert len(sesion.scalars(select(db.CobroDB)).all()) == 1


def test_confirma_lectura_sin_placa_proveniente_del_ocr(cliente, monkeypatch):
    monkeypatch.setenv("LECTOR_PLACAS", "camara")
    monkeypatch.setattr(
        lectores.LectorOCR, "leer", lambda self, imagen, sede_id: carril.LecturaPlaca(None, 0, sede_id)
    )
    respuesta = cliente.post(
        f"{RUTA}/entrada/imagen",
        data={"sede_id": 1},
        files={"imagen": ("foto.png", b"foto de prueba", "image/png")},
    )
    pendiente = respuesta.json()
    assert respuesta.status_code == 201 and pendiente["placa"] is None
    manual = validar(cliente, pendiente["evento_id"], "ABC12A").json()
    assert (manual["placa"], manual["barrera"], manual["lectura_manual"]) == ("ABC12A", "ABIERTA", True)


def test_revisa_el_cupo_antes_de_abrir_una_lectura_validada(cliente, motor):
    with Session(motor) as sesion, sesion.begin():
        sesion.get(db.CupoDB, "CARRO").capacidad = 0
    pendiente = ingresar(cliente)
    respuesta = validar(cliente, pendiente["evento_id"], "ABC123")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["lectura_manual"] is True and datos["barrera"] == "LLENO"
    assert datos["cobro"] is None


def test_el_cupo_cuenta_la_hora_de_validacion_y_no_la_de_lectura(cliente, monkeypatch):
    inicial = ingresar(cliente, confianza=0.95)
    assert cliente.post(
        f"/api/v1/cobros/{inicial['cobro']['id']}/pagos",
        headers={"Idempotency-Key": "pago-hu07-01"},
    ).status_code == 201
    monkeypatch.setattr(carril, "ahora_bogota", lambda: AHORA.replace(hour=11))
    pendiente = ingresar(cliente)
    monkeypatch.setattr(carril, "ahora_bogota", lambda: AHORA.replace(hour=12))
    salida = cliente.post(f"{RUTA}/salida", json={"placa": "ABC123", "sede_id": 1})
    assert salida.json()["barrera"] == "ABIERTA"
    assert cliente.get(f"{RUTA}/cupos?sede_id=1").json()[0]["ocupados"] == 0
    monkeypatch.setattr(carril, "ahora_bogota", lambda: AHORA.replace(hour=13))

    respuesta = validar(cliente, pendiente["evento_id"], "ABC123")

    assert respuesta.json()["barrera"] == "ABIERTA"
    assert respuesta.json()["cobro"]["id"] == inicial["cobro"]["id"]
    assert cliente.get(f"{RUTA}/cupos?sede_id=1").json()[0]["ocupados"] == 1
