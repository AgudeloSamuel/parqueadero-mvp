"""Pruebas de la HU-05: pago en efectivo, estados del cobro y pase del día."""
from datetime import date, datetime
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
from app.application.estado_salida import ConsultaSalida, formato_pesos
from app.application.pagar_cobro import CobroNoEncontrado, PagarCobro
from app.domain.cobro import Cobro
from app.domain.cobro_estados import (
    ANULADO,
    PAGADO,
    PENDIENTE,
    CobroAnulado,
    CobroYaPagado,
    TransicionInvalida,
)
from app.domain.pago import ClaveDeOtroCobro, Pago
from app.domain.usuario import Rol, Usuario
from app.infrastructure import db, eventos
from app.infrastructure.entradas import ultima_entrada_sin_salida
from app.infrastructure.seguridad import emitir_token
from app.main import app

BOGOTA = ZoneInfo("America/Bogota")


def el_dia(dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 11, dia, hora, minuto, tzinfo=BOGOTA)


def cobro(estado: str = "PENDIENTE", dia: int = 24, cobro_id: int = 1) -> Cobro:
    return Cobro(
        "ABC123", 1, date(2026, 11, dia), "CARRO", 1, 3850, estado, el_dia(dia, 10), cobro_id
    )




class CobrosEnMemoria:
    def __init__(self, *cobros: Cobro) -> None:
        self.cobros = {c.id: c for c in cobros}

    def por_id(self, cobro_id):
        return self.cobros.get(cobro_id)

    def buscar_del_dia(self, placa, sede_id, dia):
        for c in self.cobros.values():
            if (c.placa, c.sede_id, c.dia_operativo) == (placa, sede_id, dia):
                return c
        return None

    def guardar(self, nuevo):
        self.cobros[nuevo.id] = nuevo
        return nuevo


class PagosEnMemoria:
    def __init__(self, cobros: CobrosEnMemoria) -> None:
        self.cobros = cobros
        self.pagos: list[Pago] = []

    def buscar_por_clave(self, clave):
        return next((p for p in self.pagos if p.clave_idempotencia == clave), None)

    def pagar(self, a_pagar, clave, fecha_hora):
        pago = Pago(a_pagar.id, a_pagar.valor, clave, fecha_hora, len(self.pagos) + 1)
        self.pagos.append(pago)
        self.cobros.guardar(Cobro(**{**a_pagar.__dict__, "estado": "PAGADO"}))
        return pago


def caja(*cobros: Cobro, hora: datetime | None = None):
    repositorio = CobrosEnMemoria(*cobros)
    pagos = PagosEnMemoria(repositorio)
    momento = hora or el_dia(24, 11)
    return PagarCobro(repositorio, pagos, lambda: momento), repositorio, pagos



def test_pendiente_puede_pagarse_o_anularse():
    assert PENDIENTE.pagar() is PAGADO
    assert PENDIENTE.anular() is ANULADO
    assert not PENDIENTE.permite_salida


def test_pagado_no_se_paga_otra_vez_ni_se_anula():
    with pytest.raises(CobroYaPagado):
        PAGADO.pagar()
    with pytest.raises(TransicionInvalida):
        PAGADO.anular()
    assert PAGADO.permite_salida


def test_anulado_no_se_puede_pagar():
    with pytest.raises(CobroAnulado):
        ANULADO.pagar()


def test_el_cobro_conoce_su_estado():
    assert cobro("PENDIENTE").ciclo is PENDIENTE
    assert cobro("PAGADO").ciclo is PAGADO




def test_pagar_deja_el_cobro_pagado_con_pase_hasta_las_1159():
    pagar, repositorio, pagos = caja(cobro())
    resultado = pagar.ejecutar(1, "clave-0001")

    assert resultado.estado_cobro == "PAGADO"
    assert resultado.pase_hasta == datetime(2026, 11, 24, 23, 59, 59, tzinfo=BOGOTA)
    assert resultado.pago.valor == 3850
    assert repositorio.por_id(1).estado == "PAGADO"
    assert len(pagos.pagos) == 1


def test_repetir_la_misma_clave_no_duplica_el_pago():
    pagar, _, pagos = caja(cobro())
    primero = pagar.ejecutar(1, "clave-0001")
    segundo = pagar.ejecutar(1, "clave-0001")

    assert segundo.pago == primero.pago
    assert len(pagos.pagos) == 1


def test_no_se_paga_dos_veces_con_otra_clave():
    pagar, _, _ = caja(cobro())
    pagar.ejecutar(1, "clave-0001")
    with pytest.raises(CobroYaPagado):
        pagar.ejecutar(1, "clave-0002")


def test_no_se_paga_un_cobro_anulado():
    pagar, _, pagos = caja(cobro("ANULADO"))
    with pytest.raises(CobroAnulado):
        pagar.ejecutar(1, "clave-0001")
    assert pagos.pagos == []


def test_cobro_que_no_existe():
    pagar, _, _ = caja()
    with pytest.raises(CobroNoEncontrado):
        pagar.ejecutar(99, "clave-0001")


def test_una_clave_no_sirve_para_otro_cobro():
    otro = Cobro("XYZ987", 1, date(2026, 11, 24), "CARRO", 1, 3850, "PENDIENTE", el_dia(24, 10), 2)
    pagar, _, _ = caja(cobro(), otro)
    pagar.ejecutar(1, "clave-0001")
    with pytest.raises(ClaveDeOtroCobro):
        pagar.ejecutar(2, "clave-0001")


def test_el_pase_es_del_dia_de_la_entrada_aunque_pague_despues_de_medianoche():
    pagar, _, _ = caja(cobro(dia=24), hora=el_dia(25, 1))
    resultado = pagar.ejecutar(1, "clave-0001")
    assert resultado.pase_hasta.date() == date(2026, 11, 24)



def salida(*cobros: Cobro, entrada: datetime | None):
    return ConsultaSalida(CobrosEnMemoria(*cobros), lambda placa, sede: entrada)


def test_salida_con_pago_pendiente_no_abre():
    consulta = salida(cobro("PENDIENTE"), entrada=el_dia(24, 10))
    assert consulta.estado_para_salida("ABC123", 1, el_dia(24, 15)) == (
        False, "Pago pendiente: $3.850"
    )


def test_salida_con_pago_verificado_abre():
    consulta = salida(cobro("PAGADO"), entrada=el_dia(24, 10))
    assert consulta.estado_para_salida("ABC123", 1, el_dia(24, 15)) == (True, "Pago verificado")


def test_salida_sin_cobro_abre():
    consulta = salida(entrada=el_dia(24, 10))
    assert consulta.estado_para_salida("ABC12D", 1, el_dia(24, 15)) == (True, "Sin cobro")


def test_salida_despues_de_medianoche_usa_el_cobro_del_dia_de_entrada():
    pagado_ayer = salida(cobro("PAGADO", dia=24), entrada=el_dia(24, 20))
    assert pagado_ayer.estado_para_salida("ABC123", 1, el_dia(25, 1)) == (True, "Pago verificado")

    pendiente_ayer = salida(cobro("PENDIENTE", dia=24), entrada=el_dia(24, 20))
    assert pendiente_ayer.estado_para_salida("ABC123", 1, el_dia(25, 1))[0] is False


def test_formato_pesos():
    assert formato_pesos(3850) == "$3.850"
    assert formato_pesos(1800) == "$1.800"




@pytest.fixture
def motor(tmp_path, monkeypatch):
    motor = create_engine(f"sqlite:///{tmp_path / 'pagos.db'}")
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
    monkeypatch.setattr(carril, "ahora_bogota", lambda: el_dia(24, 10))
    token = emitir_token(Usuario("operador", "", Rol.OPERADOR))
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as cliente:
        yield cliente


def entrar(cliente, placa="ABC123"):
    respuesta = cliente.post(
        "/api/v1/carril/entrada", json={"placa": placa, "confianza": 0.95, "sede_id": 1}
    )
    return respuesta.json().get("cobro")


def pagar(cliente, cobro_id, clave="caja-0001"):
    return cliente.post(f"/api/v1/cobros/{cobro_id}/pagos", headers={"Idempotency-Key": clave})


def test_pago_por_la_api(cliente, motor):
    cobro_id = entrar(cliente)["id"]
    respuesta = pagar(cliente, cobro_id)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert (cuerpo["cobro_id"], cuerpo["valor"], cuerpo["estado_cobro"]) == (cobro_id, 3850, "PAGADO")
    assert cuerpo["pase_hasta"].startswith("2026-11-24T23:59:59")
    with Session(motor) as sesion:
        assert sesion.get(db.CobroDB, cobro_id).estado == "PAGADO"
        assert len(sesion.scalars(select(db.PagoDB)).all()) == 1


def test_reintento_con_la_misma_clave_por_la_api(cliente, motor):
    cobro_id = entrar(cliente)["id"]
    primero = pagar(cliente, cobro_id)
    segundo = pagar(cliente, cobro_id)

    assert segundo.status_code == 201
    assert segundo.json() == primero.json()
    with Session(motor) as sesion:
        assert len(sesion.scalars(select(db.PagoDB)).all()) == 1


def test_pagar_dos_veces_con_otra_clave_es_409(cliente):
    cobro_id = entrar(cliente)["id"]
    pagar(cliente, cobro_id, "caja-0001")
    respuesta = pagar(cliente, cobro_id, "caja-0002")
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"] == "El cobro ya está pagado"


def test_cobro_inexistente_es_404(cliente):
    respuesta = pagar(cliente, 999)
    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "Cobro no encontrado"


def test_pago_sin_clave_es_422(cliente):
    cobro_id = entrar(cliente)["id"]
    assert cliente.post(f"/api/v1/cobros/{cobro_id}/pagos").status_code == 422


def test_reingreso_despues_de_pagar_no_crea_otro_cobro(cliente, motor, monkeypatch):
    cobro_id = entrar(cliente)["id"]
    pagar(cliente, cobro_id)
    monkeypatch.setattr(carril, "ahora_bogota", lambda: el_dia(24, 19))
    reingreso = entrar(cliente)

    assert (reingreso["id"], reingreso["estado"]) == (cobro_id, "PAGADO")  # RN-03
    with Session(motor) as sesion:
        assert len(sesion.scalars(select(db.CobroDB)).all()) == 1


def test_pago_sin_token_es_401(motor):
    with TestClient(app) as anonimo:
        respuesta = anonimo.post("/api/v1/cobros/1/pagos", headers={"Idempotency-Key": "caja-0001"})
    assert respuesta.status_code == 401


def test_ultima_entrada_sin_salida_en_la_base(cliente, motor):
    entrar(cliente)
    assert ultima_entrada_sin_salida("ABC123", 1) is not None
    assert ultima_entrada_sin_salida("ZZZ999", 1) is None