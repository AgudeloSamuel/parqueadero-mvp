"""Pruebas de la HU-04: generar el cobro del día operativo."""
from datetime import date, datetime
from pathlib import Path
from secrets import token_hex
from zoneinfo import ZoneInfo

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api import carril
from app.application.generar_cobro import ServicioCobro, TipoSinTarifa
from app.domain.cobro import Cobro
from app.domain.tarifa import Tarifa, TarifaPorFranja, franja_de
from app.domain.usuario import Rol, Usuario
from app.infrastructure import db, eventos
from app.infrastructure.cobros import ConsultaTarifasSQL, RepositorioCobrosSQL
from app.infrastructure.seguridad import emitir_token
from app.main import app

BOGOTA = ZoneInfo("America/Bogota")
RUTA = "/api/v1/carril/entrada"


def el_dia(dia: int, hora: int, minuto: int = 0, segundo: int = 0) -> datetime:
    return datetime(2026, 11, dia, hora, minuto, segundo, tzinfo=BOGOTA)



class TarifasFalsas:
    def __init__(self) -> None:
        self.valores = {
            ("CARRO", "DIURNA"): Tarifa(1, "CARRO", "DIURNA", 3850),
            ("CARRO", "NOCTURNA"): Tarifa(2, "CARRO", "NOCTURNA", 1800),
            ("MOTO", "DIURNA"): Tarifa(3, "MOTO", "DIURNA", 0),
            ("MOTO", "NOCTURNA"): Tarifa(4, "MOTO", "NOCTURNA", 0),
        }

    def vigente(self, sede_id, tipo, franja):
        return self.valores[(tipo, franja)]


class CobrosEnMemoria:
    def __init__(self) -> None:
        self.cobros: list[Cobro] = []

    def buscar_del_dia(self, placa, sede_id, dia):
        for cobro in self.cobros:
            if (cobro.placa, cobro.sede_id, cobro.dia_operativo) == (placa, sede_id, dia):
                return cobro
        return None

    def guardar(self, cobro):
        guardado = cobro.con_id(len(self.cobros) + 1)
        self.cobros.append(guardado)
        return guardado


@pytest.fixture
def tarifas():
    return TarifasFalsas()


@pytest.fixture
def repositorio():
    return CobrosEnMemoria()


@pytest.fixture
def servicio(tarifas, repositorio):
    por_franja = TarifaPorFranja(tarifas)
    return ServicioCobro(repositorio, {"CARRO": por_franja, "MOTO": por_franja})




@pytest.mark.parametrize(
    ("momento", "franja"),
    [
        (el_dia(23, 4, 0), "DIURNA"),
        (el_dia(23, 12, 0), "DIURNA"),
        (el_dia(23, 17, 29, 59), "DIURNA"),
        (el_dia(23, 17, 30), "NOCTURNA"),
        (el_dia(23, 23, 59, 59), "NOCTURNA"),
    ],
)
def test_franja_segun_la_hora(momento, franja):
    assert franja_de(momento) == franja




def test_carro_de_dia_genera_cobro_diurno_pendiente(servicio, repositorio):
    cobro = servicio.generar_o_reutilizar("ABC123", "CARRO", 1, el_dia(23, 10))
    assert (cobro.valor, cobro.estado) == (3850, "PENDIENTE")
    guardado, = repositorio.cobros
    assert (guardado.dia_operativo, guardado.tarifa_id) == (date(2026, 11, 23), 1)


def test_carro_de_noche_genera_cobro_nocturno(servicio):
    cobro = servicio.generar_o_reutilizar("ABC123", "CARRO", 1, el_dia(23, 18))
    assert cobro.valor == 1800


def test_moto_no_genera_cobro(servicio, repositorio):
    assert servicio.generar_o_reutilizar("ABC12D", "MOTO", 1, el_dia(23, 10)) is None
    assert repositorio.cobros == []


def test_reingreso_el_mismo_dia_no_crea_otro_cobro(servicio, repositorio):
    manana = servicio.generar_o_reutilizar("ABC123", "CARRO", 1, el_dia(23, 9))
    tarde = servicio.generar_o_reutilizar("ABC123", "CARRO", 1, el_dia(23, 19))
    assert tarde == manana  # sigue siendo el cobro diurno de la mañana
    assert tarde.valor == 3850
    assert len(repositorio.cobros) == 1


def test_otro_dia_genera_cobro_nuevo(servicio, repositorio):
    lunes = servicio.generar_o_reutilizar("ABC123", "CARRO", 1, el_dia(23, 10))
    martes = servicio.generar_o_reutilizar("ABC123", "CARRO", 1, el_dia(24, 10))
    assert lunes.id != martes.id
    assert len(repositorio.cobros) == 2


def test_misma_placa_en_otra_sede_es_otro_cobro(servicio, repositorio):
    servicio.generar_o_reutilizar("ABC123", "CARRO", 1, el_dia(23, 10))
    servicio.generar_o_reutilizar("ABC123", "CARRO", 2, el_dia(23, 10))
    assert len(repositorio.cobros) == 2


def test_cambiar_la_tarifa_no_altera_cobros_existentes(servicio, tarifas, repositorio):
    servicio.generar_o_reutilizar("ABC123", "CARRO", 1, el_dia(23, 10))
    tarifas.valores[("CARRO", "DIURNA")] = Tarifa(1, "CARRO", "DIURNA", 5000)
    cobro = servicio.generar_o_reutilizar("ABC123", "CARRO", 1, el_dia(23, 11))
    assert cobro.valor == 3850  # RN-07
    nuevo = servicio.generar_o_reutilizar("XYZ987", "CARRO", 1, el_dia(23, 11))
    assert nuevo.valor == 5000


def test_tipo_sin_estrategia_es_error(repositorio):
    servicio = ServicioCobro(repositorio, {})
    with pytest.raises(TipoSinTarifa):
        servicio.generar_o_reutilizar("ABC123", "CARRO", 1, el_dia(23, 10))


def test_agregar_un_tipo_nuevo_es_registrar_otra_estrategia(servicio, repositorio):
    class TarifaFija:  # otra estrategia (Strategy) sin tocar ServicioCobro
        def calcular(self, tipo, sede_id, momento):
            return Tarifa(99, tipo, "DIURNA", 6000)

    servicio.estrategias = {**servicio.estrategias, "CAMIONETA": TarifaFija()}
    cobro = servicio.generar_o_reutilizar("AB1234", "CAMIONETA", 1, el_dia(23, 10))
    assert cobro.valor == 6000




@pytest.fixture
def motor(tmp_path, monkeypatch):
    motor = create_engine(f"sqlite:///{tmp_path / 'cobros.db'}")
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


def cobros_guardados(motor):
    with Session(motor) as sesion:
        return sesion.scalars(select(db.CobroDB)).all()


def test_tarifas_por_defecto_en_la_base_de_datos(motor):
    tarifas = ConsultaTarifasSQL()
    assert tarifas.vigente(1, "CARRO", "DIURNA").valor == 3850
    assert tarifas.vigente(1, "CARRO", "NOCTURNA").valor == 1800
    assert tarifas.vigente(1, "MOTO", "DIURNA").valor == 0


def test_base_de_datos_no_permite_dos_cobros_el_mismo_dia(motor):
    cobro = Cobro("ABC123", 1, date(2026, 11, 23), "CARRO", 1, 3850, "PENDIENTE", el_dia(23, 10))
    RepositorioCobrosSQL().guardar(cobro)
    with Session(motor) as sesion, pytest.raises(IntegrityError), sesion.begin():
        sesion.add(db.CobroDB(
            placa="ABC123", sede_id=1, dia_operativo=date(2026, 11, 23), tipo_vehiculo="CARRO",
            tarifa_id=1, valor=3850, estado="PENDIENTE", creado_en=el_dia(23, 11),
        ))


def test_ingreso_de_carro_devuelve_el_cobro(cliente, motor, monkeypatch):
    monkeypatch.setattr(carril, "ahora_bogota", lambda: el_dia(23, 10))
    respuesta = cliente.post(RUTA, json={"placa": "ABC123", "confianza": 0.95, "sede_id": 1})

    assert respuesta.status_code == 201
    cobro = respuesta.json()["cobro"]
    assert (cobro["valor"], cobro["estado"]) == (3850, "PENDIENTE")
    guardado, = cobros_guardados(motor)
    assert (guardado.placa, guardado.dia_operativo, guardado.valor) == (
        "ABC123", date(2026, 11, 23), 3850
    )


def test_reingreso_por_la_api_reutiliza_el_cobro(cliente, motor, monkeypatch):
    monkeypatch.setattr(carril, "ahora_bogota", lambda: el_dia(23, 10))
    primero = cliente.post(RUTA, json={"placa": "ABC123", "confianza": 0.95, "sede_id": 1})
    monkeypatch.setattr(carril, "ahora_bogota", lambda: el_dia(23, 19))
    segundo = cliente.post(RUTA, json={"placa": "ABC123", "confianza": 0.95, "sede_id": 1})

    assert segundo.json()["cobro"] == primero.json()["cobro"]
    assert len(cobros_guardados(motor)) == 1


def test_ingreso_de_moto_no_tiene_cobro(cliente, motor, monkeypatch):
    monkeypatch.setattr(carril, "ahora_bogota", lambda: el_dia(23, 10))
    respuesta = cliente.post(RUTA, json={"placa": "ABC12D", "confianza": 0.95, "sede_id": 1})

    assert respuesta.status_code == 201
    assert "cobro" not in respuesta.json()
    assert cobros_guardados(motor) == []