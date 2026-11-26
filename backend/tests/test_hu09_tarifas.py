from datetime import datetime, time
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
from app.application.administrar_tarifas import AdministrarTarifas, TipoSinTarifas
from app.domain.tarifa import (
    FranjaInvalida,
    Tarifa,
    TarifaInvalida,
    TarifaPorFranja,
    franja_de,
    validar_inicio_nocturna,
    validar_tarifas,
)
from app.domain.usuario import Rol, Usuario
from app.infrastructure import db, eventos
from app.infrastructure.seguridad import emitir_token
from app.main import app

BOGOTA = ZoneInfo("America/Bogota")


def a_las(hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 11, 27, hora, minuto, tzinfo=BOGOTA)


@pytest.mark.parametrize(("diurna", "nocturna"), [(3850, 1800), (5000, 4999), (0, 0)])
def test_tarifas_validas(diurna, nocturna):
    validar_tarifas(diurna, nocturna)


@pytest.mark.parametrize(
    ("diurna", "nocturna", "mensaje"),
    [
        (3850, 3850, "menor que la diurna"),
        (3850, 5000, "menor que la diurna"),
        (0, 500, "menor que la diurna"),
        (-1, 0, "negativas"),
        (2_000_000, 1000, "1.000.000"),
    ],
)
def test_tarifas_invalidas(diurna, nocturna, mensaje):
    with pytest.raises(TarifaInvalida, match=mensaje):
        validar_tarifas(diurna, nocturna)


@pytest.mark.parametrize("inicio", [time(4, 0), time(3, 0), time(23, 59), time(17, 30, 15)])
def test_inicio_nocturna_invalido(inicio):
    with pytest.raises(FranjaInvalida):
        validar_inicio_nocturna(inicio)


def test_franja_con_horario_configurado():
    assert franja_de(a_las(18, 30), time(19, 0)) == "DIURNA"
    assert franja_de(a_las(19, 0), time(19, 0)) == "NOCTURNA"




class TarifasEnMemoria:
    def __init__(self) -> None:
        self.valores = {("CARRO", "DIURNA"): 3850, ("CARRO", "NOCTURNA"): 1800,
                        ("MOTO", "DIURNA"): 0, ("MOTO", "NOCTURNA"): 0}
        self.inicio = time(17, 30)
        self.guardados = 0

    def listar(self):
        return [Tarifa(i, t, f, v) for i, ((t, f), v) in enumerate(self.valores.items(), 1)]

    def actualizar(self, tipo, diurna, nocturna):
        self.guardados += 1
        self.valores[(tipo, "DIURNA")] = diurna
        self.valores[(tipo, "NOCTURNA")] = nocturna
        return [t for t in self.listar() if t.tipo_vehiculo == tipo]

    def cambiar_inicio_nocturna(self, inicio):
        self.inicio = inicio

    def inicio_nocturna(self):
        return self.inicio

    def vigente(self, sede_id, tipo, franja):
        return Tarifa(1, tipo, franja, self.valores[(tipo, franja)])


@pytest.fixture
def memoria():
    return TarifasEnMemoria()


@pytest.fixture
def administracion(memoria):
    return AdministrarTarifas(memoria, memoria)


def test_cambiar_tarifas_de_carro(administracion, memoria):
    administracion.cambiar_tarifas("carro", 4000, 2000)
    assert memoria.valores[("CARRO", "DIURNA")] == 4000
    assert memoria.valores[("CARRO", "NOCTURNA")] == 2000


def test_tarifa_que_viola_rn02_no_se_guarda(administracion, memoria):
    with pytest.raises(TarifaInvalida):
        administracion.cambiar_tarifas("CARRO", 3000, 3500)
    assert memoria.guardados == 0
    assert memoria.valores[("CARRO", "NOCTURNA")] == 1800


def test_tipo_sin_tarifas(administracion):
    with pytest.raises(TipoSinTarifas):
        administracion.cambiar_tarifas("BUS", 9000, 5000)


def test_el_carril_usa_el_horario_configurado(administracion, memoria):
    estrategia = TarifaPorFranja(memoria, memoria)
    assert estrategia.calcular("CARRO", 1, a_las(18)).valor == 1800
    administracion.cambiar_inicio_nocturna(time(19, 0))
    assert estrategia.calcular("CARRO", 1, a_las(18)).valor == 3850




@pytest.fixture
def motor(tmp_path, monkeypatch):
    motor = create_engine(f"sqlite:///{tmp_path / 'tarifas.db'}")
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
    monkeypatch.setenv("LECTOR_PLACAS", "simulador")
    with TestClient(app) as cliente:
        yield cliente


def como(rol: Rol) -> dict[str, str]:
    return {"Authorization": f"Bearer {emitir_token(Usuario(rol.value.lower(), '', rol))}"}


def entrar(cliente, placa, momento, monkeypatch):
    monkeypatch.setattr(carril, "ahora_bogota", lambda: momento)
    respuesta = cliente.post(
        "/api/v1/carril/entrada",
        json={"placa": placa, "confianza": 0.95, "sede_id": 1},
        headers=como(Rol.OPERADOR),
    )
    return respuesta.json()["cobro"]


def test_admin_lista_las_tarifas(cliente):
    respuesta = cliente.get("/api/v1/admin/tarifas", headers=como(Rol.ADMIN))
    assert respuesta.status_code == 200
    valores = {(t["tipo_vehiculo"], t["franja"]): t["valor"] for t in respuesta.json()}
    assert valores[("CARRO", "DIURNA")] == 3850
    assert valores[("CARRO", "NOCTURNA")] == 1800


def test_admin_cambia_la_tarifa_y_los_cobros_viejos_no_cambian(cliente, motor, monkeypatch):
    viejo = entrar(cliente, "ABC123", a_las(10), monkeypatch)
    respuesta = cliente.put(
        "/api/v1/admin/tarifas/CARRO", json={"diurna": 4500, "nocturna": 2000}, headers=como(Rol.ADMIN)
    )
    assert respuesta.status_code == 200
    nuevo = entrar(cliente, "XYZ987", a_las(11), monkeypatch)

    assert nuevo["valor"] == 4500
    with Session(motor) as sesion:
        assert sesion.get(db.CobroDB, viejo["id"]).valor == 3850  # RN-07


def test_admin_no_puede_poner_nocturna_mayor_que_diurna(cliente, motor):
    respuesta = cliente.put(
        "/api/v1/admin/tarifas/CARRO", json={"diurna": 3000, "nocturna": 3500}, headers=como(Rol.ADMIN)
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"] == "La tarifa nocturna debe ser menor que la diurna (RN-02)"
    with Session(motor) as sesion:
        nocturna = sesion.scalars(
            select(db.TarifaDB).where(db.TarifaDB.tipo_vehiculo == "CARRO", db.TarifaDB.franja == "NOCTURNA")
        ).one()
        assert nocturna.valor == 1800


def test_tipo_inexistente_es_404(cliente):
    respuesta = cliente.put(
        "/api/v1/admin/tarifas/BUS", json={"diurna": 9000, "nocturna": 5000}, headers=como(Rol.ADMIN)
    )
    assert respuesta.status_code == 404


def test_admin_cambia_el_horario_de_la_franja_nocturna(cliente, monkeypatch):
    respuesta = cliente.put(
        "/api/v1/admin/franjas", json={"inicio_nocturna": "09:00"}, headers=como(Rol.ADMIN)
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "diurna_desde": "04:00:00",
        "diurna_hasta": "08:59:00",
        "nocturna_desde": "09:00:00",
        "nocturna_hasta": "23:59:00",
    }
    cobro = entrar(cliente, "ABC123", a_las(10), monkeypatch)
    assert cobro["valor"] == 1800  # a las 10:00 ya es franja nocturna


def test_horario_fuera_de_rango_es_422(cliente):
    respuesta = cliente.put(
        "/api/v1/admin/franjas", json={"inicio_nocturna": "03:00"}, headers=como(Rol.ADMIN)
    )
    assert respuesta.status_code == 422


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("get", "/api/v1/admin/tarifas", None),
        ("put", "/api/v1/admin/tarifas/CARRO", {"diurna": 1, "nocturna": 0}),
        ("get", "/api/v1/admin/franjas", None),
        ("put", "/api/v1/admin/franjas", {"inicio_nocturna": "18:00"}),
    ],
)
def test_el_operador_no_puede_administrar(cliente, metodo, ruta, cuerpo):
    respuesta = cliente.request(metodo.upper(), ruta, json=cuerpo, headers=como(Rol.OPERADOR))
    assert respuesta.status_code == 403