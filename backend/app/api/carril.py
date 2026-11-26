import os
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencias import requiere_rol
from app.application.estado_salida import ConsultaSalida
from app.application.generar_cobro import ServicioCobro
from app.application.registrar_ingreso import (
    RegistrarIngreso,
    ResultadoIngreso,
    ValidarConfianza,
    ValidarCupo,
    ValidarHorario,
)
from app.application.registrar_salida import RegistrarSalida
from app.domain.ingreso import CobroEntrada, LecturaInvalida, TipoVehiculo
from app.domain.tarifa import TarifaPorFranja
from app.domain.usuario import Rol
from app.infrastructure import db
from app.infrastructure.cobros import ConsultaTarifasSQL, RepositorioCobrosSQL
from app.infrastructure.cupos import CuposSQL, Disponibilidad
from app.infrastructure.entradas import ultima_entrada_sin_salida
from app.infrastructure.eventos import guardar_entrada, guardar_salida
from app.infrastructure.lectores import FabricaLector, LectorCamaraDesactivado, OCRNoDisponible

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
    placa: str | None
    confianza: float
    sede_id: int
    fecha_hora: datetime
    tipo_vehiculo: TipoVehiculo | None
    barrera: Literal["ABIERTA", "CERRADA", "LLENO", "PENDIENTE_VALIDACION"]
    motivo: str
    cobro: CobroEntrada | None = None


class SolicitudSalida(BaseModel):
    placa: str = Field(min_length=1, max_length=80)
    sede_id: int = Field(gt=0, le=2_147_483_647)


class SalidaRegistrada(BaseModel):
    evento_id: int
    tipo_evento: Literal["SALIDA"] = "SALIDA"
    placa: str
    sede_id: int
    fecha_hora: datetime
    tipo_vehiculo: TipoVehiculo
    barrera: Literal["ABIERTA", "CERRADA"]
    motivo: str


def obtener_servicio_cobro(sesion: Session) -> ServicioCobro:
    """HU-04: cobro real. Cada tipo de vehículo tiene su estrategia de tarifa (Strategy)."""
    por_franja = TarifaPorFranja(ConsultaTarifasSQL(sesion))
    return ServicioCobro(
        repositorio=RepositorioCobrosSQL(sesion),
        estrategias={"CARRO": por_franja, "MOTO": por_franja},
    )


def ahora_bogota() -> datetime:
    return datetime.now(ZoneInfo("America/Bogota"))


def sesion_carril() -> Iterator[Session]:
    with Session(db.motor_db()) as sesion, sesion.begin():
        yield sesion


SesionCarril = Annotated[Session, Depends(sesion_carril, scope="function")]


@router.get("/cupos", dependencies=operador)
def consultar_cupos(
    sede_id: Annotated[int, Query(gt=0, le=2_147_483_647)],
    sesion: SesionCarril,
) -> list[Disponibilidad]:
    return CuposSQL(sesion).disponibles(sede_id)


def obtener_registro(sesion: SesionCarril) -> RegistrarIngreso:
    return RegistrarIngreso(
        guardar=lambda evento: guardar_entrada(evento, sesion),
        ahora=ahora_bogota,
        cobros=obtener_servicio_cobro(sesion),
        validaciones=(
            ValidarHorario(),
            ValidarConfianza(float(os.environ.get("UMBRAL_CONFIANZA", "0.80"))),
        ),
        validar_cupo=ValidarCupo(CuposSQL(sesion).hay_cupo),
    )


Registro = Annotated[RegistrarIngreso, Depends(obtener_registro)]


def obtener_registro_salida(sesion: SesionCarril) -> RegistrarSalida:
    consulta = ConsultaSalida(
        RepositorioCobrosSQL(sesion),
        lambda placa, sede_id: ultima_entrada_sin_salida(placa, sede_id, sesion),
    )
    return RegistrarSalida(
        consulta,
        lambda evento: guardar_salida(evento, sesion),
        ahora_bogota,
        CuposSQL(sesion).bloquear,
    )


@router.post("/salida", status_code=201, dependencies=operador)
def registrar_salida(
    datos: SolicitudSalida,
    registro: Annotated[RegistrarSalida, Depends(obtener_registro_salida)],
) -> SalidaRegistrada:
    try:
        evento_id, evento = registro.ejecutar(datos.placa, datos.sede_id)
    except LecturaInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SalidaRegistrada(
        evento_id=evento_id,
        placa=evento.placa,
        sede_id=evento.sede_id,
        fecha_hora=evento.fecha_hora,
        tipo_vehiculo=evento.tipo_vehiculo,
        barrera=evento.barrera,
        motivo=evento.motivo,
    )


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


@router.post("/entrada/imagen", status_code=201, dependencies=operador)
def entrada_imagen(
    imagen: Annotated[UploadFile, File()],
    sede_id: Annotated[int, Form(gt=0, le=2_147_483_647)],
    registro: Registro,
) -> EntradaRegistrada:
    contenido = imagen.file.read(MAX_IMAGEN + 1)
    if len(contenido) > MAX_IMAGEN:
        raise HTTPException(status_code=413, detail="La imagen supera los 5 MiB")
    try:
        lector = FabricaLector.para_imagen()
        return respuesta(registro.ejecutar(lector.leer(contenido, sede_id)))
    except LecturaInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LectorCamaraDesactivado as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except OCRNoDisponible as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@demo.get("/demo/carril", include_in_schema=False)
def demo_carril() -> FileResponse:
    return FileResponse(Path(__file__).with_name("carril_demo.html"), media_type="text/html")
