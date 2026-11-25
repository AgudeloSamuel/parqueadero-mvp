"""Implementaciones con base de datos de los contratos del cobro (patrón Repository)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.cobro import Cobro
from app.domain.tarifa import Tarifa
from app.infrastructure import db


def _a_dominio(fila: db.CobroDB) -> Cobro:
    return Cobro(
        id=fila.id,
        placa=fila.placa,
        sede_id=fila.sede_id,
        dia_operativo=fila.dia_operativo,
        tipo_vehiculo=fila.tipo_vehiculo,
        tarifa_id=fila.tarifa_id,
        valor=fila.valor,
        estado=fila.estado,
        creado_en=fila.creado_en,
    )


class RepositorioCobrosSQL:
    def buscar_del_dia(self, placa: str, sede_id: int, dia: date) -> Cobro | None:
        with Session(db.motor_db()) as sesion:
            fila = sesion.scalars(
                select(db.CobroDB).where(
                    db.CobroDB.placa == placa,
                    db.CobroDB.sede_id == sede_id,
                    db.CobroDB.dia_operativo == dia,
                )
            ).first()
            return None if fila is None else _a_dominio(fila)

    def por_id(self, cobro_id: int) -> Cobro | None:
        with Session(db.motor_db()) as sesion:
            fila = sesion.get(db.CobroDB, cobro_id)
            return None if fila is None else _a_dominio(fila)

    def guardar(self, cobro: Cobro) -> Cobro:
        try:
            with Session(db.motor_db()) as sesion, sesion.begin():
                fila = db.CobroDB(
                    placa=cobro.placa,
                    sede_id=cobro.sede_id,
                    dia_operativo=cobro.dia_operativo,
                    tipo_vehiculo=cobro.tipo_vehiculo,
                    tarifa_id=cobro.tarifa_id,
                    valor=cobro.valor,
                    estado=cobro.estado,
                    creado_en=cobro.creado_en,
                )
                sesion.add(fila)
                sesion.flush()
                return cobro.con_id(fila.id)
        except IntegrityError:
            # Dos entradas casi simultáneas: la restricción única (F-03) dejó pasar solo una.
            existente = self.buscar_del_dia(cobro.placa, cobro.sede_id, cobro.dia_operativo)
            if existente is None:
                raise
            return existente


class ConsultaTarifasSQL:
    """Solo lectura. En el MVP las tarifas son las mismas para todas las sedes."""

    def vigente(self, sede_id: int, tipo: str, franja: str) -> Tarifa:
        with Session(db.motor_db()) as sesion:
            fila = sesion.scalars(
                select(db.TarifaDB).where(
                    db.TarifaDB.tipo_vehiculo == tipo, db.TarifaDB.franja == franja
                )
            ).one()
            return Tarifa(fila.id, fila.tipo_vehiculo, fila.franja, fila.valor)