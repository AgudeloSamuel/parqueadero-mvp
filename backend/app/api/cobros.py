from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi import Path as Ruta
from pydantic import BaseModel

from app.api import carril
from app.api.dependencias import requiere_rol
from app.application.pagar_cobro import CobroNoEncontrado, PagarCobro
from app.domain.cobro_estados import TransicionInvalida
from app.domain.pago import ClaveDeOtroCobro
from app.domain.usuario import Rol
from app.infrastructure.cobros import RepositorioCobrosSQL
from app.infrastructure.pagos import PagoEfectivoSQL

router = APIRouter(
    prefix="/cobros", tags=["Caja"], dependencies=[Depends(requiere_rol(Rol.OPERADOR))]
)


class PagoRegistrado(BaseModel):
    pago_id: int
    cobro_id: int
    valor: int
    estado_cobro: str
    pase_hasta: datetime


def obtener_pago() -> PagarCobro:
    return PagarCobro(
        cobros=RepositorioCobrosSQL(),
        pasarela=PagoEfectivoSQL(),
        ahora=carril.ahora_bogota,
    )


@router.post("/{cobro_id}/pagos", status_code=201)
def pagar_en_efectivo(
    cobro_id: Annotated[int, Ruta(gt=0, le=2_147_483_647)],
    clave: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=100)],
    pagos: Annotated[PagarCobro, Depends(obtener_pago)],
) -> PagoRegistrado:
    try:
        resultado = pagos.ejecutar(cobro_id, clave)
    except CobroNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TransicionInvalida, ClaveDeOtroCobro) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PagoRegistrado(
        pago_id=resultado.pago.id,
        cobro_id=resultado.pago.cobro_id,
        valor=resultado.pago.valor,
        estado_cobro=resultado.estado_cobro,
        pase_hasta=resultado.pase_hasta,
    )