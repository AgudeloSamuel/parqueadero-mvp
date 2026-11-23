import os
from functools import lru_cache

from sqlalchemy import CheckConstraint, String, create_engine
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.domain.usuario import Rol, Usuario


class Base(DeclarativeBase):
    pass


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
