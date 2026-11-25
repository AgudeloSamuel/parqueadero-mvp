from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure import db


def ultima_entrada_sin_salida(placa: str, sede_id: int) -> datetime | None:
    """Hora de la entrada más reciente que todavía tiene una salida efectiva pendiente."""
    with Session(db.motor_db()) as sesion:
        ultimo = sesion.execute(
            select(db.EventoDB.tipo, db.EventoDB.fecha_hora)
            .where(
                db.EventoDB.placa == placa,
                db.EventoDB.sede_id == sede_id,
                db.EventoDB.tipo.in_(("ENTRADA", "SALIDA")),
                db.EventoDB.barrera == "ABIERTA",
            )
            .order_by(db.EventoDB.fecha_hora.desc(), db.EventoDB.id.desc())
            .limit(1)
        ).first()
        if ultimo is not None and ultimo.tipo == "ENTRADA":
            return ultimo.fecha_hora
        return None
