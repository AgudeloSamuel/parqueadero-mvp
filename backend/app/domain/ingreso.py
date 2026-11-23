from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from app.domain.vehiculo import Clasificador, normalizar_placa  # noqa: F401 (lectores.py la importa desde aquí)

TipoVehiculo = Literal["CARRO", "MOTO"]

_clasificador = Clasificador()


class LecturaInvalida(ValueError):
    pass


def clasificar_placa(placa: str) -> TipoVehiculo:
    """Usa el Clasificador de la HU-03; si la placa no tiene un formato conocido, la lectura es inválida."""
    tipo = _clasificador.clasificar(placa)
    if tipo is None:
        raise LecturaInvalida("Formato de placa inválido")
    return tipo


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
    barrera: Literal["ABIERTA", "CERRADA", "PENDIENTE_VALIDACION"]
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