import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import jwt

from app.domain.usuario import Rol, Usuario

ALGORITMO = "HS256"


def hash_password(password: str) -> str:
    datos = password.encode()
    if not 1 <= len(datos) <= 72:
        raise ValueError("La contraseña debe ocupar entre 1 y 72 bytes.")
    return bcrypt.hashpw(datos, bcrypt.gensalt()).decode("ascii")


def verificar_password(password: str, password_hash: str) -> bool:
    datos = password.encode()
    return len(datos) <= 72 and bcrypt.checkpw(datos, password_hash.encode("ascii"))


def clave_jwt() -> str:
    clave = os.environ.get("JWT_SECRET", "")
    if len(clave.encode()) < 32:
        raise RuntimeError("Configura JWT_SECRET con al menos 32 bytes.")
    return clave


def emitir_token(usuario: Usuario) -> str:
    return jwt.encode(
        {
            "sub": usuario.username,
            "rol": usuario.rol.value,
            "exp": datetime.now(UTC) + timedelta(minutes=30),
        },
        clave_jwt(),
        algorithm=ALGORITMO,
    )


@dataclass(frozen=True)
class Identidad:
    username: str
    rol: Rol


def leer_identidad(token: str) -> Identidad:
    datos = jwt.decode(
        token,
        clave_jwt(),
        algorithms=[ALGORITMO],
        options={"require_exp": True, "require_sub": True},
    )
    username = datos["sub"]
    if not username.strip() or len(username) > 100:
        raise ValueError("Usuario del token inválido")
    return Identidad(username, Rol(datos.get("rol")))
