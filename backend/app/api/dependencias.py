from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.domain.usuario import Rol, Usuario
from app.infrastructure.db import buscar_usuario
from app.infrastructure.seguridad import leer_rol

bearer = HTTPBearer(auto_error=False)
CredencialesBearer = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def obtener_busqueda_usuarios() -> Callable[[str], Usuario | None]:
    return buscar_usuario


def requiere_rol(rol: Rol) -> Callable[..., Rol]:
    def validar(credenciales: CredencialesBearer) -> Rol:
        try:
            rol_actual = leer_rol(credenciales.credentials) if credenciales else None
        except (JWTError, ValueError):
            rol_actual = None
        if rol_actual is None:
            raise HTTPException(
                status_code=401,
                detail="Token ausente, inválido o vencido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if rol_actual != rol:
            raise HTTPException(status_code=403, detail="Acceso denegado")
        return rol_actual

    return validar
