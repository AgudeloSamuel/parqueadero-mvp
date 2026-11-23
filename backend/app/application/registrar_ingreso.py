from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time
from typing import Literal

from app.domain.ingreso import (
    CobroEntrada,
    EventoEntrada,
    LecturaPlaca,
    ServicioCobroEntrada,
    clasificar_placa,
)


@dataclass(frozen=True)
class Decision:
    barrera: Literal["ABIERTA", "CERRADA", "PENDIENTE_VALIDACION"]
    motivo: str


class ValidarHorario:
    """Permite el ingreso desde las 04:00 hasta el final del día en Bogotá."""

    def __call__(self, lectura: LecturaPlaca, fecha_hora: datetime) -> Decision | None:
        if fecha_hora.time() < time(4):
            return Decision("CERRADA", "Parqueadero cerrado")
        return None


class ValidarConfianza:
    def __init__(self, umbral: float) -> None:
        if not 0 <= umbral <= 1:
            raise ValueError("UMBRAL_CONFIANZA debe estar entre 0 y 1")
        self.umbral = umbral

    def __call__(self, lectura: LecturaPlaca, fecha_hora: datetime) -> Decision | None:
        if lectura.confianza < self.umbral:
            return Decision("PENDIENTE_VALIDACION", "Confianza insuficiente")
        return None


@dataclass(frozen=True)
class ResultadoIngreso:
    evento_id: int
    evento: EventoEntrada
    cobro: CobroEntrada | None


class RegistrarIngreso:
    def __init__(
        self,
        guardar: Callable[[EventoEntrada], int],
        ahora: Callable[[], datetime],
        cobros: ServicioCobroEntrada,
        validaciones: tuple[Callable[[LecturaPlaca, datetime], Decision | None], ...],
    ) -> None:
        self.guardar = guardar
        self.ahora = ahora
        self.cobros = cobros
        self.validaciones = validaciones

    def ejecutar(self, lectura: LecturaPlaca) -> ResultadoIngreso:
        tipo = clasificar_placa(lectura.placa)
        fecha_hora = self.ahora()
        decision = self._evaluar(lectura, fecha_hora)
        cobro = None
        if decision.barrera == "ABIERTA":
            cobro = self.cobros.generar_o_reutilizar(
                lectura.placa, tipo, lectura.sede_id, fecha_hora
            )
        evento = EventoEntrada(lectura, fecha_hora, tipo, decision.barrera, decision.motivo)
        return ResultadoIngreso(self.guardar(evento), evento, cobro)

    def _evaluar(self, lectura: LecturaPlaca, fecha_hora: datetime) -> Decision:
        for validar in self.validaciones:
            decision = validar(lectura, fecha_hora)
            if decision is not None:
                return decision
        return Decision("ABIERTA", "Ingreso registrado")
