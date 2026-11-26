from datetime import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Path as Ruta
from pydantic import BaseModel, Field

from app.api.dependencias import requiere_rol
from app.application.administrar_tarifas import AdministrarTarifas, TipoSinTarifas
from app.domain.tarifa import APERTURA, CIERRE, FranjaInvalida, Tarifa, TarifaInvalida
from app.domain.usuario import Rol
from app.infrastructure.tarifas import AdministracionTarifasSQL, HorarioFranjasSQL

router = APIRouter(
    prefix="/admin", tags=["Administración"], dependencies=[Depends(requiere_rol(Rol.ADMIN))]
)


class TarifaVista(BaseModel):
    id: int
    tipo_vehiculo: str
    franja: str
    valor: int


class CambioTarifas(BaseModel):
    diurna: int = Field(ge=0, examples=[3850])
    nocturna: int = Field(ge=0, examples=[1800])


class Franjas(BaseModel):
    diurna_desde: time
    diurna_hasta: time
    nocturna_desde: time
    nocturna_hasta: time


class CambioFranjas(BaseModel):
    inicio_nocturna: time = Field(examples=["17:30"])


def obtener_administracion() -> AdministrarTarifas:
    return AdministrarTarifas(AdministracionTarifasSQL(), HorarioFranjasSQL())


Administracion = Annotated[AdministrarTarifas, Depends(obtener_administracion)]


def vista(tarifas: list[Tarifa]) -> list[TarifaVista]:
    return [TarifaVista(**t.__dict__) for t in tarifas]


def franjas(inicio_nocturna: time) -> Franjas:
    minutos = inicio_nocturna.hour * 60 + inicio_nocturna.minute - 1
    return Franjas(
        diurna_desde=APERTURA,
        diurna_hasta=time(minutos // 60, minutos % 60),
        nocturna_desde=inicio_nocturna,
        nocturna_hasta=CIERRE,
    )


@router.get("/tarifas")
def listar_tarifas(administracion: Administracion) -> list[TarifaVista]:
    return vista(administracion.listar())


@router.put("/tarifas/{tipo}")
def cambiar_tarifas(
    tipo: Annotated[str, Ruta(min_length=1, max_length=12, examples=["CARRO"])],
    cambio: CambioTarifas,
    administracion: Administracion,
) -> list[TarifaVista]:
    try:
        return vista(administracion.cambiar_tarifas(tipo, cambio.diurna, cambio.nocturna))
    except TarifaInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except TipoSinTarifas as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/franjas")
def ver_franjas(administracion: Administracion) -> Franjas:
    return franjas(administracion.inicio_nocturna())


@router.put("/franjas")
def cambiar_franjas(cambio: CambioFranjas, administracion: Administracion) -> Franjas:
    try:
        return franjas(administracion.cambiar_inicio_nocturna(cambio.inicio_nocturna))
    except FranjaInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc