import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol


TipoVehiculo = Literal["CARRO", "MOTO"]


class LecturaInvalida(ValueError):
    pass


def normalizar_placa(placa: str) -> str:
    return re.sub(r"[\s-]+", "", placa).upper()


def clasificar_placa(placa: str) -> TipoVehiculo:
    if re.fullmatch(r"[A-Z]{3}[0-9]{3}", placa):
        return "CARRO"
    if re.fullmatch(r"[A-Z]{3}[0-9]{2}[A-Z]", placa):
        return "MOTO"
    raise LecturaInvalida("Formato de placa inválido")


@dataclass(frozen=True)
class LecturaPlaca:
    placa: str
    confianza: float
    sede_id: int


@dataclass(frozen=True)
class EventoEntrada:
    lectura: LecturaPlaca
    fecha_hora: datetime
    tipo_vehiculo: TipoVehiculo
    barrera: Literal["ABIERTA", "PENDIENTE_VALIDACION"]
    motivo: str


@dataclass(frozen=True)
class CobroEntrada:
    id: int
    valor: int
    estado: str


class ServicioCobroEntrada(Protocol):
    def generar_o_reutilizar(
        self, placa: str, tipo: str, sede_id: int, fecha_hora: datetime
    ) -> CobroEntrada | None: ...
