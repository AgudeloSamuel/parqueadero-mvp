"""Tarifas y franjas del parqueadero (HU-04).

Franjas: DIURNA de 4:00 a. m. a 5:29 p. m. y NOCTURNA de 5:30 p. m. a 11:59 p. m.
La franja se decide con la hora de la primera entrada del día.

"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Literal, Protocol

from app.domain.puertos import ConsultaTarifas

Franja = Literal["DIURNA", "NOCTURNA"]

INICIO_NOCTURNA = time(17, 30)


def franja_de(momento: datetime) -> Franja:
    """DIURNA antes de las 5:30 p. m.; NOCTURNA desde las 5:30 p. m."""
    return "NOCTURNA" if momento.time() >= INICIO_NOCTURNA else "DIURNA"


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

    def __init__(self, tarifas: ConsultaTarifas) -> None:
        self.tarifas = tarifas

    def calcular(self, tipo: str, sede_id: int, momento: datetime) -> Tarifa:
        return self.tarifas.vigente(sede_id, tipo, franja_de(momento))