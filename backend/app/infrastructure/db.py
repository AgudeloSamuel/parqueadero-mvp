import os
from datetime import date, datetime
from functools import lru_cache

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.domain.usuario import Rol, Usuario


class Base(DeclarativeBase):
    pass


class EventoDB(Base):
    __tablename__ = "eventos"
    __table_args__ = (
        CheckConstraint("confianza BETWEEN 0 AND 1", name="ck_eventos_confianza"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(16))
    placa: Mapped[str] = mapped_column(String(20))
    confianza: Mapped[float] = mapped_column(Float)
    sede_id: Mapped[int]
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tipo_vehiculo: Mapped[str] = mapped_column(String(12))
    barrera: Mapped[str] = mapped_column(String(24))
    motivo: Mapped[str] = mapped_column(String(160))
class TarifaDB(Base):
    __tablename__ = "tarifas"
    __table_args__ = (
        CheckConstraint("valor >= 0", name="ck_tarifas_valor"),
        CheckConstraint("franja IN ('DIURNA', 'NOCTURNA')", name="ck_tarifas_franja"),
        UniqueConstraint("tipo_vehiculo", "franja", name="uq_tarifas_tipo_franja"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo_vehiculo: Mapped[str] = mapped_column(String(12))
    franja: Mapped[str] = mapped_column(String(10))
    valor: Mapped[int]


class CobroDB(Base):
    __tablename__ = "cobros"
    __table_args__ = (
        CheckConstraint("valor >= 0", name="ck_cobros_valor"),
        UniqueConstraint("placa", "sede_id", "dia_operativo", name="uq_cobro_placa_sede_dia"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    placa: Mapped[str] = mapped_column(String(20))
    sede_id: Mapped[int]
    dia_operativo: Mapped[date] = mapped_column(Date)
    tipo_vehiculo: Mapped[str] = mapped_column(String(12))
    tarifa_id: Mapped[int] = mapped_column(ForeignKey("tarifas.id"))
    valor: Mapped[int]
    estado: Mapped[str] = mapped_column(String(12))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
class PagoDB(Base):
    __tablename__ = "pagos"
    __table_args__ = (
        CheckConstraint("valor >= 0", name="ck_pagos_valor"),
        UniqueConstraint("cobro_id", name="uq_pagos_cobro"),
        UniqueConstraint("clave_idempotencia", name="uq_pagos_clave"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cobro_id: Mapped[int] = mapped_column(ForeignKey("cobros.id"))
    valor: Mapped[int]
    clave_idempotencia: Mapped[str] = mapped_column(String(100))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UsuarioDB(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("rol IN ('OPERADOR', 'ADMIN')", name="ck_usuarios_rol"),
    )

    username: Mapped[str] = mapped_column(String(100), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(60))
    rol: Mapped[str] = mapped_column(String(8))


@lru_cache
def motor_db() -> Engine:
    url = os.environ.get("DATABASE_URL") or URL.create(
        "postgresql+psycopg2",
        username=os.environ.get("POSTGRES_USER", "parqueadero"),
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        database=os.environ.get("POSTGRES_DB", "parqueadero"),
    )
    return create_engine(url, pool_pre_ping=True)


def buscar_usuario(username: str) -> Usuario | None:
    with Session(motor_db()) as sesion:
        fila = sesion.get(UsuarioDB, username)
        if fila is None:
            return None
        return Usuario(fila.username, fila.password_hash, Rol(fila.rol))
