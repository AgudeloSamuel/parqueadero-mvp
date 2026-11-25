"""Pago en efectivo y pase del día (HU-05)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, tzinfo

FIN_DEL_PASE = time(23, 59, 59)


class ClaveDeOtroCobro(ValueError):
     """La misma clave de idempotencia no se puede usar para pagar otro cobro."""


@dataclass(frozen=True)
class Pago:
    cobro_id: int
    valor: int
    clave_idempotencia: str
    fecha_hora: datetime
    id: int | None = None


def pase_hasta(dia_operativo: date, zona: tzinfo | None) -> datetime:
    return datetime.combine(dia_operativo, FIN_DEL_PASE, tzinfo=zona)