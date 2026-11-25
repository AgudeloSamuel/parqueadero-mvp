from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infrastructure import db


def ultima_entrada_sin_salida(placa: str, sede_id: int) -> datetime | None:
    """Hora de la última entrada con barrera ABIERTA posterior a la última salida."""
    with Session(db.motor_db()) as sesion:
        del_vehiculo = (db.EventoDB.placa == placa, db.EventoDB.sede_id == sede_id)
        ultima_salida = sesion.scalar(
            select(func.max(db.EventoDB.fecha_hora)).where(
                *del_vehiculo, db.EventoDB.tipo == "SALIDA"
            )
        )
        consulta = select(db.EventoDB.fecha_hora).where(
            *del_vehiculo, db.EventoDB.tipo == "ENTRADA", db.EventoDB.barrera == "ABIERTA"
        )
        if ultima_salida is not None:
            consulta = consulta.where(db.EventoDB.fecha_hora > ultima_salida)
        return sesion.scalar(consulta.order_by(db.EventoDB.fecha_hora.desc()).limit(1))