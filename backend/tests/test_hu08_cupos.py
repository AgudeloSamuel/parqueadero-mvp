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
from app.infrastructure import db
from app.infrastructure.seguridad import emitir_token
from app.main import app

RUTA = "/api/v1/carril"
AHORA = datetime(2026, 11, 25, 10, tzinfo=ZoneInfo("America/Bogota"))


@pytest.fixture
def motor(tmp_path, monkeypatch):
    motor = create_engine(f"sqlite:///{tmp_path / 'cupos.db'}")
    monkeypatch.setattr(db, "motor_db", lambda: motor)
    try:
        config = Path(__file__).resolve().parents[1] / "alembic.ini"
        command.upgrade(Config(str(config)), "0005_lectura_sin_placa")
        # Los movimientos existentes también deben contar después de actualizar la base.
        with Session(motor) as sesion, sesion.begin():
            sesion.add_all([
                db.EventoDB(
                    tipo="ENTRADA", placa=f"ABC{indice:03}", confianza=0.95, sede_id=1,
                    fecha_hora=AHORA, tipo_vehiculo="CARRO", barrera="ABIERTA",
                    motivo="Ingreso registrado",
                )
                for indice in range(9)
            ])
        command.upgrade(Config(str(config)), "head")
        yield motor
    finally:
        motor.dispose()


@pytest.fixture
def cliente(monkeypatch, motor):
    monkeypatch.setenv("JWT_SECRET", token_hex(32))
    monkeypatch.setenv("UMBRAL_CONFIANZA", "0.80")
    monkeypatch.setattr(carril, "ahora_bogota", lambda: AHORA)
    token = emitir_token(Usuario("operador", "", Rol.OPERADOR))
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as cliente:
        yield cliente


def ingresar(cliente, placa, sede=1, confianza=0.95):
    respuesta = cliente.post(
        f"{RUTA}/entrada", json={"placa": placa, "sede_id": sede, "confianza": confianza}
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def salir(cliente, placa):
    respuesta = cliente.post(f"{RUTA}/salida", json={"placa": placa, "sede_id": 1})
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def cupos(cliente, sede=1):
    respuesta = cliente.get(f"{RUTA}/cupos", params={"sede_id": sede})
    assert respuesta.status_code == 200, respuesta.text
    return {
        fila["tipo_vehiculo"]: (fila["capacidad"], fila["ocupados"], fila["disponibles"])
        for fila in respuesta.json()
    }


def test_nueve_de_diez_permite_entrada(cliente):
    assert cupos(cliente)["CARRO"] == (10, 9, 1)
    assert ingresar(cliente, "ABC009")["barrera"] == "ABIERTA"
    assert cupos(cliente)["CARRO"] == (10, 10, 0)


def test_diez_de_diez_devuelve_lleno_sin_cobrar(cliente, motor):
    ingresar(cliente, "ABC009")
    lleno = ingresar(cliente, "ABC010")
    assert lleno["barrera"] == "LLENO"
    assert "cobro" not in lleno
    assert cupos(cliente)["CARRO"] == (10, 10, 0)
    with Session(motor) as sesion:
        assert sesion.get(db.EventoDB, lleno["evento_id"]).barrera == "LLENO"
        assert sesion.scalar(select(db.CobroDB).where(db.CobroDB.placa == "ABC010")) is None


def test_tipos_y_sedes_tienen_ocupacion_independiente(cliente):
    ingresar(cliente, "ABC009")
    assert ingresar(cliente, "ABC12A")["barrera"] == "ABIERTA"
    assert cupos(cliente) == {"CARRO": (10, 10, 0), "MOTO": (10, 1, 9)}
    assert ingresar(cliente, "ABC010", sede=2)["barrera"] == "ABIERTA"
    assert cupos(cliente, sede=2) == {"CARRO": (10, 1, 9), "MOTO": (10, 0, 10)}


def test_salida_efectiva_libera_un_cupo_y_repetirla_no_libera_otro(cliente):
    lleno = ingresar(cliente, "ABC009")
    assert salir(cliente, "ABC009")["barrera"] == "CERRADA"
    assert cupos(cliente)["CARRO"] == (10, 10, 0)
    pago = cliente.post(
        f"/api/v1/cobros/{lleno['cobro']['id']}/pagos",
        headers={"Idempotency-Key": "pago-cupo-01"},
    )
    assert pago.status_code == 201, pago.text
    assert salir(cliente, "ABC009")["barrera"] == "ABIERTA"
    assert cupos(cliente)["CARRO"] == (10, 9, 1)
    assert salir(cliente, "ABC009")["barrera"] == "ABIERTA"
    assert cupos(cliente)["CARRO"] == (10, 9, 1)
    assert ingresar(cliente, "ABC010")["barrera"] == "ABIERTA"


def test_lectura_pendiente_no_ocupa_cupo(cliente):
    assert ingresar(cliente, "ABC009", confianza=0.50)["barrera"] == "PENDIENTE_VALIDACION"
    assert cupos(cliente)["CARRO"] == (10, 9, 1)


def test_si_falla_el_evento_se_revierte_el_cobro_y_el_cupo(cliente, motor, monkeypatch):
    def fallo_de_guardado(evento, sesion):
        raise RuntimeError("No se pudo guardar el evento")

    with monkeypatch.context() as cambios:
        cambios.setattr(carril, "guardar_entrada", fallo_de_guardado)
        with pytest.raises(RuntimeError, match="No se pudo guardar el evento"):
            ingresar(cliente, "ABC009")

    assert cupos(cliente)["CARRO"] == (10, 9, 1)
    with Session(motor) as sesion:
        assert sesion.scalar(select(db.CobroDB).where(db.CobroDB.placa == "ABC009")) is None


def test_dos_ingresos_concurrentes_no_toman_el_mismo_cupo(cliente):
    inicio = Barrier(2)

    def intentar(placa):
        inicio.wait(timeout=5)
        return ingresar(cliente, placa)["barrera"]

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(intentar, ["ABC009", "ABC010"]))
    assert sorted(resultados) == ["ABIERTA", "LLENO"]
    assert cupos(cliente)["CARRO"] == (10, 10, 0)
