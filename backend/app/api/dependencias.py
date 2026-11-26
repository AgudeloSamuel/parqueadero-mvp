from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.domain.usuario import Rol, Usuario
from app.infrastructure.db import buscar_usuario
from app.infrastructure.seguridad import Identidad, leer_identidad

bearer = HTTPBearer(auto_error=False)
CredencialesBearer = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def obtener_busqueda_usuarios() -> Callable[[str], Usuario | None]:
    return buscar_usuario


def identidad_actual(credenciales: CredencialesBearer) -> Identidad:
    try:
        if credenciales:
            return leer_identidad(credenciales.credentials)
    except (JWTError, ValueError):
        pass
    raise HTTPException(
        status_code=401,
        detail="Token ausente, inválido o vencido",
        headers={"WWW-Authenticate": "Bearer"},
    )


IdentidadActual = Annotated[Identidad, Depends(identidad_actual)]


def requiere_rol(rol: Rol) -> Callable[..., Rol]:
    def validar(identidad: IdentidadActual) -> Rol:
        if identidad.rol != rol:
            raise HTTPException(status_code=403, detail="Acceso denegado")
        return identidad.rol

    return validar
