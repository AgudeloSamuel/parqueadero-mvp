from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure import db


def ultima_entrada_sin_salida(
    placa: str, sede_id: int, sesion: Session | None = None
) -> datetime | None:
    """Hora de la entrada más reciente que todavía tiene una salida efectiva pendiente."""
    contexto = nullcontext(sesion) if sesion is not None else Session(db.motor_db())
    fecha_movimiento = func.coalesce(db.EventoDB.validada_en, db.EventoDB.fecha_hora)
    with contexto as sesion:
        ultimo = sesion.execute(
            select(db.EventoDB.tipo, fecha_movimiento.label("fecha_movimiento"))
            .where(
                db.EventoDB.placa == placa,
                db.EventoDB.sede_id == sede_id,
                db.EventoDB.tipo.in_(("ENTRADA", "SALIDA")),
                db.EventoDB.barrera == "ABIERTA",
            )
            .order_by(fecha_movimiento.desc(), db.EventoDB.id.desc())
            .limit(1)
        ).first()
        if ultimo is not None and ultimo.tipo == "ENTRADA":
            return ultimo.fecha_movimiento
        return None
