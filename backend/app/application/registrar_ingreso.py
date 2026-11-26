from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time
from typing import Literal

from app.domain.ingreso import (
    CobroEntrada,
    EventoEntrada,
    LecturaPlaca,
    ServicioCobroEntrada,
    TipoVehiculo,
    clasificar_placa,
)


@dataclass(frozen=True)
class Decision:
    barrera: Literal["ABIERTA", "CERRADA", "LLENO", "PENDIENTE_VALIDACION"]
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
        if lectura.validada_por is None and lectura.placa is not None and lectura.confianza < self.umbral:
            return Decision("PENDIENTE_VALIDACION", "Confianza insuficiente")
        return None


class ValidarCupo:
    def __init__(self, hay_cupo: Callable[[int, TipoVehiculo], bool]) -> None:
        self.hay_cupo = hay_cupo

    def __call__(self, sede_id: int, tipo: TipoVehiculo) -> Decision | None:
        if not self.hay_cupo(sede_id, tipo):
            return Decision("LLENO", f"No hay cupos disponibles para {tipo.lower()}s")
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
        validar_cupo: ValidarCupo,
        bloquear_cupo: Callable[[TipoVehiculo], int],
    ) -> None:
        self.guardar = guardar
        self.ahora = ahora
        self.cobros = cobros
        self.validaciones = validaciones
        self.validar_cupo = validar_cupo
        self.bloquear_cupo = bloquear_cupo

    def ejecutar(
        self, lectura: LecturaPlaca, *, guardar: Callable[[EventoEntrada], int] | None = None
    ) -> ResultadoIngreso:
        placa = lectura.placa
        tipo = clasificar_placa(placa) if placa is not None else None
        if tipo is not None:
            self.bloquear_cupo(tipo)
        fecha_hora = self.ahora()
        decision = self._evaluar(lectura, fecha_hora)
        cobro = None
        if decision.barrera == "ABIERTA" and placa is not None and tipo is not None:
            rechazo = self.validar_cupo(lectura.sede_id, tipo)
            if rechazo is None:
                cobro = self.cobros.generar_o_reutilizar(placa, tipo, lectura.sede_id, fecha_hora)
            else:
                decision = rechazo
        evento = EventoEntrada(lectura, fecha_hora, tipo, decision.barrera, decision.motivo)
        return ResultadoIngreso((guardar or self.guardar)(evento), evento, cobro)

    def _evaluar(self, lectura: LecturaPlaca, fecha_hora: datetime) -> Decision:
        for validar in self.validaciones:
            decision = validar(lectura, fecha_hora)
            if decision is not None:
                return decision
        if lectura.placa is None:
            return Decision("PENDIENTE_VALIDACION", "No se encontró una placa válida en la imagen")
        return Decision(
            "ABIERTA", "Lectura manual validada" if lectura.validada_por else "Ingreso registrado"
        )
