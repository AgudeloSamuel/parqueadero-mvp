"""Tarifas y franjas del parqueadero (HU-04 y HU-09).

Franjas por defecto: DIURNA de 4:00 a. m. a 5:29 p. m. y NOCTURNA de 5:30 p. m. a
11:59 p. m. El administrador puede mover la hora en que empieza la franja nocturna (HU-09).
La franja se decide con la hora de la primera entrada del día.

Patrón Strategy: cada tipo de vehículo tiene una estrategia que decide qué tarifa
le corresponde. Para agregar un tipo nuevo se registra otra estrategia en el
ServicioCobro, sin modificar el cálculo existente (abierto/cerrado).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Literal, Protocol

from app.domain.puertos import ConsultaTarifas, HorarioFranjas

Franja = Literal["DIURNA", "NOCTURNA"]

APERTURA = time(4, 0)
CIERRE = time(23, 59)
INICIO_NOCTURNA = time(17, 30)
TARIFA_MAXIMA = 1_000_000


class TarifaInvalida(ValueError):
    pass


class FranjaInvalida(ValueError):
    pass


def franja_de(momento: datetime, inicio_nocturna: time = INICIO_NOCTURNA) -> Franja:
    """DIURNA antes del inicio de la nocturna; NOCTURNA desde ese momento."""
    return "NOCTURNA" if momento.time() >= inicio_nocturna else "DIURNA"


def validar_tarifas(diurna: int, nocturna: int) -> None:
    """RN-01 y RN-02: la nocturna debe ser menor que la diurna; un tipo gratis va en $0 y $0."""
    if diurna < 0 or nocturna < 0:
        raise TarifaInvalida("Las tarifas no pueden ser negativas")
    if diurna > TARIFA_MAXIMA or nocturna > TARIFA_MAXIMA:
        raise TarifaInvalida("La tarifa no puede superar $1.000.000")
    if diurna == 0 and nocturna == 0:  # RN-01: tipo de vehículo sin cobro (moto)
        return
    if nocturna >= diurna:
        raise TarifaInvalida("La tarifa nocturna debe ser menor que la diurna (RN-02)")


def validar_inicio_nocturna(inicio: time) -> None:
    """La franja nocturna tiene que empezar dentro del horario de ingreso."""
    if inicio.second or inicio.microsecond:
        raise FranjaInvalida("La hora se indica en horas y minutos")
    if not APERTURA < inicio < CIERRE:
        raise FranjaInvalida("La franja nocturna debe empezar entre las 4:01 a. m. y las 11:58 p. m.")


@dataclass(frozen=True)
class Tarifa:
    id: int
    tipo_vehiculo: str
    franja: Franja
    valor: int


class EstrategiaTarifa(Protocol):
    """Strategy: decide la tarifa que se aplica a un vehículo que entra en un momento dado."""

    def calcular(self, tipo: str, sede_id: int, momento: datetime) -> Tarifa: ...


class TarifaPorFranja:
    """Estrategia para carros y motos: la tarifa depende de la franja de la entrada."""

    def __init__(self, tarifas: ConsultaTarifas, horario: HorarioFranjas | None = None) -> None:
        self.tarifas = tarifas
        self.horario = horario

    def calcular(self, tipo: str, sede_id: int, momento: datetime) -> Tarifa:
        inicio = self.horario.inicio_nocturna() if self.horario else INICIO_NOCTURNA
        return self.tarifas.vigente(sede_id, tipo, franja_de(momento, inicio))