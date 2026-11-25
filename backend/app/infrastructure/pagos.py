from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.cobro import Cobro
from app.domain.cobro_estados import CobroYaPagado
from app.domain.pago import ClaveDeOtroCobro, Pago
from app.infrastructure import db


def _a_dominio(fila: db.PagoDB) -> Pago:
    return Pago(
        id=fila.id,
        cobro_id=fila.cobro_id,
        valor=fila.valor,
        clave_idempotencia=fila.clave_idempotencia,
        fecha_hora=fila.fecha_hora,
    )


class PagoEfectivoSQL:
    def buscar_por_clave(self, clave_idempotencia: str) -> Pago | None:
        with Session(db.motor_db()) as sesion:
            fila = sesion.scalars(
                select(db.PagoDB).where(db.PagoDB.clave_idempotencia == clave_idempotencia)
            ).first()
            return None if fila is None else _a_dominio(fila)

    def pagar(self, cobro: Cobro, clave_idempotencia: str, fecha_hora: datetime) -> Pago:
        """Registra el pago y deja el cobro en PAGADO en una sola transacción."""
        try:
            with Session(db.motor_db()) as sesion, sesion.begin():
                cambio = sesion.execute(
                    update(db.CobroDB)
                    .where(db.CobroDB.id == cobro.id, db.CobroDB.estado == "PENDIENTE")
                    .values(estado=cobro.ciclo.pagar().nombre)
                )
                if cambio.rowcount == 0:  # otro pago llegó primero
                    raise CobroYaPagado("El cobro ya está pagado")
                fila = db.PagoDB(
                    cobro_id=cobro.id,
                    valor=cobro.valor,
                    clave_idempotencia=clave_idempotencia,
                    fecha_hora=fecha_hora,
                )
                sesion.add(fila)
                sesion.flush()
                return _a_dominio(fila)
        except (IntegrityError, CobroYaPagado) as error:
            # Dos solicitudes casi al mismo tiempo: si traen la misma clave es el mismo pago.
            previo = self.buscar_por_clave(clave_idempotencia)
            if previo is not None and previo.cobro_id == cobro.id:
                return previo
            if isinstance(error, CobroYaPagado):
                raise
            raise ClaveDeOtroCobro("La clave de idempotencia ya se usó para otro cobro") from error