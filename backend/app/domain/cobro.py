from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime

from app.domain.cobro_estados import EstadoCobro, estado_de


@dataclass(frozen=True)
class Cobro:
    placa: str
    sede_id: int
    dia_operativo: date
    tipo_vehiculo: str
    tarifa_id: int
    valor: int
    estado: str
    creado_en: datetime
    id: int | None = None

    def con_id(self, nuevo_id: int) -> Cobro:
        return replace(self, id=nuevo_id)

    @property
    def ciclo(self) -> EstadoCobro:
        """Estado actual del cobro (patrón State, HU-05)."""
        return estado_de(self.estado)