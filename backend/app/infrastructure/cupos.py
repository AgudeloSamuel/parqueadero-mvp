from dataclasses import dataclass

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.domain.ingreso import TipoVehiculo
from app.infrastructure.db import CupoDB, EventoDB


@dataclass(frozen=True)
class Disponibilidad:
    tipo_vehiculo: str
    capacidad: int
    ocupados: int
    disponibles: int


class CuposSQL:
    def __init__(self, sesion: Session) -> None:
        self.sesion = sesion

    def bloquear(self, tipo: TipoVehiculo) -> int:
        # Mantiene el bloqueo de escritura hasta guardar el movimiento.
        capacidad = self.sesion.execute(
            update(CupoDB)
            .where(CupoDB.tipo_vehiculo == tipo)
            .values(capacidad=CupoDB.capacidad)
            .returning(CupoDB.capacidad)
        ).scalar_one()
        return capacidad

    def hay_cupo(self, sede_id: int, tipo: TipoVehiculo) -> bool:
        capacidad = self.sesion.execute(
            select(CupoDB.capacidad).where(CupoDB.tipo_vehiculo == tipo)
        ).scalar_one()
        return self._ocupacion(sede_id).get(tipo, 0) < capacidad

    def disponibles(self, sede_id: int) -> list[Disponibilidad]:
        ocupacion = self._ocupacion(sede_id)
        filas = self.sesion.execute(
            select(CupoDB.tipo_vehiculo, CupoDB.capacidad).order_by(CupoDB.tipo_vehiculo)
        )
        disponibilidad = []
        for tipo, capacidad in filas:
            ocupados = ocupacion.get(tipo, 0)
            disponibilidad.append(Disponibilidad(tipo, capacidad, ocupados, max(0, capacidad - ocupados)))
        return disponibilidad

    def _ocupacion(self, sede_id: int) -> dict[str, int]:
        fecha_movimiento = func.coalesce(EventoDB.validada_en, EventoDB.fecha_hora)
        ultimo = (
            select(
                EventoDB.tipo,
                EventoDB.tipo_vehiculo,
                func.row_number().over(
                    partition_by=EventoDB.placa,
                    order_by=(fecha_movimiento.desc(), EventoDB.id.desc()),
                ).label("orden"),
            )
            .where(
                EventoDB.sede_id == sede_id,
                EventoDB.barrera == "ABIERTA",
                EventoDB.tipo.in_(("ENTRADA", "SALIDA")),
                EventoDB.placa.is_not(None),
            )
            .subquery()
        )
        filas = self.sesion.execute(
            select(ultimo.c.tipo_vehiculo, func.count())
            .where(ultimo.c.orden == 1, ultimo.c.tipo == "ENTRADA")
            .group_by(ultimo.c.tipo_vehiculo)
        )
        return {tipo: cantidad for tipo, cantidad in filas}
