from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.domain.ingreso import TipoVehiculo


@dataclass(frozen=True)
class EventoSalida:
    placa: str
    sede_id: int
    fecha_hora: datetime
    tipo_vehiculo: TipoVehiculo
    barrera: Literal["ABIERTA", "CERRADA"]
    motivo: str
