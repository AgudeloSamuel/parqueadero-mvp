from __future__ import annotations

from contextlib import nullcontext
from datetime import time

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.domain.tarifa import INICIO_NOCTURNA, Tarifa
from app.infrastructure import db

CLAVE_INICIO_NOCTURNA = "INICIO_NOCTURNA"


def _a_dominio(fila: db.TarifaDB) -> Tarifa:
    return Tarifa(fila.id, fila.tipo_vehiculo, fila.franja, fila.valor)


class HorarioFranjasSQL:
    """Solo lectura: la usa el carril para saber la franja de una entrada.

    Si recibe la sesión del carril, lee dentro de la misma transacción de la entrada.
    """

    def __init__(self, sesion: Session | None = None) -> None:
        self.sesion = sesion

    def inicio_nocturna(self) -> time:
        contexto = nullcontext(self.sesion) if self.sesion is not None else Session(db.motor_db())
        with contexto as sesion:
            valor = sesion.get(db.ParametroDB, CLAVE_INICIO_NOCTURNA)
            return INICIO_NOCTURNA if valor is None else time.fromisoformat(valor.valor)


class AdministracionTarifasSQL:
    def listar(self) -> list[Tarifa]:
        with Session(db.motor_db()) as sesion:
            filas = sesion.scalars(
                select(db.TarifaDB).order_by(db.TarifaDB.tipo_vehiculo, db.TarifaDB.franja)
            ).all()
            return [_a_dominio(fila) for fila in filas]

    def actualizar(self, tipo: str, diurna: int, nocturna: int) -> list[Tarifa]:
        """Cambia las dos franjas en una sola transacción: nunca queda una mitad guardada."""
        with Session(db.motor_db()) as sesion, sesion.begin():
            for franja, valor in (("DIURNA", diurna), ("NOCTURNA", nocturna)):
                sesion.execute(
                    update(db.TarifaDB)
                    .where(db.TarifaDB.tipo_vehiculo == tipo, db.TarifaDB.franja == franja)
                    .values(valor=valor)
                )
            filas = sesion.scalars(
                select(db.TarifaDB)
                .where(db.TarifaDB.tipo_vehiculo == tipo)
                .order_by(db.TarifaDB.franja)
            ).all()
            return [_a_dominio(fila) for fila in filas]

    def cambiar_inicio_nocturna(self, inicio: time) -> None:
        with Session(db.motor_db()) as sesion, sesion.begin():
            sesion.merge(db.ParametroDB(clave=CLAVE_INICIO_NOCTURNA, valor=inicio.strftime("%H:%M")))