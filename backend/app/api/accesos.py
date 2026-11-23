from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencias import requiere_rol
from app.domain.usuario import Rol

solo_admin = [Depends(requiere_rol(Rol.ADMIN))]
admin = APIRouter(prefix="/admin", tags=["Administración"], dependencies=solo_admin)
consultas = APIRouter(prefix="/consultas", tags=["Consultas"], dependencies=solo_admin)


@admin.get("/acceso")
@consultas.get("/acceso")
def comprobar_acceso() -> dict[str, str]:
    return {"rol": Rol.ADMIN}


@admin.get("/tarifas")
def tarifas() -> None:
    raise HTTPException(status_code=501, detail="La gestión de tarifas se implementa en HU-09")
