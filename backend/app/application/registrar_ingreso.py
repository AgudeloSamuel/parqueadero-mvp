from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
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
    barrera: Literal["ABIERTA", "PENDIENTE_VALIDACION"]
    motivo: str


class ValidarConfianza:
    def __init__(self, umbral: float) -> None:
        if not 0 <= umbral <= 1:
            raise ValueError("UMBRAL_CONFIANZA debe estar entre 0 y 1")
        self.umbral = umbral

    def __call__(self, lectura: LecturaPlaca) -> Decision | None:
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
        validaciones: tuple[Callable[[LecturaPlaca], Decision | None], ...],
    ) -> None:
        self.guardar = guardar
        self.ahora = ahora
        self.cobros = cobros
        self.validaciones = validaciones

    def ejecutar(self, lectura: LecturaPlaca) -> ResultadoIngreso:
        tipo = clasificar_placa(lectura.placa)
        decision = self._evaluar(lectura)
        fecha_hora = self.ahora()
        cobro = None
        if decision.barrera == "ABIERTA":
            cobro = self.cobros.generar_o_reutilizar(
                lectura.placa, tipo, lectura.sede_id, fecha_hora
            )
        evento = EventoEntrada(lectura, fecha_hora, tipo, decision.barrera, decision.motivo)
        return ResultadoIngreso(self.guardar(evento), evento, cobro)

    def _evaluar(self, lectura: LecturaPlaca) -> Decision:
        for validar in self.validaciones:
            decision = validar(lectura)
            if decision is not None:
                return decision
        return Decision("ABIERTA", "Ingreso registrado")
