from dataclasses import dataclass
from enum import StrEnum


class Rol(StrEnum):
    OPERADOR = "OPERADOR"
    ADMIN = "ADMIN"


@dataclass(frozen=True)
class Usuario:
    username: str
    password_hash: str
    rol: Rol
