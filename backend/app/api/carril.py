import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api.dependencias import requiere_rol
from app.application.registrar_ingreso import RegistrarIngreso, ResultadoIngreso, ValidarConfianza
from app.domain.ingreso import CobroEntrada, LecturaInvalida, TipoVehiculo
from app.domain.usuario import Rol
from app.infrastructure.eventos import guardar_entrada
from app.infrastructure.lectores import FabricaLector, OCRNoDisponible

router = APIRouter(prefix="/carril", tags=["Carril"])
demo = APIRouter()
operador = [Depends(requiere_rol(Rol.OPERADOR))]
MAX_IMAGEN = 5 * 1024 * 1024


class EntradaSimulada(BaseModel):
    placa: str = Field(min_length=1, max_length=80)
    confianza: float = Field(ge=0, le=1)
    sede_id: int = Field(gt=0, le=2_147_483_647)


class EntradaRegistrada(BaseModel):
    evento_id: int
    tipo_evento: Literal["ENTRADA"] = "ENTRADA"
    placa: str
    confianza: float
    sede_id: int
    fecha_hora: datetime
    tipo_vehiculo: TipoVehiculo
    barrera: Literal["ABIERTA", "PENDIENTE_VALIDACION"]
    motivo: str
    cobro: CobroEntrada | None = None


class CobroSimulado:
    def generar_o_reutilizar(
        self, placa: str, tipo: str, sede_id: int, fecha_hora: datetime
    ) -> None:
        """Deja el ingreso disponible mientras HU-04 implementa el cobro."""
        return None


def obtener_registro() -> RegistrarIngreso:
    return RegistrarIngreso(
        guardar=guardar_entrada,
        ahora=lambda: datetime.now(ZoneInfo("America/Bogota")),
        cobros=CobroSimulado(),
        validaciones=(ValidarConfianza(float(os.environ.get("UMBRAL_CONFIANZA", "0.80"))),),
    )


Registro = Annotated[RegistrarIngreso, Depends(obtener_registro)]


def respuesta(resultado: ResultadoIngreso) -> EntradaRegistrada:
    evento = resultado.evento
    return EntradaRegistrada(
        evento_id=resultado.evento_id,
        placa=evento.lectura.placa,
        confianza=evento.lectura.confianza,
        sede_id=evento.lectura.sede_id,
        fecha_hora=evento.fecha_hora,
        tipo_vehiculo=evento.tipo_vehiculo,
        barrera=evento.barrera,
        motivo=evento.motivo,
        cobro=resultado.cobro,
    )


@router.post("/entrada", status_code=201, dependencies=operador, response_model_exclude_none=True)
def entrada_simulada(datos: EntradaSimulada, registro: Registro) -> EntradaRegistrada:
    try:
        lector = FabricaLector.crear("simulador")
        return respuesta(registro.ejecutar(lector.leer(datos.placa, datos.confianza, datos.sede_id)))
    except LecturaInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/entrada/imagen", status_code=201, dependencies=operador, response_model_exclude_none=True
)
def entrada_imagen(
    imagen: Annotated[UploadFile, File()],
    sede_id: Annotated[int, Form(gt=0, le=2_147_483_647)],
    registro: Registro,
) -> EntradaRegistrada:
    contenido = imagen.file.read(MAX_IMAGEN + 1)
    if len(contenido) > MAX_IMAGEN:
        raise HTTPException(status_code=413, detail="La imagen supera los 5 MiB")
    try:
        lector = FabricaLector.crear("imagen")
        return respuesta(registro.ejecutar(lector.leer(contenido, sede_id)))
    except LecturaInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OCRNoDisponible as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@demo.get("/demo/carril", include_in_schema=False)
def demo_carril() -> FileResponse:
    return FileResponse(Path(__file__).with_name("carril_demo.html"), media_type="text/html")
