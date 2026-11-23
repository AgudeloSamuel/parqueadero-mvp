from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencias import obtener_busqueda_usuarios
from app.application.autenticacion import autenticar
from app.domain.usuario import Rol, Usuario
from app.infrastructure.seguridad import emitir_token, verificar_password

router = APIRouter(prefix="/auth", tags=["Autenticación"])


class Credenciales(BaseModel):
    username: str = Field(max_length=100)
    password: str


class RespuestaLogin(BaseModel):
    access_token: str
    rol: Rol


@router.post("/login")
def login(
    datos: Credenciales,
    buscar: Annotated[Callable[[str], Usuario | None], Depends(obtener_busqueda_usuarios)],
) -> RespuestaLogin:
    usuario = autenticar(datos.username, datos.password, buscar, verificar_password)
    if usuario is None:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    return RespuestaLogin(access_token=emitir_token(usuario), rol=usuario.rol)
